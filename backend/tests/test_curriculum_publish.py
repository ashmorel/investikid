import pytest

from app.models.content import Lesson, Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.curriculum_publish_service import publish_market_curriculum

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session, *, published, order_index, title, with_lesson):
    m = Module(topic="money", title=title, country_codes=[], market_code="GB",
               is_premium=False, order_index=order_index, icon="💷",
               min_age=10, max_age=14, published=published)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    if with_lesson:
        db_session.add(Lesson(module_id=m.id, level_id=lvl.id, type="card", xp_reward=0,
                              order_index=0, content_json={"title": "t", "body": "b"}))
        await db_session.flush()
    return m


async def _accepted_proposal(db_session, staged_module_ids):
    row = MarketCurriculumProposal(
        market_code="GB", status="accepted",
        proposal_json={"market_code": "GB", "modules": [
            {"topic": "money", "title": "New", "icon": "💷", "min_age": 10, "max_age": 14,
             "order_index": 0, "module_id": str(mid), "levels": []} for mid in staged_module_ids]},
        coverage_json={"ok": True})
    db_session.add(row)
    await db_session.flush()
    return row


async def test_publish_swaps_live_and_retires_old(db_session):
    old = await _module(db_session, published=True, order_index=0, title="OldLive", with_lesson=True)
    staged = await _module(db_session, published=False, order_index=1, title="NewStaged", with_lesson=True)
    await _accepted_proposal(db_session, [staged.id])

    result = await publish_market_curriculum(db_session, "GB")
    assert result == {"published": 1, "retired": 1}
    await db_session.refresh(old)
    await db_session.refresh(staged)
    assert staged.published is True and old.published is False


async def test_publish_blocked_when_staged_module_has_no_lessons(db_session):
    staged = await _module(db_session, published=False, order_index=0, title="Empty", with_lesson=False)
    await _accepted_proposal(db_session, [staged.id])
    with pytest.raises(ValueError):
        await publish_market_curriculum(db_session, "GB")
    await db_session.refresh(staged)
    assert staged.published is False  # nothing changed


async def test_publish_no_accepted_proposal_raises(db_session):
    with pytest.raises(ValueError):
        await publish_market_curriculum(db_session, "ZZ")
