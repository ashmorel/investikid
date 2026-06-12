"""/billing/plans + plan-aware checkout (M5 Task 2)."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from tests.test_billing import _csrf_headers, _setup_parent

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_plans_requires_parent_auth(client):
    assert (await client.get("/billing/plans")).status_code == 401


async def test_plans_household_currency_and_order(client, db_session):
    await _setup_parent(
        client, db_session,
        parent_email="plans1@example.com",
        child_email="planskid1@example.com", child_username="planskid1",
    )
    r = await client.get("/billing/plans")
    assert r.status_code == 200
    body = r.json()
    assert body["currency"] == "GBP"  # child registered with GBP
    assert [p["plan"] for p in body["plans"]] == ["annual", "monthly"]
    annual = body["plans"][0]
    assert annual["display_price"] == "£29.99"
    assert annual["interval"] == "year"
    assert annual["savings_pct"] == 33
    assert annual["apple_product_id"]
    assert annual["google_product_id"]
    monthly = body["plans"][1]
    assert monthly["display_price"] == "£3.99"
    assert monthly["savings_pct"] is None


@patch("app.services.billing_service.stripe")
async def test_checkout_uses_annual_price_by_default(mock_stripe, client, db_session, monkeypatch):
    await _setup_parent(
        client, db_session,
        parent_email="plans2@example.com",
        child_email="planskid2@example.com", child_username="planskid2",
    )
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id_monthly", "price_m")
    monkeypatch.setattr(settings, "stripe_price_id_annual", "price_a")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_p2")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://x")

    r = await client.post("/billing/checkout", headers=_csrf_headers(client))
    assert r.status_code == 200
    kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_a", "quantity": 1}]
    assert kwargs["metadata"]["plan"] == "annual"


@patch("app.services.billing_service.stripe")
async def test_checkout_monthly_plan(mock_stripe, client, db_session, monkeypatch):
    await _setup_parent(
        client, db_session,
        parent_email="plans3@example.com",
        child_email="planskid3@example.com", child_username="planskid3",
    )
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id_monthly", "price_m")
    monkeypatch.setattr(settings, "stripe_price_id_annual", "price_a")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_p3")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://x")

    r = await client.post(
        "/billing/checkout", json={"plan": "monthly"}, headers=_csrf_headers(client)
    )
    assert r.status_code == 200
    kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_m", "quantity": 1}]
    assert kwargs["metadata"]["plan"] == "monthly"


@patch("app.services.billing_service.stripe")
async def test_checkout_annual_falls_back_when_unconfigured(mock_stripe, client, db_session, monkeypatch):
    await _setup_parent(
        client, db_session,
        parent_email="plans4@example.com",
        child_email="planskid4@example.com", child_username="planskid4",
    )
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id", "price_legacy")
    monkeypatch.setattr(settings, "stripe_price_id_monthly", "")
    monkeypatch.setattr(settings, "stripe_price_id_annual", "")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_p4")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://x")

    r = await client.post(
        "/billing/checkout", json={"plan": "annual"}, headers=_csrf_headers(client)
    )
    assert r.status_code == 200
    kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_legacy", "quantity": 1}]


async def test_checkout_rejects_unknown_plan(client, db_session):
    await _setup_parent(
        client, db_session,
        parent_email="plans5@example.com",
        child_email="planskid5@example.com", child_username="planskid5",
    )
    r = await client.post(
        "/billing/checkout", json={"plan": "lifetime"}, headers=_csrf_headers(client)
    )
    assert r.status_code == 422
