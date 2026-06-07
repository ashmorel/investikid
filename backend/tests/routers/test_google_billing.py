import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup_parent(client, db_session, parent_email="google@example.com",
                        child_email="googlekid@example.com",
                        child_username="googlekid"):
    """Create child + parent magic-link session (mirrors test_apple_billing)."""
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


async def test_google_verify_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.post("/billing/google/verify", json={"purchaseToken": "x", "productId": "p"})
    assert r.status_code in (401, 403)


async def test_google_notifications_csrf_exempt_and_dispatches(client):
    client.cookies.clear()
    with patch("app.routers.billing.google_billing_service.handle_notification", new=AsyncMock()) as m:
        r = await client.post("/billing/google/notifications", json={"message": {"data": "e30="}})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    m.assert_awaited_once()


async def test_google_verify_authenticated(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="gverify@example.com", child_username="gverify",
                        parent_email="gverify-parent@example.com")
    with patch("app.routers.billing.google_billing_service.verify_purchase",
               new=AsyncMock()) as m:
        r = await client.post(
            "/billing/google/verify",
            json={"purchaseToken": "TOK", "productId": "premium_monthly"},
            headers=_csrf_headers(client),
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    m.assert_awaited_once()


async def test_account_token_authenticated(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="gtoken@example.com", child_username="gtoken",
                        parent_email="gtoken-parent@example.com")
    r = await client.get("/billing/account-token")
    assert r.status_code == 200
    uuid.UUID(r.json()["token"])
