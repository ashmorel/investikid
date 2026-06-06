from __future__ import annotations

import logging
from datetime import UTC, datetime

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.premium_request import PremiumRequest
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import set_premium

logger = logging.getLogger(__name__)


async def resolve_premium_requests(session: AsyncSession, parent_email: str) -> None:
    """Mark this parent's open premium requests resolved (called when premium is granted)."""
    await session.execute(
        update(PremiumRequest)
        .where(
            PremiumRequest.parent_email == parent_email,
            PremiumRequest.resolved_at.is_(None),
        )
        .values(resolved_at=datetime.now(UTC))
    )


async def handle_checkout_completed(
    session: AsyncSession, event: dict
) -> None:
    """Handle checkout.session.completed — upsert Subscription, grant premium."""
    data = event["data"]["object"]
    customer_id: str = data["customer"]
    subscription_id: str = data["subscription"]
    parent_email: str = data["metadata"]["parent_email"]

    # Retrieve the full subscription to get status and period info
    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    now = datetime.now(UTC)
    sub = await session.scalar(
        select(Subscription).where(
            Subscription.stripe_customer_id == customer_id
        )
    )
    if sub is None:
        sub = Subscription(
            parent_email=parent_email,
            stripe_customer_id=customer_id,
            created_at=now,
            updated_at=now,
        )
        session.add(sub)

    sub.stripe_subscription_id = subscription_id
    sub.status = stripe_sub.status
    sub.current_period_end = datetime.fromtimestamp(
        stripe_sub.current_period_end, tz=UTC
    )
    sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
    sub.updated_at = now

    # Grant premium to all children under this parent
    children = (
        await session.scalars(
            select(User).where(User.parent_email == parent_email)
        )
    ).all()
    for child in children:
        await set_premium(session, child, value=True, actor="stripe")

    await resolve_premium_requests(session, parent_email)

    await session.commit()
    logger.info("checkout.session.completed: parent=%s children=%d", parent_email, len(children))


async def handle_subscription_updated(
    session: AsyncSession, event: dict
) -> None:
    """Handle customer.subscription.updated — sync billing state."""
    data = event["data"]["object"]
    subscription_id: str = data["id"]

    sub = await session.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    if sub is None:
        logger.warning("subscription.updated: unknown subscription %s", subscription_id)
        return

    sub.status = data["status"]
    sub.current_period_end = datetime.fromtimestamp(
        data["current_period_end"], tz=UTC
    )
    sub.cancel_at_period_end = data.get("cancel_at_period_end", False)
    sub.updated_at = datetime.now(UTC)

    await session.commit()
    logger.info("subscription.updated: sub=%s status=%s", subscription_id, sub.status)


async def handle_subscription_deleted(
    session: AsyncSession, event: dict
) -> None:
    """Handle customer.subscription.deleted — revoke premium."""
    data = event["data"]["object"]
    subscription_id: str = data["id"]

    sub = await session.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    if sub is None:
        logger.warning("subscription.deleted: unknown subscription %s", subscription_id)
        return

    sub.status = "canceled"
    sub.cancel_at_period_end = False
    sub.updated_at = datetime.now(UTC)

    # Revoke premium from all children
    children = (
        await session.scalars(
            select(User).where(User.parent_email == sub.parent_email)
        )
    ).all()
    for child in children:
        await set_premium(session, child, value=False, actor="stripe")

    await session.commit()
    logger.info("subscription.deleted: parent=%s children=%d downgraded", sub.parent_email, len(children))


async def handle_payment_failed(
    session: AsyncSession, event: dict
) -> None:
    """Handle invoice.payment_failed — mark past_due, children stay premium."""
    data = event["data"]["object"]
    subscription_id: str | None = data.get("subscription")
    if subscription_id is None:
        return

    sub = await session.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    if sub is None:
        logger.warning("payment_failed: unknown subscription %s", subscription_id)
        return

    sub.status = "past_due"
    sub.updated_at = datetime.now(UTC)
    await session.commit()
    logger.info("payment_failed: sub=%s → past_due", subscription_id)


EVENT_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.payment_failed": handle_payment_failed,
}


async def dispatch_webhook_event(session: AsyncSession, event: dict) -> None:
    """Route a verified Stripe event to the appropriate handler."""
    event_type = event.get("type", "")
    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.debug("Ignoring unhandled event type: %s", event_type)
        return
    await handler(session, event)
