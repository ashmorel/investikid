"""A05-1: POST /tutor/chat is session-authenticated and mutating, so it must
NOT be exempt from the CSRF double-submit check."""
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.content import Lesson, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def logged_in(db_session, client):
    user = User(
        email="csrf@example.com", username="csrfkid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    module = Module(
        topic="stocks", title="Stocks", country_codes=[],
        is_premium=False, order_index=0, icon="X",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={"question": "Q", "choices": ["A", "B"],
                      "answer_index": 0, "explanation": "E"},
    )
    db_session.add(quiz)
    await db_session.flush()
    resp = await client.post(
        "/auth/login", json={"email": "csrf@example.com", "password": "TestPassword123!"}
    )
    assert resp.status_code == 200
    return client, quiz


async def test_tutor_chat_rejects_request_without_csrf_header(logged_in):
    client, quiz = logged_in
    # Authenticated (cookies set by login) but NO X-CSRF-Token header — a
    # cross-site forged request would look exactly like this.
    client.headers.pop("X-CSRF-Token", None)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="hi")
    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        resp = await client.post(
            "/tutor/chat",
            json={"lesson_id": str(quiz.id), "message": "What is a stock?"},
        )
    assert resp.status_code == 403, (
        f"authed mutating /tutor/chat must enforce CSRF (got {resp.status_code})"
    )
