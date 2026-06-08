# Cross-Store Payments + Live iOS IAP (Item 4A · Sub-project A2) — Design Spec

**Date:** 2026-06-07
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** premium content & pricing → **4A (multi-channel payments)**, sub-project **A2**
**Sequence within 4A:** **A2 (this — payment core + live iOS IAP)** → A1 (Android app foundation) → A3 (Android Play Billing)
**Builds on:** 4D (simulator) ✅, 4B (free/premium clarity + paywall + child→parent request) ✅, and the existing **web Stripe billing** ✅.

## Goal

Let parents pay for premium on **iOS** (Apple In-App Purchase) in addition to the existing **web Stripe** path, behind a single **source-agnostic entitlement core**, and bridge 4B's child→parent request into an explicit **approve/decline** loop. Ships a **7-day free trial** on both channels. Android is explicitly **out of scope** here (A1 + A3).

## Decisions (from brainstorming)

1. **Channels now:** iOS IAP + keep web Stripe. (Android app + Play Billing are separate sub-projects A1/A3.)
2. **Integration approach:** **native, self-validated** — StoreKit 2 on device + server-side validation via Apple's App Store Server API and App Store Server Notifications V2. No third-party (e.g. RevenueCat).
3. **Entitlement model:** **household-level**, keyed by `parent_email`. Premium = **OR** across all the household's active subscriptions (any channel). Overlap is informed ("already subscribed"), not hard-blocked.
4. **Purchase placement:** behind **parent authentication** (parental gate); the StoreKit purchase carries `appAccountToken = household id` so entitlement is granted **server-side**, device-independent. Child experience stays purchase-free (4B/Apple-kids compliant).
5. **Request → approve/decline:** extend 4B's `PremiumRequest` with approve (routes parent into purchase) / decline (records `declined_at`, gentle child-facing state).
6. **Free trial:** 7-day, on web (Stripe `trial_period_days`) and iOS (App Store Connect intro offer); trial counts as an **active/entitled** status.

## Current state (what exists)

- Entitlement seam `app/services/entitlements.py`: `is_premium(user)` reads the per-child `users.is_premium` boolean; `set_premium(session, child, *, value, actor)` flips it idempotently + writes an `AuditLog` row. **Callers never read `user.is_premium` directly.**
- `app/models/subscription.py`: a **Stripe-only** `Subscription` (`parent_email`, `stripe_customer_id`, `stripe_subscription_id`, `status`, `current_period_end`, `cancel_at_period_end`).
- `app/services/billing_service.py` (Stripe API wrapper) + `app/services/webhook_service.py` (`handle_checkout_completed` sets premium on the parent's children) + `app/routers/billing.py` (checkout + Stripe webhook, CSRF-exempt).
- Frontend `SubscriptionCard` (web Stripe; suppressed on native today). 4B `PremiumPaywall` + `usePremiumPaywall` + `PremiumRequestsCard` + `GET /parent/premium-requests` + `POST /premium/request`.

---

## Section 1 — Architecture & source-agnostic entitlement core

**Generalise the `subscriptions` table** to be provider-agnostic:
- Add `provider` (`stripe` | `apple` | `google`).
- Keep `parent_email` (household key), `status`, `current_period_end`, `cancel_at_period_end`.
- Add a generic `external_id` (Stripe subscription id / Apple `originalTransactionId` / Google `purchaseToken`), unique per `(provider, external_id)`.
- Keep `stripe_customer_id` (Stripe-only, nullable) for the portal; other Stripe-specific columns stay nullable.
- **Migration:** existing rows become `provider='stripe'`, `external_id = stripe_subscription_id`. One hand-written chained Alembic migration (check `alembic heads` first).
- A household may have **multiple** rows (e.g. lapsed Stripe + active Apple).

**The recompute seam — the heart of the design.** A single pure-ish function:
```
async def recompute_household_premium(session, parent_email) -> None
```
1. Load all `subscriptions` rows for `parent_email`.
2. `entitled = any(row.status in ACTIVE_STATUSES)` where `ACTIVE_STATUSES = {active, trialing, in_grace_period}`.
3. For each child of that parent (`users.parent_email == parent_email`), call existing `set_premium(child, value=entitled, actor="billing:recompute")` (idempotent + audited).

**Every channel calls `recompute_household_premium` after writing its row** — the Stripe webhook (refactored), the Apple verify + notifications paths, and later Google. `is_premium()` and all its callers are **unchanged**; only the upstream feeders change. Adding a channel = "upsert a row, call recompute."

---

## Section 2 — iOS client purchase flow

- **Placement:** a parent-authenticated "Manage subscription" surface in the app (parent logs in on-device via existing magic-link / Apple / Google). Child UI shows no price/buy button (4B intact). This is the parental gate.
- **`SubscriptionCard` becomes channel-aware:**
  - **Web** → existing Stripe checkout (unchanged, now with trial).
  - **iOS native** → native **Subscribe** button (StoreKit) + Apple-mandated **Restore Purchases** + **Manage subscription** (deep-links to Apple's manage-subscriptions).
- **Custom Capacitor StoreKit 2 plugin** (thin Swift wrapper, ~1 file) exposing: `getProducts()`, `purchase(productId, appAccountToken)`, `restore()`. Returns the **signed transaction (JWS)** to JS. *(StoreKit 2 + JWS server validation is the deciding factor over general community plugins; this plugin is the main implementation risk — device-only testing.)*
- **Flow:** parent taps Subscribe → plugin `purchase(productId, appAccountToken = household id)` → Apple's native sheet → plugin returns JWS → frontend `POST /billing/apple/verify` → backend validates + records + recomputes → UI shows "Premium active" (or "Trial — N days left"). **Restore** returns current entitlements → same verify endpoint.
- **Product:** single auto-renewing monthly subscription, parity with the web tier, **with a 7-day introductory free trial** (configured in App Store Connect). Pricing set in App Store Connect.

---

## Section 3 — Backend (Apple validation + notifications + Stripe refactor)

Generalised billing router (extend `app/routers/billing.py` or split provider routers; keep the router thin).

- **`POST /billing/apple/verify`** (parent-authenticated): receives the JWS signed transaction. Verifies it against Apple's public keys, calls the **App Store Server API** for authoritative status, upserts a `subscriptions` row (`provider='apple'`, `external_id = originalTransactionId`, `parent_email` = authenticated parent, `status`, `current_period_end`), then `recompute_household_premium`. Returns fresh entitlement.
- **`POST /billing/apple/notifications`** (no auth, **CSRF-exempt**): App Store Server Notifications V2. Verifies the signed payload; maps the notification type (`DID_RENEW`, `EXPIRED`, `DID_CHANGE_RENEWAL_STATUS`, `GRACE_PERIOD_EXPIRED`, `REFUND`, etc.) to a status update on the matching row; recomputes. Keeps premium correct over time without the app open.
- **`apple_billing_service`** (mirrors the Stripe `billing_service`/`webhook_service` split): owns JWS verification + App Store Server API calls. Apple credentials (issuer id, key id, `.p8`, bundle id, shared secret) are **env vars the user sets** — not handled by the assistant.
- **Stripe refactor:** the Stripe webhook stops flipping the boolean directly; it writes/updates its `subscriptions` row and calls `recompute_household_premium`. Stripe checkout adds **`trial_period_days = 7`**.
- **Idempotency & ordering:** verify + notifications are idempotent (keyed on `(provider, external_id)` + transaction id); status is always re-derived from the latest known state, never blind-toggled, so out-of-order notifications converge.

---

## Section 4 — Request → approve/decline bridge (extends 4B)

- **Data:** add `declined_at: datetime | None` to 4B's `PremiumRequest` (already has `resolved_at` for grants). States: **pending** (neither), **declined** (`declined_at`), **resolved/granted** (`resolved_at`).
- **Parent UI** (`PremiumRequestsCard`), per pending request:
  - **Approve** → routes the parent into the Subscribe surface (Stripe checkout on web / StoreKit Subscribe on iOS). It does **not** grant premium itself; when payment completes and recompute flips premium, open requests **auto-resolve** (4B already does this on grant). No privileged grant-without-pay path.
  - **Decline** → `POST /parent/premium-requests/{id}/decline` sets `declined_at` (parent-scoped, IDOR-safe, mirrors `list_children`).
- **Child UI (gentle, COPPA-safe):** a child whose request was declined sees a soft "Your grown-up will sort it out later 💛" state at that paywall instead of re-nagging, surfaced via the child's existing request status. No new PII, no price, no purchase UI. After the existing cooldown a child may ask again.

---

## Section 5 — Compliance, edge cases, testing

**Compliance (Apple kids' category — critical):**
- Purchase UI only behind parent auth (parental gate); child app never shows price/buy (4B intact). **Restore Purchases** included.
- iOS app uses **IAP only** — no mention of or link to web/Stripe pricing inside the app (anti-steering, Guideline 3.1.1). Web keeps Stripe; the two never cross-reference.
- `appAccountToken` is an opaque household UUID — **no child PII** to Apple.

**Edge cases:**
- **Multiple active channels:** entitlement OR keeps them premium; pre-purchase UI shows current status ("already subscribed via …"). Cross-store double-purchase can't be hard-blocked reliably → inform, don't fail.
- **Refund (`REFUND`), expiry, billing-retry/grace:** notifications update the row; grace = entitled; expiry/refund → recompute revokes only if no other channel active.
- **Trial:** `trialing` is an active status; conversion/expiry handled by renewal/expiry notifications (Apple) and webhooks (Stripe).
- **Cancel / manage:** deep-link to Apple manage-subscriptions (iOS) / Stripe portal (web).
- **Restore on fresh install:** association uses the authenticated parent session at verify time.

**Testing:**
- *Backend* (async, `loop_scope="session"` + `client`/`admin_client`/`db_session` fixtures): JWS verification (mocked Apple verifier + sandbox payloads); `/apple/verify` upsert + recompute; notifications V2 (renew/cancel/refund/expire/grace/trial-convert); Stripe refactor still grants; `recompute_household_premium` OR-logic across providers; trial = entitled; decline endpoint (parent-scoped); idempotency/out-of-order.
- *Frontend* (Vitest + `vitest-axe`): channel-aware `SubscriptionCard` (web vs native, incl. Restore/Manage); purchase flow with a **mocked** StoreKit plugin; approve/decline UI + child "declined" state.
- *Device:* StoreKit **sandbox** testing via TestFlight (manual — the custom plugin needs real-device verification).

**Out of scope for A2:** Android app (A1) + Play Billing (A3); annual tier; promo/offer codes beyond the single 7-day trial; family-plan special-casing.

**Promotion:** ships a DB migration (generalise `subscriptions` + add `PremiumRequest.declined_at`) → testing → staging → production, **backup-first** per the standing rule in `docs/deployment-environments.md`. **User-side setup:** App Store Connect product + 7-day intro offer + Apple API credentials (issuer/key id/`.p8`/bundle id/shared secret) as Railway env vars; Stripe trial needs no new secret.

**Main risks:** the custom StoreKit 2 Capacitor plugin (device-only testing) and App Store Connect product/credential setup (user-side).
