import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
REFRESH_URL = "/auth/refresh"

_BASE_USER = {
    "password": "SecurePass123!",
    "dob": "2006-01-01",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email: str, username: str):
    await client.post(REGISTER_URL, json={**_BASE_USER, "email": email, "username": username})
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})


async def test_login_sets_csrf_cookie(client):
    await client.post(
        REGISTER_URL,
        json={**_BASE_USER, "email": "csrf1@example.com", "username": "csrf1user"},
    )
    resp = await client.post(
        LOGIN_URL, json={"email": "csrf1@example.com", "password": "SecurePass123!"}
    )
    assert resp.status_code == 200
    assert client.cookies.get("csrf_token")


async def test_login_without_csrf_succeeds_exempt(client):
    # /auth/login is exempt — no CSRF header needed for the initial login.
    await client.post(
        REGISTER_URL,
        json={**_BASE_USER, "email": "exempt@example.com", "username": "exemptuser"},
    )
    resp = await client.post(
        LOGIN_URL, json={"email": "exempt@example.com", "password": "SecurePass123!"}
    )
    assert resp.status_code == 200


async def test_get_me_no_csrf_header_succeeds(client):
    await _register_and_login(client, "get@example.com", "getuser")
    # GET is a safe method and exempt from CSRF — no header required.
    resp = await client.get("/users/me")
    assert resp.status_code == 200


async def test_patch_without_csrf_header_rejected(client):
    await _register_and_login(client, "patch@example.com", "patchuser")
    # Do NOT attach the X-CSRF-Token header.
    resp = await client.patch(
        "/users/me",
        json={"country_code": "US"},
        headers={},  # no CSRF header
    )
    assert resp.status_code == 403


async def test_patch_with_mismatched_csrf_rejected(client):
    await _register_and_login(client, "mismatch@example.com", "mismatchu")
    resp = await client.patch(
        "/users/me",
        json={"country_code": "US"},
        headers={"X-CSRF-Token": "not-the-right-token"},
    )
    assert resp.status_code == 403


async def test_patch_with_matching_csrf_succeeds(client):
    await _register_and_login(client, "ok@example.com", "okuser")
    csrf = client.cookies.get("csrf_token")
    assert csrf
    resp = await client.patch(
        "/users/me",
        json={"country_code": "US"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200


async def test_refresh_without_csrf_header_rejected(client):
    await _register_and_login(client, "refr@example.com", "refruser")
    # Explicitly bypass any default headers set on the client.
    resp = await client.post(REFRESH_URL, headers={})
    assert resp.status_code == 403
