import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.services.market_scaffold_service import scaffold_market_from_gb

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _batch_adapt(**kw) -> str:
    """The mocked adapter: ONE call receives a JSON object mapping ids -> source
    records; echo back the SAME ids with each record adapted (title prefixed 'US ').
    Proves the titles came from the (batched) adapter, not copied from GB."""
    sources = json.loads(kw["messages"][0]["content"])
    out: dict = {}
    for key, rec in sources.items():
        adapted: dict = {"title": f"US {rec['title']}"}
        if "conversation_prompt" in rec:
            adapted["conversation_prompt"] = "Adapted prompt for the US."
        if "learning_objectives" in rec:
            adapted["learning_objectives"] = ["Adapted objective."]
        out[key] = adapted
    return json.dumps(out)


def _mock_client():
    client = AsyncMock()
    # The adapter now runs as a SINGLE batched call for the whole market.
    client.complete = AsyncMock(side_effect=_batch_adapt)
    return client


async def _seed_gb(db_session):
    """Two GB modules, each with 1-2 levels. Mirrors content creation in
    test_market_completion_reward."""
    mod_a = Module(
        topic="savings", title="GB Saving", country_codes=[], is_premium=False,
        order_index=10, icon="💷", market_code="GB", min_age=8, max_age=12,
        conversation_prompt="Talk about saving.",
    )
    mod_b = Module(
        topic="investing", title="GB Investing", country_codes=[], is_premium=True,
        order_index=20, icon="📈", market_code="GB", min_age=12, max_age=16,
        conversation_prompt="Talk about investing.",
    )
    db_session.add_all([mod_a, mod_b])
    await db_session.flush()

    lvl_a1 = Level(
        module_id=mod_a.id, title="GB Saving L1", order_index=0, is_premium=False,
        pass_threshold=0.7, learning_objectives=["Understand saving."],
    )
    lvl_a2 = Level(
        module_id=mod_a.id, title="GB Saving L2", order_index=1, is_premium=False,
        pass_threshold=0.8, learning_objectives=["Build a habit."],
    )
    lvl_b1 = Level(
        module_id=mod_b.id, title="GB Investing L1", order_index=0, is_premium=True,
        pass_threshold=0.75, learning_objectives=["Understand risk."],
    )
    db_session.add_all([lvl_a1, lvl_a2, lvl_b1])
    await db_session.flush()
    return mod_a, mod_b


async def _verified_us_brief(db_session):
    brief = MarketBrief(
        market_code="US",
        brief_json={"currency": "USD", "regulators": ["SEC"]},
        status="verified",
        model_used="test-model",
    )
    db_session.add(brief)
    await db_session.flush()
    return brief


async def test_scaffold_mirrors_gb_structure(db_session):
    gb_mods = await _seed_gb(db_session)
    await _verified_us_brief(db_session)

    with patch(
        "app.services.market_scaffold_service.get_llm_client",
        return_value=_mock_client(),
    ):
        summary = await scaffold_market_from_gb(db_session, "US")

    assert summary["modules_created"] == 2
    assert summary["levels_created"] == 3

    us_mods = (await db_session.scalars(
        select(Module).where(Module.market_code == "US").order_by(Module.order_index)
    )).all()
    assert len(us_mods) == 2

    # Structural fields copied; title from the (mocked) adapter.
    for gb, us in zip(gb_mods, us_mods, strict=True):
        assert us.market_code == "US"
        assert us.topic == gb.topic
        assert us.order_index == gb.order_index
        assert us.icon == gb.icon
        assert us.is_premium == gb.is_premium
        assert us.min_age == gb.min_age
        assert us.max_age == gb.max_age
        assert us.title.startswith("US ")  # adapted, not the GB title
        assert us.title != gb.title

    # Levels mirror GB levels per module.
    us_levels = (await db_session.scalars(
        select(Level).join(Module, Module.id == Level.module_id)
        .where(Module.market_code == "US")
    )).all()
    assert len(us_levels) == 3
    for lvl in us_levels:
        assert lvl.title.startswith("US ")
        assert lvl.learning_objectives == ["Adapted objective."]

    # NO lessons created.
    us_lessons = await db_session.scalar(
        select(Lesson.id).join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == "US")
    )
    assert us_lessons is None

    # has_content untouched.
    market = await db_session.get(Market, "US")
    assert market.has_content is False


async def test_scaffold_is_idempotent(db_session):
    await _seed_gb(db_session)
    await _verified_us_brief(db_session)

    with patch(
        "app.services.market_scaffold_service.get_llm_client",
        return_value=_mock_client(),
    ):
        await scaffold_market_from_gb(db_session, "US")
        summary2 = await scaffold_market_from_gb(db_session, "US")

    # Second run creates nothing.
    assert summary2["modules_created"] == 0
    us_count = await db_session.scalar(
        select(Market).where(Market.code == "US")
    )
    assert us_count is not None
    mod_count = len((await db_session.scalars(
        select(Module).where(Module.market_code == "US")
    )).all())
    assert mod_count == 2  # not 4


async def test_scaffold_requires_verified_brief(db_session):
    await _seed_gb(db_session)
    # Draft (unverified) brief.
    db_session.add(MarketBrief(
        market_code="US", brief_json={"currency": "USD"}, status="draft",
        model_used="test-model",
    ))
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await scaffold_market_from_gb(db_session, "US")
    assert exc.value.status_code == 409


async def test_scaffold_makes_a_single_batched_llm_call(db_session):
    # The whole market (every module + level) must be adapted in ONE call, not
    # one-per-entity — otherwise the request runs for minutes and times out.
    await _seed_gb(db_session)
    await _verified_us_brief(db_session)
    client = _mock_client()
    with patch(
        "app.services.market_scaffold_service.get_llm_client", return_value=client,
    ):
        await scaffold_market_from_gb(db_session, "US")
    assert client.complete.await_count == 1


async def test_scaffold_falls_back_to_gb_titles_on_llm_failure(db_session):
    # If the single adapter call fails, scaffolding still completes with GB titles.
    gb_mods = await _seed_gb(db_session)
    await _verified_us_brief(db_session)
    broken = AsyncMock()
    broken.complete = AsyncMock(side_effect=RuntimeError("upstream down"))
    with patch(
        "app.services.market_scaffold_service.get_llm_client", return_value=broken,
    ):
        summary = await scaffold_market_from_gb(db_session, "US")
    assert summary["modules_created"] == 2
    us_titles = {
        m.title for m in (await db_session.scalars(
            select(Module).where(Module.market_code == "US")
        )).all()
    }
    assert {m.title for m in gb_mods} == us_titles  # GB titles preserved on failure
