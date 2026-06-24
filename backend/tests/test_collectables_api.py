# backend/tests/test_collectables_api.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.content import Lesson, Module
from app.models.cosmetics import CosmeticItem
from tests.test_content import _register_and_login
from tests.test_cosmetics_api import _login_with_coins

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _seed_drop(db_session, slug="_api_drop"):
    now = datetime.now(UTC)
    d = CosmeticItem(
        slug=slug, name="Crown", emoji="👑", type="accessory", coin_cost=0, is_premium=False,
        rarity="legendary", unlock_type="streak_days", unlock_threshold=7,
        available_from=now - timedelta(days=1), available_until=now + timedelta(days=3),
    )
    db_session.add(d)
    await db_session.commit()
    return d

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


async def test_lesson_complete_response_carries_granted_collectables(client, db_session):
    """Regression: lesson-complete response must include granted_collectables so
    the frontend earn toast can fire when a drop threshold is crossed."""
    suffix = uuid.uuid4().hex[:8]
    email = f"drops_{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"drops_{suffix}")

    # Seed a streak_days drop with threshold=1 so completing one lesson (which
    # sets streak_count=1) pushes it over the edge.
    now = datetime.now(UTC)
    drop = CosmeticItem(
        slug=f"_lesson_drop_{suffix}",
        name="Lesson Drop",
        emoji="⭐",
        type="accessory",
        coin_cost=0,
        is_premium=False,
        rarity="rare",
        unlock_type="streak_days",
        unlock_threshold=1,
        available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
    )
    db_session.add(drop)

    module = Module(
        topic="stocks",
        title=f"Module {suffix}",
        country_codes=["GB"],
        is_premium=False,
        order_index=99,
        market_code="GB",
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    r = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r.status_code == 200
    body = r.json()
    assert "granted_collectables" in body
    assert drop.slug in body["granted_collectables"]
