import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

_BASE = {
    "password": "SecurePass123!",
    "dob": "2006-05-10",
    "parent_email": "parent@example.com",
}


async def _register_child(
    client,
    *,
    country_code="US",
    currency_code="USD",
    email="region@example.com",
    username="regionuser",
):
    await client.post(
        REGISTER_URL,
        json={
            **_BASE,
            "email": email,
            "username": username,
            "country_code": country_code,
            "currency_code": currency_code,
        },
    )
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_patch_accepts_valid_content_region(client):
    await _register_child(client, country_code="US", currency_code="USD")
    resp = await client.patch("/users/me", json={"content_region": "GB"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_region"] == "GB"
    assert body["country_code"] == "US"  # legal country untouched


async def test_patch_rejects_unsupported_region(client):
    await _register_child(
        client,
        country_code="US",
        currency_code="USD",
        email="region2@example.com",
        username="regionuser2",
    )
    resp = await client.patch("/users/me", json={"content_region": "FR"})
    assert resp.status_code == 422


async def test_patch_currency_still_works_independently(client):
    await _register_child(
        client,
        country_code="US",
        currency_code="USD",
        email="region3@example.com",
        username="regionuser3",
    )
    resp = await client.patch("/users/me", json={"currency_code": "HKD"})
    assert resp.status_code == 200
    assert resp.json()["currency_code"] == "HKD"
    # content_region not set by a currency change
    assert resp.json()["content_region"] is None
