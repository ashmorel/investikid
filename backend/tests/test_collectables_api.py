# backend/tests/test_collectables_api.py
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem
from tests.test_cosmetics_api import _login_with_coins, _item
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _seed_drop(db_session, slug="_api_drop"):
    now = datetime.now(UTC)
    d = CosmeticItem(slug=slug, name="Crown", emoji="👑", type="accessory", coin_cost=0, is_premium=False,
                     rarity="legendary", unlock_type="streak_days", unlock_threshold=7,
                     available_from=now - timedelta(days=1), available_until=now + timedelta(days=3))
    db_session.add(d); await db_session.commit(); return d

async def test_collectables_lists_active_drop_with_progress(client, db_session):
    await _login_with_coins(client, db_session, coins=0)
    await _seed_drop(db_session)
    r = await client.get("/collectables")
    assert r.status_code == 200
    body = r.json()
    drop = next(d for d in body["active"] if d["slug"] == "_api_drop")
    assert drop["rarity"] == "legendary"
    assert drop["goal"]["type"] == "streak_days" and drop["goal"]["threshold"] == 7
    assert drop["earned"] is False

async def test_normal_shop_excludes_drops(client, db_session):
    await _login_with_coins(client, db_session, coins=0)
    await _seed_drop(db_session, slug="_api_drop2")
    body = (await client.get("/cosmetics")).json()
    assert all(i["slug"] != "_api_drop2" for i in body["items"])

async def test_buying_a_drop_is_rejected(client, db_session):
    await _login_with_coins(client, db_session, coins=1000)
    d = await _seed_drop(db_session, slug="_api_drop3")
    r = await client.post(f"/cosmetics/{d.id}/buy")
    assert r.status_code == 403
