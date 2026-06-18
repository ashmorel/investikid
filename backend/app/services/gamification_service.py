from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import LessonCompletion
from app.models.gamification import (
    Badge,
    Challenge,
    GroupChallengeCompletion,
    UserBadge,
    UserChallenge,
)
from app.models.group import GroupMembership
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


async def update_challenge_progress(
    session: AsyncSession,
    user_id,
    event_type: str,
    increment: int,
) -> list[Challenge]:
    """Advance any active challenges matching event_type. Returns newly completed challenges.
    Caller commits.
    """
    now = datetime.now(UTC)
    active = (await session.scalars(
        select(Challenge).where(
            Challenge.type == event_type,
            Challenge.starts_at <= now,
            Challenge.ends_at > now,
        )
    )).all()

    newly_completed: list[Challenge] = []
    for challenge in active:
        uc = await session.get(UserChallenge, (user_id, challenge.id))
        if uc is None:
            uc = UserChallenge(user_id=user_id, challenge_id=challenge.id, progress=0)
            session.add(uc)
        if uc.completed_at is not None:
            continue
        uc.progress = uc.progress + increment
        if challenge.scope == "group":
            # Co-op: completion is decided by the GROUP sum, not this row.
            await session.flush()
            await _settle_group_challenge(session, user_id, challenge, now)
            continue
        if uc.progress >= challenge.target_value:
            uc.completed_at = now
            newly_completed.append(challenge)
    if active:
        await session.flush()
    return newly_completed


async def _settle_group_challenge(
    session: AsyncSession, user_id, challenge: Challenge, now: datetime
) -> None:
    """For each of the child's groups: if the members' summed progress crossed
    the shared target and the group hasn't been settled, record the completion
    (race-safe) and reward every member exactly once (their UserChallenge
    completed_at is the per-member guard)."""
    from app.services.market_progress_service import award_xp

    group_ids = (await session.scalars(
        select(GroupMembership.group_id).where(GroupMembership.user_id == user_id)
    )).all()
    for group_id in group_ids:
        settled = await session.scalar(
            select(GroupChallengeCompletion).where(
                GroupChallengeCompletion.group_id == group_id,
                GroupChallengeCompletion.challenge_id == challenge.id,
            )
        )
        if settled is not None:
            continue
        member_ids = (await session.scalars(
            select(GroupMembership.user_id).where(GroupMembership.group_id == group_id)
        )).all()
        total = (await session.scalar(
            select(func.coalesce(func.sum(UserChallenge.progress), 0)).where(
                UserChallenge.challenge_id == challenge.id,
                UserChallenge.user_id.in_(member_ids),
            )
        )) or 0
        if total < challenge.target_value:
            continue
        try:
            async with session.begin_nested():
                session.add(GroupChallengeCompletion(
                    group_id=group_id, challenge_id=challenge.id, completed_at=now
                ))
                await session.flush()
        except IntegrityError:
            continue  # raced: another member's event settled this group first
        for member_id in member_ids:
            muc = await session.get(UserChallenge, (member_id, challenge.id))
            if muc is None:
                muc = UserChallenge(user_id=member_id, challenge_id=challenge.id, progress=0)
                session.add(muc)
            if muc.completed_at is not None:
                continue  # already rewarded (e.g. via another group)
            muc.completed_at = now
            progress = await session.get(UserProgress, member_id)
            if progress is not None:
                await award_xp(session, progress, challenge.xp_reward)
        await session.flush()
