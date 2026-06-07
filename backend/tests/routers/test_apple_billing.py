import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup_parent(client, db_session, parent_email="apple@example.com",
                        child_email="applekid@example.com",
                        child_username="applekid"):
    """Create child + parent magic-link session (mirrors test_billing)."""
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


async def test_verify_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.post("/billing/apple/verify", json={"jws": "x"})
    assert r.status_code in (401, 403)


async def test_account_token_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.get("/billing/apple/account-token")
    assert r.status_code in (401, 403)


@patch("app.routers.billing.apple_billing_service.verify_transaction",
       new_callable=AsyncMock)
async def test_verify_authenticated(mock_verify, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="averify@example.com", child_username="averify",
                        parent_email="averify-parent@example.com")
    r = await client.post(
        "/billing/apple/verify",
        json={"jws": "signed"},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    mock_verify.assert_awaited_once()


async def test_account_token_authenticated(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="atoken@example.com", child_username="atoken",
                        parent_email="atoken-parent@example.com")
    r = await client.get("/billing/apple/account-token")
    assert r.status_code == 200
    # token must parse as a UUID
    uuid.UUID(r.json()["token"])
