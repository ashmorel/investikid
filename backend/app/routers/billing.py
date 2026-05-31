from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from app.core.config import settings
from app.core.database import get_session
from app.routers.parent_auth import get_current_parent
from app.schemas.billing import (
    CheckoutResponse,
    PortalResponse,
    SubscriptionStatusResponse,
)
from app.services.billing_service import (
    create_checkout_session,
    create_portal_session,
    get_subscription_status,
)
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    url = await create_checkout_session(session, parent_email)
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=PortalResponse)
async def portal(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    url = await create_portal_session(session, parent_email)
    return PortalResponse(url=url)


@router.get("/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    result = await get_subscription_status(session, parent_email)
    return SubscriptionStatusResponse(**result)


@router.post("/webhook")
async def webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    await dispatch_webhook_event(session, event)
    return {"status": "ok"}
