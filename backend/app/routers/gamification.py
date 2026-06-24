from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.gamification import (
    BadgeDefinitionOut,
    BadgeOut,
    ChallengeOut,
    LeaderboardRowOut,
)
from app.services.handles import _handle_taken, ensure_handle, generate_handle
from app.services.leaderboard_service import leaderboard

router = APIRouter(tags=["gamification"])


@router.get("/users/me/badges", response_model=list[BadgeOut])
async def list_my_badges(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(Badge, UserBadge.earned_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == current_user.id)
        .order_by(UserBadge.earned_at.desc())
    )).all()
    return [
        BadgeOut(
            id=b.id, name=b.name, description=b.description,
            icon_url=b.icon_url, earned_at=earned_at,
        )
        for b, earned_at in rows
    ]


@router.get("/badges", response_model=list[BadgeDefinitionOut])
async def list_all_badges(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    badges = (await session.scalars(select(Badge).order_by(Badge.name))).all()
    return badges


@router.get("/challenges", response_model=list[ChallengeOut])
async def list_active_challenges(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(UTC)
    challenges = (await session.scalars(
        select(Challenge)
        .where(Challenge.starts_at <= now, Challenge.ends_at > now)
        .order_by(Challenge.starts_at)
    )).all()

    if challenges:
        uc_rows = (await session.scalars(
            select(UserChallenge).where(
                UserChallenge.user_id == current_user.id,
                UserChallenge.challenge_id.in_([c.id for c in challenges]),
            )
        )).all()
    else:
        uc_rows = []
    uc_by_id = {uc.challenge_id: uc for uc in uc_rows}

    out: list[ChallengeOut] = []
    for c in challenges:
        uc = uc_by_id.get(c.id)
        out.append(ChallengeOut(
            id=c.id, title=c.title, description=c.description, type=c.type,
            target_value=c.target_value, xp_reward=c.xp_reward,
            starts_at=c.starts_at, ends_at=c.ends_at, is_premium=c.is_premium,
            progress=uc.progress if uc else 0,
            completed_at=uc.completed_at if uc else None,
        ))
    return out


@router.get("/leaderboard", response_model=list[LeaderboardRowOut])
@limiter.limit("60/hour")
async def weekly_leaderboard(
    request: Request,
    scope: Literal["market", "global", "friends"] = Query("market"),
    metric: Literal["xp", "arcade"] = Query("xp"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not current_user.display_handle:
        await ensure_handle(session, current_user)
        await session.commit()
    rows = await leaderboard(session, viewer=current_user, scope=scope, metric=metric)
    return [
        LeaderboardRowOut(
            rank=r.rank, name=r.name, country_code=r.country_code,
            points=r.points, is_me=r.is_me,
        )
        for r in rows
    ]


@router.get("/me/handle")
async def get_my_handle(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handle = await ensure_handle(session, current_user)
    await session.commit()
    return {"handle": handle, "hidden": current_user.leaderboard_hidden}


@router.post("/me/handle/reroll")
async def reroll_my_handle(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    for _ in range(20):
        candidate = generate_handle()
        if candidate != current_user.display_handle and not await _handle_taken(session, candidate):
            current_user.display_handle = candidate
            await session.commit()
            return {"handle": candidate}
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "handle_unavailable")


class VisibilityRequest(BaseModel):
    hidden: bool


@router.patch("/me/leaderboard-visibility")
async def set_my_visibility(
    payload: VisibilityRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    current_user.leaderboard_hidden = payload.hidden
    await session.commit()
    return {"hidden": current_user.leaderboard_hidden}
