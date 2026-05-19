import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.audit import AuditLog
from app.models.content import Lesson, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.tutor_service import (
    TutorInputTooLong,
    chat,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def tutor_fixture(db_session):
    user = User(
        email="tutor@example.com", username="tutorkid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="stocks", title="What is a Stock?",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "What is a stock?",
            "choices": ["A loan", "A slice of a company", "A bond"],
            "answer_index": 1,
            "explanation": "A stock is a tiny piece of a company.",
        },
    )
    db_session.add(quiz)
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=0.4,
        quizzes_attempted=5, quizzes_correct=2,
    ))
    await db_session.flush()
    return user, module, quiz


async def test_chat_returns_response(db_session, tutor_fixture):
    user, module, quiz = tutor_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="A stock means you own a small part of a business!")

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        result = await chat(
            session=db_session,
            user=user,
            lesson=quiz,
            topic="stocks",
            message="I don't understand what a stock is",
            conversation_id=None,
            premium=False,
        )
    assert result["response"] is not None
    assert result["conversation_id"] is not None
    assert len(result["response"]) > 0


async def test_chat_rejects_long_input(db_session, tutor_fixture):
    user, module, quiz = tutor_fixture
    with pytest.raises(TutorInputTooLong):
        await chat(
            session=db_session,
            user=user,
            lesson=quiz,
            topic="stocks",
            message="x" * 300,
            conversation_id=None,
            premium=False,
        )


async def test_moderation_blocks_financial_advice_in_tutor():
    from app.services.moderation import _SAFE_FALLBACKS, moderate_output
    r = await moderate_output("You should buy Apple stock", surface="tutor")
    assert r.safe is False
    assert r.category == "financial_advice"
    assert r.text == _SAFE_FALLBACKS["tutor"]


async def test_moderation_passes_clean_tutor_text():
    from app.services.moderation import moderate_output
    clean = "A stock is a small share of a company."
    r = await moderate_output(clean, surface="tutor")
    assert r.safe is True
    assert r.text == clean


async def test_tutor_chat_returns_fallback_when_model_unsafe(db_session, tutor_fixture):
    from sqlalchemy import select

    from app.services.moderation import _SAFE_FALLBACKS

    user, module, quiz = tutor_fixture
    unsafe = "You should buy Tesla stock right now!"
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=unsafe)

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        result = await chat(
            session=db_session,
            user=user,
            lesson=quiz,
            topic="stocks",
            message="Should I buy Tesla?",
            conversation_id=None,
            premium=False,
        )

    assert result["response"] == _SAFE_FALLBACKS["tutor"]
    assert unsafe not in result["response"]

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == "moderation_block")
        )
    ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.metadata_json["surface"] == "tutor"
    assert row.metadata_json["category"] == "financial_advice"
    assert unsafe not in json.dumps(row.metadata_json)
