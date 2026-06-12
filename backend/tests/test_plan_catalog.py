"""Plan catalog resolution (M5 Task 1)."""
import pytest

from app.core.config import settings
from app.services import plan_catalog

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_plans_annual_first_with_display_prices():
    plans = plan_catalog.PLANS
    assert list(plans.keys()) == ["annual", "monthly"]
    assert plans["annual"]["display"]["USD"] == "$39.99"
    assert plans["annual"]["display"]["GBP"] == "£29.99"
    assert plans["annual"]["display"]["HKD"] == "HK$298"
    assert plans["annual"]["savings_pct"] == 33
    assert plans["monthly"]["display"]["USD"] == "$4.99"
    assert plans["monthly"].get("savings_pct") is None


def test_resolve_stripe_price_with_both_configured(monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_id", "price_legacy")
    monkeypatch.setattr(settings, "stripe_price_id_monthly", "price_m")
    monkeypatch.setattr(settings, "stripe_price_id_annual", "price_a")
    assert plan_catalog.resolve_stripe_price("annual") == "price_a"
    assert plan_catalog.resolve_stripe_price("monthly") == "price_m"


def test_resolve_stripe_price_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_id", "price_legacy")
    monkeypatch.setattr(settings, "stripe_price_id_monthly", "")
    monkeypatch.setattr(settings, "stripe_price_id_annual", "")
    # annual unconfigured -> graceful fallback to monthly -> legacy
    assert plan_catalog.resolve_stripe_price("annual") == "price_legacy"
    assert plan_catalog.resolve_stripe_price("monthly") == "price_legacy"


def test_store_product_ids_and_allowed_sets(monkeypatch):
    monkeypatch.setattr(settings, "apple_iap_product_id", "premium_monthly")
    monkeypatch.setattr(settings, "apple_iap_product_id_annual", "premium_annual")
    monkeypatch.setattr(settings, "google_play_product_id", "")
    monkeypatch.setattr(settings, "google_play_product_id_annual", "")
    assert plan_catalog.apple_product_id("annual") == "premium_annual"
    assert plan_catalog.apple_product_id("monthly") == "premium_monthly"
    # unconfigured google falls back to conventional ids
    assert plan_catalog.google_product_id("monthly") == "premium_monthly"
    assert plan_catalog.google_product_id("annual") == "premium_annual"
    assert plan_catalog.allowed_apple_products() == {"premium_monthly", "premium_annual"}
    assert plan_catalog.allowed_google_products() == set()


async def test_google_verify_accepts_annual_product(db_session, monkeypatch):
    """Membership check in google_billing_service uses the allowed set."""
    from unittest.mock import MagicMock

    from app.services import google_billing_service as gbs

    monkeypatch.setattr(settings, "google_play_product_id", "premium_monthly")
    monkeypatch.setattr(settings, "google_play_product_id_annual", "premium_annual")
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    resp = {
        "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
        "lineItems": [{"productId": "premium_annual", "expiryTime": "2027-01-01T00:00:00Z"}],
        "externalAccountIdentifiers": {},
        "acknowledgementState": "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED",
    }
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: resp)
    monkeypatch.setattr(gbs, "_acknowledge", MagicMock())
    await gbs.verify_purchase(
        db_session,
        parent_email="gannual@example.com",
        purchase_token="tok-annual",
        product_id="premium_annual",
    )

    import pytest as _pytest

    with _pytest.raises(gbs.GoogleBillingError):
        await gbs.verify_purchase(
            db_session,
            parent_email="gannual@example.com",
            purchase_token="tok-bad",
            product_id="premium_lifetime_scam",
        )
