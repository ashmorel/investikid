import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"

_BASE = {
    "password": "SecurePass123!",
    "dob": "2006-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email, username):
    await client.post(_REGISTER_URL, json={**_BASE, "email": email, "username": username})
    await client.post(_LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_new_user_defaults_to_english(client):
    await _register_and_login(client, "lang_default@example.com", "langdefault")
    me = (await client.get("/users/me")).json()
    assert me["language"] == "en"


async def test_patch_language_persists(client):
    await _register_and_login(client, "lang_patch@example.com", "langpatch")
    r = await client.patch("/users/me/language", json={"language": "zh-Hant"})
    assert r.status_code == 200
    assert r.json()["language"] == "zh-Hant"
    assert (await client.get("/users/me")).json()["language"] == "zh-Hant"


async def test_patch_rejects_unknown_language(client):
    await _register_and_login(client, "lang_reject@example.com", "langreject")
    r = await client.patch("/users/me/language", json={"language": "xx"})
    assert r.status_code == 422
