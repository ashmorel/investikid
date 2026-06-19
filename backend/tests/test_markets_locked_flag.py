import pytest
from sqlalchemy import select

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username, email=None):
    """Register + login a GB child, set the CSRF header, return the User row.
    Mirrors backend/tests/test_market_enroll_reward.py."""
    email = email or f"{username}@example.com"
    payload = {
        "email": email,
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


async def test_free_started_market_locks_others(client, db_session):
    child = await _register_child(client, db_session, username="lockedfreekid")
    child.started_market_code = "GB"
    child.is_premium = False
    await db_session.commit()

    r = await client.get("/markets")
    assert r.status_code == 200
    by = {m["code"]: m for m in r.json()}
    assert by["GB"]["locked"] is False
    # any non-GB active market is locked for a free user started in GB
    non_gb = [code for code in by if code != "GB"]
    assert non_gb, "expected at least one non-GB market in the list"
    assert all(by[code]["locked"] is True for code in non_gb)


async def test_premium_user_nothing_locked(client, db_session):
    child = await _register_child(client, db_session, username="lockedpremiumkid")
    child.started_market_code = "GB"
    child.is_premium = True
    await db_session.commit()

    r = await client.get("/markets")
    assert r.status_code == 200
    assert all(m["locked"] is False for m in r.json())
