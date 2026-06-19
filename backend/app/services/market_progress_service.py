from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress
from app.services.xp_service import XpResult, record_xp


@dataclass
class RewardGrant:
    coins: int = 0
    badge_name: str | None = None
    badge_icon: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.coins == 0 and self.badge_name is None


async def _add_market_xp(session: AsyncSession, user_id: uuid.UUID, market_code: str, amount: int) -> None:
    """Add `amount` XP to the (user, market) row, creating it if absent (= lazy
    enrollment). Concurrency-safe: a racing first-insert is caught and retried as
    an increment, matching the codebase's begin_nested + IntegrityError pattern."""
    row = await session.get(UserMarketProgress, (user_id, market_code))
    if row is not None:
        row.xp += amount
        return
    try:
        async with session.begin_nested():
            session.add(UserMarketProgress(user_id=user_id, market_code=market_code, xp=amount))
    except IntegrityError:
        row = await session.get(UserMarketProgress, (user_id, market_code))
        row.xp += amount


async def award_xp(
    session: AsyncSession,
    progress: UserProgress,
    amount: int,
    *,
    market_code: str | None = None,
    today: date | None = None,
) -> XpResult:
    """Canonical XP-award seam: updates the GLOBAL total/level/goal (via record_xp)
    AND the active market's per-market row. When market_code is omitted, it is
    resolved from the user's active_market_code. Keeps sum(per-market) == global."""
    result = record_xp(progress, amount, today=today)
    if market_code is None:
        market_code = await session.scalar(
            select(User.active_market_code).where(User.id == progress.user_id)
        ) or "GB"
    await _add_market_xp(session, progress.user_id, market_code, amount)
    return result


async def ensure_enrolled(session: AsyncSession, user_id: uuid.UUID, market_code: str) -> None:
    """Create the (user, market) row if absent (no XP change). Used by the
    market-switch + registration flows (Sub-project C2a Task 5). Idempotent +
    concurrency-safe."""
    if await session.get(UserMarketProgress, (user_id, market_code)) is not None:
        return
    try:
        async with session.begin_nested():
            session.add(UserMarketProgress(user_id=user_id, market_code=market_code, xp=0))
    except IntegrityError:
        pass


async def grant_enroll_reward(
    session: AsyncSession, user: User, market_code: str
) -> RewardGrant:
    """One-time coin bonus the first time a user enrolls in a NON-home market.
    Idempotent via enroll_rewarded_at; the home market never qualifies."""
    if market_code == user.home_market_code:
        return RewardGrant()
    row = await session.get(UserMarketProgress, (user.id, market_code))
    if row is None or row.enroll_rewarded_at is not None:
        return RewardGrant()
    from datetime import UTC, datetime

    from app.services.app_settings import get_market_enroll_bonus_coins

    coins = await get_market_enroll_bonus_coins(session)
    progress = await session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id)
        session.add(progress)
        await session.flush()
    progress.virtual_coins = (progress.virtual_coins or 0) + coins
    row.enroll_rewarded_at = datetime.now(UTC)
    return RewardGrant(coins=coins)
