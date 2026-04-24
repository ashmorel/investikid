from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.main import limiter
from app.core.security import (
    create_token,
    decode_token,
    get_token_from_cookie,
    hash_password,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.user import User, UserProgress
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(httponly=True, samesite="lax")


def _set_auth_cookies(response: Response, user_id: str, secure: bool) -> None:
    access = create_token(
        {"sub": user_id},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh = create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    response.set_cookie(
        "access_token", access,
        max_age=settings.access_token_expire_minutes * 60,
        secure=secure, **_COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token", refresh,
        max_age=settings.refresh_token_expire_days * 86400,
        secure=secure, **_COOKIE_OPTS,
    )


@router.post("/register", response_model=UserProfile, status_code=201)
async def register(
    request: Request,
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        dob=payload.dob,
        country_code=payload.country_code,
        currency_code=payload.currency_code,
        topic_path=payload.topic_path,
        parent_email=str(payload.parent_email) if payload.parent_email else None,
    )
    session.add(user)
    await session.flush()

    session.add(UserProgress(user_id=user.id))
    session.add(AuditLog(
        user_id=user.id,
        event_type="register",
        ip_address=request.client.host if request.client else None,
    ))
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
    user = await session.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    secure = settings.environment != "development"
    _set_auth_cookies(response, str(user.id), secure)
    session.add(AuditLog(
        user_id=user.id,
        event_type="login",
        ip_address=request.client.host if request.client else None,
    ))
    await session.commit()
    return TokenResponse()


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    secure = settings.environment != "development"
    _set_auth_cookies(response, payload["sub"], secure)
    return TokenResponse()
