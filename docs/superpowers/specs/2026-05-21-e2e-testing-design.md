# E2E Integration Testing — Design Spec

## Goal

Expand the Playwright e2e suite to cover the new Stripe billing flow and fill coverage gaps in auth error states, password reset, email verification, and route guards. No new backend code required — tests use existing endpoints.

## Context

Invest-Ed has 7 existing e2e spec files (16 tests) covering child signup, parent consent/dashboard, lessons, simulator, stats, responsive layout, and a11y axe scans. All run against a live backend + Postgres via `npm run test:e2e`. Helpers in `tests/e2e/helpers.ts` provide `registerMinor()`, `readLatestEmailToken()`, and `uniq()`.

Sub-project 7 added Stripe Checkout subscriptions, but there are no e2e tests for the billing UI or premium entitlement propagation.

## Architecture

### Premium Test Seam

Tests cannot hit real Stripe. Instead, we use the existing `POST /parent/children/{user_id}/premium` endpoint (in `backend/app/routers/parent.py:71`) to grant/revoke premium. This endpoint:

- Requires parent authentication (session cookie)
- Accepts `{ "premium": true/false }`
- Calls `entitlements.set_premium()` with audit logging
- Is already CSRF-protected (parent session includes CSRF token)

In e2e tests, the parent is already authenticated via magic link. We extract session cookies from the Playwright browser context and make a direct `fetch()` call to the backend to toggle premium. No new backend endpoint needed.

### Shared Helpers

Promote duplicated patterns from existing spec files into `tests/e2e/helpers.ts`:

- `loginParentViaMagicLink(page, parentEmail)` — request magic link, read token from DB, navigate to callback, wait for dashboard. Extracted from `parent-flow.spec.ts` pattern.
- `grantPremiumViaApi(page, childUserId)` — extract cookies from Playwright browser context via `page.context().cookies()`, build `Cookie` header string. Read `csrf_token` cookie value and send it as `X-CSRF-Token` header. POST to `http://localhost:8000/parent/children/{user_id}/premium` with `{ "premium": true }`. Returns after the API responds. A second variant or boolean param supports revoke (`{ "premium": false }`).
- `loginChild(page, email, password?)` — navigate to `/login`, fill email + password, submit, wait for `/home`. Currently duplicated in `simulator-flow.spec.ts` and `stats-flow.spec.ts`.
- `registerOverThresholdUS(page, username)` — register a US 14-year-old (no parent consent needed). Currently duplicated in `lessons-flow.spec.ts`.

Existing helpers (`registerMinor`, `readLatestEmailToken`, `uniq`) are unchanged.

## New Spec Files

### 1. `billing-flow.spec.ts` — 4 tests

Tests the SubscriptionCard UI on the Parent Dashboard and premium propagation to children.

**Test 1: Free state — parent sees upgrade CTA**
- Register minor + approve consent + parent magic-link login
- Parent Dashboard shows SubscriptionCard with text "Free plan"
- "Subscribe to Premium" button is visible
- Child card does NOT show "Premium" badge

**Test 2: Premium grant — dashboard updates**
- Same setup as Test 1
- Call `grantPremiumViaApi()` for the child
- Reload the page (or navigate away and back)
- Child card shows "Premium" badge

**Test 3: Premium visible to child**
- Register minor, approve consent, grant premium via parent
- Child logs in at `/login`
- Navigate to `/lessons` — premium modules are accessible (no "Premium required" toast or 403 block)

**Test 4: Premium revoke — badge removed**
- Grant premium, verify badge shows
- Revoke premium via API (`{ "premium": false }`)
- Reload — child card no longer shows "Premium" badge

### 2. `auth-errors-flow.spec.ts` — 4 tests

Tests auth error handling and the password recovery flow.

**Test 1: Wrong password shows error**
- Register an over-threshold child (so they can log in directly)
- Navigate to `/login`, enter correct email, wrong password
- Expect error text: "Email or password incorrect"

**Test 2: Nonexistent user shows error**
- Navigate to `/login`, enter `nobody@example.com` + any password
- Expect error text: "Email or password incorrect"

**Test 3: Forgot password → reset → login**
- Register an over-threshold child
- Navigate to `/forgot-password`, enter email, submit
- Expect "Check your email" confirmation
- Read password_reset token from `sent_emails` via `readLatestEmailToken()`
- Navigate to `/reset-password?token=<token>`
- Enter new password (meets validation: 12+ chars, letter, digit), confirm, submit
- Expect success message with link to sign in
- Navigate to `/login`, log in with new password
- Expect to land on `/home`

**Test 4: Verify email flow**
- Register an over-threshold child (triggers verify_email sent_email row)
- Read verify_email token from DB
- Navigate to `/verify-email?token=<token>`
- Expect success state (verified confirmation)

### 3. `route-guards-flow.spec.ts` — 3 tests

Tests that unauthenticated access is properly redirected and invalid routes show 404.

**Test 1: Unauthenticated child route → login**
- Navigate to `/home` with no session
- Expect redirect to `/login`

**Test 2: Unauthenticated parent route → parent login**
- Navigate to `/parent` with no session
- Expect redirect to `/parent/login`

**Test 3: 404 page**
- Navigate to `/this-page-does-not-exist`
- Expect "Not found" text visible

## What's Out of Scope

- **Real Stripe integration testing** — webhook handling is covered by 14 backend unit tests. The e2e suite verifies the UI reacts correctly to premium state.
- **Refactoring existing spec files** — won't change simulator-flow, stats-flow, etc. to use new shared helpers (that's cleanup, not test coverage).
- **New backend endpoints** — no test-only routes. We reuse `POST /parent/children/{user_id}/premium`.
- **CI pipeline changes** — existing `npm run test:e2e` picks up new files automatically.
- **Stripe Checkout redirect testing** — the redirect to `checkout.stripe.com` can't be followed in e2e. We verify the button exists and is clickable, but don't assert the redirect destination.

## Test Count

| Spec file | Tests | Status |
|-----------|-------|--------|
| child-flow.spec.ts | 3 | existing |
| parent-flow.spec.ts | 3 | existing |
| lessons-flow.spec.ts | 3 | existing |
| simulator-flow.spec.ts | 1 | existing |
| stats-flow.spec.ts | 1 | existing |
| a11y-flow.spec.ts | 1 | existing |
| responsive.spec.ts | 4 | existing |
| **billing-flow.spec.ts** | **4** | **new** |
| **auth-errors-flow.spec.ts** | **4** | **new** |
| **route-guards-flow.spec.ts** | **3** | **new** |
| **Total** | **27** | 16 existing + 11 new |

## Dependencies

- Playwright + `@axe-core/playwright` already installed
- Backend running at `localhost:8000` with Postgres (existing requirement)
- `psql` available for `readLatestEmailToken()` (existing requirement)
- No new npm packages needed
