import pytest

from app.models.content import Lesson, Level, Module
from app.models.market import Market

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_publish_empty_market_returns_409_and_leaves_has_content_false(
    admin_client, db_session
):
    # US is seeded with has_content=False and has no curriculum content.
    r = await admin_client.post("/admin/markets/US/publish")
    assert r.status_code == 409

    market = await db_session.get(Market, "US")
    await db_session.refresh(market)
    assert market.has_content is False


async def test_publish_market_with_a_lesson_then_unpublish(admin_client, db_session):
    # Build a minimal US curriculum: module -> level -> lesson.
    module = Module(
        topic="savings", title="US Mod", country_codes=[],
        is_premium=False, order_index=910, icon="💵", market_code="US",
    )
    db_session.add(module)
    await db_session.flush()

    level = Level(module_id=module.id, title="US Level 1", order_index=0)
    db_session.add(level)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id, level_id=level.id, type="card", xp_reward=0,
        order_index=0, content_json={"title": "Saving up", "body": "A plan."},
    )
    db_session.add(lesson)
    await db_session.flush()

    r = await admin_client.post("/admin/markets/US/publish")
    assert r.status_code == 200
    assert r.json() == {"code": "US", "has_content": True}

    market = await db_session.get(Market, "US")
    await db_session.refresh(market)
    assert market.has_content is True

    # Unpublish flips it back; the lesson/module rows are untouched.
    r2 = await admin_client.post("/admin/markets/US/unpublish")
    assert r2.status_code == 200
    assert r2.json() == {"code": "US", "has_content": False}

    await db_session.refresh(market)
    assert market.has_content is False

    still_there = await db_session.get(Lesson, lesson.id)
    assert still_there is not None


async def test_publish_unknown_market_returns_404(admin_client):
    r = await admin_client.post("/admin/markets/ZZ/publish")
    assert r.status_code == 404
