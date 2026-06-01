import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_and_login(client, email="normaluser@example.com", username="normaluser"):
    """Register + log in a normal (non-admin) user; sets cookies + CSRF header."""
    payload = {
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2010-05-10",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": email, "password": payload["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_admin_stats_anonymous_unauthorized(client):
    """Anonymous (no session) → 401."""
    resp = await client.get("/admin/stats")
    assert resp.status_code == 401


async def test_admin_stats_non_admin_forbidden(client):
    """Authenticated but non-admin user → 403."""
    await _register_and_login(client)
    resp = await client.get("/admin/stats")
    assert resp.status_code == 403


async def test_admin_stats_admin_ok(admin_client):
    """Authenticated admin → 200 with stats payload."""
    resp = await admin_client.get("/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "modules" in data
    assert "lessons" in data
    assert "badges" in data
    assert "challenges" in data


async def test_admin_mutation_rejected_without_csrf(admin_client):
    """Admin mutation without the X-CSRF-Token header is rejected (403)."""
    admin_client.headers.pop("X-CSRF-Token", None)
    resp = await admin_client.post("/admin/modules", json={
        "topic": "csrf_test", "title": "CSRF Test", "icon": "🔒",
        "is_premium": False, "country_codes": [], "order_index": 0,
    })
    assert resp.status_code == 403
