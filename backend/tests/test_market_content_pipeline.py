from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Lesson, Level, Module
from app.models.market_brief import MarketBrief
from app.models.market_curriculum import MarketCurriculumProposal
from app.services import market_content_pipeline as mcp

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_staged_level(db_session, *, with_lesson: bool):
    mod = Module(topic="t", title="M", country_codes=[], market_code="US",
                 is_premium=False, order_index=0, icon="📚", published=False)
    db_session.add(mod)
    await db_session.flush()
    lvl = Level(module_id=mod.id, title="L", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    if with_lesson:
        db_session.add(Lesson(module_id=mod.id, level_id=lvl.id, type="card",
                              xp_reward=0, order_index=0, content_json={"title": "x", "body": "y"}))
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="verified"))
    db_session.add(MarketCurriculumProposal(
        market_code="US", status="accepted",
        proposal_json={"market_code": "US", "modules": [{"module_id": str(mod.id),
            "topic": "t", "title": "M", "icon": "📚", "min_age": 10, "max_age": 14,
            "order_index": 0, "levels": [{"title": "L", "order_index": 0,
                "complexity_tier": 1, "learning_objective": "o", "concepts": ["c0", "c1"],
                "backbone_keys": ["saving_goals"], "level_id": str(lvl.id)}]}]},
        coverage_json={"ok": True}))
    await db_session.flush()
    return mod, lvl


async def test_generate_next_level_skips_levels_with_lessons(db_session):
    await _seed_staged_level(db_session, with_lesson=True)
    res = await mcp.generate_next_level(db_session, "US")
    assert res["remaining"] == 0  # the only staged level already has a lesson


async def test_generate_next_level_generates_pending_level(db_session):
    _, lvl = await _seed_staged_level(db_session, with_lesson=False)

    fake_result = type("R", (), {"created": list(range(10))})()
    with patch("app.services.market_content_pipeline.generate_native_level_lessons",
               new=AsyncMock(return_value=fake_result)) as gen, \
         patch("app.services.market_content_pipeline.approve_level_drafts",
               new=AsyncMock(return_value={"approved": 10})) as appr:
        res = await mcp.generate_next_level(db_session, "US")

    assert res["remaining"] == 0 and res["drafts"] == 10 and res["approved"] == 10
    # tier-1 level → target 10; concepts from the proposal node threaded through
    _, gkw = gen.await_args
    assert gkw["target_count"] == 10 and gkw["concepts"] == ["c0", "c1"]
    appr.assert_awaited_once()


async def test_generate_next_level_raises_without_proposal(db_session):
    with pytest.raises(ValueError):
        await mcp.generate_next_level(db_session, "ZZ")


async def test_publish_market_delegates(db_session):
    with patch("app.services.market_content_pipeline.publish_market_curriculum",
               new=AsyncMock(return_value={"published": 9, "retired": 9})) as pub:
        res = await mcp.publish_market(db_session, "US")
    assert res["stage"] == "published" and res["published"] == 9
    pub.assert_awaited_once_with(db_session, "US")


async def test_scaffold_cleans_up_orphan_staged_modules(db_session):
    from datetime import UTC, datetime

    def _mod(published, archived):
        m = Module(topic="t", title="M", country_codes=[], market_code="US",
                   is_premium=False, order_index=0, icon="📚", published=published)
        if archived:
            m.archived_at = datetime.now(UTC)
        return m

    live = _mod(True, False)
    archived = _mod(False, True)
    orphan = _mod(False, False)   # staged, never archived/live → should be deleted
    db_session.add_all([live, archived, orphan])
    await db_session.flush()
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="verified"))
    await db_session.flush()
    live_id, archived_id, orphan_id = live.id, archived.id, orphan.id

    report = type("R", (), {"ok": True})()
    with patch("app.services.market_content_pipeline.design_curriculum",
               new=AsyncMock(return_value=(object(), report))), \
         patch("app.services.market_content_pipeline.save_proposal",
               new=AsyncMock(return_value=object())), \
         patch("app.services.market_content_pipeline.accept_proposal",
               new=AsyncMock(return_value={"modules": 9, "levels": 27})):
        res = await mcp.scaffold_market(db_session, "US")

    from sqlalchemy import select as _select
    remaining = set((await db_session.execute(_select(Module.id))).scalars().all())
    assert orphan_id not in remaining            # orphan staged deleted
    assert live_id in remaining and archived_id in remaining  # live + archived kept
    assert res["modules"] == 9
