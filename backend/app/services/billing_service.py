from __future__ import annotations

from datetime import UTC, datetime

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription


def _require_stripe() -> None:
    """Raise 503 if Stripe keys are not configured."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )


def _stripe_client() -> None:
    """Set the Stripe API key. Called before any Stripe API call."""
    stripe.api_key = settings.stripe_secret_key


async def get_or_create_subscription(
    session: AsyncSession, parent_email: str
) -> Subscription:
    """Return existing Subscription row or create one with a new Stripe Customer."""
    sub = await session.scalar(
        select(Subscription).where(Subscription.parent_email == parent_email)
    )
    if sub is not None:
        return sub

    _stripe_client()
    customer = stripe.Customer.create(
        email=parent_email,
        metadata={"parent_email": parent_email},
    )
    now = datetime.now(UTC)
    sub = Subscription(
        parent_email=parent_email,
        stripe_customer_id=customer.id,
        status="incomplete",
        created_at=now,
        updated_at=now,
    )
    session.add(sub)
    await session.flush()
    return sub


async def create_checkout_session(
    session: AsyncSession, parent_email: str
) -> str:
    """Create a Stripe Checkout Session and return its URL."""
    _require_stripe()
    sub = await get_or_create_subscription(session, parent_email)

    _stripe_client()
    # Only offer trial if no prior subscription ID (first-time subscriber)
    subscription_data: dict = {}
    if sub.stripe_subscription_id is None:
        subscription_data["trial_period_days"] = 7

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=sub.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        subscription_data=subscription_data if subscription_data else None,
        success_url=f"{settings.app_base_url}/parent?checkout=success",
        cancel_url=f"{settings.app_base_url}/parent?checkout=canceled",
        metadata={"parent_email": parent_email},
    )
    await session.commit()
    return checkout.url


async def create_portal_session(
    session: AsyncSession, parent_email: str
) -> str:
    """Create a Stripe Customer Portal session and return its URL."""
    _require_stripe()
    sub = await session.scalar(
        select(Subscription).where(Subscription.parent_email == parent_email)
    )
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found",
        )

    _stripe_client()
    kwargs: dict = {
        "customer": sub.stripe_customer_id,
        "return_url": f"{settings.app_base_url}/parent",
    }
    if settings.stripe_portal_config_id:
        kwargs["configuration"] = settings.stripe_portal_config_id

    portal = stripe.billing_portal.Session.create(**kwargs)
    return portal.url


async def get_subscription_status(
    session: AsyncSession, parent_email: str
) -> dict:
    """Return the billing status for a parent."""
    sub = await session.scalar(
        select(Subscription).where(Subscription.parent_email == parent_email)
    )
    if sub is None or sub.status in ("incomplete", "canceled"):
        return {
            "has_subscription": False,
            "status": None,
            "trial_ends_at": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }

    # For trialing subscriptions, trial_ends_at = current_period_end
    trial_ends_at = sub.current_period_end if sub.status == "trialing" else None

    return {
        "has_subscription": True,
        "status": sub.status,
        "trial_ends_at": trial_ends_at,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }
