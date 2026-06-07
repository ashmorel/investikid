# 4A·A2 — Cross-Store Payments + Live iOS IAP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native Apple In-App Purchase (StoreKit 2, self-validated) alongside the existing web Stripe billing, behind one source-agnostic entitlement core, and bridge 4B's child request into a parent approve/decline loop.

**Architecture:** Generalise the Stripe-only `subscriptions` table to carry a `provider`; every channel writes/updates its row then calls one `recompute_household_premium()` which ORs all the household's active subscriptions and drives the existing `set_premium()` seam. Apple is validated server-side via Apple's official `app-store-server-library` (JWS verification + App Store Server API + App Store Server Notifications V2). The iOS client uses a small custom Capacitor StoreKit 2 plugin.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · Alembic · pydantic v2 · `app-store-server-library` (Python) · React 18 + Vite + TS + TanStack Query + Tailwind v4 + shadcn · Capacitor 8 (Swift StoreKit 2 plugin) · pytest (async, `loop_scope="session"`) · Vitest + vitest-axe.

**Branch:** `testing`. **Current Alembic head:** `d2e3f4a5b6c7`. **Existing fact:** the Stripe checkout already sets `trial_period_days = 7` and handles `trialing` — web trial is DONE; only Apple needs trial config (App Store Connect, user-side).

---

## File Structure

**Backend (create):**
- `app/services/entitlements.py` — add `ACTIVE_SUBSCRIPTION_STATUSES` + `recompute_household_premium()` (extend existing file).
- `app/services/apple_billing_service.py` — JWS verify + App Store Server API + row upsert + recompute.
- `app/schemas/apple_billing.py` — request/response models for `/billing/apple/*`.
- `tests/services/test_recompute_household_premium.py`, `tests/services/test_apple_billing_service.py`, `tests/routers/test_apple_billing.py`, `tests/routers/test_premium_request_decline.py`.

**Backend (modify):**
- `app/models/subscription.py` — add `provider`, `external_id`; make Stripe columns nullable.
- `app/models/premium_request.py` — add `declined_at`.
- `app/services/webhook_service.py` — refactor Stripe handlers to write row + call recompute.
- `app/routers/billing.py` — add `/billing/apple/verify` + `/billing/apple/notifications`.
- `app/routers/parent.py` — add `POST /premium-requests/{id}/decline`; exclude declined from list.
- `app/core/csrf.py` — exempt `/billing/apple/notifications`.
- `app/core/config.py` — Apple billing settings; `backend/.env.example`.
- `alembic/versions/` — one chained migration.

**Frontend (create):**
- `ios/App/App/StoreKitPlugin.swift` + `StoreKitPlugin.m` — custom Capacitor StoreKit 2 plugin.
- `src/lib/storekit.ts` — typed bridge to the plugin.
- tests under `src/components/__tests__/` and `src/components/parent/__tests__/`.

**Frontend (modify):**
- `src/api/billing.ts` — add `appleVerify`, `appleRestore` calls.
- `src/api/premium.ts` — add `declineRequest`.
- `src/components/SubscriptionCard.tsx` — channel-aware (web Stripe vs native StoreKit).
- `src/components/parent/PremiumRequestsCard.tsx` — Approve/Decline actions.
- the child paywall (`src/components/child/PremiumPaywall.tsx`) — gentle "declined" state.

---

## Task 1: Generalise the `subscriptions` table + add `declined_at`

**Files:**
- Modify: `app/models/subscription.py`
- Modify: `app/models/premium_request.py`
- Create: `alembic/versions/e3f4a5b6c7d8_provider_agnostic_subscriptions.py`
- Test: `tests/models/test_subscription_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/models/test_subscription_provider.py
import pytest
from sqlalchemy import select
from app.models.subscription import Subscription
from app.models.premium_request import PremiumRequest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_subscription_has_provider_and_external_id(db_session):
    sub = Subscription(
        parent_email="p@example.com", provider="apple",
        external_id="apple-orig-tx-1", status="active",
    )
    db_session.add(sub)
    await db_session.flush()
    got = await db_session.scalar(select(Subscription).where(Subscription.external_id == "apple-orig-tx-1"))
    assert got.provider == "apple"
    assert got.stripe_customer_id is None  # now nullable


async def test_premium_request_has_declined_at(db_session):
    pr = PremiumRequest(
        child_user_id=__import__("uuid").uuid4(), parent_email="p@example.com",
        context_kind="module", context_label="Investing Basics",
    )
    db_session.add(pr)
    await db_session.flush()
    assert pr.declined_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_subscription_provider.py -v`
Expected: FAIL (`provider` / `external_id` / `declined_at` do not exist).

- [ ] **Step 3: Update the models**

In `app/models/subscription.py`, add the two columns and make Stripe fields nullable:

```python
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="stripe", index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

(Remove the old `unique=True` on `stripe_customer_id`/`stripe_subscription_id`; uniqueness now lives on `(provider, external_id)` — added in the migration. Keep all other columns.)

In `app/models/premium_request.py`, add:

```python
    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Write the chained migration**

```python
# alembic/versions/e3f4a5b6c7d8_provider_agnostic_subscriptions.py
"""provider-agnostic subscriptions + premium_request.declined_at

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("provider", sa.String(length=20), nullable=False, server_default="stripe"))
    op.add_column("subscriptions", sa.Column("external_id", sa.String(length=255), nullable=True))
    op.alter_column("subscriptions", "stripe_customer_id", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("subscriptions", "stripe_subscription_id", existing_type=sa.String(length=255), nullable=True)
    # backfill external_id for existing Stripe rows
    op.execute("UPDATE subscriptions SET external_id = stripe_subscription_id WHERE stripe_subscription_id IS NOT NULL")
    # drop old single-column unique constraints if present, add composite + indexes
    op.create_index("ix_subscriptions_provider", "subscriptions", ["provider"])
    op.create_index("ix_subscriptions_external_id", "subscriptions", ["external_id"])
    op.create_unique_constraint("uq_subscriptions_provider_external_id", "subscriptions", ["provider", "external_id"])
    op.add_column("premium_requests", sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True))
    # server_default was only needed to backfill existing rows
    op.alter_column("subscriptions", "provider", server_default=None)


def downgrade() -> None:
    op.drop_column("premium_requests", "declined_at")
    op.drop_constraint("uq_subscriptions_provider_external_id", "subscriptions", type_="unique")
    op.drop_index("ix_subscriptions_external_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider", table_name="subscriptions")
    op.drop_column("subscriptions", "external_id")
    op.drop_column("subscriptions", "provider")
```

> Note: if the original migration created named unique constraints on `stripe_customer_id`/`stripe_subscription_id`, drop them here with `op.drop_constraint(...)`. Check with `\d subscriptions` in psql against the testing DB; add the matching `op.drop_constraint`/`op.create_unique`-less lines if needed.

- [ ] **Step 5: Apply migration + run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_subscription_provider.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/subscription.py app/models/premium_request.py alembic/versions/e3f4a5b6c7d8_provider_agnostic_subscriptions.py tests/models/test_subscription_provider.py
git commit -m "feat(billing): provider-agnostic subscriptions + premium_request.declined_at"
```

---

## Task 2: `recompute_household_premium` seam

**Files:**
- Modify: `app/services/entitlements.py`
- Test: `tests/services/test_recompute_household_premium.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_recompute_household_premium.py
import pytest
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import recompute_household_premium, is_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session, email):
    u = User(username="kid", email="kid@example.com", parent_email=email,
             hashed_password="x", is_active=True)
    db_session.add(u); await db_session.flush(); return u


async def test_grants_when_any_active(db_session):
    email = "a@example.com"
    child = await _child(db_session, email)
    db_session.add(Subscription(parent_email=email, provider="apple", external_id="t1", status="active"))
    await db_session.flush()
    await recompute_household_premium(db_session, email)
    assert is_premium(child) is True


async def test_revokes_when_none_active(db_session):
    email = "b@example.com"
    child = await _child(db_session, email)
    child.is_premium = True
    db_session.add(Subscription(parent_email=email, provider="apple", external_id="t2", status="expired"))
    await db_session.flush()
    await recompute_household_premium(db_session, email)
    assert is_premium(child) is False


async def test_trialing_and_grace_count_as_active(db_session):
    for email, st in (("c@example.com", "trialing"), ("d@example.com", "in_grace_period")):
        child = await _child(db_session, email)
        db_session.add(Subscription(parent_email=email, provider="apple", external_id=f"t-{st}", status=st))
        await db_session.flush()
        await recompute_household_premium(db_session, email)
        assert is_premium(child) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_recompute_household_premium.py -v`
Expected: FAIL (`recompute_household_premium` not defined).

- [ ] **Step 3: Implement in `app/services/entitlements.py`**

Add at the top (after imports) and a new function:

```python
from sqlalchemy import select
from app.models.subscription import Subscription

# Statuses that grant entitlement across every provider.
ACTIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "trialing", "in_grace_period", "past_due"})


async def recompute_household_premium(session: AsyncSession, parent_email: str) -> None:
    """Recompute premium for every child of `parent_email` as the OR of all
    the household's subscription rows across providers. Idempotent."""
    rows = (await session.scalars(
        select(Subscription).where(Subscription.parent_email == parent_email)
    )).all()
    entitled = any(r.status in ACTIVE_SUBSCRIPTION_STATUSES for r in rows)

    children = (await session.scalars(
        select(User).where(User.parent_email == parent_email)
    )).all()
    for child in children:
        await set_premium(session, child, value=entitled, actor="billing:recompute")
```

> `past_due` stays entitled (Stripe dunning grace), matching the existing `handle_payment_failed` behaviour ("children stay premium").

- [ ] **Step 4: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_recompute_household_premium.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/entitlements.py tests/services/test_recompute_household_premium.py
git commit -m "feat(billing): recompute_household_premium entitlement seam"
```

---

## Task 3: Refactor Stripe webhook to use the recompute seam

**Files:**
- Modify: `app/services/webhook_service.py`
- Test: `tests/services/test_webhook_recompute.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_webhook_recompute.py
import pytest
from datetime import UTC, datetime
from unittest.mock import patch
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import is_premium
from app.services import webhook_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_subscription_deleted_revokes_via_recompute(db_session):
    email = "z@example.com"
    child = User(username="k", email="k@example.com", parent_email=email,
                 hashed_password="x", is_active=True, is_premium=True)
    db_session.add(child)
    db_session.add(Subscription(parent_email=email, provider="stripe",
                   external_id="sub_1", stripe_subscription_id="sub_1",
                   stripe_customer_id="cus_1", status="active"))
    await db_session.flush()

    event = {"data": {"object": {"id": "sub_1"}}}
    with patch.object(webhook_service, "_commit_noop", create=True):
        await webhook_service.handle_subscription_deleted(db_session, event)
    assert is_premium(child) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_webhook_recompute.py -v`
Expected: FAIL (handler still does direct `set_premium`, but row uses new fields; assertion may pass incidentally — confirm by checking an AuditLog actor `billing:recompute` once refactored).

- [ ] **Step 3: Refactor handlers**

In `app/services/webhook_service.py`, import the seam and replace the per-handler child loops with recompute. Concretely:

```python
from app.services.entitlements import recompute_household_premium
```

In `handle_checkout_completed`, also set `sub.provider = "stripe"` and `sub.external_id = subscription_id`, and **replace** the `for child in children: set_premium(...True...)` loop with:

```python
    await recompute_household_premium(session, parent_email)
    await resolve_premium_requests(session, parent_email)
    await session.commit()
```

In `handle_subscription_updated`, set `sub.external_id = sub.external_id or subscription_id`, then **after** updating status add `await recompute_household_premium(session, sub.parent_email)` before `await session.commit()` (so a lapse-to-canceled via update also revokes).

In `handle_subscription_deleted`, **replace** the revoke loop with `await recompute_household_premium(session, sub.parent_email)`.

Keep `handle_payment_failed` as-is (sets `past_due`, which recompute treats as active) but add `await recompute_household_premium(session, sub.parent_email)` before commit for consistency.

Remove the now-unused direct `set_premium`/`User` imports if no longer referenced.

- [ ] **Step 4: Run the full billing test suite**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_webhook_recompute.py tests/ -k "webhook or billing or premium" -v`
Expected: PASS (existing Stripe webhook tests still green).

- [ ] **Step 5: Commit**

```bash
git add app/services/webhook_service.py tests/services/test_webhook_recompute.py
git commit -m "refactor(billing): Stripe webhook routes through recompute_household_premium"
```

---

## Task 4: Apple billing config + .env.example

**Files:**
- Modify: `app/core/config.py`
- Modify: `backend/.env.example`
- Test: `tests/core/test_apple_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_apple_config.py
from app.core.config import settings

def test_apple_settings_exist_with_defaults():
    assert settings.apple_iap_bundle_id == settings.apple_iap_bundle_id  # attribute exists
    assert settings.apple_iap_environment in ("Sandbox", "Production", "")
    assert hasattr(settings, "apple_iap_issuer_id")
    assert hasattr(settings, "apple_iap_key_id")
    assert hasattr(settings, "apple_iap_private_key")
    assert hasattr(settings, "apple_iap_app_apple_id")
    assert hasattr(settings, "apple_iap_product_id")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/core/test_apple_config.py -v`
Expected: FAIL (attributes missing).

- [ ] **Step 3: Add settings**

In `app/core/config.py` (Settings class), add:

```python
    apple_iap_issuer_id: str = ""          # App Store Connect API issuer id
    apple_iap_key_id: str = ""             # in-app-purchase key id
    apple_iap_private_key: str = ""        # contents of the .p8 (PEM)
    apple_iap_bundle_id: str = ""          # e.g. com.investikid.app
    apple_iap_app_apple_id: int | None = None  # numeric App Store app id
    apple_iap_environment: str = "Sandbox"  # "Sandbox" | "Production"
    apple_iap_product_id: str = ""         # the auto-renewable subscription product id
```

In `backend/.env.example`, add a commented block:

```bash
# Apple In-App Purchase (item 4A·A2) — set in production/sandbox; leave blank to disable Apple IAP
APPLE_IAP_ISSUER_ID=
APPLE_IAP_KEY_ID=
APPLE_IAP_PRIVATE_KEY=
APPLE_IAP_BUNDLE_ID=
APPLE_IAP_APP_APPLE_ID=
APPLE_IAP_ENVIRONMENT=Sandbox
APPLE_IAP_PRODUCT_ID=
```

- [ ] **Step 4: Run test**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/core/test_apple_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/config.py backend/.env.example tests/core/test_apple_config.py
git commit -m "feat(billing): Apple IAP configuration settings"
```

---

## Task 5: `apple_billing_service` — verify transaction + record + recompute

Add the dependency first: append `app-store-server-library` to `backend/requirements.txt` and `pip install -r requirements.txt` in the venv.

**Files:**
- Modify: `backend/requirements.txt`
- Create: `app/services/apple_billing_service.py`
- Test: `tests/services/test_apple_billing_service.py`

- [ ] **Step 1: Write the failing test** (verifier + API client are injected, so tests use fakes)

```python
# tests/services/test_apple_billing_service.py
import pytest
from datetime import UTC, datetime
from types import SimpleNamespace
from sqlalchemy import select
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import is_premium
from app.services import apple_billing_service as abs_

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeVerifier:
    def __init__(self, payload): self._p = payload
    def verify_and_decode_signed_transaction(self, jws): return self._p


def _payload(**kw):
    base = dict(originalTransactionId="OT-1", productId="premium_monthly",
                appAccountToken="a@example.com", expiresDate=int(
                    (datetime.now(UTC).timestamp() + 86400) * 1000),
                revocationDate=None)
    base.update(kw); return SimpleNamespace(**base)


async def test_verify_records_subscription_and_grants(db_session, monkeypatch):
    email = "a@example.com"
    child = User(username="k", email="k@example.com", parent_email=email,
                 hashed_password="x", is_active=True)
    db_session.add(child); await db_session.flush()

    monkeypatch.setattr(abs_, "_build_verifier", lambda: _FakeVerifier(_payload()))
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")

    await abs_.verify_transaction(db_session, parent_email=email, jws="signed-jws")

    row = await db_session.scalar(select(Subscription).where(
        Subscription.provider == "apple", Subscription.external_id == "OT-1"))
    assert row.status == "active"
    assert row.parent_email == email
    assert is_premium(child) is True


async def test_verify_rejects_token_parent_mismatch(db_session, monkeypatch):
    monkeypatch.setattr(abs_, "_build_verifier",
                        lambda: _FakeVerifier(_payload(appAccountToken="someone@else.com")))
    monkeypatch.setattr(abs_, "_fetch_status", lambda tx_id: "active")
    with pytest.raises(abs_.AppleBillingError):
        await abs_.verify_transaction(db_session, parent_email="a@example.com", jws="x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_apple_billing_service.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `app/services/apple_billing_service.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription
from app.services.entitlements import recompute_household_premium


class AppleBillingError(Exception):
    """Raised when an Apple transaction cannot be trusted/processed."""


def _require_apple() -> None:
    if not (settings.apple_iap_bundle_id and settings.apple_iap_issuer_id
            and settings.apple_iap_key_id and settings.apple_iap_private_key):
        raise AppleBillingError("Apple IAP is not configured")


def _environment():
    from appstoreserverlibrary.models.Environment import Environment
    return Environment.PRODUCTION if settings.apple_iap_environment == "Production" else Environment.SANDBOX


def _build_verifier():
    """Construct a SignedDataVerifier from Apple's library. Patched in tests."""
    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
    # Apple root CAs must be bundled at app/services/apple_roots/*.cer (see Step 3b)
    import pathlib
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
    """Return our normalized status from the App Store Server API. Patched in tests."""
    client = _api_client()
    resp = client.get_all_subscription_statuses(original_transaction_id)
    # status codes: 1=active 2=expired 3=in_billing_retry 4=in_grace_period 5=revoked
    code = resp.data[0].lastTransactions[0].status
    return {1: "active", 2: "expired", 3: "past_due", 4: "in_grace_period", 5: "expired"}.get(code, "expired")


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


async def verify_transaction(session: AsyncSession, *, parent_email: str, jws: str) -> None:
    """Verify a StoreKit signed transaction (JWS), associate it to the parent
    via appAccountToken, record the subscription, and recompute entitlement."""
    _require_apple()
    payload = _build_verifier().verify_and_decode_signed_transaction(jws)

    token = (getattr(payload, "appAccountToken", "") or "").lower()
    if token and token != parent_email.lower():
        raise AppleBillingError("appAccountToken does not match the authenticated parent")

    otid = payload.originalTransactionId
    # prefer authoritative status from the API; fall back to payload if unavailable
    try:
        status = _fetch_status(otid)
    except Exception:
        status = _status_from_payload(payload)

    await _upsert_and_recompute(
        session, parent_email=parent_email, original_transaction_id=otid,
        status=status, expires_ms=getattr(payload, "expiresDate", None))
    await session.commit()
```

- [ ] **Step 3b: Bundle Apple root CAs**

Download the four Apple Root CA `.cer` files (Apple Root CA - G3 and intermediates) from Apple's PKI page and place them in `app/services/apple_roots/`. Add a `app/services/apple_roots/README.md` noting their provenance. (No code; required for real JWS verification. Tests patch `_build_verifier`, so they don't need them.)

- [ ] **Step 4: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_apple_billing_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt app/services/apple_billing_service.py app/services/apple_roots/ tests/services/test_apple_billing_service.py
git commit -m "feat(billing): apple_billing_service (JWS verify + status + recompute)"
```

---

## Task 6: Apple schemas + `POST /billing/apple/verify`

**Files:**
- Create: `app/schemas/apple_billing.py`
- Modify: `app/routers/billing.py`
- Test: `tests/routers/test_apple_billing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/routers/test_apple_billing.py
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_verify_requires_parent_auth(client):
    r = await client.post("/billing/apple/verify", json={"jws": "x"})
    assert r.status_code in (401, 403)


async def test_verify_calls_service(parent_client):  # parent_client = authenticated parent fixture
    with patch("app.routers.billing.apple_billing_service.verify_transaction",
               new=AsyncMock()) as mock:
        r = await parent_client.post("/billing/apple/verify", json={"jws": "signed"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    mock.assert_awaited_once()
```

> If a `parent_client` fixture does not exist, add one in `tests/conftest.py` mirroring `admin_client` but authenticating via `get_current_parent` (override the dependency to return a fixed `parent_email`). Include that fixture addition in this task.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_apple_billing.py -v`
Expected: FAIL (route missing).

- [ ] **Step 3: Implement schema + route**

`app/schemas/apple_billing.py`:

```python
from __future__ import annotations
from pydantic import BaseModel


class AppleVerifyRequest(BaseModel):
    jws: str


class AppleVerifyResponse(BaseModel):
    status: str = "ok"
```

In `app/routers/billing.py` add imports and routes:

```python
from app.routers.parent_auth import get_current_parent  # already imported
from app.schemas.apple_billing import AppleVerifyRequest, AppleVerifyResponse
from app.services import apple_billing_service


@router.post("/apple/verify", response_model=AppleVerifyResponse)
async def apple_verify(
    payload: AppleVerifyRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await apple_billing_service.verify_transaction(
            session, parent_email=parent_email, jws=payload.jws)
    except apple_billing_service.AppleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppleVerifyResponse()
```

- [ ] **Step 4: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_apple_billing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/apple_billing.py app/routers/billing.py tests/routers/test_apple_billing.py tests/conftest.py
git commit -m "feat(billing): POST /billing/apple/verify endpoint"
```

---

## Task 7: `POST /billing/apple/notifications` (App Store Server Notifications V2) + CSRF exempt

**Files:**
- Modify: `app/services/apple_billing_service.py` (add `handle_notification`)
- Modify: `app/routers/billing.py`
- Modify: `app/core/csrf.py`
- Test: `tests/routers/test_apple_notifications.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/routers/test_apple_notifications.py
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_notifications_is_csrf_exempt_and_dispatches(client):
    with patch("app.routers.billing.apple_billing_service.handle_notification",
               new=AsyncMock()) as mock:
        r = await client.post("/billing/apple/notifications",
                              json={"signedPayload": "signed-notification"})
    assert r.status_code == 200       # not 403 (CSRF) — exempt like the Stripe webhook
    mock.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_apple_notifications.py -v`
Expected: FAIL (route missing / CSRF 403).

- [ ] **Step 3: Add `handle_notification` to `apple_billing_service.py`**

```python
async def handle_notification(session: AsyncSession, signed_payload: str) -> None:
    """Verify and process an App Store Server Notification V2 payload."""
    _require_apple()
    from appstoreserverlibrary.models.Environment import Environment  # noqa: F401
    verifier = _build_verifier()
    notification = verifier.verify_and_decode_notification(signed_payload)
    data = getattr(notification, "data", None)
    if data is None or not getattr(data, "signedTransactionInfo", None):
        return
    tx = verifier.verify_and_decode_signed_transaction(data.signedTransactionInfo)
    otid = tx.originalTransactionId

    # find which household this transaction belongs to (set at verify time)
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "apple", Subscription.external_id == otid))
    if sub is None:
        return  # unknown transaction (e.g. a purchase we never saw a verify for)

    try:
        status_ = _fetch_status(otid)
    except Exception:
        status_ = _status_from_payload(tx)

    await _upsert_and_recompute(
        session, parent_email=sub.parent_email, original_transaction_id=otid,
        status=status_, expires_ms=getattr(tx, "expiresDate", None))
    await session.commit()
```

- [ ] **Step 4: Add route + CSRF exemption**

In `app/routers/billing.py`:

```python
@router.post("/apple/notifications")
async def apple_notifications(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    body = await request.json()
    signed = body.get("signedPayload")
    if not signed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signedPayload")
    try:
        await apple_billing_service.handle_notification(session, signed)
    except apple_billing_service.AppleBillingError:
        # don't 500 to Apple for config issues; ack and log upstream
        return {"status": "ignored"}
    return {"status": "ok"}
```

In `app/core/csrf.py`, add to `_DEFAULT_EXEMPT_PATHS`:

```python
    "/billing/apple/notifications",
```

- [ ] **Step 5: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_apple_notifications.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/apple_billing_service.py app/routers/billing.py app/core/csrf.py tests/routers/test_apple_notifications.py
git commit -m "feat(billing): App Store Server Notifications V2 endpoint (CSRF-exempt)"
```

---

## Task 8: Decline endpoint + exclude declined + child declined state (backend)

**Files:**
- Modify: `app/routers/parent.py`
- Modify: `app/routers/premium.py` (child-facing declined status — verify exact path; the 4B child request endpoint lives here)
- Test: `tests/routers/test_premium_request_decline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/routers/test_premium_request_decline.py
import pytest
from datetime import UTC, datetime
from sqlalchemy import select
from app.models.premium_request import PremiumRequest
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_decline_sets_declined_at_and_hides_from_list(parent_client, db_session):
    # parent_client authenticates as parent_email "parent@example.com"
    child = User(username="kid", email="kid@example.com",
                 parent_email="parent@example.com", hashed_password="x", is_active=True)
    db_session.add(child); await db_session.flush()
    pr = PremiumRequest(child_user_id=child.id, parent_email="parent@example.com",
                        context_kind="module", context_label="Investing Basics")
    db_session.add(pr); await db_session.commit()

    r = await parent_client.post(f"/parent/premium-requests/{pr.id}/decline")
    assert r.status_code == 200

    row = await db_session.scalar(select(PremiumRequest).where(PremiumRequest.id == pr.id))
    assert row.declined_at is not None

    listed = await parent_client.get("/parent/premium-requests")
    assert all(item["id"] != str(pr.id) for item in listed.json())


async def test_decline_rejects_other_parents_request(parent_client, db_session):
    child = User(username="x", email="x@example.com", parent_email="other@example.com",
                 hashed_password="x", is_active=True)
    db_session.add(child); await db_session.flush()
    pr = PremiumRequest(child_user_id=child.id, parent_email="other@example.com",
                        context_kind="module", context_label="X")
    db_session.add(pr); await db_session.commit()
    r = await parent_client.post(f"/parent/premium-requests/{pr.id}/decline")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_premium_request_decline.py -v`
Expected: FAIL (route missing).

- [ ] **Step 3: Implement**

In `app/routers/parent.py`, update the existing `list_premium_requests` query to also exclude declined:

```python
        .where(PremiumRequest.parent_email == parent_email,
               PremiumRequest.resolved_at.is_(None),
               PremiumRequest.declined_at.is_(None))
```

Add the decline route (parent-scoped, IDOR-safe):

```python
import uuid
from datetime import UTC, datetime

@router.post("/premium-requests/{request_id}/decline")
async def decline_premium_request(
    request_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(select(PremiumRequest).where(
        PremiumRequest.id == request_id,
        PremiumRequest.parent_email == parent_email))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if row.declined_at is None and row.resolved_at is None:
        row.declined_at = datetime.now(UTC)
        await session.commit()
    return {"status": "ok"}
```

For the child-facing declined state: in the child request endpoint (`app/routers/premium.py`, `POST /premium/request`), when an existing **unresolved** request for the same child is already `declined_at`, return `{"status": "declined"}` instead of re-sending — so the child UI can show the gentle state. Add to the response `Literal` union: `"declined"`. (Add a focused test asserting a second request after decline returns `declined` within the cooldown.)

- [ ] **Step 4: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_premium_request_decline.py tests/ -k premium -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/parent.py app/routers/premium.py tests/routers/test_premium_request_decline.py
git commit -m "feat(premium): parent decline endpoint + child declined state"
```

---

## Task 9: Backend full regression

- [ ] **Step 1: Lint + tests**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: ruff clean; all green (pre-existing known failures, if any, unchanged).

- [ ] **Step 2: Commit** (only if fixes were needed)

```bash
git commit -am "test(billing): backend regression green for A2"
```

---

## Task 10: Custom Capacitor StoreKit 2 plugin (iOS)

**Files:**
- Create: `frontend/ios/App/App/StoreKitPlugin.swift`
- Create: `frontend/ios/App/App/StoreKitPlugin.m`
- Create: `frontend/src/lib/storekit.ts`

- [ ] **Step 1: Swift plugin** (`StoreKitPlugin.swift`)

```swift
import Foundation
import Capacitor
import StoreKit

@objc(StoreKitPlugin)
public class StoreKitPlugin: CAPPlugin {

    @objc func getProducts(_ call: CAPPluginCall) {
        guard let ids = call.getArray("productIds", String.self) else {
            call.reject("productIds required"); return
        }
        Task {
            do {
                let products = try await Product.products(for: ids)
                let out = products.map { ["id": $0.id, "displayPrice": $0.displayPrice, "displayName": $0.displayName] }
                call.resolve(["products": out])
            } catch { call.reject("getProducts failed: \(error.localizedDescription)") }
        }
    }

    @objc func purchase(_ call: CAPPluginCall) {
        guard let productId = call.getString("productId"),
              let tokenStr = call.getString("appAccountToken"),
              let token = UUID(uuidString: tokenStr) else {
            call.reject("productId and a UUID appAccountToken are required"); return
        }
        Task {
            do {
                let products = try await Product.products(for: [productId])
                guard let product = products.first else { call.reject("Unknown product"); return }
                let result = try await product.purchase(options: [.appAccountToken(token)])
                switch result {
                case .success(let verification):
                    let jws = verification.jwsRepresentation
                    if case .verified(let transaction) = verification { await transaction.finish() }
                    call.resolve(["jws": jws])
                case .userCancelled: call.reject("cancelled", "USER_CANCELLED")
                case .pending: call.resolve(["pending": true])
                @unknown default: call.reject("unknown purchase result")
                }
            } catch { call.reject("purchase failed: \(error.localizedDescription)") }
        }
    }

    @objc func restore(_ call: CAPPluginCall) {
        Task {
            var jwsList: [String] = []
            for await result in Transaction.currentEntitlements {
                jwsList.append(result.jwsRepresentation)
            }
            call.resolve(["jws": jwsList])
        }
    }
}
```

- [ ] **Step 2: Objective-C registration** (`StoreKitPlugin.m`)

```objc
#import <Foundation/Foundation.h>
#import <Capacitor/Capacitor.h>

CAP_PLUGIN(StoreKitPlugin, "StoreKitPlugin",
  CAP_PLUGIN_METHOD(getProducts, CAPPluginReturnPromise);
  CAP_PLUGIN_METHOD(purchase, CAPPluginReturnPromise);
  CAP_PLUGIN_METHOD(restore, CAPPluginReturnPromise);
)
```

- [ ] **Step 3: TS bridge** (`frontend/src/lib/storekit.ts`)

```ts
import { registerPlugin } from '@capacitor/core';

export interface StoreKitProduct { id: string; displayPrice: string; displayName: string }
export interface StoreKitPlugin {
  getProducts(o: { productIds: string[] }): Promise<{ products: StoreKitProduct[] }>;
  purchase(o: { productId: string; appAccountToken: string }): Promise<{ jws?: string; pending?: boolean }>;
  restore(): Promise<{ jws: string[] }>;
}
export const StoreKit = registerPlugin<StoreKitPlugin>('StoreKitPlugin');
```

- [ ] **Step 4: Register in Xcode + build check**

Run: `cd frontend && npm run build && npx cap sync ios`
Expected: sync succeeds; the new Swift files compile in a subsequent Xcode build (device test happens in Task 15 / TestFlight). No automated test (native).

- [ ] **Step 5: Commit**

```bash
git add frontend/ios/App/App/StoreKitPlugin.swift frontend/ios/App/App/StoreKitPlugin.m frontend/src/lib/storekit.ts
git commit -m "feat(ios): custom StoreKit 2 Capacitor plugin (getProducts/purchase/restore)"
```

---

## Task 11: Frontend billing + premium API client additions

**Files:**
- Modify: `frontend/src/api/billing.ts`
- Modify: `frontend/src/api/premium.ts`
- Test: `frontend/src/api/__tests__/billing.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/api/__tests__/billing.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { billingApi } from '../billing';

describe('billingApi apple', () => {
  beforeEach(() => vi.restoreAllMocks());
  it('POSTs the jws to /billing/apple/verify', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ status: 'ok' } as never);
    await billingApi.appleVerify('signed-jws');
    expect(spy).toHaveBeenCalledWith('/billing/apple/verify',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ jws: 'signed-jws' }) }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/__tests__/billing.test.ts`
Expected: FAIL (`appleVerify` missing).

- [ ] **Step 3: Implement**

Add to `frontend/src/api/billing.ts` (within the existing `billingApi` object):

```ts
  appleVerify: (jws: string) =>
    apiFetch<{ status: string }>('/billing/apple/verify',
      { method: 'POST', body: JSON.stringify({ jws }) }),
```

Add to `frontend/src/api/premium.ts` (within `premiumApi`):

```ts
  declineRequest: (id: string) =>
    apiFetch<{ status: string }>(`/parent/premium-requests/${id}/decline`, { method: 'POST' }),
```

- [ ] **Step 4: Run test**

Run: `cd frontend && npx vitest run src/api/__tests__/billing.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/billing.ts frontend/src/api/premium.ts frontend/src/api/__tests__/billing.test.ts
git commit -m "feat(fe): apple verify + decline-request API clients"
```

---

## Task 12: Channel-aware `SubscriptionCard` (web Stripe vs native StoreKit)

**Files:**
- Modify: `frontend/src/components/SubscriptionCard.tsx`
- Test: `frontend/src/components/__tests__/SubscriptionCard.native.test.tsx`

- [ ] **Step 1: Write the failing test** (mock the plugin + platform)

```tsx
// frontend/src/components/__tests__/SubscriptionCard.native.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('@/lib/platform', () => ({ isNativeApp: () => true }));
vi.mock('@/lib/storekit', () => ({
  StoreKit: {
    getProducts: vi.fn().mockResolvedValue({ products: [{ id: 'premium_monthly', displayPrice: '£4.99', displayName: 'Premium' }] }),
    purchase: vi.fn().mockResolvedValue({ jws: 'signed-jws' }),
    restore: vi.fn().mockResolvedValue({ jws: [] }),
  },
}));
const appleVerify = vi.fn().mockResolvedValue({ status: 'ok' });
vi.mock('@/api/billing', () => ({ billingApi: { appleVerify: (...a: unknown[]) => appleVerify(...a),
  status: vi.fn().mockResolvedValue({ has_subscription: false }) } }));

import SubscriptionCard from '../SubscriptionCard';
import { renderWithProviders } from '@/test/utils'; // existing helper if present; else wrap QueryClientProvider

describe('SubscriptionCard (native)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows native Subscribe + Restore (no Stripe checkout) and verifies purchase', async () => {
    renderWithProviders(<SubscriptionCard householdToken="11111111-1111-1111-1111-111111111111" />);
    const subscribe = await screen.findByRole('button', { name: /subscribe/i });
    expect(screen.getByRole('button', { name: /restore/i })).toBeInTheDocument();
    fireEvent.click(subscribe);
    await waitFor(() => expect(appleVerify).toHaveBeenCalledWith('signed-jws'));
  });

  it('has no axe violations', async () => {
    const { container } = renderWithProviders(<SubscriptionCard householdToken="11111111-1111-1111-1111-111111111111" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

> If `renderWithProviders`/`@/test/utils` doesn't exist, use the project's existing test render pattern (wrap in `QueryClientProvider`). Match what other component tests in `src/components/__tests__/` already do.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/__tests__/SubscriptionCard.native.test.tsx`
Expected: FAIL (native branch not implemented).

- [ ] **Step 3: Implement the native branch**

In `SubscriptionCard.tsx`: detect platform via `isNativeApp()` from `@/lib/platform`. On web, keep the existing Stripe checkout button/flow unchanged. On native, render:
- a **Subscribe** button → `StoreKit.getProducts({ productIds: ['premium_monthly'] })` then on click `StoreKit.purchase({ productId, appAccountToken: householdToken })` → if `jws`, `billingApi.appleVerify(jws)` → invalidate the `['billing','status']` query.
- a **Restore Purchases** button → `StoreKit.restore()` → for each returned `jws`, `billingApi.appleVerify(jws)` → invalidate status.
- a **Manage subscription** link → on native, open `itms-apps://apps.apple.com/account/subscriptions` (Apple manage-subscriptions). On web keep the Stripe portal.

Add a `householdToken: string` prop (the parent's household id used as `appAccountToken`); the parent dashboard passes it (derive from the authenticated parent — a stable per-household UUID; if one doesn't exist yet, add a `household_token` to the parent identity or deterministically derive a UUIDv5 from `parent_email` — choose UUIDv5 from `parent_email` to avoid schema change, documented inline). **Never** show price/checkout in the child experience (this card is parent-only — unchanged from today).

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run src/components/__tests__/SubscriptionCard.native.test.tsx`
Expected: PASS (incl. axe).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SubscriptionCard.tsx frontend/src/components/__tests__/SubscriptionCard.native.test.tsx
git commit -m "feat(fe): channel-aware SubscriptionCard (native StoreKit purchase/restore)"
```

---

## Task 13: Approve/Decline on `PremiumRequestsCard`

**Files:**
- Modify: `frontend/src/components/parent/PremiumRequestsCard.tsx`
- Test: `frontend/src/components/parent/__tests__/PremiumRequestsCard.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// add cases to the existing/new test file
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const decline = vi.fn().mockResolvedValue({ status: 'ok' });
const parentRequests = vi.fn().mockResolvedValue([
  { id: 'req-1', child_username: 'Yasmin', context_kind: 'module', context_label: 'Investing Basics', created_at: new Date().toISOString() },
]);
vi.mock('@/api/premium', () => ({ premiumApi: {
  parentRequests: () => parentRequests(), declineRequest: (id: string) => decline(id) } }));

import PremiumRequestsCard from '../PremiumRequestsCard';
import { renderWithProviders } from '@/test/utils';

describe('PremiumRequestsCard approve/decline', () => {
  beforeEach(() => vi.clearAllMocks());
  it('declines a request', async () => {
    renderWithProviders(<PremiumRequestsCard onApprove={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /decline/i }));
    await waitFor(() => expect(decline).toHaveBeenCalledWith('req-1'));
  });
  it('approve calls the onApprove handler (routes to subscribe)', async () => {
    const onApprove = vi.fn();
    renderWithProviders(<PremiumRequestsCard onApprove={onApprove} />);
    fireEvent.click(await screen.findByRole('button', { name: /approve/i }));
    expect(onApprove).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/parent/__tests__/PremiumRequestsCard.test.tsx`
Expected: FAIL (buttons/props missing).

- [ ] **Step 3: Implement**

Add per-request **Approve** and **Decline** buttons. **Decline** → `premiumApi.declineRequest(id)` then invalidate `['premium','parentRequests']`. **Approve** → call an `onApprove()` prop the parent dashboard wires to scroll/route to `SubscriptionCard` (the purchase surface). Keep buttons keyboard-accessible with clear labels ("Approve — go to subscribe", "Decline").

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run src/components/parent/__tests__/PremiumRequestsCard.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/parent/PremiumRequestsCard.tsx frontend/src/components/parent/__tests__/PremiumRequestsCard.test.tsx
git commit -m "feat(fe): approve/decline actions on premium requests"
```

---

## Task 14: Gentle child "declined" state in the paywall

**Files:**
- Modify: `frontend/src/components/child/PremiumPaywall.tsx`
- Test: `frontend/src/components/child/__tests__/PremiumPaywall.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// add a case to PremiumPaywall's test
it('shows a gentle declined state when the request status is declined', async () => {
  // mock premiumApi.requestUnlock to resolve { status: 'declined' }
  // trigger the "Ask my grown-up" action, then assert the soft copy renders
  expect(await screen.findByText(/sort it out later/i)).toBeInTheDocument();
  // no price, no purchase button present
  expect(screen.queryByRole('button', { name: /subscribe|buy|pay/i })).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/child/__tests__/PremiumPaywall.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

In `PremiumPaywall.tsx`, when `requestUnlock` returns `{ status: 'declined' }`, render the gentle confirmation state: copy like **"Your grown-up will sort it out later 💛"** (single source in `src/lib/premiumConfig.ts`). No price, no purchase button (4B/Apple-kids compliance preserved). Reuse the existing confirmation-state pattern already in the sheet.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run src/components/child/__tests__/PremiumPaywall.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/PremiumPaywall.tsx frontend/src/lib/premiumConfig.ts frontend/src/components/child/__tests__/PremiumPaywall.test.tsx
git commit -m "feat(fe): gentle child declined state in paywall"
```

---

## Task 15: Frontend regression + iOS sync + close-out

- [ ] **Step 1: Typecheck, lint, test, build**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green.

- [ ] **Step 2: iOS sync**

Run: `cd frontend && npx cap sync ios`
Expected: success; StoreKit plugin present. (Device/TestFlight sandbox purchase is a manual verification step — note it in the close-out, not automated.)

- [ ] **Step 3: Update docs**

Mark A2 in `docs/superpowers/PROGRESS.md` (or the backlog doc) as implemented; note the user-side App Store Connect setup (product `premium_monthly` + 7-day intro offer + Apple API key envs) and that the prod migration is gated/backup-first.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: mark 4A·A2 cross-store payments implemented"
```

---

## Self-Review (completed)

- **Spec coverage:** §1 entitlement core → Tasks 1–3; §2 iOS client → Tasks 10, 12; §3 backend Apple verify/notifications + Stripe refactor → Tasks 3, 5, 6, 7; §4 approve/decline → Tasks 8, 13, 14; §5 compliance/testing → embedded per task + Task 9/15; 7-day trial → web already done (noted), Apple via App Store Connect (Task 15 docs).
- **Type consistency:** `recompute_household_premium(session, parent_email)`, `AppleBillingError`, `verify_transaction(session, *, parent_email, jws)`, `handle_notification(session, signed_payload)`, `StoreKit.purchase({productId, appAccountToken})`, `billingApi.appleVerify(jws)`, `premiumApi.declineRequest(id)`, `provider`/`external_id`/`declined_at` — consistent across tasks.
- **Known follow-ups flagged inline:** confirm/drop any legacy unique constraints in the migration (Task 1 note); `parent_client` fixture may need adding (Task 6 note); `householdToken` via UUIDv5 of `parent_email` (Task 12) to avoid a schema change.
