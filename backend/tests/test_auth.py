import pytest

REGISTER_URL = "/auth/register"

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_register_success(client):
    response = await client.post(REGISTER_URL, json={
        "email": "alice@example.com",
        "username": "alice123",
        "password": "SecurePass123!",
        "dob": "2008-03-15",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password_hash" not in data


async def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "bob@example.com",
        "username": "bob1",
        "password": "SecurePass123!",
        "dob": "2008-03-15",
        "country_code": "US",
        "currency_code": "USD",
        "parent_email": "bobparent@example.com",
    }
    await client.post(REGISTER_URL, json=payload)
    response = await client.post(REGISTER_URL, json=payload)
    assert response.status_code == 409


async def test_register_under_18_without_parent_email_rejected(client):
    response = await client.post(REGISTER_URL, json={
        "email": "young@example.com",
        "username": "younguser",
        "password": "SecurePass123!",
        "dob": "2015-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
    })
    assert response.status_code == 422
