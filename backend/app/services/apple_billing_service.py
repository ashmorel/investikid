from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription
from app.services.entitlements import recompute_household_premium

# Fixed namespace for deriving an opaque, deterministic household token from a
# parent email. This token is sent to Apple as the StoreKit appAccountToken
# (a UUID, no PII). Do NOT change this value once in production.
_HOUSEHOLD_TOKEN_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def household_token(parent_email: str) -> str:
    """Opaque, stable UUIDv5 for a household (keyed on the lowercased parent email).
    Used as the StoreKit appAccountToken so no PII is sent to Apple."""
    return str(uuid.uuid5(_HOUSEHOLD_TOKEN_NAMESPACE, parent_email.strip().lower()))


class AppleBillingError(Exception):
    """Raised when an Apple transaction cannot be trusted/processed."""


def _require_apple() -> None:
    if not (settings.apple_iap_bundle_id and settings.apple_iap_issuer_id
            and settings.apple_iap_key_id and settings.apple_iap_private_key):
        raise AppleBillingError("Apple IAP is not configured")


def _environment():
    from appstoreserverlibrary.models.Environment import Environment
    return (Environment.PRODUCTION if settings.apple_iap_environment == "Production"
            else Environment.SANDBOX)


def _build_verifier():
    """Construct a SignedDataVerifier. Patched in tests."""
    import pathlib

    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
    root_dir = pathlib.Path(__file__).parent / "apple_roots"
    roots = [p.read_bytes() for p in sorted(root_dir.glob("*.cer"))]
    return SignedDataVerifier(roots, True, _environment(),
                              settings.apple_iap_bundle_id, settings.apple_iap_app_apple_id)


def _api_client():
    from appstoreserverlibrary.api_client import AppStoreServerAPIClient
    return AppStoreServerAPIClient(
        settings.apple_iap_private_key.encode("utf-8"), settings.apple_iap_key_id,
        settings.apple_iap_issuer_id, settings.apple_iap_bundle_id, _environment())


def _fetch_status(original_transaction_id: str) -> str:
    """Normalized status from the App Store Server API. Patched in tests."""
    client = _api_client()
    resp = client.get_all_subscription_statuses(original_transaction_id)
    code = resp.data[0].lastTransactions[0].status
    return {1: "active", 2: "expired", 3: "past_due",
            4: "in_grace_period", 5: "expired"}.get(code, "expired")


def _status_from_payload(payload) -> str:
    if getattr(payload, "revocationDate", None):
        return "expired"
    exp = getattr(payload, "expiresDate", None)
    if exp and datetime.fromtimestamp(exp / 1000, tz=UTC) < datetime.now(UTC):
        return "expired"
    return "active"


async def _upsert_and_recompute(session: AsyncSession, *, parent_email: str,
                                original_transaction_id: str, status: str,
                                expires_ms: int | None) -> None:
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "apple",
        Subscription.external_id == original_transaction_id))
    now = datetime.now(UTC)
    if sub is None:
        sub = Subscription(parent_email=parent_email, provider="apple",
                           external_id=original_transaction_id, created_at=now)
        session.add(sub)
    sub.status = status
    sub.parent_email = parent_email
    sub.current_period_end = (datetime.fromtimestamp(expires_ms / 1000, tz=UTC)
                              if expires_ms else None)
    sub.updated_at = now
    await session.flush()
    await recompute_household_premium(session, sub.parent_email)


async def handle_notification(session: AsyncSession, signed_payload: str) -> None:
    """Verify and process an App Store Server Notification V2 payload."""
    _require_apple()
    verifier = _build_verifier()
    notification = verifier.verify_and_decode_notification(signed_payload)
    data = getattr(notification, "data", None)
    signed_tx = getattr(data, "signedTransactionInfo", None) if data is not None else None
    if not signed_tx:
        return
    tx = verifier.verify_and_decode_signed_transaction(signed_tx)
    otid = tx.originalTransactionId
    # Only act on transactions we already know (associated to a household at verify time)
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "apple", Subscription.external_id == otid))
    if sub is None:
        return
    try:
        status_ = _fetch_status(otid)
    except Exception:
        status_ = _status_from_payload(tx)
    await _upsert_and_recompute(session, parent_email=sub.parent_email,
                               original_transaction_id=otid, status=status_,
                               expires_ms=getattr(tx, "expiresDate", None))
    await session.commit()


async def verify_transaction(session: AsyncSession, *, parent_email: str, jws: str) -> None:
    """Verify a StoreKit signed transaction (JWS), associate it to the parent via
    appAccountToken, record the subscription, and recompute entitlement."""
    _require_apple()
    payload = _build_verifier().verify_and_decode_signed_transaction(jws)
    token = (getattr(payload, "appAccountToken", "") or "").lower()
    if token and token != household_token(parent_email):
        raise AppleBillingError("appAccountToken does not match the authenticated parent")
    otid = payload.originalTransactionId
    try:
        status = _fetch_status(otid)
    except Exception:
        status = _status_from_payload(payload)
    await _upsert_and_recompute(session, parent_email=parent_email,
                                original_transaction_id=otid, status=status,
                                expires_ms=getattr(payload, "expiresDate", None))
    await session.commit()
