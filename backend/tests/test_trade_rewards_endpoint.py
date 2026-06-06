import pytest

from app.services.simulator_rewards_config import SIM_XP_PER_TRADE

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _login(client, email="rewards@example.com", username="rewardstrader"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_buy_returns_rewards_block(client):
    await _login(client)
    resp = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "VOD"  # trade fields still present
    assert "rewards" in body
    # Fresh account, first trade of the day: deterministic full XP + streak start.
    assert body["rewards"]["xp_awarded"] == SIM_XP_PER_TRADE
    assert body["rewards"]["streak_extended"] is True
    assert body["rewards"]["missions_completed"] == []
