import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.content import Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.schemas.admin import GenerateNativeLessonsRequest
from app.services.admin_content_generation_service import (
    _system_prompt,
    generate_native_level_lessons,
)
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_native_request_rejects_bad_type():
    with pytest.raises(ValidationError):
        GenerateNativeLessonsRequest(concepts=["x"], types=["widget"])


def test_native_request_rejects_empty_concepts():
    with pytest.raises(ValidationError):
        GenerateNativeLessonsRequest(concepts=[])

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


def _us_module_and_level():
    module = Module(
        topic="savings", title="US College Saving", country_codes=[], is_premium=False,
        order_index=902, icon="💵", market_code="US", min_age=10, max_age=14,
    )
    level = Level(module_id=None, title="US Native Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    return module, level


# --- Pure (no-DB) regression + native-prompt assertions -------------------

@pytest.mark.asyncio(loop_scope=None)
async def test_native_prompt_mode_and_generic_regression():
    module, level = _us_module_and_level()

    # Native mode: brief present, source_text None.
    native_prompt = _system_prompt("card", module, level, brief=US_BRIEF, source_text=None)
    assert "MARKET-NATIVE" in native_prompt
    assert "US" in native_prompt  # market signal
    assert "USD" in native_prompt  # brief fact
    assert "Source lesson:" not in native_prompt  # no GB source
    assert "ADAPT the following GB" not in native_prompt

    # Generic mode (brief=None, source_text=None) is unchanged: base prompt only.
    base_prompt = _system_prompt("card", module, level)
    assert "MARKET-NATIVE" not in base_prompt
    assert "ADAPT the following GB" not in base_prompt
    assert "Source lesson:" not in base_prompt


# --- DB-backed generator test (may be deferred to CI if local DB hangs) ---

async def _seed_us_level(db_session):
    module = Module(
        topic="savings", title="US College Saving", country_codes=[], is_premium=False,
        order_index=902, icon="💵", market_code="US", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="US Native Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return level


async def test_native_generation_grounds_on_brief_no_gb_source(db_session):
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
        result = await generate_native_level_lessons(
            db_session, us_level, brief=us_brief,
            concepts=["Saving for college with a 529 plan"], types=["card"],
        )

    assert len(result.created) == 1
    assert result.skipped == 0
    drafts = (await db_session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == us_level.id)
    )).all()
    assert len(drafts) == 1

    assert mock_client.complete.await_count == 1
    system_prompt = mock_client.complete.await_args.kwargs["system_prompt"]
    # Brief facts present, market signal present, no GB source.
    assert "USD" in system_prompt
    assert "US" in system_prompt
    assert "Source lesson:" not in system_prompt
