import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_cosmetic_item_has_collectable_fields(db_session):
    item = CosmeticItem(
        slug="_t_drop",
        name="T",
        emoji="👑",
        type="accessory",
        coin_cost=0,
        is_premium=False,
        rarity="legendary",
        unlock_type="streak_days",
        unlock_threshold=7,
    )
    db_session.add(item)
    await db_session.flush()
    got = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == "_t_drop"))
    assert got.rarity == "legendary"
    assert got.unlock_type == "streak_days"
    assert got.unlock_threshold == 7
    assert got.available_from is None and got.available_until is None  # nullable
