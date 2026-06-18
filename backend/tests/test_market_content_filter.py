import pytest

from app.services.content_service import is_module_in_market, is_module_premium_ok


def test_is_module_in_market():
    assert is_module_in_market("GB", "GB") is True
    assert is_module_in_market("US", "GB") is False


def test_is_module_premium_ok():
    assert is_module_premium_ok(module_is_premium=False, is_premium_user=False) is True
    assert is_module_premium_ok(module_is_premium=True, is_premium_user=False) is False
    assert is_module_premium_ok(module_is_premium=True, is_premium_user=True) is True


@pytest.mark.asyncio(loop_scope="session")
async def test_gb_user_sees_gb_modules_not_us(client, db_session):
    from app.models.content import Module

    # Register + login a GB user (home_market_code defaults to "GB")
    payload = {
        "email": "market_filter_test@example.com",
        "username": "marketfilteruser",
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "mf_parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    db_session.add(Module(
        topic="savings", title="GB Module C1", country_codes=[], is_premium=False,
        order_index=900, icon="💷", market_code="GB",
    ))
    db_session.add(Module(
        topic="savings", title="US Module C1", country_codes=[], is_premium=False,
        order_index=901, icon="💵", market_code="US",
    ))
    await db_session.flush()

    titles = [m["title"] for m in (await client.get("/modules")).json()]
    assert "GB Module C1" in titles
    assert "US Module C1" not in titles
