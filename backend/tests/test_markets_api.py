import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REGISTER_PAYLOAD = {
    "email": "markets_api_user@example.com",
    "username": "markets_api_user",
    "password": "SecurePass123!",
    "dob": "2008-03-15",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "markets_api_parent@example.com",
}


async def _login(client):
    """Register (idempotent) + login so the client has an auth cookie."""
    await client.post("/auth/register", json=_REGISTER_PAYLOAD)
    await client.post(
        "/auth/login",
        json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_list_markets(client):
    await _login(client)
    rows = (await client.get("/markets")).json()
    by_code = {m["code"]: m for m in rows}
    assert set(by_code) == {"GB", "US", "AU", "CA", "IE", "ES", "FR", "DE", "HK", "SG"}
    assert by_code["GB"]["has_content"] is True
    assert by_code["US"]["has_content"] is False
    assert by_code["GB"]["is_active"] is True
    # GB enrolled = True because registration calls ensure_enrolled(home_market_code)
    assert by_code["GB"]["enrolled"] is True


async def test_switch_active_market_lazy_enrolls(client):
    await _login(client)
    r = await client.post("/me/active-market", json={"market_code": "US"})
    assert r.status_code == 200
    assert r.json()["active_market_code"] == "US"
    rows = {m["code"]: m for m in (await client.get("/markets")).json()}
    assert rows["US"]["is_active"] is True
    assert rows["US"]["enrolled"] is True


async def test_switch_unknown_market_422(client):
    await _login(client)
    r = await client.post("/me/active-market", json={"market_code": "ZZ"})
    assert r.status_code == 422


async def test_my_market_progress(client):
    await _login(client)
    r = await client.get("/me/markets")
    assert r.status_code == 200
    data = r.json()
    assert "markets" in data
    assert "total_xp" in data
    assert "level" in data
    # GB should be enrolled after registration
    codes = {m["market_code"] for m in data["markets"]}
    assert "GB" in codes
