from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.content import Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def coach_client(db_session, client):
    user = User(
        email="coach@example.com", username="coachkid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    db_session.add(progress)
    module = Module(
        topic="stocks", title="Stocks 101",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()

    response = await client.post("/auth/login", json={
        "email": "coach@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, user, module


async def test_coach_chat_returns_response(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value="Try Stocks 101! [ACTION:module:" + str(module.id) + "]"
    )

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/coach", json={
            "message": "What should I learn?",
        })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "messages_remaining" in data
    assert "actions" in data
    assert isinstance(data["actions"], list)


async def test_coach_chat_parses_action(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value="Go here [ACTION:module:" + str(module.id) + "]"
    )

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/coach", json={
            "message": "What next?",
        })
    data = response.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["type"] == "module"
    assert data["actions"][0]["module_id"] == str(module.id)
    assert "Stocks 101" in data["actions"][0]["label"]
    assert "[ACTION:" not in data["response"]


async def test_coach_chat_continues_conversation(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="Sure!")

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        r1 = await client.post("/tutor/coach", json={"message": "Hi"})
        cid = r1.json()["conversation_id"]
        r2 = await client.post("/tutor/coach", json={
            "message": "Tell me more",
            "conversation_id": cid,
        })
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == cid
