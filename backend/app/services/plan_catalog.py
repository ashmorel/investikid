"""Subscription plan catalog (M5).

The single source for plan structure and in-app display prices. Real charge
amounts live in Stripe Prices / App Store / Play price points (operator-managed);
these strings are what the UI shows. Both plans entitle the WHOLE household
(see entitlements.recompute_household_premium) — there is deliberately no
separate family SKU.
"""
from __future__ import annotations

from app.core.config import settings

Plan = str  # 'annual' | 'monthly'

PLANS: dict[Plan, dict] = {
    "annual": {
        "interval": "year",
        "display": {"USD": "$39.99", "GBP": "£29.99", "HKD": "HK$298"},
        "savings_pct": 33,
    },
    "monthly": {
        "interval": "month",
        "display": {"USD": "$4.99", "GBP": "£3.99", "HKD": "HK$38"},
        "savings_pct": None,
    },
}

_FALLBACK_PRODUCT_IDS: dict[Plan, str] = {
    "monthly": "premium_monthly",
    "annual": "premium_annual",
}


def resolve_stripe_price(plan: Plan) -> str:
    """Stripe Price id for a plan, degrading gracefully during rollout.

    annual -> annual id, else monthly id, else legacy id;
    monthly -> monthly id, else legacy id.
    """
    monthly = settings.stripe_price_id_monthly or settings.stripe_price_id
    if plan == "annual":
        return settings.stripe_price_id_annual or monthly
    return monthly


def apple_product_id(plan: Plan) -> str:
    configured = {
        "monthly": settings.apple_iap_product_id,
        "annual": settings.apple_iap_product_id_annual,
    }[plan]
    return configured or _FALLBACK_PRODUCT_IDS[plan]


def google_product_id(plan: Plan) -> str:
    configured = {
        "monthly": settings.google_play_product_id,
        "annual": settings.google_play_product_id_annual,
    }[plan]
    return configured or _FALLBACK_PRODUCT_IDS[plan]


def allowed_apple_products() -> set[str]:
    """Configured Apple product ids (empty set = check disabled, matching the
    pre-M5 permissive default when nothing is configured)."""
    return {
        p
        for p in (settings.apple_iap_product_id, settings.apple_iap_product_id_annual)
        if p
    }


def allowed_google_products() -> set[str]:
    return {
        p
        for p in (settings.google_play_product_id, settings.google_play_product_id_annual)
        if p
    }
