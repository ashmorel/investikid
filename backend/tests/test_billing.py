import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
import stripe
from sqlalchemy import select

from app.core.config import settings
from app.models.subscription import Subscription
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup_parent(client, db_session, parent_email="billing@example.com",
                        child_email="billingkid@example.com",
                        child_username="billingkid"):
    """Create child + parent magic-link session."""
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


# --- Checkout ---

@patch("app.services.billing_service.stripe")
async def test_checkout_creates_session(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="ckout1@example.com", child_username="ckout1")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/test")

    original_key = settings.stripe_secret_key
    settings.stripe_secret_key = "sk_test_fake"
    try:
        r = await client.post("/billing/checkout", headers=_csrf_headers(client))
    finally:
        settings.stripe_secret_key = original_key
    assert r.status_code == 200
    body = r.json()
    assert body["url"] == "https://checkout.stripe.com/test"

    # Verify Subscription row was created
    sub = await db_session.scalar(
        select(Subscription).where(Subscription.parent_email == "billing@example.com")
    )
    assert sub is not None
    assert sub.stripe_customer_id == "cus_test123"


@patch("app.services.billing_service.stripe")
async def test_checkout_reuses_customer(mock_stripe, client, db_session):
    """Second checkout call reuses existing Stripe customer."""
    await _setup_parent(client, db_session,
                        child_email="ckout2@example.com", child_username="ckout2",
                        parent_email="reuse@example.com")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_reuse")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/1")

    original_key = settings.stripe_secret_key
    settings.stripe_secret_key = "sk_test_fake"
    try:
        await client.post("/billing/checkout", headers=_csrf_headers(client))
        mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/2")
        r = await client.post("/billing/checkout", headers=_csrf_headers(client))
    finally:
        settings.stripe_secret_key = original_key
    assert r.status_code == 200
    # Customer.create should only be called once (first time)
    assert mock_stripe.Customer.create.call_count == 1


async def test_checkout_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.post("/billing/checkout")
    # CSRF middleware runs before auth; no CSRF cookie → 403
    assert r.status_code in (401, 403)


async def test_checkout_503_without_stripe_key(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="ckout503@example.com", child_username="ckout503",
                        parent_email="nokey@example.com")
    original = settings.stripe_secret_key
    settings.stripe_secret_key = ""
    try:
        r = await client.post("/billing/checkout", headers=_csrf_headers(client))
        assert r.status_code == 503
    finally:
        settings.stripe_secret_key = original


# --- Portal ---

@patch("app.services.billing_service.stripe")
async def test_portal_returns_url(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="portal1@example.com", child_username="portal1",
                        parent_email="portal@example.com")
    # Create a subscription row first
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_portal")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://co.stripe.com/x")
    mock_stripe.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/portal")

    original_key = settings.stripe_secret_key
    settings.stripe_secret_key = "sk_test_fake"
    try:
        await client.post("/billing/checkout", headers=_csrf_headers(client))
        r = await client.post("/billing/portal", headers=_csrf_headers(client))
    finally:
        settings.stripe_secret_key = original_key
    assert r.status_code == 200
    assert r.json()["url"] == "https://billing.stripe.com/portal"


async def test_portal_404_no_subscription(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="portal404@example.com", child_username="portal404",
                        parent_email="noportal@example.com")
    original_key = settings.stripe_secret_key
    settings.stripe_secret_key = "sk_test_fake"
    try:
        r = await client.post("/billing/portal", headers=_csrf_headers(client))
    finally:
        settings.stripe_secret_key = original_key
    assert r.status_code == 404


# --- Status ---

async def test_status_no_subscription(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="stat1@example.com", child_username="stat1",
                        parent_email="nostatus@example.com")
    r = await client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_subscription"] is False
    assert body["status"] is None


@patch("app.services.billing_service.stripe")
async def test_status_active(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="stat2@example.com", child_username="stat2",
                        parent_email="active@example.com")
    # Create subscription and set it to active
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_active")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://co.stripe.com/x")
    original_key = settings.stripe_secret_key
    settings.stripe_secret_key = "sk_test_fake"
    try:
        await client.post("/billing/checkout", headers=_csrf_headers(client))
    finally:
        settings.stripe_secret_key = original_key

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.parent_email == "active@example.com")
    )
    sub.status = "active"
    sub.stripe_subscription_id = "sub_active"
    from datetime import UTC, datetime
    sub.current_period_end = datetime(2026, 6, 21, tzinfo=UTC)
    await db_session.flush()

    r = await client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_subscription"] is True
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is False


# --- Webhook ---

@patch("app.services.webhook_service.stripe")
@patch("app.routers.billing.stripe")
async def test_webhook_checkout_completed(mock_router_stripe, mock_ws_stripe, client, db_session):
    """checkout.session.completed upserts Subscription and grants premium to children."""
    parent_email = "whook@example.com"
    await _setup_parent(client, db_session,
                        child_email="whookchild@example.com", child_username="whookchild",
                        parent_email=parent_email)

    # Pre-create a subscription row
    sub = Subscription(
        parent_email=parent_email,
        stripe_customer_id="cus_whook",
        status="incomplete",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_whook",
                "subscription": "sub_whook",
                "metadata": {"parent_email": parent_email},
            }
        },
    }

    mock_router_stripe.Webhook.construct_event.return_value = event_payload
    mock_ws_stripe.Subscription.retrieve.return_value = MagicMock(
        status="trialing",
        current_period_end=1748476800,
        cancel_at_period_end=False,
    )

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200

    # Verify subscription was updated
    await db_session.refresh(sub)
    assert sub.stripe_subscription_id == "sub_whook"
    assert sub.status == "trialing"

    # Verify child got premium
    child = await db_session.scalar(
        select(User).where(User.email == "whookchild@example.com")
    )
    await db_session.refresh(child)
    assert child.is_premium is True


@patch("app.routers.billing.stripe")
async def test_webhook_subscription_updated_cancel(mock_stripe, client, db_session):
    """customer.subscription.updated with cancel_at_period_end=true."""
    sub = Subscription(
        parent_email="cancelup@example.com",
        stripe_customer_id="cus_cancelup",
        stripe_subscription_id="sub_cancelup",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_cancelup",
                "status": "active",
                "current_period_end": 1748476800,
                "cancel_at_period_end": True,
            }
        },
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.cancel_at_period_end is True


@patch("app.routers.billing.stripe")
async def test_webhook_subscription_deleted(mock_stripe, client, db_session):
    """customer.subscription.deleted downgrades all children."""
    parent_email = "delsub@example.com"
    await _setup_parent(client, db_session,
                        child_email="delchild@example.com", child_username="delchild",
                        parent_email=parent_email)
    # Make child premium first
    child = await db_session.scalar(
        select(User).where(User.email == "delchild@example.com")
    )
    child.is_premium = True
    await db_session.flush()

    sub = Subscription(
        parent_email=parent_email,
        stripe_customer_id="cus_delsub",
        stripe_subscription_id="sub_delsub",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_delsub"}},
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    await db_session.refresh(child)
    assert child.is_premium is False


@patch("app.routers.billing.stripe")
async def test_webhook_payment_failed(mock_stripe, client, db_session):
    """invoice.payment_failed marks subscription past_due, children stay premium."""
    sub = Subscription(
        parent_email="pf@example.com",
        stripe_customer_id="cus_pf",
        stripe_subscription_id="sub_pf",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": "sub_pf"}},
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "past_due"


@patch("app.routers.billing.stripe")
async def test_webhook_bad_signature(mock_stripe, client):
    mock_stripe.Webhook.construct_event.side_effect = (
        stripe.error.SignatureVerificationError("bad", "sig")
    )
    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=bad"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret
    assert r.status_code == 400


@patch("app.routers.billing.stripe")
async def test_webhook_idempotent(mock_stripe, client, db_session):
    """Duplicate subscription.updated event is a no-op."""
    sub = Subscription(
        parent_email="idem@example.com",
        stripe_customer_id="cus_idem",
        stripe_subscription_id="sub_idem",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_idem",
                "status": "active",
                "current_period_end": 1748476800,
                "cancel_at_period_end": False,
            }
        },
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        # Send same event twice
        r1 = await client.post("/billing/webhook", content=b'{}',
                               headers={"stripe-signature": "t=1,v1=sig"})
        r2 = await client.post("/billing/webhook", content=b'{}',
                               headers={"stripe-signature": "t=1,v1=sig"})
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r1.status_code == 200
    assert r2.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "active"
