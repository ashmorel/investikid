import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.services.admin_content_generation_service import generate_market_level_lessons
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

# The mocked premium model always returns this valid card.
US_CARD = json.dumps({"title": "Saving up", "body": "A plan for your dollars."})

US_BRIEF = {
    "currency": "USD",
    "tax_advantaged_accounts": ["Roth IRA", "529 plan"],
    "regulators": ["SEC", "FINRA"],
    "deposit_protection": "FDIC insures up to $250,000",
    "typical_products": ["savings account"],
    "local_examples": ["allowance in a piggy bank"],
    "notes": "Dollars and cents.",
}


async def _seed_gb_level_with_lesson(db_session):
    module = Module(
        topic="savings", title="GB Saving", country_codes=[], is_premium=False,
        order_index=900, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="GB Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, level_id=level.id, type="card", xp_reward=0, order_index=0,
        content_json={"title": "ISA savings in pounds",
                      "body": "Put your £ into an ISA with the FCA-regulated bank."},
    )
    db_session.add(lesson)
    await db_session.flush()
    return level, lesson


async def _seed_us_level(db_session):
    module = Module(
        topic="savings", title="US Saving", country_codes=[], is_premium=False,
        order_index=901, icon="💵", market_code="US", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="US Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return level


async def test_market_generation_grounds_on_brief_and_gb_source(db_session):
    gb_level, gb_lesson = await _seed_gb_level_with_lesson(db_session)
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=US_CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    # (a) a LessonDraft is created under us_level
    assert len(result.created) == 1
    drafts = (await db_session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == us_level.id)
    )).all()
    assert len(drafts) == 1

    # (b) the LLM was called with a system prompt containing the brief currency
    #     AND the GB source lesson's text.
    assert mock_client.complete.await_count == 1
    system_prompt = mock_client.complete.await_args.kwargs["system_prompt"]
    assert "USD" in system_prompt
    assert "ISA savings in pounds" in system_prompt


async def test_market_generation_skips_non_generatable_video_lessons(db_session):
    """A GB level can contain a `video` lesson (curated YouTube, not LLM-
    generatable). Market generation must SKIP it, not crash with KeyError."""
    module = Module(
        topic="savings", title="GB Mixed", country_codes=[], is_premium=False,
        order_index=902, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    gb_level = Level(module_id=module.id, title="GB Mixed L1", order_index=0,
                     is_premium=False, pass_threshold=0.7)
    db_session.add(gb_level)
    await db_session.flush()
    db_session.add_all([
        Lesson(module_id=module.id, level_id=gb_level.id, type="video",
               xp_reward=0, order_index=0,
               content_json={"caption": "Watch", "youtube_id": "abc123"}),
        Lesson(module_id=module.id, level_id=gb_level.id, type="card",
               xp_reward=0, order_index=1,
               content_json={"title": "Saving", "body": "Save your £."}),
    ])
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=US_CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    # The video lesson is skipped; only the card is generated (no KeyError).
    assert result.skipped == 1
    assert len(result.created) == 1
    assert mock_client.complete.await_count == 1


async def test_generate_market_endpoint_blocks_unverified_brief(admin_client, db_session):
    gb_level, _ = await _seed_gb_level_with_lesson(db_session)
    us_level = await _seed_us_level(db_session)
    # Draft (not verified) brief → endpoint must 409.
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="draft"))
    await db_session.flush()

    resp = await admin_client.post(
        f"/admin/levels/{us_level.id}/generate-market",
        json={"source_level_id": str(gb_level.id)},
    )
    assert resp.status_code == 409, resp.text
