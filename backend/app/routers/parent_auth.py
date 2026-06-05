import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.parent_identity import ParentIdentity
from app.models.parent_session import ParentSession
from app.models.user import User
from app.routers.auth import _cookie_samesite, _set_csrf_cookie
from app.schemas.parent import IdentityOut, OAuthSignInRequest, ParentMagicLinkRequest
from app.services.email import get_email_sender
from app.services.oidc import OidcError, OidcNotConfigured, verify_id_token
from app.services.tokens import (
    PARENT_MAGIC_AUDIENCE,
    PARENT_MAGIC_EXPIRY,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    consume_one_time_token,
    decode_parent_session,
    issue_one_time_token,
    issue_parent_session,
    revoke_parent_session,
)

router = APIRouter(prefix="/parent/auth", tags=["parent_auth"])

_PARENT_COOKIE = "parent_session"


@router.post("/request", status_code=202)
@limiter.limit("5/hour")
async def request_magic_link(
    request: Request,  # noqa: ARG001  -- required by slowapi
    payload: ParentMagicLinkRequest,
    session: AsyncSession = Depends(get_session),
):
    match = await session.scalar(
        select(User).where(User.parent_email == str(payload.email)).limit(1)
    )
    if match is None:
        return {"status": "queued"}

    token = await issue_one_time_token(
        session, purpose=PARENT_MAGIC_AUDIENCE, email=str(payload.email),
        subject_id=None, expires_in=PARENT_MAGIC_EXPIRY,
    )
    link = f"{settings.app_base_url}/parent/auth/callback?token={token}"
    await get_email_sender().send(
        session, str(payload.email), "parent_magic_link", {"link": link},
        subject_id=None,
    )
    await session.commit()
    return {"status": "queued"}


@router.get("/callback", status_code=200)
async def magic_callback(
    token: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    try:
        record = await consume_one_time_token(session, token, PARENT_MAGIC_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired")

    parent_session_token = await issue_parent_session(session, record.email)
    await session.commit()

    secure = settings.environment != "development"
    response.set_cookie(
        _PARENT_COOKIE, parent_session_token,
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)
    return {"status": "signed_in", "email": record.email}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(_PARENT_COOKIE)
    if token:
        try:
            _email, jti = decode_parent_session(token)
        except TokenInvalid:
            jti = None
        if jti is not None:
            await revoke_parent_session(session, jti)
            await session.commit()
    secure = settings.environment != "development"
    response.delete_cookie(
        _PARENT_COOKIE,
        samesite=_cookie_samesite(),
        secure=secure,
        httponly=True,
        path="/",
    )
    return {"status": "ok"}


_OAUTH_PROVIDERS = {"google", "apple"}


async def _set_parent_cookies(
    session: AsyncSession, response: Response, email: str
) -> None:
    secure = settings.environment != "development"
    token = await issue_parent_session(session, email)
    await session.commit()
    response.set_cookie(
        _PARENT_COOKIE, token,
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)


@router.post("/oauth/{provider}", status_code=200)
@limiter.limit("10/hour")
async def oauth_sign_in(
    request: Request,  # noqa: ARG001  -- required by slowapi
    provider: str,
    payload: OAuthSignInRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    try:
        identity = await verify_id_token(provider, payload.id_token, payload.nonce)
    except OidcNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Provider not configured")
    except OidcError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sign-in")

    link = await session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider,
            ParentIdentity.provider_subject == identity.sub,
        ).limit(1)
    )
    parent_email: str | None = link.parent_email if link else None

    if parent_email is None and identity.email and identity.email_verified:
        match = await session.scalar(select(User).where(User.parent_email == identity.email).limit(1))
        if match is not None:
            parent_email = identity.email
            session.add(ParentIdentity(
                id=uuid.uuid4(), provider=provider, provider_subject=identity.sub,
                parent_email=parent_email, created_at=datetime.now(UTC),
            ))
            await session.commit()

    if parent_email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No parent account for this sign-in")

    await _set_parent_cookies(session, response, parent_email)
    return {"status": "signed_in", "email": parent_email}


async def get_current_parent(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> str:
    """Returns the parent email from a valid, non-revoked, unexpired session cookie."""
    token = request.cookies.get(_PARENT_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        email, jti = decode_parent_session(token)
    except TokenInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    row = await session.scalar(
        select(ParentSession).where(ParentSession.jti == jti).limit(1)
    )
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return email


@router.post("/oauth/{provider}/link", status_code=200)
async def link_provider(
    provider: str,
    payload: OAuthSignInRequest,
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    try:
        identity = await verify_id_token(provider, payload.id_token, payload.nonce)
    except OidcNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Provider not configured")
    except OidcError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    existing = await session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider,
            ParentIdentity.provider_subject == identity.sub,
        ).limit(1)
    )
    if existing is None:
        session.add(ParentIdentity(
            id=uuid.uuid4(), provider=provider, provider_subject=identity.sub,
            parent_email=parent_email, created_at=datetime.now(UTC),
        ))
        await session.commit()
    elif existing.parent_email != parent_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked to another account")
    return {"status": "linked", "provider": provider}


@router.delete("/oauth/{provider}/link", status_code=200)
async def unlink_provider(
    provider: str,
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    rows = (await session.scalars(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider,
            ParentIdentity.parent_email == parent_email,
        )
    )).all()
    for row in rows:
        await session.delete(row)
    await session.commit()
    return {"status": "unlinked", "provider": provider}


@router.get("/identities", response_model=list[IdentityOut])
async def list_identities(
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    rows = (await session.scalars(
        select(ParentIdentity).where(ParentIdentity.parent_email == parent_email)
    )).all()
    return [IdentityOut(provider=r.provider, parent_email=r.parent_email) for r in rows]


