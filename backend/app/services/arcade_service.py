from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.user import User, UserProgress
from app.services.market_progress_service import award_xp

ARCADE_DAILY_XP_CAP = 25


async def award_arcade_coins(
    session: AsyncSession,
    progress: UserProgress,
    amount: int,
    *,
    market_code: str,
    today: date | None = None,
) -> int:
    """Award up to the remaining daily arcade cap (25 XP=coins). Returns coins actually awarded."""
    today = today or datetime.now(UTC).date()
    if progress.arcade_xp_date != today:
        progress.arcade_xp_date = today
        progress.arcade_xp_today = 0
    remaining = max(0, ARCADE_DAILY_XP_CAP - progress.arcade_xp_today)
    grant = max(0, min(amount, remaining))
    if grant:
        await award_xp(session, progress, grant, market_code=market_code, today=today)
        progress.arcade_xp_today += grant
    return grant


async def record_score(
    session: AsyncSession,
    *,
    user_id,
    game: str,
    points: int,
    market_code: str,
) -> ArcadeScore:
    """Insert a new arcade score row and return it."""
    row = ArcadeScore(user_id=user_id, game=game, points=points, market_code=market_code)
    session.add(row)
    await session.flush()
    return row


async def personal_best(session: AsyncSession, *, user_id, game: str) -> int:
    """Return the user's all-time highest points for the given game (0 if none)."""
    best = await session.scalar(
        select(func.max(ArcadeScore.points)).where(
            ArcadeScore.user_id == user_id,
            ArcadeScore.game == game,
        )
    )
    return best or 0


async def weekly_leaderboard(
    session: AsyncSession,
    *,
    game: str,
    market_code: str,
    limit: int = 50,
) -> list[tuple[str, str, int]]:
    """Top-N (username, country_code, points_this_week) for a game+market since Monday 00:00 UTC."""
    now = datetime.now(UTC)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    total = func.sum(ArcadeScore.points).label("pts")
    stmt = (
        select(User.username, User.country_code, total)
        .join(ArcadeScore, ArcadeScore.user_id == User.id)
        .where(
            ArcadeScore.game == game,
            ArcadeScore.market_code == market_code,
            ArcadeScore.created_at >= monday,
        )
        .group_by(User.id, User.username, User.country_code)
        .order_by(total.desc())
        .limit(limit)
    )
    return [(u, c, int(p)) for u, c, p in (await session.execute(stmt)).all()]
