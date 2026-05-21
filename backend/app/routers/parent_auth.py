from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.auth import _set_csrf_cookie
from app.schemas.parent import ParentMagicLinkRequest
from app.services.email import get_email_sender
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
    await session.commit()

    parent_session_token = issue_parent_session(record.email)
    secure = settings.environment != "development"
    response.set_cookie(
        _PARENT_COOKIE, parent_session_token,
        max_age=7 * 86400, httponly=True, samesite="lax", secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)
    return {"status": "signed_in", "email": record.email}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(_PARENT_COOKIE, path="/")
    return {"status": "ok"}


async def get_current_parent(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> str:
    """Returns the parent email from a valid session cookie."""
    token = request.cookies.get(_PARENT_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_parent_session(token)
    except TokenInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
