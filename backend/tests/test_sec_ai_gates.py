"""Security gate tests for ai.py: premium gate on practice_quiz and tutor_chat.

TDD — these tests must FAIL before the fix (current code only calls
is_module_visible, missing the premium gate) and PASS after.
"""
from datetime import date

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.content import Lesson, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def sec_client(db_session, client):
    """Create a free user + premium module + lesson, log in, return (client, lesson_id)."""
    user = User(
        email="sec_gate@example.com",
        username="secgatekid",
        password_hash=hash_password("SecGate123!"),
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        active_market_code="GB",
        is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()

    progress = UserProgress(user_id=user.id)
    db_session.add(progress)

    # Published premium module in GB market
    module = Module(
        topic="investing",
        title="Premium Module",
        market_code="GB",
        is_premium=True,
        published=True,
        order_index=0,
        icon="💎",
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=25,
        order_index=0,
        content_json={
            "question": "What is a share?",
            "choices": ["A loan", "Part of a company", "A bond"],
            "answer_index": 1,
            "explanation": "A share is a slice of a company.",
        },
    )
    db_session.add(lesson)
    await db_session.flush()

    response = await client.post(
        "/auth/login",
        json={"email": "sec_gate@example.com", "password": "SecGate123!"},
    )
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, lesson


async def test_practice_quiz_premium_module_free_user(sec_client):
    """Free user must get 403 when accessing a premium module via practice_quiz."""
    client, lesson = sec_client
    response = await client.post(
        f"/lessons/{lesson.id}/practice",
        json={"wrong_answer_index": 0},
    )
    assert response.status_code == 403, (
        f"Expected 403 (premium gate), got {response.status_code}: {response.text}"
    )


async def test_tutor_chat_premium_module_free_user(sec_client):
    """Free user must get 403 when accessing a premium module via tutor_chat."""
    client, lesson = sec_client
    response = await client.post(
        "/tutor/chat",
        json={"lesson_id": str(lesson.id), "message": "hi"},
    )
    assert response.status_code == 403, (
        f"Expected 403 (premium gate), got {response.status_code}: {response.text}"
    )
