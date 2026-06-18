from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress
from app.services.xp_service import XpResult, record_xp


async def _add_market_xp(session: AsyncSession, user_id, market_code: str, amount: int) -> None:
    """Upsert the (user, market) row and add XP (= lazy enrollment)."""
    row = await session.get(UserMarketProgress, (user_id, market_code))
    if row is None:
        row = UserMarketProgress(user_id=user_id, market_code=market_code, xp=0)
        session.add(row)
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


async def ensure_enrolled(session: AsyncSession, user_id, market_code: str) -> None:
    """Create the (user, market) progress row if absent (no XP change)."""
    if await session.get(UserMarketProgress, (user_id, market_code)) is None:
        session.add(UserMarketProgress(user_id=user_id, market_code=market_code, xp=0))
