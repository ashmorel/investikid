from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.subscription import Subscription
from app.models.user import User
from app.services import google_billing_service as gbs
from app.services.apple_billing_service import household_token
from app.services.entitlements import is_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session, email):
    u = User(username=f"kid-{email}", email=f"kid-{email}", parent_email=email,
             password_hash="x", dob=datetime(2014, 1, 1).date(), country_code="GB",
             currency_code="GBP", is_active=True)
    db_session.add(u)
    await db_session.flush()
    return u


def _sub_response(email, *, product="premium_monthly", state="SUBSCRIPTION_STATE_ACTIVE",
                  acknowledged=True):
    expiry = (datetime.now(UTC) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    return {
        "subscriptionState": state,
        "acknowledgementState": ("ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED" if acknowledged
                                 else "ACKNOWLEDGEMENT_STATE_PENDING"),
        "externalAccountIdentifiers": {"obfuscatedExternalAccountId": household_token(email)},
        "lineItems": [{"productId": product, "expiryTime": expiry}],
    }


async def test_verify_records_and_grants(db_session, monkeypatch):
    email = "a@example.com"
    child = await _child(db_session, email)
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: _sub_response(email))
    acks = []
    monkeypatch.setattr(gbs, "_acknowledge", lambda product_id, token: acks.append(token))
    await gbs.verify_purchase(db_session, parent_email=email,
                              purchase_token="TOK-1", product_id="premium_monthly")
    row = await db_session.scalar(select(Subscription).where(
        Subscription.provider == "google", Subscription.external_id == "TOK-1"))
    assert row is not None and row.status == "active" and row.parent_email == email
    assert is_premium(child) is True
    assert acks == []


async def test_verify_acknowledges_when_pending(db_session, monkeypatch):
    email = "b@example.com"
    await _child(db_session, email)
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription",
                        lambda token: _sub_response(email, acknowledged=False))
    acks = []
    monkeypatch.setattr(gbs, "_acknowledge", lambda product_id, token: acks.append((product_id, token)))
    await gbs.verify_purchase(db_session, parent_email=email,
                              purchase_token="TOK-2", product_id="premium_monthly")
    assert acks == [("premium_monthly", "TOK-2")]


async def test_verify_rejects_household_mismatch(db_session, monkeypatch):
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    resp = _sub_response("a@example.com")
    resp["externalAccountIdentifiers"]["obfuscatedExternalAccountId"] = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: resp)
    monkeypatch.setattr(gbs, "_acknowledge", lambda *a: None)
    with pytest.raises(gbs.GoogleBillingError):
        await gbs.verify_purchase(db_session, parent_email="a@example.com",
                                  purchase_token="x", product_id="premium_monthly")


async def test_verify_rejects_wrong_product(db_session, monkeypatch):
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: _sub_response("a@example.com"))
    monkeypatch.setattr(gbs, "_acknowledge", lambda *a: None)
    monkeypatch.setattr(gbs.settings, "google_play_product_id", "premium_monthly")
    with pytest.raises(gbs.GoogleBillingError):
        await gbs.verify_purchase(db_session, parent_email="a@example.com",
                                  purchase_token="x", product_id="something_else")
