"""Tests for the admin /settings endpoints (GET + PUT) and related service."""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── HTTP endpoint tests ──────────────────────────────────────────────

async def test_get_settings_returns_list(admin_client):
    """GET /admin/settings returns a dict with alert_emails as a list."""
    resp = await admin_client.get("/admin/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "alert_emails" in data
    assert isinstance(data["alert_emails"], list)


async def test_put_settings_persists_and_get_reflects(admin_client):
    """PUT with valid emails → 200; subsequent GET returns the same list."""
    emails = ["ops@example.com", "cto@example.com"]
    resp = await admin_client.put("/admin/settings", json={"alert_emails": emails})
    assert resp.status_code == 200
    assert set(resp.json()["alert_emails"]) == set(emails)

    resp2 = await admin_client.get("/admin/settings")
    assert resp2.status_code == 200
    assert set(resp2.json()["alert_emails"]) == set(emails)


async def test_put_settings_rejects_invalid_email(admin_client):
    """PUT with a non-email value → 422."""
    resp = await admin_client.put("/admin/settings", json={"alert_emails": ["not-an-email"]})
    assert resp.status_code == 422


async def test_put_settings_deduplicate(admin_client):
    """Duplicate emails (case-insensitive) are collapsed to one entry."""
    resp = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": ["A@Example.com", "a@example.com", "B@EXAMPLE.COM"]},
    )
    assert resp.status_code == 200
    result = resp.json()["alert_emails"]
    # Should have deduplicated to 2 unique addresses
    assert len(result) == 2
    lower = [e.lower() for e in result]
    assert "a@example.com" in lower
    assert "b@example.com" in lower


async def test_put_settings_rejects_too_many_emails(admin_client):
    """PUT with more than 10 emails → 422."""
    emails = [f"user{i}@example.com" for i in range(11)]
    resp = await admin_client.put("/admin/settings", json={"alert_emails": emails})
    assert resp.status_code == 422


async def test_settings_requires_admin(client):
    """A normal authenticated user (not admin) cannot access /admin/settings."""
    # Register and log in as a normal user
    await client.post("/auth/register", json={
        "email": "normal@example.com",
        "username": "normaluser",
        "password": "SecurePass123!",
        "dob": "2010-05-10",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent2@example.com",
    })
    await client.post("/auth/login", json={
        "email": "normal@example.com",
        "password": "SecurePass123!",
    })
    resp = await client.get("/admin/settings")
    assert resp.status_code == 403
