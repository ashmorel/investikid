import pytest
from sqlalchemy import select

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username="startedkid"):
    """Register + login a GB child and return the User row (mirrors the
    markets-test pattern)."""
    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"{username}_parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return await db_session.scalar(select(User).where(User.username == username))


async def test_started_market_code_defaults_null_and_settable(client, db_session):
    user = await _register_child(client, db_session)
    assert user.started_market_code is None

    user.started_market_code = "GB"
    await db_session.flush()

    fetched = await db_session.get(User, user.id)
    assert fetched.started_market_code == "GB"
