import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token, get_token_from_cookie
from app.models.user import User, UserProgress
from app.schemas.user import UpdatePreferencesRequest, UserProfile, UserProgressOut

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


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfile)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if payload.country_code is not None:
        current_user.country_code = payload.country_code
    if payload.currency_code is not None:
        current_user.currency_code = payload.currency_code
    if payload.topic_path is not None:
        current_user.topic_path = payload.topic_path
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.get("/me/progress", response_model=UserProgressOut)
async def get_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progress = await session.get(UserProgress, current_user.id)
    if progress is None:
        return UserProgressOut(xp=0, level=1, streak_count=0, last_activity_date=None)
    return UserProgressOut(
        xp=progress.xp,
        level=progress.level,
        streak_count=progress.streak_count,
        last_activity_date=progress.last_activity_date,
    )
