import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem
from app.seed.cosmetics import seed_cosmetics

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_creates_a_limited_drop(db_session):
    await seed_cosmetics(db_session)
    await db_session.commit()
    drop = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None)))
    assert drop is not None
    assert drop.rarity in {"common", "rare", "epic", "legendary"}
    assert drop.unlock_threshold and drop.unlock_threshold > 0
