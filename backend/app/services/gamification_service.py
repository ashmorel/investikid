from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import LessonCompletion
from app.models.gamification import Badge, UserBadge
from app.models.simulator import Portfolio, Trade
from app.models.user import UserProgress


class UserStats(TypedDict):
    lesson_count: int
    streak_days: int
    trade_count: int
    total_xp: int


_CONDITION_KEYS: dict[str, str] = {
    "lesson_count": "lesson_count",
    "streak_days": "streak_days",
    "trade_count": "trade_count",
    "total_xp": "total_xp",
}


def is_badge_earned(condition_type: str, condition_value: int, stats: UserStats) -> bool:
    key = _CONDITION_KEYS.get(condition_type)
    if key is None:
        return False
    return stats[key] >= condition_value


async def collect_user_stats(session: AsyncSession, user_id, progress: UserProgress) -> UserStats:
    lesson_count = await session.scalar(
        select(func.count()).select_from(LessonCompletion).where(LessonCompletion.user_id == user_id)
    ) or 0
    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user_id))
    trade_count = 0
    if portfolio:
        trade_count = await session.scalar(
            select(func.count()).select_from(Trade).where(Trade.portfolio_id == portfolio.id)
        ) or 0
    return UserStats(
        lesson_count=int(lesson_count),
        streak_days=int(progress.streak_count),
        trade_count=int(trade_count),
        total_xp=int(progress.xp),
    )


async def evaluate_and_award_badges(
    session: AsyncSession, user_id, progress: UserProgress,
) -> list[Badge]:
    """Return newly-awarded badges (and insert UserBadge rows). Caller commits."""
    stats = await collect_user_stats(session, user_id, progress)

    all_badges = (await session.scalars(select(Badge))).all()
    owned_ids = set((await session.scalars(
        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
    )).all())

    newly_earned: list[Badge] = []
    for badge in all_badges:
        if badge.id in owned_ids:
            continue
        if is_badge_earned(badge.condition_type, badge.condition_value, stats):
            session.add(UserBadge(user_id=user_id, badge_id=badge.id))
            newly_earned.append(badge)
    if newly_earned:
        await session.flush()
    return newly_earned
