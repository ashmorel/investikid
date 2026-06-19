import pytest
from sqlalchemy import select

from app.models.gamification import Badge
from app.seed.gamification import seed_market_badges

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_market_badges_idempotent(db_session):
    await seed_market_badges(db_session)
    await seed_market_badges(db_session)
    await db_session.flush()
    badges = (await db_session.scalars(
        select(Badge).where(Badge.condition_type == "market_completed")
    )).all()
    assert len(badges) == 10
    gb = next(b for b in badges if b.market_code == "GB")
    assert gb.name == "Market Mastered: United Kingdom"
    assert gb.icon_url == "🇬🇧"
