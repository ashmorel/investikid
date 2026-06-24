# backend/tests/test_collectables_admin.py
import pytest

from app.models.cosmetics import CosmeticItem
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unscheduled_pool_item_hidden_from_shop(client, db_session):
    # A drop-eligible pool item with no unlock_type must NOT appear in the buyable shop.
    db_session.add(CosmeticItem(
        slug="_pool_hat", name="Pool Hat", emoji="🎩", type="accessory",
        coin_cost=0, is_premium=False, drop_eligible=True, unlock_type=None,
    ))
    await db_session.commit()
    await _register_and_login(client, email="shopper@example.com", username="shopper")
    r = await client.get("/cosmetics")
    assert r.status_code == 200
    slugs = {i["slug"] for i in r.json()["items"]}
    assert "_pool_hat" not in slugs
