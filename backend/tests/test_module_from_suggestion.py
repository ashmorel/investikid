import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.market import Market

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _us_market(db_session):
    # The US market is seeded globally by the test suite; reuse it if present.
    market = await db_session.get(Market, "US")
    if market is None:
        market = Market(code="US", name="United States", currency_code="USD")
        db_session.add(market)
        await db_session.flush()
    return market


async def test_create_module_from_suggestion(admin_client, db_session):
    market = await _us_market(db_session)
    has_content_before = market.has_content
    max_order_before = await db_session.scalar(
        select(func.max(Module.order_index)).where(Module.market_code == "US")
    )

    body = {
        "title": "College Savings (529)",
        "topic": "saving",
        "suggested_concepts": ["What is a 529 plan", "Tax advantages"],
        "action": "add",
        "replaces": None,
    }
    resp = await admin_client.post("/admin/markets/US/modules/from-suggestion", json=body)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "module_id" in data
    assert "level_id" in data
    module_id = data["module_id"]
    level_id = data["level_id"]
    assert module_id and level_id
    assert data["suggested_concepts"] == ["What is a 529 plan", "Tax advantages"]

    # The new module exists in the US market with the given title/topic.
    module = await db_session.get(Module, module_id)
    assert module is not None
    assert module.market_code == "US"
    assert module.title == "College Savings (529)"
    assert module.topic == "saving"
    assert module.order_index > (max_order_before or -1)

    # Exactly ONE level under it, NO lessons.
    levels = (
        await db_session.scalars(select(Level).where(Level.module_id == module.id))
    ).all()
    assert len(levels) == 1
    assert str(levels[0].id) == level_id

    lessons = (
        await db_session.scalars(select(Lesson).where(Lesson.module_id == module.id))
    ).all()
    assert lessons == []

    # has_content is unchanged — no auto-publish.
    await db_session.refresh(market)
    assert market.has_content == has_content_before


async def test_create_module_from_suggestion_unknown_market(admin_client):
    body = {"title": "Anything", "topic": "saving"}
    resp = await admin_client.post("/admin/markets/ZZ/modules/from-suggestion", json=body)
    assert resp.status_code == 404, resp.text
