"""B6 — coin-funded streak repair.

A child may spend earned virtual coins to revive a *just-lapsed* streak. This is
server-authoritative: eligibility (the repair window) and the coin balance are
validated here, never trusted from the client. Idempotent — after a repair the
gap is 1, so a second immediate call is no longer eligible (409).
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.time import today_utc
from app.models.user import User, UserProgress
from app.routers.users import get_current_user, get_progress
from app.schemas.user import UserProgressOut
from app.services.content_service import repair_eligibility
from app.services.streak_config import STREAK_REPAIR_COST

router = APIRouter(prefix="/streak", tags=["streak"])


def _conflict(code: str) -> HTTPException:
    """409 with a structured detail so the client can branch on ``code``."""
    return HTTPException(status.HTTP_409_CONFLICT, detail={"code": code, "message": code})


@router.post("/repair", response_model=UserProgressOut)
async def repair_streak(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Spend STREAK_REPAIR_COST coins to revive an eligible just-lapsed streak.

    Sets ``last_activity_date = today - 1`` (gap becomes 1) so the next activity
    continues the streak; ``streak_count`` is preserved. No real money — coins only.

    The progress row is locked FOR UPDATE and validated under the lock, so two
    concurrent requests (double-tap / multi-tab) cannot both deduct — the second
    waits, then sees gap == 1 and is rejected. Idempotent thereafter.
    """
    today = today_utc()
    progress = (
        await session.scalars(
            select(UserProgress)
            .where(UserProgress.user_id == current_user.id)
            .with_for_update()
        )
    ).first()
    if progress is None or not repair_eligibility(progress, today).eligible:
        raise _conflict("streak_not_repairable")
    if (progress.virtual_coins or 0) < STREAK_REPAIR_COST:
        raise _conflict("not_enough_coins")

    progress.virtual_coins = (progress.virtual_coins or 0) - STREAK_REPAIR_COST
    progress.last_activity_date = today - timedelta(days=1)
    await session.commit()
    return await get_progress(current_user, session)
