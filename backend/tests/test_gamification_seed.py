import pytest
from sqlalchemy import func, select

from app.models.gamification import Badge, Challenge
from app.seed.gamification import seed_badges_and_challenges

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_creates_badges_and_challenges(db_session):
    await seed_badges_and_challenges(db_session)
    await db_session.commit()
    assert (await db_session.scalar(select(func.count()).select_from(Badge))) >= 4
    assert (await db_session.scalar(select(func.count()).select_from(Challenge))) >= 2


async def test_seed_idempotent(db_session):
    await seed_badges_and_challenges(db_session)
    await db_session.commit()
    first = await db_session.scalar(select(func.count()).select_from(Badge))
    await seed_badges_and_challenges(db_session)
    await db_session.commit()
    assert (await db_session.scalar(select(func.count()).select_from(Badge))) == first
