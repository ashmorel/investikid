from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription
from app.services.apple_billing_service import household_token
from app.services.entitlements import recompute_household_premium

_SCOPE = "https://www.googleapis.com/auth/androidpublisher"

_STATE_MAP = {
    "SUBSCRIPTION_STATE_ACTIVE": "active",
    "SUBSCRIPTION_STATE_CANCELED": "active",        # access continues until expiry
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "in_grace_period",
    "SUBSCRIPTION_STATE_ON_HOLD": "expired",
    "SUBSCRIPTION_STATE_PAUSED": "expired",
    "SUBSCRIPTION_STATE_EXPIRED": "expired",
    "SUBSCRIPTION_STATE_PENDING": "expired",
}


class GoogleBillingError(Exception):
    """Raised when a Play purchase cannot be trusted/processed."""


def _require_google() -> None:
    if not (settings.google_play_package_name and settings.google_play_service_account_json):
        raise GoogleBillingError("Google Play billing is not configured")


def _play_client():
    """Android Publisher client from the service-account JSON. Patched in tests."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = json.loads(settings.google_play_service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=[_SCOPE])
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def _fetch_subscription(purchase_token: str) -> dict:
    """Authoritative subscription state from the Play Developer API. Patched in tests."""
    client = _play_client()
    return client.purchases().subscriptionsv2().get(
        packageName=settings.google_play_package_name, token=purchase_token).execute()


def _acknowledge(product_id: str, purchase_token: str) -> None:
    """Acknowledge a purchase. Patched in tests."""
    client = _play_client()
    client.purchases().subscriptions().acknowledge(
        packageName=settings.google_play_package_name,
        subscriptionId=product_id, token=purchase_token, body={}).execute()


def _map_status(state: str | None) -> str:
    return _STATE_MAP.get(state or "", "expired")


def _line_item(resp: dict) -> dict:
    items = resp.get("lineItems") or [{}]
    return items[0]


def _expiry_dt(resp: dict) -> datetime | None:
    exp = _line_item(resp).get("expiryTime")
    if not exp:
        return None
    return datetime.fromisoformat(exp.replace("Z", "+00:00"))


async def _upsert_and_recompute(session: AsyncSession, *, parent_email: str,
                                purchase_token: str, status: str,
                                expiry: datetime | None) -> None:
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "google", Subscription.external_id == purchase_token))
    now = datetime.now(UTC)
    if sub is None:
        sub = Subscription(parent_email=parent_email, provider="google",
                           external_id=purchase_token, created_at=now)
        session.add(sub)
    sub.status = status
    sub.parent_email = parent_email
    sub.current_period_end = expiry
    sub.updated_at = now
    await session.flush()
    await recompute_household_premium(session, sub.parent_email)


async def verify_purchase(session: AsyncSession, *, parent_email: str,
                          purchase_token: str, product_id: str) -> None:
    """Validate a Play purchase token, bind to the household, acknowledge, record + recompute."""
    _require_google()
    resp = _fetch_subscription(purchase_token)

    obfuscated = (resp.get("externalAccountIdentifiers") or {}).get("obfuscatedExternalAccountId")
    if obfuscated and obfuscated != household_token(parent_email):
        raise GoogleBillingError("obfuscatedAccountId does not match the authenticated parent")

    expected_product = settings.google_play_product_id
    line_product = _line_item(resp).get("productId") or product_id
    if expected_product and (line_product != expected_product or product_id != expected_product):
        raise GoogleBillingError("Purchase product does not match the configured subscription product")

    if resp.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_PENDING":
        try:
            _acknowledge(line_product, purchase_token)
        except Exception:
            pass

    await _upsert_and_recompute(session, parent_email=parent_email,
                                purchase_token=purchase_token,
                                status=_map_status(resp.get("subscriptionState")),
                                expiry=_expiry_dt(resp))
    await session.commit()
