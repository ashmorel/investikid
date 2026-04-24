import pytest

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

pytestmark = pytest.mark.asyncio(loop_scope="session")

_BASE = {
    "password": "SecurePass123!",
    "dob": "2006-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="me@example.com", username="meuser"):
    await client.post(REGISTER_URL, json={**_BASE, "email": email, "username": username})
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_get_profile_authenticated(client):
    await _register_and_login(client)
    response = await client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "password_hash" not in data


async def test_get_profile_unauthenticated(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_update_country_and_currency(client):
    await _register_and_login(client, "update@example.com", "updateuser")
    response = await client.patch("/users/me", json={"country_code": "US", "currency_code": "USD"})
    assert response.status_code == 200
    assert response.json()["country_code"] == "US"
    assert response.json()["currency_code"] == "USD"


async def test_update_topic_path(client):
    await _register_and_login(client, "topic@example.com", "topicuser")
    response = await client.patch("/users/me", json={"topic_path": "stocks"})
    assert response.status_code == 200
    assert response.json()["topic_path"] == "stocks"
