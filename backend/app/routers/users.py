import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token, get_token_from_cookie
from app.models.push_device import PushDevice
from app.models.user import User, UserProgress
from app.schemas.user import (
    DailyGoalUpdate,
    UpdateLanguageRequest,
    UpdatePreferencesRequest,
    UserProfile,
    UserProgressOut,
)
from app.services.export_service import build_user_export

router = APIRouter(prefix="/users", tags=["users"])


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = get_token_from_cookie(request)
    payload = decode_token(token, expected_type=None)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


async def _is_parent(session: AsyncSession, user: User) -> bool:
    if user.email_verified_at is None or not user.email:
        return False
    found = await session.scalar(
        select(User.id)
        .where(User.parent_email == user.email, User.deleted_at.is_(None))
        .limit(1)
    )
    return found is not None


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = UserProfile.model_validate(current_user)
    profile.is_parent = await _is_parent(session, current_user)
    return profile


@router.patch("/me", response_model=UserProfile)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # country_code is fixed at registration (consent regime) and not updatable here.
    if payload.currency_code is not None:
        current_user.currency_code = payload.currency_code
    if payload.topic_path is not None:
        current_user.topic_path = payload.topic_path
    if payload.content_region is not None:
        current_user.content_region = payload.content_region
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.patch("/me/language", response_model=UserProfile)
async def update_language(
    payload: UpdateLanguageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    current_user.language = payload.language
    await session.commit()
    await session.refresh(current_user)
    profile = UserProfile.model_validate(current_user)
    profile.is_parent = await _is_parent(session, current_user)
    return profile


@router.get("/me/progress", response_model=UserProgressOut)
async def get_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progress = await session.get(UserProgress, current_user.id)
    if progress is None:
        return UserProgressOut(xp=0, level=1, streak_count=0, streak_freezes=0, last_activity_date=None)
    today = datetime.now(UTC).date()
    xp_today = progress.xp_today if progress.xp_today_date == today else 0
    return UserProgressOut(
        xp=progress.xp,
        level=progress.level,
        streak_count=progress.streak_count,
        streak_freezes=progress.streak_freezes,
        last_activity_date=progress.last_activity_date,
        daily_goal_xp=progress.daily_goal_xp,
        xp_today=xp_today,
        goal_met=xp_today >= progress.daily_goal_xp,
        virtual_coins=progress.virtual_coins or 0,
    )


@router.patch("/me/goal", response_model=UserProgressOut)
async def set_daily_goal(
    payload: DailyGoalUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progress = await session.get(UserProgress, current_user.id)
    if progress is None:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()
    progress.daily_goal_xp = payload.daily_goal_xp
    await session.commit()
    return await get_progress(current_user, session)


@router.get("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    data = await build_user_export(session, current_user)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="invest-ed-export.json"'},
    )


class PushDeviceRequest(BaseModel):
    platform: Literal["ios", "android"]
    token: str = Field(min_length=8, max_length=255)


@router.post("/me/push-devices", status_code=201)
async def register_push_device(
    payload: PushDeviceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register (upsert) a device token. Server-side consent enforcement: the
    parent master switch must be on regardless of what the client does."""
    if not current_user.push_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Push is not enabled by your parent")
    device = await session.scalar(
        select(PushDevice).where(PushDevice.token == payload.token)
    )
    now = datetime.now(UTC)
    if device is None:
        device = PushDevice(
            user_id=current_user.id, platform=payload.platform, token=payload.token
        )
        session.add(device)
    else:
        device.user_id = current_user.id
        device.platform = payload.platform
        device.last_seen_at = now
    await session.commit()
    return {"status": "ok"}


@router.delete("/me/push-devices/{token}")
async def unregister_push_device(
    token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(PushDevice).where(
            PushDevice.token == token, PushDevice.user_id == current_user.id
        )
    )
    await session.commit()
    return {"status": "ok"}
