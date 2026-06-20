import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.native_batch import generate_market_native
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

US_BRIEF = {"currency": "USD", "regulators": ["SEC"]}


def _llm():
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps({"title": "Saving up", "body": "Plan your dollars."}))
    return (client,
            patch("app.services.admin_content_generation_service.get_llm_client", return_value=client),
            patch("app.services.admin_content_generation_service.moderate_output",
                  AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))))


async def _seed(db_session, *, with_lesson=False, with_draft=False):
    module = Module(topic="money", title="Money", country_codes=[], market_code="US",
                    is_premium=False, order_index=0, icon="💵", min_age=10, max_age=14)
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="L0", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    if with_lesson:
        db_session.add(Lesson(module_id=module.id, level_id=level.id, type="card",
                              xp_reward=0, order_index=0, content_json={"title": "x", "body": "y"}))
    if with_draft:
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": "d", "body": "e"}, concept="c",
                                   model_used="t", moderation_safe=True, moderation_category=None))
    proposal = MarketCurriculumProposal(
        market_code="US", status="accepted",
        proposal_json={"market_code": "US", "modules": [{"topic": "money", "title": "Money",
            "icon": "💵", "min_age": 10, "max_age": 14, "order_index": 0, "levels": [
            {"title": "L0", "order_index": 0, "complexity_tier": 2, "learning_objective": "o",
             "concepts": ["saving", "budgeting"], "backbone_keys": ["saving_goals"],
             "level_id": str(level.id)}]}]},
        coverage_json={"ok": True})
    db_session.add(proposal)
    await db_session.flush()
    return module, level, proposal


async def test_generates_from_proposal_concepts(db_session):
    module, level, proposal = await _seed(db_session)
    brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(brief)
    await db_session.flush()
    client, p_client, p_mod = _llm()
    with p_client, p_mod:
        summary = await generate_market_native(db_session, module, brief=brief,
                                               proposal_row=proposal, include_populated=False)
    assert summary["generated"] == 1
    n = await db_session.scalar(select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level.id))
    assert n == 2  # one draft per concept
    # the complexity-tier depth instruction reached the prompt
    assert "develop" in client.complete.call_args.kwargs["system_prompt"].lower()


async def test_skips_level_with_pending_drafts(db_session):
    module, level, proposal = await _seed(db_session, with_draft=True)
    brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(brief)
    await db_session.flush()
    client, p_client, p_mod = _llm()
    with p_client, p_mod:
        summary = await generate_market_native(db_session, module, brief=brief,
                                               proposal_row=proposal, include_populated=False)
    assert summary["generated"] == 0 and summary["skipped_has_drafts"] == 1
    assert client.complete.await_count == 0
