from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, LessonCompletion
from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.gamification import BadgeOut, ChallengeOut, LeaderboardEntry

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


@router.get("/challenges", response_model=list[ChallengeOut])
async def list_active_challenges(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)
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


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def weekly_leaderboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    xp_expr = func.sum(Lesson.xp_reward).label("xp_this_week")
    stmt = (
        select(User.username, User.country_code, xp_expr)
        .join(LessonCompletion, LessonCompletion.user_id == User.id)
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(LessonCompletion.completed_at >= monday)
        .group_by(User.id, User.username, User.country_code)
        .order_by(xp_expr.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).all()
    return [
        LeaderboardEntry(username=u, country_code=c, xp_this_week=x)
        for u, c, x in rows
    ]
