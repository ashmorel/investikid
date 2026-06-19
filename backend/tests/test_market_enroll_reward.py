import pytest
from sqlalchemy import select

from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username="enrollkid", email=None):
    """Register + login a GB child (home_market_code = active_market_code = "GB"),
    set the CSRF header, and return the User row. Mirrors the markets-test pattern."""
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


async def test_switch_to_new_nonhome_market_grants_enroll_coins_once(client, db_session):
    child = await _register_child(client, db_session, username="enrollkid")
    prog = await db_session.get(UserProgress, child.id)
    start = (prog.virtual_coins or 0) if prog else 0

    r1 = await client.post("/me/active-market", json={"market_code": "US"})
    assert r1.status_code == 200
    assert r1.json()["reward"]["coins"] == 25

    prog = await db_session.get(UserProgress, child.id)
    await db_session.refresh(prog)
    assert (prog.virtual_coins or 0) == start + 25
    row = await db_session.get(UserMarketProgress, (child.id, "US"))
    assert row.enroll_rewarded_at is not None

    r2 = await client.post("/me/active-market", json={"market_code": "US"})
    assert r2.json()["reward"]["coins"] == 0


async def test_switch_to_home_market_grants_nothing(client, db_session):
    await _register_child(client, db_session, username="homekid")
    r = await client.post("/me/active-market", json={"market_code": "GB"})
    assert r.json()["reward"]["coins"] == 0
