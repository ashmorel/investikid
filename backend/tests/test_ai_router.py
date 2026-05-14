from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.content import Lesson, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def auth_client(db_session, client):
    user = User(
        email="ai@example.com", username="aikid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    db_session.add(progress)
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
    await db_session.flush()

    # Log in
    response = await client.post("/auth/login", json={
        "email": "ai@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, user, module, quiz


async def test_get_recommendations(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "next_quest" in data
    assert "suggested_modules" in data


async def test_get_mastery_profile(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/profile/mastery")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "weak_concepts" in data


async def test_practice_quiz_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=(
        '{"question": "New Q", "choices": ["A", "B", "C"], "answer_index": 0, "explanation": "E"}'
    ))

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            f"/lessons/{quiz.id}/practice",
            json={"wrong_answer_index": 0},
        )
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "choices" in data


async def test_tutor_chat_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="A stock is a small piece of a company!")

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/chat", json={
            "lesson_id": str(quiz.id),
            "message": "What is a stock?",
        })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "messages_remaining" in data
