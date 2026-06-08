# Google Play Billing (Item 4A · Sub-project A3) — Design Spec

**Date:** 2026-06-07
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** premium content & pricing → **4A (multi-channel payments)**, sub-project **A3**
**Sequence within 4A:** A2 (payments + iOS) ✅ → A1 (Android foundation) ✅ → **A3 (this — Google Play Billing)**
**Builds on:** A2 (provider-agnostic `subscriptions`, `recompute_household_premium`, `household_token` UUIDv5, channel-aware `SubscriptionCard`, 7-day trial, product-allowlist guard) and A1 (committed Capacitor Android app + manifest + plugins).

## Goal

Add Android in-app **subscription** purchases via **Google Play Billing**, validated **server-side** (native self-validated — consistent with A2's Apple approach, **not** RevenueCat), feeding the existing source-agnostic entitlement core. A Google *feeder* only: no entitlement-core, iOS, or Stripe changes.

## Decisions (from brainstorming)

1. **Android purchase client:** a **custom Kotlin Capacitor plugin** wrapping Google Play Billing Library 7 (mirrors the A2 StoreKit plugin) — not a community lib, not RevenueCat.
2. **Validation:** server-side via the **Google Play Developer API** (service-account auth); **RTDN** (Pub/Sub) keeps state fresh; always re-fetch authoritative state from the API rather than trusting a push.
3. **Household binding:** Play `obfuscatedAccountId` = `household_token(parent_email)` (the A2 UUIDv5), verified server-side — same model as Apple's `appAccountToken`.
4. **Acknowledgement:** server acknowledges the purchase after validation (Play auto-refunds unacknowledged purchases within 3 days); idempotent.
5. **Trial:** 7-day Play **free-trial offer** on the base plan; `trialing` maps to an active status in the seam.
6. **No DB migration** — the `provider` column already exists.

## Section 1 — Backend

**`app/services/google_billing_service.py`** (mirrors `apple_billing_service.py`):
- `class GoogleBillingError(Exception)`.
- `_require_google()` — raises if `google_play_package_name` / `google_play_service_account_json` unset.
- `_play_client()` — builds the Android Publisher client from the service-account JSON via `google-api-python-client` + `google-auth` (lazy import; patched in tests).
- `_fetch_subscription(purchase_token)` — `purchases.subscriptionsv2.get(packageName, token)`; returns the raw state (patched in tests).
- `_map_status(state)` — Google states → `active | trialing | in_grace_period | past_due | expired`.
- `_acknowledge(purchase_token)` — `purchases.subscriptions.acknowledge` if not already acknowledged; idempotent.
- `_upsert_and_recompute(session, *, parent_email, purchase_token, status, expires_ms)` — upsert `provider="google"` row (`external_id = purchaseToken`), set status/parent_email/current_period_end, flush, `recompute_household_premium`.
- `verify_purchase(session, *, parent_email, purchase_token, product_id)`:
  1. `_require_google()`.
  2. fetch authoritative state; derive the linked product + `obfuscatedExternalAccountId` + expiry.
  3. **reject** if `obfuscatedExternalAccountId` present and != `household_token(parent_email)` (`GoogleBillingError`).
  4. **reject** if `settings.google_play_product_id` is configured and `product_id` != it.
  5. `_acknowledge(...)` (best-effort, swallow already-acknowledged).
  6. `_upsert_and_recompute(...)`; `session.commit()`.
- `handle_notification(session, signed_message)` — decode the Pub/Sub RTDN envelope (`message.data` base64 → JSON with `subscriptionNotification.purchaseToken`), look up the existing `provider="google"` row by token; if unknown → no-op; else re-fetch authoritative state, upsert + recompute, commit. Fail-closed (mirrors Apple).

**Endpoints (`app/routers/billing.py`):**
- `POST /billing/google/verify` (parent-auth via `get_current_parent`): body `{ purchaseToken, productId }` → `verify_purchase`; `GoogleBillingError` → HTTP 400; returns `{ status: "ok" }`.
- `POST /billing/google/notifications` (no auth, **CSRF-exempt**): parse the Pub/Sub push body, dispatch to `handle_notification`; `GoogleBillingError` → `{ status: "ignored" }`; else `{ status: "ok" }`.
- Add `/billing/google/notifications` to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py`.

**Shared token endpoint:** generalise the household-token endpoint to provider-neutral `GET /billing/account-token` (returns `{ token: household_token(parent_email) }`); keep `GET /billing/apple/account-token` as a thin alias for back-compat.

**Config (`app/core/config.py` + `backend/.env.example`):** `google_play_package_name: str = ""`, `google_play_service_account_json: str = ""` (the JSON key contents), `google_play_product_id: str = ""`.

**Dependency:** add `google-api-python-client` + `google-auth` to `backend/requirements.txt` (pinned).

## Section 2 — Android client + UI

**Custom Kotlin plugin** `frontend/android/app/src/main/java/.../PlayBillingPlugin.kt` (+ `@CapacitorPlugin` registration in `MainActivity`/package), wrapping Play Billing Library 7:
- `getProducts({ productIds })` → `queryProductDetailsAsync` (SUBS); returns `{ id, displayPrice, displayName }[]`.
- `purchase({ productId, obfuscatedAccountId })` → ensure `BillingClient` connected → `launchBillingFlow` (current Activity) with `setObfuscatedAccountId(token)` and the offer token; on the purchase-updated callback resolve `{ purchaseToken, productId }` (or `{ pending: true }` / reject `USER_CANCELLED`). No client-side acknowledge.
- `restore()` → `queryPurchasesAsync(SUBS)` → `{ purchaseTokens: string[] }`.
- Add the Play Billing Gradle dependency to `frontend/android/app/build.gradle` and register the plugin.
- TS bridge `frontend/src/lib/playBilling.ts` (`registerPlugin('PlayBilling')`) with a typed interface mirroring `storekit.ts`.

**Frontend billing API (`src/api/billing.ts`):** add `googleVerify({ purchaseToken, productId })` → `POST /billing/google/verify`; add `accountToken()` → `GET /billing/account-token` (and keep `appleAccountToken` as alias).

**`SubscriptionCard` native branch** — split by `isAndroid()`:
- iOS → existing StoreKit flow (unchanged).
- Android → `accountToken()` → `PlayBilling.purchase({ productId, obfuscatedAccountId })` → `googleVerify({...})` → invalidate `['subscription-status']`. Restore → `PlayBilling.restore()` → `googleVerify` per token. Manage → open `https://play.google.com/store/account/subscriptions`.
- Child experience stays purchase-free (4B).
- Product id constant `PLAY_PRODUCT_ID` (mirrors `PREMIUM_PRODUCT_ID`).

## Section 3 — Trial, compliance, edge cases, testing

- **Trial:** Play free-trial offer on the base plan (Play Console); `trialing` is an active status.
- **Compliance:** purchase only behind parent auth; child app purchase-free; Play Designed-for-Families declarations operator-side; Android uses Play Billing only.
- **Edge cases:** server-side acknowledge (idempotent, within 3 days); refund/revoke/expire/on-hold/grace via RTDN → re-fetch → recompute; re-subscribe/upgrade `linkedPurchaseToken` handled by keying on the current token + recompute; cross-channel OR + product/household guards already in place.
- **Testing:** backend pytest with the Play API client + RTDN decode mocked — `verify_purchase` records + acknowledges + recomputes; household-token mismatch rejected; productId mismatch rejected; `handle_notification` re-fetches + no-ops on unknown token; status mapping. Async fixtures. Frontend `tsc`/lint/`test`/build + a `SubscriptionCard` Android-branch test (mock `PlayBilling` + `googleVerify`, assert no Stripe button, axe). Device purchase testing is operator-side.

## Operator setup (runbook)

Play Console subscription product + base plan + 7-day trial offer; Google Cloud **service account** with Play Developer API access (grant it in Play Console → API access); enable Pub/Sub, create the RTDN topic + a push subscription → `{backend}/billing/google/notifications`, set Play's Real-time developer notifications topic; set env vars (`GOOGLE_PLAY_PACKAGE_NAME`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`, `GOOGLE_PLAY_PRODUCT_ID`); add license-test accounts. (Folds into `docs/2026-06-07-android-operator-runbook.md`.)

## Verification limits

Backend is fully unit-tested here (pytest). Frontend verified via `tsc`/lint/`test`/build + `cap sync`. The Kotlin plugin + Gradle changes **cannot be compiled here** (no Android toolchain) — first compile is the on-demand checkpoint `run_android` job / Android Studio; device purchase test is operator-side.

## Out of scope

iOS, Stripe, and entitlement-core changes; one-time products (subscriptions only); Play publishing. No DB migration.
