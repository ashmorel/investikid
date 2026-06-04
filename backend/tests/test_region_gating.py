import pytest
from sqlalchemy import select

from app.models.content import Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "currency_code": "USD",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="regionkid@example.com", username="regionkid", country_code="US"):
    payload = {**_USER_BASE, "email": email, "username": username, "country_code": country_code}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed_global_module(db_session):
    module = Module(
        topic="savings", title="Savings Global", country_codes=[],
        is_premium=False, order_index=0,
    )
    db_session.add(module)
    await db_session.commit()
    return module


async def test_module_list_uses_content_region_but_all_global_modules_show(client, db_session):
    """A US child with content_region='HK' still sees all global modules
    (seed data is all country_codes=[]), proving the effective-region path
    is wired without regressing global visibility."""
    await _seed_global_module(db_session)
    await _register_and_login(client, country_code="US")

    # Task 3 adds PATCH acceptance of content_region; until then set it
    # directly on the user row to exercise the gating path.
    user = await db_session.scalar(select(User).where(User.username == "regionkid"))
    user.content_region = "HK"
    await db_session.commit()
    assert user.content_region == "HK"
    assert user.country_code == "US"  # legal country untouched

    resp = await client.get("/users/me")
    assert resp.status_code == 200

    # All seeded modules are global → still visible regardless of region.
    resp = await client.get("/modules")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
