from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Badge, Challenge

# icon_url holds a display emoji (rendered directly in the UI); the previous
# /badges/*.svg paths pointed at assets that never existed.
_BADGES = [
    {"name": "First Step", "description": "Complete your first lesson",
     "icon_url": "👣", "condition_type": "lesson_count", "condition_value": 1},
    {"name": "Quiz Ace", "description": "Complete 10 lessons",
     "icon_url": "🎯", "condition_type": "lesson_count", "condition_value": 10},
    {"name": "Streak Master", "description": "Maintain a 7-day streak",
     "icon_url": "🔥", "condition_type": "streak_days", "condition_value": 7},
    {"name": "First Trade", "description": "Execute your first paper trade",
     "icon_url": "📈", "condition_type": "trade_count", "condition_value": 1},
    {"name": "Century Club", "description": "Earn 100 XP",
     "icon_url": "💯", "condition_type": "total_xp", "condition_value": 100},
]


def _challenges_for_week() -> list[dict]:
    now = datetime.now(UTC)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = monday + timedelta(days=7)
    return [
        {"title": "Weekly Learner", "description": "Complete 3 lessons this week",
         "type": "lessons_completed", "target_value": 3, "xp_reward": 50,
         "starts_at": monday, "ends_at": end, "is_premium": False},
        {"title": "Market Explorer", "description": "Make 1 paper trade this week",
         "type": "trades_executed", "target_value": 1, "xp_reward": 30,
         "starts_at": monday, "ends_at": end, "is_premium": True},  # SAMPLE premium gating fixture — real premium curriculum is sub-project #4
    ]


_MARKET_BADGES = [
    ("GB", "United Kingdom", "🇬🇧"), ("US", "United States", "🇺🇸"),
    ("AU", "Australia", "🇦🇺"), ("CA", "Canada", "🇨🇦"),
    ("IE", "Ireland", "🇮🇪"), ("ES", "Spain", "🇪🇸"),
    ("FR", "France", "🇫🇷"), ("DE", "Germany", "🇩🇪"),
    ("HK", "Hong Kong", "🇭🇰"), ("SG", "Singapore", "🇸🇬"),
]


async def seed_market_badges(session: AsyncSession) -> None:
    """Idempotent. One 'Market Mastered: <name>' badge per market, keyed by name."""
    for code, name, flag in _MARKET_BADGES:
        badge_name = f"Market Mastered: {name}"
        existing = await session.scalar(select(Badge).where(Badge.name == badge_name))
        if existing is None:
            session.add(Badge(
                name=badge_name,
                description=f"Finish all the {name} money lessons",
                icon_url=flag,
                condition_type="market_completed",
                condition_value=0,
                market_code=code,
            ))
        elif existing.market_code != code:
            existing.market_code = code


async def seed_badges_and_challenges(session: AsyncSession) -> None:
    """Idempotent. Badges keyed by name; challenges keyed by (title, starts_at)."""
    for spec in _BADGES:
        existing = await session.scalar(select(Badge).where(Badge.name == spec["name"]))
        if existing:
            # Heal legacy rows whose icon_url is a dead /badges/*.svg path.
            if existing.icon_url.startswith("/"):
                existing.icon_url = spec["icon_url"]
            continue
        session.add(Badge(**spec))

    for spec in _challenges_for_week():
        existing = await session.scalar(
            select(Challenge).where(
                Challenge.title == spec["title"],
                Challenge.starts_at == spec["starts_at"],
            )
        )
        if existing:
            continue
        session.add(Challenge(**spec))
