from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.services.entitlements import ACTIVE_SUBSCRIPTION_STATUSES, recompute_household_premium

logger = logging.getLogger(__name__)

# Re-check rows whose period ends within this window (or has already passed),
# since those are the ones a missed renewal/cancel webhook would leave stale.
_AT_RISK_WINDOW = timedelta(days=2)


def _repull_stripe(stripe_subscription_id: str) -> tuple[str, datetime | None]:
    """Authoritative (status, current_period_end) from Stripe. Patched in tests."""
    import stripe

    sub = stripe.Subscription.retrieve(stripe_subscription_id)
    end = datetime.fromtimestamp(sub.current_period_end, tz=UTC) if sub.current_period_end else None
    return sub.status, end


def _repull_apple(original_transaction_id: str) -> tuple[str, datetime | None]:
    """Authoritative status from Apple (no period end available here)."""
    from app.services import apple_billing_service

    return apple_billing_service._fetch_status(original_transaction_id), None


def _repull_google(purchase_token: str) -> tuple[str, datetime | None]:
    """Authoritative (status, expiry) from Google Play."""
    from app.services import google_billing_service

    resp = google_billing_service._fetch_subscription(purchase_token)
    return (
        google_billing_service._map_status(resp.get("subscriptionState")),
        google_billing_service._expiry_dt(resp),
    )


def _repull(row: Subscription) -> tuple[str, datetime | None] | None:
    if row.provider == "stripe" and row.stripe_subscription_id:
        return _repull_stripe(row.stripe_subscription_id)
    if row.provider == "apple" and row.external_id:
        return _repull_apple(row.external_id)
    if row.provider == "google" and row.external_id:
        return _repull_google(row.external_id)
    return None  # unknown provider / missing id → skip


async def run(session: AsyncSession) -> dict:
    """Re-pull provider state for at-risk subscription rows and recompute the
    affected households. Best-effort per row; one failure never aborts the run."""
    now = datetime.now(UTC)
    cutoff = now + _AT_RISK_WINDOW
    rows = (await session.scalars(
        select(Subscription).where(
            Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
            or_(
                Subscription.current_period_end.is_(None),
                Subscription.current_period_end <= cutoff,
            ),
        )
    )).all()

    checked = updated = errored = 0
    affected: set[str] = set()
    for row in rows:
        checked += 1
        try:
            # _repull does a synchronous provider API call (Stripe/Apple/Google).
            # Run it off the event loop so the batch can't stall the worker.
            pulled = await asyncio.to_thread(_repull, row)
            if pulled is None:
                continue
            status, period_end = pulled
            # Only count a real field change. A provider with no period (Apple
            # returns None) must not register as "updated" when nothing persists.
            changed = status != row.status or (
                period_end is not None and period_end != row.current_period_end
            )
            if changed:
                row.status = status
                if period_end is not None:
                    row.current_period_end = period_end
                updated += 1
            affected.add(row.parent_email)
        except Exception as exc:  # noqa: BLE001 — one bad provider call must not abort the batch
            errored += 1
            logger.warning("reconcile failed for sub %s (%s): %s", row.id, row.provider, exc)

    for parent_email in affected:
        await recompute_household_premium(session, parent_email)

    return {"checked": checked, "updated": updated, "errored": errored}
