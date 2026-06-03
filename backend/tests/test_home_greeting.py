from datetime import date

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")

_BODY = {
    "name": "Sam",
    "mode": "start",
    "lesson_label": "What is a Stock?",
    "streak_count": 0,
    "due_count": 0,
}


@pytest_asyncio.fixture
async def premium_client(db_session, client):
    user = User(
        email="homegreet_premium@example.com",
        username="homegreetpremium",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_premium=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    await db_session.flush()

    response = await client.post(
        "/auth/login",
        json={"email": "homegreet_premium@example.com", "password": "TestPassword123!"},
    )
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client


@pytest_asyncio.fixture
async def free_client(db_session, client):
    user = User(
        email="homegreet_free@example.com",
        username="homegreetfree",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    await db_session.flush()

    response = await client.post(
        "/auth/login",
        json={"email": "homegreet_free@example.com", "password": "TestPassword123!"},
    )
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client


async def test_home_greeting_premium_returns_greeting(premium_client, monkeypatch):
    async def fake_gen(**kwargs):
        return "Let's go, Sam!"

    monkeypatch.setattr("app.routers.ai.generate_home_greeting", fake_gen)
    r = await premium_client.post("/home-greeting", json=_BODY)
    assert r.status_code == 200
    assert r.json()["greeting"] == "Let's go, Sam!"


async def test_home_greeting_non_premium_403(free_client):
    r = await free_client.post("/home-greeting", json=_BODY)
    assert r.status_code == 403


async def test_home_greeting_provider_failure_503(premium_client, monkeypatch):
    async def boom(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.routers.ai.generate_home_greeting", boom)
    r = await premium_client.post("/home-greeting", json=_BODY)
    assert r.status_code == 503
