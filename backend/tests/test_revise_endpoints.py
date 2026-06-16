from datetime import date

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def child_client(db_session, client):
    """Authenticated child session: creates a user and logs in via /auth/login,
    which sets the access_token + csrf_token cookies on the shared client."""
    user = User(
        email="revise@example.com", username="revisekid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    await db_session.flush()

    response = await client.post("/auth/login", json={
        "email": "revise@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, user


async def test_revise_modules_requires_auth(client):
    resp = await client.get("/revise/modules")
    assert resp.status_code in (401, 403)


async def test_revise_modules_empty_for_new_user(child_client):
    client, _user = child_client
    resp = await client.get("/revise/modules")
    assert resp.status_code == 200
    assert resp.json() == []
