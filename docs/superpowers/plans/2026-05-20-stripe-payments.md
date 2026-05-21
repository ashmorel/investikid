# Stripe Payments Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let parents pay for Premium via Stripe Checkout subscriptions, with webhooks bridging Stripe billing state to the existing `is_premium` entitlement seam.

**Architecture:** New `Subscription` model tracks billing state per `parent_email`. Four billing endpoints handle checkout, portal, status, and webhooks. Stripe hosts all payment UI — no card data touches our servers. Webhook handlers call `set_premium()` to grant/revoke premium for all children under a parent.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Stripe Python SDK, React 18, TypeScript, TanStack Query, Tailwind CSS.

---

## File Map

### New Files — Backend

| File | Responsibility |
|------|---------------|
| `backend/app/models/subscription.py` | SQLAlchemy `Subscription` model |
| `backend/app/schemas/billing.py` | Pydantic request/response schemas for billing endpoints |
| `backend/app/services/billing_service.py` | Stripe API calls: create customer, checkout session, portal session |
| `backend/app/services/webhook_service.py` | Webhook event dispatch — maps Stripe events to entitlement changes |
| `backend/app/routers/billing.py` | HTTP endpoints: checkout, portal, status, webhook |
| `backend/alembic/versions/xxxx_add_subscriptions.py` | Migration for the `subscriptions` table |
| `backend/tests/test_billing.py` | Backend tests for billing endpoints and webhook handling |

### New Files — Frontend

| File | Responsibility |
|------|---------------|
| `frontend/src/api/billing.ts` | API client: `createCheckout()`, `createPortal()`, `getSubscriptionStatus()` |
| `frontend/src/components/SubscriptionCard.tsx` | Subscription status + action button for Parent Dashboard |
| `frontend/tests/unit/SubscriptionCard.test.tsx` | Unit tests for the card's states |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/core/config.py` | Add `stripe_price_id`, `stripe_portal_config_id` fields |
| `backend/app/models/__init__.py` | Import `Subscription` model |
| `backend/app/main.py` | Register billing router |
| `backend/app/core/csrf.py` | Exempt `/billing/webhook` from CSRF |
| `backend/app/routers/parent.py` | Remove manual premium toggle endpoint |
| `backend/app/schemas/parent.py` | Remove `PremiumToggleRequest` |
| `frontend/src/api/parent.ts` | Remove `setChildPremium()` |
| `frontend/src/components/ChildCard.tsx` | Remove premium toggle button, keep badge |
| `frontend/src/pages/ParentDashboard.tsx` | Add `SubscriptionCard`, handle checkout redirect query params |
| `frontend/tests/unit/ChildCard.test.tsx` | Update tests for removed toggle |

---

## Task Breakdown

### Task 1: Config + Subscription Model + Migration

**Files:**
- Modify: `backend/app/core/config.py:14-15` (add two fields after existing stripe fields)
- Create: `backend/app/models/subscription.py`
- Modify: `backend/app/models/__init__.py` (add Subscription import)
- Create: `backend/alembic/versions/xxxx_add_subscriptions.py`

- [ ] **Step 1: Add missing config fields**

In `backend/app/core/config.py`, add `stripe_price_id` and `stripe_portal_config_id` after the existing `stripe_webhook_secret` line:

```python
stripe_secret_key: str = ""
stripe_webhook_secret: str = ""
stripe_price_id: str = ""
stripe_portal_config_id: str = ""
```

- [ ] **Step 2: Create the Subscription model**

Create `backend/app/models/subscription.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    parent_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="incomplete")
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

- [ ] **Step 3: Register the model**

In `backend/app/models/__init__.py`, add at the end:

```python
from app.models.subscription import Subscription  # noqa: F401
```

- [ ] **Step 4: Create the Alembic migration**

Create `backend/alembic/versions/a1b2c3d4e5f6_add_subscriptions.py`:

```python
"""add subscriptions table

Revision ID: a1b2c3d4e5f6
Revises: 09718bc80afc
Create Date: 2026-05-21 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "09718bc80afc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_email", sa.String(255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="incomplete"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index(op.f("ix_subscriptions_parent_email"), "subscriptions", ["parent_email"])


def downgrade() -> None:
    op.drop_index(op.f("ix_subscriptions_parent_email"), table_name="subscriptions")
    op.drop_table("subscriptions")
```

- [ ] **Step 5: Verify the model loads**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -c "from app.models.subscription import Subscription; print('OK:', Subscription.__tablename__)"`

Expected: `OK: subscriptions`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/models/subscription.py backend/app/models/__init__.py backend/alembic/versions/a1b2c3d4e5f6_add_subscriptions.py
git commit -m "feat: add Subscription model, migration, and config fields for Stripe billing"
```

---

### Task 2: Billing Schemas

**Files:**
- Create: `backend/app/schemas/billing.py`

- [ ] **Step 1: Create billing schemas**

Create `backend/app/schemas/billing.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    status: str | None = None
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
```

- [ ] **Step 2: Verify import**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -c "from app.schemas.billing import CheckoutResponse, PortalResponse, SubscriptionStatusResponse; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/billing.py
git commit -m "feat: add Pydantic schemas for billing endpoints"
```

---

### Task 3: Billing Service (Stripe API wrapper)

**Files:**
- Create: `backend/app/services/billing_service.py`

- [ ] **Step 1: Create the billing service**

Create `backend/app/services/billing_service.py`:

```python
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
```

- [ ] **Step 2: Verify import**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -c "from app.services.billing_service import create_checkout_session, create_portal_session, get_subscription_status; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/billing_service.py
git commit -m "feat: add billing service wrapping Stripe API calls"
```

---

### Task 4: Webhook Service

**Files:**
- Create: `backend/app/services/webhook_service.py`

- [ ] **Step 1: Create the webhook service**

Create `backend/app/services/webhook_service.py`:

```python
from __future__ import annotations

import logging
from datetime import UTC, datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import set_premium

logger = logging.getLogger(__name__)


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
```

- [ ] **Step 2: Verify import**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -c "from app.services.webhook_service import dispatch_webhook_event, EVENT_HANDLERS; print('Handlers:', list(EVENT_HANDLERS.keys()))"`

Expected: `Handlers: ['checkout.session.completed', 'customer.subscription.updated', 'customer.subscription.deleted', 'invoice.payment_failed']`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/webhook_service.py
git commit -m "feat: add webhook service to map Stripe events to entitlement changes"
```

---

### Task 5: Billing Router + CSRF Exemption + App Registration

**Files:**
- Create: `backend/app/routers/billing.py`
- Modify: `backend/app/core/csrf.py` (add `/billing/webhook` to exempt paths)
- Modify: `backend/app/main.py` (register billing router)

- [ ] **Step 1: Create the billing router**

Create `backend/app/routers/billing.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

import stripe

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
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    await dispatch_webhook_event(session, event)
    return {"status": "ok"}
```

- [ ] **Step 2: Exempt `/billing/webhook` from CSRF**

In `backend/app/core/csrf.py`, add `"/billing/webhook"` to the `_DEFAULT_EXEMPT_PATHS` frozenset:

```python
_DEFAULT_EXEMPT_PATHS = frozenset({
    "/auth/login", "/auth/register", "/health",
    "/auth/forgot-password", "/auth/reset-password",
    "/consent/decide",
    "/parent/auth/request",
    "/billing/webhook",
})
```

- [ ] **Step 3: Register the billing router in main.py**

In `backend/app/main.py`, add the import at the top with the other router imports:

```python
from app.routers import billing as billing_router
```

And add this line after the existing `application.include_router(ai_router.router)`:

```python
application.include_router(billing_router.router)
```

- [ ] **Step 4: Verify import**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -c "from app.routers.billing import router; print('Routes:', [r.path for r in router.routes])"`

Expected output showing `/checkout`, `/portal`, `/status`, `/webhook` paths.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/billing.py backend/app/core/csrf.py backend/app/main.py
git commit -m "feat: add billing router with checkout, portal, status, webhook endpoints"
```

---

### Task 6: Backend Tests

**Files:**
- Create: `backend/tests/test_billing.py`

This is the largest task. Tests mock all Stripe API calls at the service boundary.

- [ ] **Step 1: Write all billing tests**

Create `backend/tests/test_billing.py`:

```python
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.subscription import Subscription
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup_parent(client, db_session, parent_email="billing@example.com",
                        child_email="billingkid@example.com",
                        child_username="billingkid"):
    """Create child + parent magic-link session."""
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


# --- Checkout ---

@patch("app.services.billing_service.stripe")
async def test_checkout_creates_session(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="ckout1@example.com", child_username="ckout1")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/test")

    r = await client.post("/billing/checkout", headers=_csrf_headers(client))
    assert r.status_code == 200
    body = r.json()
    assert body["url"] == "https://checkout.stripe.com/test"

    # Verify Subscription row was created
    sub = await db_session.scalar(
        select(Subscription).where(Subscription.parent_email == "billing@example.com")
    )
    assert sub is not None
    assert sub.stripe_customer_id == "cus_test123"


@patch("app.services.billing_service.stripe")
async def test_checkout_reuses_customer(mock_stripe, client, db_session):
    """Second checkout call reuses existing Stripe customer."""
    await _setup_parent(client, db_session,
                        child_email="ckout2@example.com", child_username="ckout2",
                        parent_email="reuse@example.com")
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_reuse")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/1")
    await client.post("/billing/checkout", headers=_csrf_headers(client))

    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/2")
    r = await client.post("/billing/checkout", headers=_csrf_headers(client))
    assert r.status_code == 200
    # Customer.create should only be called once (first time)
    assert mock_stripe.Customer.create.call_count == 1


async def test_checkout_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.post("/billing/checkout")
    assert r.status_code == 401


async def test_checkout_503_without_stripe_key(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="ckout503@example.com", child_username="ckout503",
                        parent_email="nokey@example.com")
    original = settings.stripe_secret_key
    settings.stripe_secret_key = ""
    try:
        r = await client.post("/billing/checkout", headers=_csrf_headers(client))
        assert r.status_code == 503
    finally:
        settings.stripe_secret_key = original


# --- Portal ---

@patch("app.services.billing_service.stripe")
async def test_portal_returns_url(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="portal1@example.com", child_username="portal1",
                        parent_email="portal@example.com")
    # Create a subscription row first
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_portal")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://co.stripe.com/x")
    await client.post("/billing/checkout", headers=_csrf_headers(client))

    mock_stripe.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/portal")
    r = await client.post("/billing/portal", headers=_csrf_headers(client))
    assert r.status_code == 200
    assert r.json()["url"] == "https://billing.stripe.com/portal"


async def test_portal_404_no_subscription(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="portal404@example.com", child_username="portal404",
                        parent_email="noportal@example.com")
    r = await client.post("/billing/portal", headers=_csrf_headers(client))
    assert r.status_code == 404


# --- Status ---

async def test_status_no_subscription(client, db_session):
    await _setup_parent(client, db_session,
                        child_email="stat1@example.com", child_username="stat1",
                        parent_email="nostatus@example.com")
    r = await client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_subscription"] is False
    assert body["status"] is None


@patch("app.services.billing_service.stripe")
async def test_status_active(mock_stripe, client, db_session):
    await _setup_parent(client, db_session,
                        child_email="stat2@example.com", child_username="stat2",
                        parent_email="active@example.com")
    # Create subscription and set it to active
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_active")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://co.stripe.com/x")
    await client.post("/billing/checkout", headers=_csrf_headers(client))

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.parent_email == "active@example.com")
    )
    sub.status = "active"
    sub.stripe_subscription_id = "sub_active"
    from datetime import UTC, datetime
    sub.current_period_end = datetime(2026, 6, 21, tzinfo=UTC)
    await db_session.flush()

    r = await client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_subscription"] is True
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is False


# --- Webhook ---

@patch("app.services.webhook_service.stripe")
@patch("app.routers.billing.stripe")
async def test_webhook_checkout_completed(mock_router_stripe, mock_ws_stripe, client, db_session):
    """checkout.session.completed upserts Subscription and grants premium to children."""
    parent_email = "whook@example.com"
    await _setup_parent(client, db_session,
                        child_email="whookchild@example.com", child_username="whookchild",
                        parent_email=parent_email)

    # Pre-create a subscription row
    sub = Subscription(
        parent_email=parent_email,
        stripe_customer_id="cus_whook",
        status="incomplete",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_whook",
                "subscription": "sub_whook",
                "metadata": {"parent_email": parent_email},
            }
        },
    }

    mock_router_stripe.Webhook.construct_event.return_value = event_payload
    mock_ws_stripe.Subscription.retrieve.return_value = MagicMock(
        status="trialing",
        current_period_end=1748476800,  # 2025-05-28 in epoch
        cancel_at_period_end=False,
    )

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200

    # Verify subscription was updated
    await db_session.refresh(sub)
    assert sub.stripe_subscription_id == "sub_whook"
    assert sub.status == "trialing"

    # Verify child got premium
    child = await db_session.scalar(
        select(User).where(User.email == "whookchild@example.com")
    )
    await db_session.refresh(child)
    assert child.is_premium is True


@patch("app.routers.billing.stripe")
async def test_webhook_subscription_updated_cancel(mock_stripe, client, db_session):
    """customer.subscription.updated with cancel_at_period_end=true."""
    sub = Subscription(
        parent_email="cancelup@example.com",
        stripe_customer_id="cus_cancelup",
        stripe_subscription_id="sub_cancelup",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_cancelup",
                "status": "active",
                "current_period_end": 1748476800,
                "cancel_at_period_end": True,
            }
        },
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.cancel_at_period_end is True


@patch("app.routers.billing.stripe")
async def test_webhook_subscription_deleted(mock_stripe, client, db_session):
    """customer.subscription.deleted downgrades all children."""
    parent_email = "delsub@example.com"
    await _setup_parent(client, db_session,
                        child_email="delchild@example.com", child_username="delchild",
                        parent_email=parent_email)
    # Make child premium first
    child = await db_session.scalar(
        select(User).where(User.email == "delchild@example.com")
    )
    child.is_premium = True
    await db_session.flush()

    sub = Subscription(
        parent_email=parent_email,
        stripe_customer_id="cus_delsub",
        stripe_subscription_id="sub_delsub",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_delsub"}},
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    await db_session.refresh(child)
    assert child.is_premium is False


@patch("app.routers.billing.stripe")
async def test_webhook_payment_failed(mock_stripe, client, db_session):
    """invoice.payment_failed marks subscription past_due, children stay premium."""
    sub = Subscription(
        parent_email="pf@example.com",
        stripe_customer_id="cus_pf",
        stripe_subscription_id="sub_pf",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": "sub_pf"}},
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=sig"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "past_due"


@patch("app.routers.billing.stripe")
async def test_webhook_bad_signature(mock_stripe, client):
    mock_stripe.Webhook.construct_event.side_effect = (
        stripe.error.SignatureVerificationError("bad", "sig")
    )
    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        r = await client.post(
            "/billing/webhook",
            content=b'{}',
            headers={"stripe-signature": "t=1,v1=bad"},
        )
    finally:
        settings.stripe_webhook_secret = original_secret
    assert r.status_code == 400


@patch("app.routers.billing.stripe")
async def test_webhook_idempotent(mock_stripe, client, db_session):
    """Duplicate subscription.updated event is a no-op."""
    sub = Subscription(
        parent_email="idem@example.com",
        stripe_customer_id="cus_idem",
        stripe_subscription_id="sub_idem",
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()

    event_payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_idem",
                "status": "active",
                "current_period_end": 1748476800,
                "cancel_at_period_end": False,
            }
        },
    }
    mock_stripe.Webhook.construct_event.return_value = event_payload

    original_secret = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = "whsec_test"
    try:
        # Send same event twice
        r1 = await client.post("/billing/webhook", content=b'{}',
                               headers={"stripe-signature": "t=1,v1=sig"})
        r2 = await client.post("/billing/webhook", content=b'{}',
                               headers={"stripe-signature": "t=1,v1=sig"})
    finally:
        settings.stripe_webhook_secret = original_secret

    assert r1.status_code == 200
    assert r2.status_code == 200
    await db_session.refresh(sub)
    assert sub.status == "active"
```

- [ ] **Step 2: Install stripe dependency**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pip install stripe`

Then add `stripe` to `backend/requirements.txt` (if it exists) or note the dependency.

- [ ] **Step 3: Run the tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_billing.py -v`

Expected: All 14 tests PASS.

- [ ] **Step 4: Run full backend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -v`

Expected: All tests pass (baseline + 14 new billing tests).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_billing.py
git commit -m "test: add 14 billing endpoint and webhook tests"
```

---

### Task 7: Remove Manual Premium Toggle (Backend)

**Files:**
- Modify: `backend/app/routers/parent.py` (remove `set_child_premium` endpoint)
- Modify: `backend/app/schemas/parent.py` (remove `PremiumToggleRequest`)

- [ ] **Step 1: Remove PremiumToggleRequest schema**

In `backend/app/schemas/parent.py`, remove the `PremiumToggleRequest` class:

```python
class PremiumToggleRequest(BaseModel):
    premium: bool
```

The file should end after `FreezeRequest`.

- [ ] **Step 2: Remove the premium toggle endpoint from the parent router**

In `backend/app/routers/parent.py`:

Remove the import of `PremiumToggleRequest` from the imports line:
```python
from app.schemas.parent import ChildOut, FreezeRequest
```

Remove the import of `set_premium` (no longer used by this router):
```python
# Remove: from app.services.entitlements import set_premium
```

Remove the entire `set_child_premium` function (lines 71-83):
```python
# Remove entire function:
# @router.post("/children/{user_id}/premium")
# async def set_child_premium(...):
#     ...
```

- [ ] **Step 3: Update any backend tests referencing the removed endpoint**

Check if `test_parent_dashboard.py` tests the premium toggle endpoint. If so, remove those tests. The endpoint no longer exists.

Run: `grep -n "premium" /Users/leeashmore/Local\ Repo/invest-ed/backend/tests/test_parent_dashboard.py`

Remove any tests calling `POST /parent/children/{id}/premium`.

- [ ] **Step 4: Run full backend tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -v`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/parent.py backend/app/schemas/parent.py backend/tests/test_parent_dashboard.py
git commit -m "refactor: remove manual premium toggle endpoint — billing handles premium now"
```

---

### Task 8: Frontend Billing API Client

**Files:**
- Create: `frontend/src/api/billing.ts`
- Modify: `frontend/src/api/parent.ts` (remove `setChildPremium`)

- [ ] **Step 1: Create the billing API client**

Create `frontend/src/api/billing.ts`:

```typescript
import { apiFetch } from './client';

export type SubscriptionStatus = {
  has_subscription: boolean;
  status: string | null;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export const billingApi = {
  createCheckout: () =>
    apiFetch<{ url: string }>('/billing/checkout', { method: 'POST' }),

  createPortal: () =>
    apiFetch<{ url: string }>('/billing/portal', { method: 'POST' }),

  getStatus: () =>
    apiFetch<SubscriptionStatus>('/billing/status'),
};
```

- [ ] **Step 2: Remove setChildPremium from parent API**

In `frontend/src/api/parent.ts`, remove the `setChildPremium` method:

```typescript
// Remove these lines:
//   setChildPremium: (userId: string, premium: boolean) =>
//     apiFetch<{ status: string; premium: boolean }>(
//       `/parent/children/${userId}/premium`,
//       { method: 'POST', body: JSON.stringify({ premium }) },
//     ),
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`

If there are errors referencing `setChildPremium`, they will be fixed in the next task (ChildCard).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/billing.ts frontend/src/api/parent.ts
git commit -m "feat: add billing API client, remove setChildPremium"
```

---

### Task 9: SubscriptionCard Component

**Files:**
- Create: `frontend/src/components/SubscriptionCard.tsx`

- [ ] **Step 1: Create the SubscriptionCard component**

Create `frontend/src/components/SubscriptionCard.tsx`:

```tsx
import { useMutation, useQuery } from '@tanstack/react-query';
import { billingApi, type SubscriptionStatus } from '@/api/billing';
import { Button } from '@/components/ui/button';

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function SubscriptionCard() {
  const { data: sub, isLoading } = useQuery<SubscriptionStatus | null>({
    queryKey: ['subscription-status'],
    queryFn: billingApi.getStatus,
  });

  const checkout = useMutation({
    mutationFn: billingApi.createCheckout,
    onSuccess: (data) => {
      if (data?.url) window.location.href = data.url;
    },
  });

  const portal = useMutation({
    mutationFn: billingApi.createPortal,
    onSuccess: (data) => {
      if (data?.url) window.location.href = data.url;
    },
  });

  if (isLoading || !sub) return null;

  const isActive = sub.has_subscription && sub.status !== 'canceled';

  // No subscription or canceled — show upgrade CTA
  if (!isActive) {
    return (
      <section
        className="rounded-lg border-2 border-amber-200 bg-amber-50 px-4 py-4 sm:px-6 sm:py-6"
        aria-label="Subscription status"
      >
        <p className="text-sm font-medium text-amber-900">
          Free plan — upgrade for AI coach, advanced scenarios, and more
        </p>
        <Button
          className="mt-3 bg-amber-500 text-white hover:bg-amber-600"
          onClick={() => checkout.mutate()}
          disabled={checkout.isPending}
        >
          {checkout.isPending ? 'Redirecting…' : 'Subscribe to Premium'}
        </Button>
      </section>
    );
  }

  // Active subscription states
  let statusText = '';
  if (sub.status === 'trialing' && sub.trial_ends_at) {
    const days = daysUntil(sub.trial_ends_at);
    statusText = `Premium trial — ${days} day${days !== 1 ? 's' : ''} remaining`;
  } else if (sub.cancel_at_period_end && sub.current_period_end) {
    statusText = `Premium — cancels ${formatDate(sub.current_period_end)}`;
  } else if (sub.status === 'past_due') {
    statusText = 'Premium — payment issue, retrying';
  } else if (sub.current_period_end) {
    statusText = `Premium — renews ${formatDate(sub.current_period_end)}`;
  } else {
    statusText = 'Premium — active';
  }

  return (
    <section
      className="rounded-lg border-2 border-amber-200 bg-amber-50 px-4 py-4 sm:px-6 sm:py-6"
      aria-label="Subscription status"
    >
      <p className="text-sm font-medium text-amber-900">{statusText}</p>
      <Button
        variant="outline"
        className="mt-3"
        onClick={() => portal.mutate()}
        disabled={portal.isPending}
      >
        {portal.isPending ? 'Redirecting…' : 'Manage Billing'}
      </Button>
    </section>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`

Expected: Clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SubscriptionCard.tsx
git commit -m "feat: add SubscriptionCard component for Parent Dashboard"
```

---

### Task 10: SubscriptionCard Tests

**Files:**
- Create: `frontend/tests/unit/SubscriptionCard.test.tsx`

- [ ] **Step 1: Write SubscriptionCard tests**

Create `frontend/tests/unit/SubscriptionCard.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubscriptionCard } from '@/components/SubscriptionCard';

// Mock the billing API
const mockGetStatus = vi.fn();
const mockCreateCheckout = vi.fn();
const mockCreatePortal = vi.fn();

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => mockGetStatus(),
    createCheckout: () => mockCreateCheckout(),
    createPortal: () => mockCreatePortal(),
  },
}));

function wrap() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={qc}>
      <SubscriptionCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SubscriptionCard', () => {
  it('shows Subscribe button when no subscription', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByRole('button', { name: /subscribe to premium/i })).toBeInTheDocument();
    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
  });

  it('shows trial status with days remaining', async () => {
    const futureDate = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'trialing',
      trial_ends_at: futureDate,
      current_period_end: futureDate,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/premium trial/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  it('shows active status with renewal date', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'active',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/premium — renews/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  it('shows cancellation date when cancel_at_period_end', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'active',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: true,
    });
    wrap();
    expect(await screen.findByText(/premium — cancels/i)).toBeInTheDocument();
  });

  it('shows payment issue for past_due', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'past_due',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/payment issue/i)).toBeInTheDocument();
  });

  it('shows Subscribe button when canceled', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByRole('button', { name: /subscribe to premium/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run tests/unit/SubscriptionCard.test.tsx`

Expected: 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/unit/SubscriptionCard.test.tsx
git commit -m "test: add SubscriptionCard unit tests for all subscription states"
```

---

### Task 11: Update ChildCard + ParentDashboard

**Files:**
- Modify: `frontend/src/components/ChildCard.tsx` (remove premium toggle)
- Modify: `frontend/src/pages/ParentDashboard.tsx` (add SubscriptionCard, handle checkout params)
- Modify: `frontend/tests/unit/ChildCard.test.tsx` (update tests)

- [ ] **Step 1: Remove premium toggle from ChildCard**

In `frontend/src/components/ChildCard.tsx`:

1. Remove the `premium` mutation (lines 57-75 — the entire `useMutation` for `parentApi.setChildPremium`).

2. Remove the premium toggle button and placeholder text (lines 119-135). Keep the "Premium ✨" badge. The section between the freeze toggle and the delete dialog should become:

```tsx
{child.is_premium && (
  <span className="text-xs font-medium text-amber-600">Premium ✨</span>
)}
```

3. Remove the `PremiumToggleRequest` import if it appears (it doesn't — it's only in the backend schema, but check).

4. Clean up unused imports: remove `parentApi.setChildPremium` reference. Since `parentApi` is still used for `freezeChild` and `eraseChild`, keep the import but the `setChildPremium` method no longer exists.

The updated JSX for the middle section (between freeze toggle and delete dialog) should be:

```tsx
<div className="mt-4 flex items-center justify-between">
  <div className="flex items-center gap-2">
    <Switch
      id={`freeze-${child.user_id}`}
      checked={!child.is_active && !isDeleted}
      disabled={isDeleted || freeze.isPending}
      onCheckedChange={(frozen) => freeze.mutate(frozen)}
    />
    <Label htmlFor={`freeze-${child.user_id}`} className="text-sm">
      Freeze account
    </Label>
  </div>

  {child.is_premium && (
    <span className="text-xs font-medium text-amber-600">Premium ✨</span>
  )}

  <Dialog open={open} onOpenChange={setOpen}>
    {/* ... existing delete dialog unchanged ... */}
  </Dialog>
</div>
```

- [ ] **Step 2: Add SubscriptionCard to ParentDashboard**

In `frontend/src/pages/ParentDashboard.tsx`:

Add imports:
```tsx
import { useSearchParams } from 'react-router-dom';
import { useEffect } from 'react';
import { SubscriptionCard } from '@/components/SubscriptionCard';
import { useToast } from '@/hooks/use-toast';
```

Inside the component, add checkout redirect handling after the existing hooks:
```tsx
const [searchParams, setSearchParams] = useSearchParams();
const { toast } = useToast();

useEffect(() => {
  const checkoutResult = searchParams.get('checkout');
  if (checkoutResult === 'success') {
    toast({
      title: 'Welcome to Premium!',
      description: 'All your children now have access to premium features.',
    });
    searchParams.delete('checkout');
    setSearchParams(searchParams, { replace: true });
  } else if (checkoutResult === 'canceled') {
    searchParams.delete('checkout');
    setSearchParams(searchParams, { replace: true });
  }
}, [searchParams, setSearchParams, toast]);
```

Add the `<SubscriptionCard />` above the children list, after the header and before the loading/error/data conditionals:

```tsx
<SubscriptionCard />
```

- [ ] **Step 3: Update ChildCard tests**

In `frontend/tests/unit/ChildCard.test.tsx`:

Remove the two tests about the premium toggle:
- `'renders Upgrade to Premium button for a free child'`
- `'renders Premium ✨ indicator and Downgrade button for a premium child'`

Replace them with:
```tsx
it('shows Premium badge when child is premium', () => {
  wrap({ ...baseChild, is_premium: true });
  expect(screen.getByText(/Premium ✨/)).toBeInTheDocument();
});

it('does not show premium toggle button', () => {
  wrap(baseChild);
  expect(screen.queryByTestId('premium-toggle')).not.toBeInTheDocument();
});
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`

Expected: Clean.

- [ ] **Step 5: Run all frontend tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`

Expected: All tests pass (baseline minus removed tests + new tests).

- [ ] **Step 6: Run lint**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx eslint src/ --ext .ts,.tsx`

Expected: Clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ChildCard.tsx frontend/src/pages/ParentDashboard.tsx frontend/tests/unit/ChildCard.test.tsx
git commit -m "feat: wire SubscriptionCard into ParentDashboard, remove manual premium toggle from ChildCard"
```

---

### Task 12: Full Regression + Close-Out

**Files:** None new — verification only.

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -v`

Expected: All tests pass.

- [ ] **Step 2: Run full frontend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`

Expected: All tests pass.

- [ ] **Step 3: TypeScript check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`

Expected: Clean.

- [ ] **Step 4: Lint check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx eslint src/ --ext .ts,.tsx`

Expected: Clean.

- [ ] **Step 5: Verify no leftover references to removed code**

Run:
```bash
grep -r "setChildPremium" /Users/leeashmore/Local\ Repo/invest-ed/frontend/src/
grep -r "PremiumToggleRequest" /Users/leeashmore/Local\ Repo/invest-ed/backend/app/
grep -r "premium-toggle" /Users/leeashmore/Local\ Repo/invest-ed/frontend/src/
grep -r "/children/{user_id}/premium" /Users/leeashmore/Local\ Repo/invest-ed/backend/
```

Expected: No matches for any of these.

- [ ] **Step 6: Verify Stripe dependency is listed**

Run: `grep stripe /Users/leeashmore/Local\ Repo/invest-ed/backend/requirements.txt`

Expected: `stripe` appears in requirements.

---

## Spec Coverage Checklist

| Spec Section | Plan Task(s) |
|---|---|
| 1.1 Pricing (family plan, trial, grace) | Task 3 (`subscription_data`), Task 4 (`handle_subscription_deleted`) |
| 1.2 Data Model (`subscriptions` table) | Task 1 |
| 2.1 New Files | Tasks 1–6 |
| 2.2 Configuration | Task 1 (config fields) |
| 2.3 Endpoints (checkout, portal, status, webhook) | Task 5 |
| 2.4 Webhook Event Handling | Task 4 |
| 3.1 Frontend New Files | Tasks 8–10 |
| 3.2 SubscriptionCard states | Task 9 |
| 3.3 ChildCard changes (remove toggle, keep badge) | Task 11 |
| 3.4 ParentDashboard changes | Task 11 |
| 3.5 Child-facing premium gates ("Ask your parent") | Out of scope for this plan — existing gates already work; text update is minor copy change |
| 4.1–4.4 Checkout/Webhook flows & idempotency | Tasks 3–6 |
| 5.1–5.4 Testing (mocking, backend, frontend) | Tasks 6, 10, 11 |
| 6 Dependencies (stripe pip) | Task 6 |

**Note:** Spec section 3.5 mentions adding "Ask your parent to upgrade to Premium!" text below lock icons on child-facing premium gates. This is a one-line copy change in the existing premium gate components. If the implementer notices the exact component during implementation, they should add it. Otherwise it's a trivial follow-up.
