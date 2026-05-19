import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.generated_content import GeneratedContent
from app.models.user import User
from app.services.ai_content_service import _fallback, generate_practice_quiz

pytestmark = pytest.mark.asyncio(loop_scope="session")


VALID_QUIZ_JSON = (
    '{"question": "If your weekly allowance is £20, how much is 20% to save?",'
    ' "choices": ["£2", "£4", "£10"], "answer_index": 1,'
    ' "explanation": "20% of £20 is £4."}'
)


@pytest_asyncio.fixture
async def lesson_fixture(db_session):
    user = User(
        email="practice@example.com", username="practicekid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting", title="Budgeting Basics",
        country_codes=[], is_premium=False, order_index=0, icon="💰",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "Using the 50/30/20 rule, how much of £100 should you save?",
            "choices": ["£50", "£20", "£30"],
            "answer_index": 1,
            "explanation": "The 50/30/20 rule says save 20%.",
        },
    )
    db_session.add(quiz)
    await db_session.flush()
    return user, module, quiz


async def test_generate_practice_quiz_calls_llm(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=VALID_QUIZ_JSON)

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    assert result["question"] is not None
    assert len(result["choices"]) >= 3
    assert isinstance(result["answer_index"], int)
    mock_client.complete.assert_awaited_once()


async def test_generate_practice_quiz_uses_cache(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    # Pre-populate cache
    cached = GeneratedContent(
        lesson_id=quiz.id,
        concept="50/30/20 rule",
        content_json={
            "question": "Cached question",
            "choices": ["A", "B", "C"],
            "answer_index": 0,
            "explanation": "Cached.",
        },
        model_used="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
    )
    db_session.add(cached)
    await db_session.flush()

    mock_client = AsyncMock()
    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    assert result["question"] == "Cached question"
    mock_client.complete.assert_not_awaited()


async def test_generate_practice_quiz_fallback_on_invalid_json(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not valid json at all")

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    # Should fall back to original question (shuffled or not)
    assert result["question"] is not None
    assert len(result["choices"]) >= 2


UNSAFE_QUIZ_JSON = (
    '{"question": "What is a good investment?",'
    ' "choices": ["Save", "Spend", "Wait"], "answer_index": 0,'
    ' "explanation": "You should buy Apple stock right now."}'
)

SAFE_QUIZ_JSON = (
    '{"question": "If you save 20% of £20, how much is that?",'
    ' "choices": ["£2", "£4", "£10"], "answer_index": 1,'
    ' "explanation": "20% of £20 is £4, a smart amount to save."}'
)


async def test_generate_practice_quiz_blocks_unsafe_and_falls_back(db_session, lesson_fixture):
    from sqlalchemy import select

    from app.models.audit import AuditLog

    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=UNSAFE_QUIZ_JSON)

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )

    # Unsafe model quiz rejected → deterministic _fallback(content) shape.
    expected = _fallback(quiz.content_json)
    assert set(result["choices"]) == set(expected["choices"])
    assert result["question"] == expected["question"]
    assert result["explanation"] == expected["explanation"]
    assert result["choices"][result["answer_index"]] == expected["choices"][expected["answer_index"]]
    assert "You should buy Apple" not in json.dumps(result)

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == "moderation_block")
        )
    ).scalars().all()
    # Regenerate-once loop blocks on both attempts → one row per blocked attempt.
    assert len(rows) == 2
    for row in rows:
        assert row.user_id is None
        assert row.metadata_json["surface"] == "quiz"
        assert row.metadata_json["category"] == "financial_advice"
        assert "You should buy Apple" not in json.dumps(row.metadata_json)


async def test_generate_practice_quiz_safe_passes_through(db_session, lesson_fixture):
    from sqlalchemy import select

    from app.models.audit import AuditLog

    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=SAFE_QUIZ_JSON)

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )

    assert result["question"] == "If you save 20% of £20, how much is that?"
    assert result["explanation"] == "20% of £20 is £4, a smart amount to save."

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == "moderation_block")
        )
    ).scalars().all()
    assert rows == []
