from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services import apple_billing_service
from app.services.apple_billing_service import household_token

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

# A child (age ~9, GB) with a parent_email — so household_key resolves to the
# parent. currency_code drives the /child/plans currency.
_CHILD = {
    "password": "SecurePass123!",
    "dob": "2016-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "Billing.Parent@Example.com",
}
_EXPECTED_SCOPE = "billing.parent@example.com"  # household_key lowercases


async def _register_and_login(
    client, db_session, email="billingchild@example.com", username="billingchild"
):
    """Register an age-9 GB child (which enters pending_consent), grant consent
    so the account is active, then log in. household_key(child) → parent_email."""
    payload = {**_CHILD, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    user = await db_session.scalar(select(User).where(User.email == email))
    user.is_active = True
    user.parent_consent_given_at = datetime.now(UTC)
    await db_session.commit()
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_child_apple_account_token(client, db_session):
    await _register_and_login(
        client, db_session, email="capple@example.com", username="capple"
    )
    r = await client.get("/billing/child/apple/account-token")
    assert r.status_code == 200
    assert r.json()["token"] == household_token(_EXPECTED_SCOPE)


async def test_child_account_token(client, db_session):
    await _register_and_login(
        client, db_session, email="cgtoken@example.com", username="cgtoken"
    )
    r = await client.get("/billing/child/account-token")
    assert r.status_code == 200
    assert r.json()["token"] == household_token(_EXPECTED_SCOPE)


async def test_child_plans(client, db_session):
    await _register_and_login(
        client, db_session, email="cplans@example.com", username="cplans"
    )
    r = await client.get("/billing/child/plans")
    assert r.status_code == 200
    body = r.json()
    assert body["currency"] == "GBP"
    assert body["plans"]
    for plan in body["plans"]:
        assert plan["apple_product_id"]
        assert plan["google_product_id"]


async def test_child_apple_verify(client, db_session):
    await _register_and_login(
        client, db_session, email="caverify@example.com", username="caverify"
    )
    with patch.object(
        apple_billing_service, "verify_transaction", new=AsyncMock()
    ) as mock_verify:
        r = await client.post("/billing/child/apple/verify", json={"jws": "x"})
    assert r.status_code == 200
    mock_verify.assert_awaited_once()
    assert mock_verify.await_args.kwargs["parent_email"] == _EXPECTED_SCOPE
    assert mock_verify.await_args.kwargs["jws"] == "x"


async def test_child_google_verify(client, db_session):
    await _register_and_login(
        client, db_session, email="cgverify@example.com", username="cgverify"
    )
    from app.services import google_billing_service

    with patch.object(
        google_billing_service, "verify_purchase", new=AsyncMock()
    ) as mock_verify:
        r = await client.post(
            "/billing/child/google/verify",
            json={"purchaseToken": "t", "productId": "premium_monthly"},
        )
    assert r.status_code == 200
    mock_verify.assert_awaited_once()
    assert mock_verify.await_args.kwargs["parent_email"] == _EXPECTED_SCOPE
    assert mock_verify.await_args.kwargs["purchase_token"] == "t"
    assert mock_verify.await_args.kwargs["product_id"] == "premium_monthly"


async def test_child_apple_account_token_unauthenticated(client):
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    r = await client.get("/billing/child/apple/account-token")
    assert r.status_code == 401
