import pytest
from sqlalchemy import select

from app.models.content import Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_content_follows_active_market_not_home(client, db_session):
    # Register + login a GB user (home_market_code = active_market_code = "GB" by default)
    payload = {
        "email": "active_market_test@example.com",
        "username": "activemarketuser",
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "am_parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    db_session.add(Module(
        topic="savings", title="GB Mod C2a", country_codes=[],
        is_premium=False, order_index=950, icon="💷", market_code="GB",
    ))
    db_session.add(Module(
        topic="savings", title="US Mod C2a", country_codes=[],
        is_premium=False, order_index=951, icon="💵", market_code="US",
    ))
    await db_session.flush()

    titles = [m["title"] for m in (await client.get("/modules")).json()]
    assert "GB Mod C2a" in titles and "US Mod C2a" not in titles  # default active = GB

    # Switch active_market_code to US
    current_user_row = await db_session.scalar(
        select(User).where(User.username == "activemarketuser")
    )
    current_user_row.active_market_code = "US"
    await db_session.flush()

    titles = [m["title"] for m in (await client.get("/modules")).json()]
    assert "US Mod C2a" in titles and "GB Mod C2a" not in titles  # follows active
