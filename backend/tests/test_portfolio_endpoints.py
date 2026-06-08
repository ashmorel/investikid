import pytest

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


async def _login(client, email="ccfx@example.com", username="ccfx"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_set_currency_rejects_unsupported(client):
    await _login(client, email="ccfx1@example.com", username="ccfx1")
    resp = await client.post("/portfolio/currency", json={"currency_code": "EUR"})
    assert resp.status_code == 422


async def test_set_currency_happy_path(client):
    await _login(client, email="ccfx2@example.com", username="ccfx2")
    resp = await client.post("/portfolio/currency", json={"currency_code": "GBP"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency_code"] == "GBP"
    assert "virtual_cash" in body and "id" in body


async def test_reset_requires_auth(client):
    resp = await client.post("/portfolio/reset")
    assert resp.status_code == 403


async def test_reset_happy_path(client):
    await _login(client, email="ccfx3@example.com", username="ccfx3")
    resp = await client.post("/portfolio/reset")
    assert resp.status_code == 200
    assert "currency_code" in resp.json()
