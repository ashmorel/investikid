from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.routers.parent_auth import get_current_parent
from app.routers.users import get_current_user
from app.schemas.apple_billing import (
    AppleAccountTokenResponse,
    AppleVerifyRequest,
    AppleVerifyResponse,
)
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanOut,
    PlansResponse,
    PortalResponse,
    SubscriptionStatusResponse,
)
from app.schemas.google_billing import (
    AccountTokenResponse,
    GoogleVerifyRequest,
    GoogleVerifyResponse,
)
from app.services import apple_billing_service, google_billing_service
from app.services.billing_service import (
    create_checkout_session,
    create_portal_session,
    get_subscription_status,
)
from app.services.entitlements import household_key
from app.services.plan_catalog import PLANS, apple_product_id, google_product_id
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/billing", tags=["billing"])


def _plans_for_currency(currency: str) -> PlansResponse:
    """Build the plan catalog response for a resolved display currency,
    falling back to USD when the currency has no display strings."""
    if currency not in next(iter(PLANS.values()))["display"]:
        currency = "USD"
    return PlansResponse(
        currency=currency,
        plans=[
            PlanOut(
                plan=name,
                interval=spec["interval"],
                display_price=spec["display"][currency],
                savings_pct=spec["savings_pct"],
                apple_product_id=apple_product_id(name),
                google_product_id=google_product_id(name),
            )
            for name, spec in PLANS.items()
        ],
    )


def _child_scope(user: User) -> str:
    """Billing household scope for a child-authed request. Fails closed when a
    user has neither parent_email nor email (should not happen)."""
    key = household_key(user)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="no billing household for this account",
        )
    return key


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest | None = None,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    plan = payload.plan if payload else "annual"
    url = await create_checkout_session(session, parent_email, plan)
    return CheckoutResponse(url=url)


@router.get("/plans", response_model=PlansResponse)
async def list_plans(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    """Plan catalog with the household's display currency (first child's
    currency_code, default USD). Display strings only — real charge amounts
    live in the stores/Stripe."""
    currency = (
        await session.scalar(
            select(User.currency_code)
            .where(User.parent_email == parent_email)
            .order_by(User.created_at)
            .limit(1)
        )
    ) or "USD"
    return _plans_for_currency(currency)


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


@router.get("/apple/account-token", response_model=AppleAccountTokenResponse)
async def apple_account_token(parent_email: str = Depends(get_current_parent)):
    return AppleAccountTokenResponse(
        token=apple_billing_service.household_token(parent_email)
    )


@router.post("/apple/verify", response_model=AppleVerifyResponse)
async def apple_verify(
    payload: AppleVerifyRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await apple_billing_service.verify_transaction(
            session, parent_email=parent_email, jws=payload.jws
        )
    except apple_billing_service.AppleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppleVerifyResponse()


@router.post("/apple/notifications")
async def apple_notifications(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    body = await request.json()
    signed = body.get("signedPayload")
    if not signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signedPayload"
        )
    try:
        await apple_billing_service.handle_notification(session, signed)
    except apple_billing_service.AppleBillingError:
        return {"status": "ignored"}
    return {"status": "ok"}


@router.get("/account-token", response_model=AccountTokenResponse)
async def account_token(parent_email: str = Depends(get_current_parent)):
    return AccountTokenResponse(
        token=apple_billing_service.household_token(parent_email)
    )


@router.post("/google/verify", response_model=GoogleVerifyResponse)
async def google_verify(
    payload: GoogleVerifyRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await google_billing_service.verify_purchase(
            session,
            parent_email=parent_email,
            purchase_token=payload.purchaseToken,
            product_id=payload.productId,
        )
    except google_billing_service.GoogleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return GoogleVerifyResponse()


# --- Child-authed mirrors -------------------------------------------------
# Same verify services as the parent endpoints; only the auth dependency and
# scope source differ (household_key(child) instead of the parent's email),
# so a child can drive a native StoreKit/Play Billing purchase.


@router.get("/child/apple/account-token", response_model=AppleAccountTokenResponse)
async def child_apple_account_token(user: User = Depends(get_current_user)):
    return AppleAccountTokenResponse(
        token=apple_billing_service.household_token(_child_scope(user))
    )


@router.get("/child/account-token", response_model=AccountTokenResponse)
async def child_account_token(user: User = Depends(get_current_user)):
    return AccountTokenResponse(
        token=apple_billing_service.household_token(_child_scope(user))
    )


@router.get("/child/plans", response_model=PlansResponse)
async def child_list_plans(user: User = Depends(get_current_user)):
    return _plans_for_currency(user.currency_code or "USD")


@router.post("/child/apple/verify", response_model=AppleVerifyResponse)
async def child_apple_verify(
    payload: AppleVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        await apple_billing_service.verify_transaction(
            session, parent_email=_child_scope(user), jws=payload.jws
        )
    except apple_billing_service.AppleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppleVerifyResponse()


@router.post("/child/google/verify", response_model=GoogleVerifyResponse)
async def child_google_verify(
    payload: GoogleVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        await google_billing_service.verify_purchase(
            session,
            parent_email=_child_scope(user),
            purchase_token=payload.purchaseToken,
            product_id=payload.productId,
        )
    except google_billing_service.GoogleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return GoogleVerifyResponse()


@router.post("/google/notifications")
async def google_notifications(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    body = await request.json()
    try:
        await google_billing_service.handle_notification(session, body)
    except google_billing_service.GoogleBillingError:
        return {"status": "ignored"}
    return {"status": "ok"}


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
