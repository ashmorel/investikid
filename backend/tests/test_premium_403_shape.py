import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REG = {"password": "SecurePass123!", "dob": "2010-05-10", "country_code": "GB",
       "currency_code": "GBP", "parent_email": "g403-parent@example.com"}


async def _login(client, email="g403-child@example.com", username="g403child"):
    await client.post("/auth/register", json={**REG, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_premium_ticker_403_is_structured(client):
    await _login(client)
    resp = await client.post("/portfolio/trades",
                             json={"ticker": "0700", "exchange": "HKEX", "type": "buy", "shares": "1"})
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "premium_required"
    assert detail["context"]["kind"] == "ticker"
