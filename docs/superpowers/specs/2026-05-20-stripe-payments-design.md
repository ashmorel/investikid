# Sub-project 7: Stripe Payments Integration

**Status:** Approved — 2026-05-20
**Depends on:** Sub-projects 1–6 (all DONE)

## Goal

Let parents pay for Premium via Stripe Checkout subscriptions. One family plan covers all children under a parent account. Stripe hosts all payment UI — no card data touches our servers.

## Audience & Constraints

- Parents are the only payers. Children never see purchase buttons or Stripe UI (COPPA/AADC compliant).
- The existing `is_premium` boolean on the `User` model stays. The entitlements service (`is_premium()` / `set_premium()`) is the sole read/write seam — webhook handlers call `set_premium()` to grant or revoke.
- App must boot without Stripe keys configured (dev/test). Billing endpoints return 503 when keys are missing.
- No offline/cached payment state — subscription status is always fetched live.
- WCAG 2.2 AA conformance from sub-project 5 preserved on all new UI.
- Mobile-first responsive design from sub-project 6 applies to all new components.

---

## 1. Subscription Model

### 1.1 Pricing

- **Family plan:** one monthly subscription per parent covers all children under that `parent_email`.
- **7-day free trial:** Stripe-native `trial_period_days: 7` on the first subscription.
- **Cancellation grace:** when a parent cancels, premium stays active until `current_period_end`. Children are downgraded only when the period expires.

### 1.2 Data Model

New table `subscriptions`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | Server-generated |
| `parent_email` | VARCHAR NOT NULL | Matches `User.parent_email` — not an FK (parent has no User row) |
| `stripe_customer_id` | VARCHAR UNIQUE NOT NULL | Stripe Customer object ID (`cus_...`) |
| `stripe_subscription_id` | VARCHAR UNIQUE NULL | NULL before first checkout completes |
| `status` | VARCHAR NOT NULL | One of: `trialing`, `active`, `past_due`, `canceled`, `unpaid` |
| `current_period_end` | TIMESTAMP NULL | When current billing period expires |
| `cancel_at_period_end` | BOOLEAN NOT NULL DEFAULT FALSE | True if parent cancelled but period hasn't ended |
| `created_at` | TIMESTAMP NOT NULL | |
| `updated_at` | TIMESTAMP NOT NULL | |

No changes to the `User` model. The `is_premium` column continues to be the source of truth for feature gating. The `Subscription` table tracks billing state; webhook handlers bridge the two via `set_premium()`.

---

## 2. Backend Architecture

### 2.1 New Files

| File | Responsibility |
|------|---------------|
| `models/subscription.py` | SQLAlchemy `Subscription` model |
| `schemas/billing.py` | Pydantic request/response schemas for billing endpoints |
| `services/billing_service.py` | Stripe API calls: create customer, create checkout session, create portal session |
| `services/webhook_service.py` | Webhook event dispatch — maps Stripe events to entitlement changes |
| `routers/billing.py` | HTTP endpoints for checkout, portal, webhook, status |
| `alembic/versions/xxxx_add_subscriptions.py` | Migration for the `subscriptions` table |

### 2.2 Configuration

New fields in `Settings` (all optional — app boots without them):

```python
stripe_secret_key: str = ""
stripe_webhook_secret: str = ""
stripe_price_id: str = ""
stripe_portal_config_id: str = ""  # omit to use Stripe defaults
frontend_url: str = "http://localhost:5173"
```

Billing endpoints check `stripe_secret_key` at request time and return 503 if empty.

### 2.3 Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/billing/checkout` | Parent session cookie | Creates Stripe Checkout Session, returns `{ url }` |
| `POST` | `/billing/portal` | Parent session cookie | Creates Stripe Customer Portal session, returns `{ url }` |
| `GET` | `/billing/status` | Parent session cookie | Returns subscription status for display |
| `POST` | `/billing/webhook` | Stripe signature (no cookie) | Receives Stripe webhook events |

**`POST /billing/checkout`**

1. Look up existing `Subscription` row by `parent_email`.
2. If no Stripe customer exists, call `stripe.Customer.create(email=parent_email, metadata={"parent_email": parent_email})`.
3. Upsert `Subscription` row with `stripe_customer_id`.
4. Call `stripe.checkout.Session.create()` with:
   - `mode="subscription"`
   - `customer=stripe_customer_id`
   - `line_items=[{"price": stripe_price_id, "quantity": 1}]`
   - `subscription_data={"trial_period_days": 7}` (only if no prior subscription)
   - `success_url="{frontend_url}/parent?checkout=success"`
   - `cancel_url="{frontend_url}/parent?checkout=canceled"`
   - `metadata={"parent_email": parent_email}`
5. Return `{ "url": session.url }`.

**`POST /billing/portal`**

1. Look up `Subscription` row by `parent_email`.
2. If no subscription exists, return 404.
3. Call `stripe.billing_portal.Session.create(customer=stripe_customer_id, return_url="{frontend_url}/parent")`.
4. Return `{ "url": session.url }`.

**`GET /billing/status`**

Returns:
```json
{
  "has_subscription": true,
  "status": "trialing",
  "trial_ends_at": "2026-05-27T00:00:00Z",
  "current_period_end": "2026-06-20T00:00:00Z",
  "cancel_at_period_end": false
}
```

Or when no subscription:
```json
{
  "has_subscription": false,
  "status": null,
  "trial_ends_at": null,
  "current_period_end": null,
  "cancel_at_period_end": false
}
```

**`POST /billing/webhook`**

1. Read raw body bytes.
2. Verify signature via `stripe.Webhook.construct_event(payload, sig_header, webhook_secret)`.
3. Reject with 400 if signature invalid.
4. Dispatch based on `event.type` to `webhook_service`.
5. Return 200 immediately (Stripe retries on non-2xx).

### 2.4 Webhook Event Handling

All handlers are idempotent — duplicate events are no-ops when the `Subscription` row already reflects the event's state.

**`checkout.session.completed`:**
1. Extract `customer`, `subscription`, and `metadata.parent_email` from the event.
2. Upsert `Subscription` row with `stripe_customer_id`, `stripe_subscription_id`, `status` from the subscription object.
3. Retrieve the subscription from Stripe to get `current_period_end` and `trial_end`.
4. Query all `User` rows where `parent_email` matches.
5. Call `set_premium(child, value=True, actor="stripe")` for each child.
6. Commit.

**`customer.subscription.updated`:**
1. Extract subscription ID, `status`, `current_period_end`, `cancel_at_period_end`.
2. Update the `Subscription` row.
3. If `status` changed to `active` from `trialing`, no entitlement change needed (already premium).
4. If `status` is `past_due`, children stay premium (Stripe is retrying payment).
5. Commit.

**`customer.subscription.deleted`:**
1. Update `Subscription` row: `status=canceled`.
2. Query all `User` rows where `parent_email` matches.
3. Call `set_premium(child, value=False, actor="stripe")` for each child.
4. Commit.

**`invoice.payment_failed`:**
1. Look up `Subscription` by the invoice's `subscription` field.
2. Update status to `past_due`.
3. Children stay premium — Stripe retries payment per its configured retry schedule.
4. If all retries exhaust, Stripe sends `customer.subscription.deleted` and children are downgraded then.
5. Commit.

---

## 3. Frontend Changes

### 3.1 New Files

| File | Responsibility |
|------|---------------|
| `src/api/billing.ts` | API client: `createCheckout()`, `createPortal()`, `getSubscriptionStatus()` |
| `src/components/SubscriptionCard.tsx` | Subscription status + action button for Parent Dashboard |
| `tests/unit/SubscriptionCard.test.tsx` | Unit tests for the card's states |

### 3.2 SubscriptionCard Component

Displayed at the top of the Parent Dashboard, above the children list.

**States:**

| Subscription state | Display | Action button |
|-------------------|---------|--------------|
| No subscription | "Free plan — upgrade for AI coach, advanced scenarios, and more" | "Subscribe to Premium" → redirect to Stripe Checkout |
| `trialing` | "Premium trial — N days remaining" | "Manage Billing" → redirect to Stripe Portal |
| `active` | "Premium — renews [date]" | "Manage Billing" |
| `active` + `cancel_at_period_end` | "Premium — cancels [date]" | "Manage Billing" (can resubscribe in portal) |
| `past_due` | "Premium — payment issue, retrying" | "Manage Billing" (update card) |
| `canceled` | Same as no subscription | "Subscribe to Premium" |

Card styling: consistent with the existing amber/orange design system. Responsive via sub-project 6 patterns (`px-4 py-4 sm:px-6 sm:py-6`).

After Stripe Checkout redirects back with `?checkout=success`, show a toast: "Welcome to Premium! All your children now have access to premium features."

### 3.3 ChildCard Changes

- Remove the "Upgrade to Premium" / "Downgrade" toggle button.
- Remove the "Billing isn't set up yet" placeholder text.
- Keep the "Premium ✨" badge — now driven by the subscription via `is_premium`.

### 3.4 ParentDashboard Changes

- Remove the manual `PATCH /parent/children/:id/premium` toggle from the parent router (or keep it behind an admin flag for testing — decision: remove it; the seed script can set premium for test accounts).
- Add `SubscriptionCard` above children list.
- Handle `?checkout=success` and `?checkout=canceled` query params for post-redirect feedback.

### 3.5 Child-Facing Premium Gates

Existing premium gates (from sub-project 4) already show lock icons on gated features. Add a line of text below the lock: "Ask your parent to upgrade to Premium!" — no buttons, no links to Stripe, no purchase pressure.

---

## 4. Checkout & Webhook Flow

### 4.1 New Subscriber (Happy Path)

```
Parent clicks "Subscribe to Premium"
  → Frontend: POST /billing/checkout
  → Backend: create Stripe Customer (if new), create Checkout Session
  → Frontend: window.location.href = checkout_url
  → Parent completes payment on Stripe Checkout
  → Stripe redirects to /parent?checkout=success
  → Webhook: checkout.session.completed
      → Upsert Subscription (status=trialing)
      → set_premium(child, value=True) for all children
  → Parent sees success toast + SubscriptionCard shows trial status
```

### 4.2 Cancellation

```
Parent clicks "Manage Billing" → Stripe Portal
  → Parent cancels subscription
  → Webhook: customer.subscription.updated (cancel_at_period_end=true)
      → Update Subscription row
      → Children stay premium
  → At period end:
  → Webhook: customer.subscription.deleted
      → Update Subscription (status=canceled)
      → set_premium(child, value=False) for all children
```

### 4.3 Payment Failure

```
Stripe invoice fails
  → Webhook: invoice.payment_failed
      → Subscription status → past_due
      → Children stay premium (Stripe retries)
  → If all retries fail:
  → Webhook: customer.subscription.deleted
      → Downgrade all children
```

### 4.4 Idempotency

Webhook handlers use `stripe_subscription_id` as the key. If the `Subscription` row already reflects the event's state (same status, same `cancel_at_period_end`, same `current_period_end`), the handler commits without changes. Stripe sends duplicate events — this is expected and safe.

---

## 5. Testing

### 5.1 Stripe Mocking Strategy

Mock at the service boundary: `stripe.checkout.Session.create`, `stripe.billing_portal.Session.create`, `stripe.Customer.create`, `stripe.Webhook.construct_event`, `stripe.Subscription.retrieve`. No real Stripe API calls in CI.

### 5.2 Backend Tests

| Test | Assertion |
|------|-----------|
| `test_checkout_creates_session` | Returns 200 with `url`, creates Stripe Customer, upserts Subscription |
| `test_checkout_reuses_customer` | Second call reuses existing `stripe_customer_id` |
| `test_checkout_requires_parent_auth` | 401 without parent session cookie |
| `test_checkout_503_without_stripe_key` | 503 when `stripe_secret_key` is empty |
| `test_portal_returns_url` | Returns 200 with portal URL for existing subscriber |
| `test_portal_404_no_subscription` | 404 when parent has no subscription |
| `test_status_no_subscription` | Returns `has_subscription: false` |
| `test_status_active` | Returns correct status shape |
| `test_webhook_checkout_completed` | Upserts Subscription, flips all children to premium |
| `test_webhook_subscription_updated_cancel` | Sets `cancel_at_period_end=true`, children stay premium |
| `test_webhook_subscription_deleted` | Status=canceled, all children downgraded |
| `test_webhook_payment_failed` | Status=past_due, children stay premium |
| `test_webhook_bad_signature` | 400 on invalid signature |
| `test_webhook_idempotent` | Duplicate event is a no-op |

### 5.3 Frontend Tests

| Test | Assertion |
|------|-----------|
| `test_subscription_card_free` | Shows "Subscribe" button when no subscription |
| `test_subscription_card_active` | Shows status text + "Manage Billing" button |
| `test_subscription_card_trialing` | Shows trial days remaining |
| `test_subscription_card_canceled` | Shows "Subscribe" button (re-subscribe) |
| `test_child_card_no_toggle` | Premium toggle button is removed |

### 5.4 No Playwright E2E for Stripe

Checkout and Portal are Stripe-hosted pages outside our control. E2e coverage stops at "redirect URL is correct."

---

## 6. Dependencies

### Backend
- `stripe` (pip) — Stripe Python SDK. Only new dependency.

### Frontend
- None. No `@stripe/stripe-js` needed — we redirect to Stripe-hosted pages.

---

## 7. Stripe Dashboard Setup (Manual)

Documented here for the operator — not automated in code:

1. Create Product: "Invest-Ed Premium Family Plan"
2. Create Price: monthly recurring (e.g. $9.99/month)
3. Configure Customer Portal: allow cancellation, hide plan switching
4. Create Webhook endpoint: `{backend_url}/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
5. Copy signing secret to `STRIPE_WEBHOOK_SECRET` env var
6. Copy price ID to `STRIPE_PRICE_ID` env var

---

## Out of Scope

- Annual billing / plan switching (single monthly plan only)
- Coupons / promotional pricing
- Invoice PDF display in-app (Stripe emails receipts)
- Multiple payment methods per customer
- Refund automation (handle manually in Stripe Dashboard)
- Child-initiated upgrade requests / notifications
- Metered billing / usage-based pricing
