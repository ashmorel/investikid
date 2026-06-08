import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content import Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.admin_content_generation_service import generate_level_lessons
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

CARD = json.dumps({"title": "Compound Interest", "body": "Money grows on money."})


async def _seed_level(db_session):
    module = Module(topic="saving", title="Saving", country_codes=[], is_premium=True,
                    order_index=0, min_age=10, max_age=14)
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Level 2", order_index=1, is_premium=True, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return level


async def test_generates_n_safe_drafts(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_level_lessons(db_session, level, concept="compound interest",
                                              count=2, types=["card"])
    assert len(result.created) == 2
    assert result.skipped == 0
    drafts = (await db_session.scalars(select(LessonDraft).where(LessonDraft.level_id == level.id))).all()
    assert len(drafts) == 2
    assert all(d.moderation_safe for d in drafts)


async def test_unsafe_output_flagged(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=False, category="violence", text="x"))):
        result = await generate_level_lessons(db_session, level, concept="x", count=1, types=["card"])
    assert len(result.created) == 1
    assert result.created[0].moderation_safe is False
    assert result.created[0].moderation_category == "violence"


async def test_bad_json_retried_then_skipped(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not json")
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_level_lessons(db_session, level, concept="x", count=1, types=["card"])
    assert result.created == []
    assert result.skipped == 1
    assert mock_client.complete.await_count == 2  # initial + one retry
