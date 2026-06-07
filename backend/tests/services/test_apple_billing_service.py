import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.subscription import Subscription
from app.models.user import User
from app.services import apple_billing_service as abs_
from app.services.entitlements import is_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeVerifier:
    def __init__(self, payload):
        self._p = payload

    def verify_and_decode_signed_transaction(self, jws):
        return self._p


def _payload(**kw):
    base = dict(
        originalTransactionId="OT-1",
        productId="premium_monthly",
        appAccountToken=abs_.household_token("a@example.com"),
        expiresDate=int((datetime.now(UTC).timestamp() + 86400) * 1000),
        revocationDate=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


async def _child(db_session, email):
    u = User(
        username=f"kid-{email}",
        email=f"kid-{email}",
        parent_email=email,
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_verify_records_subscription_and_grants(db_session, monkeypatch):
    email = "a@example.com"
    child = await _child(db_session, email)
    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(abs_, "_build_verifier", lambda: _FakeVerifier(_payload()))
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")
    await abs_.verify_transaction(db_session, parent_email=email, jws="signed-jws")
    row = await db_session.scalar(
        select(Subscription).where(
            Subscription.provider == "apple", Subscription.external_id == "OT-1"
        )
    )
    assert row is not None and row.status == "active" and row.parent_email == email
    assert is_premium(child) is True


async def test_verify_rejects_token_parent_mismatch(db_session, monkeypatch):
    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(
        abs_, "_build_verifier",
        lambda: _FakeVerifier(
            _payload(appAccountToken="00000000-0000-0000-0000-000000000000")
        ),
    )
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")
    with pytest.raises(abs_.AppleBillingError):
        await abs_.verify_transaction(db_session, parent_email="a@example.com", jws="x")


async def test_verify_rejects_non_configured_product(db_session, monkeypatch):
    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(abs_.settings, "apple_iap_product_id", "premium_monthly")
    monkeypatch.setattr(
        abs_, "_build_verifier",
        lambda: _FakeVerifier(_payload(productId="something_else")),
    )
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")
    with pytest.raises(abs_.AppleBillingError):
        await abs_.verify_transaction(db_session, parent_email="a@example.com", jws="x")


async def test_verify_accepts_matching_product(db_session, monkeypatch):
    email = "match@example.com"
    child = await _child(db_session, email)
    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(abs_.settings, "apple_iap_product_id", "premium_monthly")
    monkeypatch.setattr(
        abs_, "_build_verifier",
        lambda: _FakeVerifier(
            _payload(
                productId="premium_monthly",
                appAccountToken=abs_.household_token(email),
            )
        ),
    )
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")
    await abs_.verify_transaction(db_session, parent_email=email, jws="signed-jws")
    row = await db_session.scalar(
        select(Subscription).where(
            Subscription.provider == "apple", Subscription.external_id == "OT-1"
        )
    )
    assert row is not None and row.status == "active"
    assert is_premium(child) is True


class _FakeNotificationVerifier:
    """Fake SignedDataVerifier for App Store Server Notifications V2."""

    def __init__(self, tx_payload, signed_tx="tx-jws"):
        self._tx = tx_payload
        self._signed_tx = signed_tx

    def verify_and_decode_notification(self, signed_payload):
        return SimpleNamespace(
            data=SimpleNamespace(signedTransactionInfo=self._signed_tx)
        )

    def verify_and_decode_signed_transaction(self, jws):
        return self._tx


async def test_handle_notification_updates_existing_and_recomputes(db_session, monkeypatch):
    email = "notify@example.com"
    child = await _child(db_session, email)
    existing = Subscription(
        parent_email=email, provider="apple", external_id="OT-1",
        status="active", created_at=datetime.now(UTC),
    )
    db_session.add(existing)
    await db_session.flush()
    # Grant premium up front so we can assert it is revoked.
    from app.services.entitlements import recompute_household_premium
    await recompute_household_premium(db_session, email)
    await db_session.flush()
    assert is_premium(child) is True

    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(
        abs_, "_build_verifier",
        lambda: _FakeNotificationVerifier(_payload(appAccountToken=None)),
    )
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "expired")

    await abs_.handle_notification(db_session, "signed-notification")

    await db_session.refresh(existing)
    assert existing.status == "expired"
    await db_session.refresh(child)
    assert is_premium(child) is False


async def test_handle_notification_unknown_otid_is_noop(db_session, monkeypatch):
    monkeypatch.setattr(abs_, "_require_apple", lambda: None)
    monkeypatch.setattr(
        abs_, "_build_verifier",
        lambda: _FakeNotificationVerifier(_payload(originalTransactionId="UNKNOWN-OTID")),
    )
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "expired")

    # No error, and no row created for the unknown transaction.
    await abs_.handle_notification(db_session, "signed-notification")
    row = await db_session.scalar(
        select(Subscription).where(
            Subscription.provider == "apple",
            Subscription.external_id == "UNKNOWN-OTID",
        )
    )
    assert row is None


def test_household_token_is_stable_uuid5():
    t = abs_.household_token("a@example.com")
    assert t == abs_.household_token("A@Example.com ")
    uuid.UUID(t)  # parses as a valid UUID
    assert t != abs_.household_token("b@example.com")
