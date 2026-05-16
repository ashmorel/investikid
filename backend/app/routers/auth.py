import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.core.security import (
    create_token,
    decode_token,
    dummy_verify,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.user import RefreshToken, User, UserProgress
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    PendingConsentResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserProfile
from app.services.compliance import resolve_policy
from app.services.consent_service import age_in_years
from app.services.email import get_email_sender
from app.services.tokens import (
    CONSENT_AUDIENCE,
    CONSENT_EXPIRY,
    VERIFY_EMAIL_AUDIENCE,
    VERIFY_EMAIL_EXPIRY,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    consume_one_time_token,
    issue_one_time_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(httponly=True, samesite="lax")

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _set_access_cookie(response: Response, user_id: str, secure: bool) -> None:
    access = create_token(
        {"sub": user_id},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    response.set_cookie(
        "access_token", access,
        max_age=settings.access_token_expire_minutes * 60,
        secure=secure, path="/", **_COOKIE_OPTS,
    )


async def _issue_refresh_token(
    session: AsyncSession,
    response: Response,
    user_id: uuid.UUID,
    secure: bool,
) -> None:
    jti = uuid.uuid4()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    session.add(RefreshToken(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at,
    ))
    token = create_token(
        {"sub": str(user_id), "type": "refresh", "jti": str(jti)},
        timedelta(days=settings.refresh_token_expire_days),
    )
    response.set_cookie(
        "refresh_token", token,
        max_age=settings.refresh_token_expire_days * 86400,
        secure=secure, path="/", **_COOKIE_OPTS,
    )


def _set_csrf_cookie(response: Response, secure: bool) -> None:
    response.set_cookie(
        "csrf_token", generate_csrf_token(),
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,  # JS must read it
        samesite="lax",
        secure=secure,
        path="/",
    )


@router.post("/register", response_model=UserProfile | PendingConsentResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if payload.email:
        existing = await session.scalar(select(User).where(User.email == payload.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_username = await session.scalar(
        select(User).where(User.username == payload.username)
    )
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    today = date.today()
    policy = resolve_policy(payload.country_code, payload.dob, today)
    needs_consent = policy.requires_parental_consent

    if needs_consent and not payload.parent_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent email required for users under the consent threshold",
        )
    if not needs_consent and not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email required for self-managed accounts",
        )

    now = datetime.now(UTC)
    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        dob=payload.dob,
        country_code=payload.country_code,
        currency_code=payload.currency_code,
        topic_path=payload.topic_path,
        parent_email=str(payload.parent_email) if payload.parent_email else None,
        is_active=not needs_consent,
        policy_version_accepted=payload.policy_version_accepted,
        policy_accepted_at=now if payload.policy_version_accepted else None,
    )
    session.add(user)
    await session.flush()

    session.add(UserProgress(user_id=user.id))
    session.add(AuditLog(
        user_id=user.id,
        event_type="register",
        ip_address=request.client.host if request.client else None,
    ))

    if needs_consent:
        age = age_in_years(payload.dob, today)
        token = await issue_one_time_token(
            session, purpose=CONSENT_AUDIENCE,
            email=str(payload.parent_email), subject_id=user.id,
            expires_in=CONSENT_EXPIRY,
        )
        link = f"{settings.app_base_url}/consent/verify?token={token}"
        await get_email_sender().send(
            session, str(payload.parent_email), "consent_request",
            {
                "child_username": user.username,
                "age": age,
                "country_code": user.country_code,
                "link": link,
            },
        )
        await session.commit()
        return PendingConsentResponse(user_id=user.id)

    verify_token = await issue_one_time_token(
        session, purpose=VERIFY_EMAIL_AUDIENCE,
        email=str(payload.email), subject_id=user.id,
        expires_in=VERIFY_EMAIL_EXPIRY,
    )
    verify_link = f"{settings.app_base_url}/verify-email?token={verify_token}"
    await get_email_sender().send(
        session, str(payload.email), "verify_email",
        {"username": user.username, "link": verify_link},
    )

    secure = settings.environment != "development"
    _set_access_cookie(response, str(user.id), secure)
    await _issue_refresh_token(session, response, user.id, secure)
    _set_csrf_cookie(response, secure)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    ident = payload.email
    user = await session.scalar(
        select(User).where((User.email == ident) | (User.username == ident))
    )
    if not user:
        # Equalise timing against the wrong-password branch.
        dummy_verify()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    now = datetime.now(UTC)

    if not user.is_active:
        if user.parent_consent_given_at is None and user.consent_declined_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account pending parental consent",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account access denied"
        )

    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + LOCKOUT_DURATION
            user.failed_login_count = 0
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.failed_login_count > 0 or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None

    secure = settings.environment != "development"
    _set_access_cookie(response, str(user.id), secure)
    await _issue_refresh_token(session, response, user.id, secure)
    _set_csrf_cookie(response, secure)
    session.add(AuditLog(
        user_id=user.id,
        event_type="login",
        ip_address=request.client.host if request.client else None,
    ))
    await session.commit()
    return TokenResponse()


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    secure = settings.environment != "development"
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_token(token, expected_type="refresh")
            jti_str = payload.get("jti")
            if jti_str:
                jti = uuid.UUID(jti_str)
                rt = await session.scalar(
                    select(RefreshToken).where(RefreshToken.jti == jti)
                )
                if rt is not None and rt.revoked_at is None:
                    rt.revoked_at = datetime.now(UTC)
                    await session.commit()
        except Exception:
            # Logout is best-effort; still clear cookies.
            pass
    response.delete_cookie(
        "access_token", httponly=True, samesite="lax", secure=secure, path="/"
    )
    response.delete_cookie(
        "refresh_token", httponly=True, samesite="lax", secure=secure, path="/"
    )
    response.delete_cookie(
        "csrf_token", httponly=False, samesite="lax", secure=secure, path="/"
    )
    return {"message": "logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(token, expected_type="refresh")

    jti_str = payload.get("jti")
    sub = payload.get("sub")
    if not jti_str or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        jti = uuid.UUID(jti_str)
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    rt = await session.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    now = datetime.now(UTC)
    if rt is None or rt.revoked_at is not None or rt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # Compare as aware datetimes.
    expires_at = rt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    rt.revoked_at = now

    secure = settings.environment != "development"
    _set_access_cookie(response, str(user_id), secure)
    await _issue_refresh_token(session, response, user_id, secure)
    _set_csrf_cookie(response, secure)
    await session.commit()
    return TokenResponse()


@router.get("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    try:
        row = await consume_one_time_token(session, token, VERIFY_EMAIL_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed) as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired") from exc
    user = await session.get(User, row.subject_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account not found")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
    await session.commit()
    return {"status": "ok"}


@router.post("/verify-email/resend")
@limiter.limit("3/hour")
async def resend_verify_email(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    from app.routers.users import get_current_user
    user = await get_current_user(request, session)
    if user.email and user.email_verified_at is None:
        token = await issue_one_time_token(
            session, purpose=VERIFY_EMAIL_AUDIENCE, email=user.email,
            subject_id=user.id, expires_in=VERIFY_EMAIL_EXPIRY,
        )
        link = f"{settings.app_base_url}/verify-email?token={token}"
        await get_email_sender().send(
            session, user.email, "verify_email",
            {"username": user.username, "link": link},
        )
        await session.commit()
    return {"status": "accepted"}


@router.post("/forgot-password", status_code=202)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY
    ident = payload.email
    user = await session.scalar(
        select(User).where((User.email == ident) | (User.username == ident))
    )
    if user and user.deleted_at is None and (user.is_active or user.parent_email):
        today = date.today()
        policy = resolve_policy(user.country_code, user.dob, today)
        if policy.password_reset_mode == "parent":
            recipient = user.parent_email
        else:
            recipient = user.email
        if recipient:
            token = await issue_one_time_token(
                session, purpose=PASSWORD_RESET_AUDIENCE, email=recipient,
                subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
            )
            link = f"{settings.app_base_url}/reset-password?token={token}"
            await get_email_sender().send(
                session, recipient, "password_reset", {"link": link},
            )
            await session.commit()
    return {"status": "accepted"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.services.tokens import PASSWORD_RESET_AUDIENCE
    try:
        row = await consume_one_time_token(session, payload.token, PASSWORD_RESET_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed) as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired") from exc
    user = await session.get(User, row.subject_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account not found")
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_count = 0
    user.locked_until = None
    now = datetime.now(UTC)
    tokens = await session.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    )
    for t in tokens:
        t.revoked_at = now
    await session.commit()
    return {"status": "ok"}
