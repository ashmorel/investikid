from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.tutor_service import (
    TutorInputTooLong,
    chat,
    safety_filter,
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


def test_safety_filter_catches_financial_advice():
    dangerous = "You should buy Apple stock right now, it's going up!"
    filtered = safety_filter(dangerous)
    assert "parent or teacher" in filtered.lower()


def test_safety_filter_passes_clean_response():
    clean = "A stock is a small piece of a company. If the company does well, your stock can be worth more!"
    assert safety_filter(clean) == clean
