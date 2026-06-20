# Seamless Onboarding + Native Child-Initiated Purchase — Design Spec

**Date:** 2026-06-20
**Status:** Approved (design); ready for implementation plan
**Programme:** Pre-launch UX + monetization. Follows the pre-TestFlight hardening sub-project.

---

## Context

Two related asks for a more Duolingo-like experience:
1. **Seamless onboarding** — only collect a parent email where the child's country + age legally requires it.
2. **Native subscription approval via the platform** — on iOS/Android let the child *initiate* the purchase so Apple **Ask to Buy** / Google Play **family approval** mediates parental consent at the OS level, instead of the app's internal child→parent **email** request. Keep the email model on **web**.

Investigation of the current code established:
- **Onboarding already conditional.** `POST /auth/register` runs `resolve_policy(country_code, dob)` (`app/services/compliance.py`) and requires `parent_email` ONLY when the child is under the consent age for their country (COPPA/UK-AADC < 13; six EU countries < 16; etc.). Over-threshold teens register with their own email, no parent email. The 2-step signup form (`pages/child/Signup.tsx`) renders the parent-email field only when consent is needed. So the legal core exists; this sub-project **verifies + polishes**, it does not rebuild onboarding.
- **Native IAP already hits the OS purchase sheet** — but only from the **parent dashboard** `SubscriptionCard`, behind `get_current_parent`. Every `/billing/*` endpoint is parent-authed.
- **The child paywall always emails the parent.** `components/child/PremiumPaywall.tsx` calls `premiumApi.requestUnlock` (→ `POST /premium/request` → email) on every platform; there is no native purchase path for the child today.
- **Ask to Buy is an OS feature the app cannot require or detect.** On a Family-Sharing child Apple ID with Ask to Buy on, a child-initiated purchase returns a **pending/deferred** result and the parent approves on their device; on a non-managed device the purchase simply completes against the signed-in Apple ID (its own auth is the only gate). Apple's Kids guidelines expect a parental gate before the purchase flow regardless.

**Locked decisions (from the brainstorm):**
- Onboarding = **verify + polish** (no rebuild).
- A **lightweight parental gate** precedes the native child-initiated purchase.
- **Web is unchanged** (keeps the email `premium_request` flow).
- **Self-managed teens may self-purchase** (their own Apple/Google ID).
- **Ask-to-Buy `.pending` → "asked your grown-up"** is the seamless approval path; entitlement flips later via the existing Apple/Google notification webhook + the daily reconcile.

## Goal

Let a child on native start a subscription themselves — gated by a parental check and mediated by the platform's parental-approval system — while keeping signup free of unnecessary parent-email collection and the web flow unchanged.

## Non-goals (deferred / out of scope)

- Rebuilding onboarding (guest "try before signup", deferred account creation) — separate future sub-project.
- Changing the web paywall / email `premium_request` flow.
- Changing the consent-age matrix in `resolve_policy` (treated as authoritative; legal review is the user's call).
- New pricing/plan SKUs (uses the existing `premium_monthly`/`premium_annual`).
- Re-implementing transaction verification (reuses `apple_billing_service` / `google_billing_service`).

---

## Architecture

### Unit 1 — Onboarding verify + polish (frontend, light)

Audit + tighten, no structural change:
- Confirm `parent_email` is requested only when `resolve_policy(...).requires_parental_consent` is true, and that no later screen re-asks for it.
- Smooth the 2-step copy/transitions to feel Duolingo-clean (encouraging microcopy, clear "why we ask for a grown-up's email" only on the consent path).
- Add/strengthen a test asserting the conditional: over-threshold (e.g. GB age 14) → no parent-email field/requirement; under-threshold (GB age 10) → parent-email required.
- No backend change; the registration logic already enforces it server-side.

### Unit 2 — Child-scoped billing endpoints (backend)

The child needs household-scoped billing access without parent auth. Add **child-authed** (`get_current_user`) endpoints that mirror the parent ones but derive the household from the authenticated child:
- `GET /billing/child/apple/account-token` → the Apple `appAccountToken` for the child's household.
- `GET /billing/child/account-token` → the Google `obfuscatedAccountId` for the child's household.
- `POST /billing/child/apple/verify` → verify a StoreKit JWS for the child's household.
- `POST /billing/child/google/verify` → verify a Play purchase token for the child's household.
- `GET /billing/child/plans` → the plan catalog (prices/product ids) readable by a child.

**Household key.** Today the token is `household_token(parent_email)` (a uuid5). Generalize to a `household_key(user)` helper: `user.parent_email` when present, else a stable per-user fallback (the child's own verified email, or a deterministic id-derived key) so a self-managed teen forms their own single-member household. The Apple/Google verify services already accept a `parent_email`-style scope argument; they are called with the resolved household key. Entitlement still flows through `recompute_household_premium(household_key)`, unlocking every child in the household.

**Reuse:** `apple_billing_service.verify_transaction` / `google_billing_service.verify_purchase` and the existing `household_token` / `account_token` derivations — only the *auth dependency* and the *scope source* change (child instead of parent). No new verification logic.

### Unit 3 — Lightweight parental gate (frontend, native)

A reusable `ParentalGate` component: a brief "Ask a grown-up to continue" challenge (a spelled-out arithmetic / number-entry check that a young child can't trivially pass but is accessible and not a real auth). Returns pass/fail to the caller; fails closed. Native-only; never shown on web. Pure + unit-testable (the challenge logic separate from the UI).

### Unit 4 — Native purchase path on the child paywall (frontend, native)

Extend `PremiumPaywall` so on **native** the primary CTA is "Get premium" → `ParentalGate` → on pass, run the purchase:
1. Fetch the plan (`/billing/child/plans`) + the child account-token.
2. Call the existing native purchase (the `StoreKit.purchase` / `PlayBilling.purchase` calls currently inline in `SubscriptionCard`, **extracted into a shared `nativePurchase` helper** so both the parent card and the child paywall use one implementation).
3. Handle the result:
   - **success** → `POST /billing/child/{apple|google}/verify` → on active entitlement, show unlocked.
   - **pending / deferred** (Ask-to-Buy) → show "Asked your grown-up to approve 👍"; do NOT unlock. Entitlement flips later via the Apple/Google notification webhook + the daily `subscription_reconcile` cron (already shipped), reflected on next app open / refetch.
   - **cancelled / failed** → return to the paywall, friendly message.

On **web** the paywall keeps the existing `premiumApi.requestUnlock` email flow unchanged. On native, the email "or ask a grown-up to set it up" remains as a secondary link (covers devices/markets where the child can't or shouldn't purchase). Platform branch via `isNativeApp()`.

### Unit 5 — Verify + promote

Backend `ruff` + `pytest` (child-scoped auth; household-key scoping incl. the teen fallback; a child cannot scope to another household). Frontend `tsc` + `lint` + `test` + `build` (gate logic, native-vs-web branch, success/pending/cancel paths, a11y on the gate + paywall). `npm run build && npx cap sync ios`. Promote `testing → staging → main`.

---

## Data flow (native child purchase)

```
Child hits premium lock → PremiumPaywall (native) "Get premium"
  → ParentalGate (pass/fail)  [fail → stop]
  → GET /billing/child/plans + /billing/child/apple/account-token
  → StoreKit.purchase(productId, appAccountToken)  [OS sheet; Ask-to-Buy mediates if configured]
     ├─ success  → POST /billing/child/apple/verify → recompute_household_premium → unlocked
     ├─ pending  → "asked your grown-up" (no unlock; webhook/reconcile flips it later)
     └─ cancel   → back to paywall
```

## Error handling / edge cases

- **Child with no parent_email (self-managed teen):** `household_key` falls back to the child's own identity → a valid single-member household; self-purchase works.
- **Child scoping safety:** the child-scoped endpoints derive the household ONLY from the authenticated `get_current_user`; a child can never pass a different household/parent_email. Verify rejects a token whose `appAccountToken`/`obfuscatedAccountId` doesn't match the resolved household key (same check the parent path already does).
- **Ask-to-Buy pending never unlocks early:** entitlement is granted only on a *verified active* provider state, never on the client-side `.pending` signal.
- **Parental gate is not security:** it's a friction gate (kids-app convention), not authentication — the real spend authorization is the OS purchase sheet + Ask-to-Buy. Stated explicitly so it isn't over-trusted.
- **Web:** no native plugin → the native CTA/gate never render; the email flow is the only path.
- **Unconfigured billing env** (no Apple/Google keys): the child endpoints behave like the parent ones (graceful 503 / not-configured), the paywall falls back to the email link.

## Testing strategy

- **Onboarding:** conditional parent-email test (under- vs over-threshold by country/age); no unnecessary collection.
- **Backend:** child-scoped account-token returns the household token for `parent_email`; teen fallback returns a stable self-household token; child-scoped verify scopes to the child's household and rejects a mismatched account token; a child cannot obtain another household's token. Reuse the existing apple/google verify test doubles.
- **Frontend:** `ParentalGate` pass/fail (pure logic); paywall renders the native CTA + gate on native and the email flow on web; success→verify→unlock, pending→"asked your grown-up" (no unlock), cancel→paywall; a11y (vitest-axe).
- **Full gates + CI authoritative.**

## Definition of done

1. Signup never asks for a parent email unless the child's country+age requires it (verified by test) and the flow reads cleanly.
2. On native, a child can start a subscription behind a parental gate; Ask-to-Buy / Play family approval mediates where configured; a pending approval shows "asked your grown-up" and does not unlock until verified-active.
3. Self-managed teens can self-purchase.
4. Web keeps the email request flow unchanged.
5. Entitlement still flows through `recompute_household_premium` and is checked server-side per request.
6. All CI green; promoted testing → staging → main; `cap sync ios` for the native build.

## Rollout / safety

- **Migration:** likely none — `parent_email` already exists on the child and the teen fallback is derived, not stored. The implementation plan confirms; if a stored household-key column proves cleaner, it is additive (snapshot ask per the standing rule).
- Native-only behavior; web unchanged. Promote testing → staging → main on green CI; manual Vercel prod for web; the native purchase path reaches users via the next TestFlight build.
- **Compliance:** the parental gate + OS Ask-to-Buy are the consent mechanisms; the consent-age matrix is unchanged. Legal review of the matrix + the kids-purchase flow is recommended before public launch (operator/user responsibility).

---

## Self-review

- **Placeholders:** none — each unit names its endpoints, components, and the household-key generalization.
- **Internal consistency:** child-scoped endpoints (Unit 2) feed the native paywall (Unit 4) gated by Unit 3; web path untouched throughout; entitlement consistently via `recompute_household_premium`.
- **Scope:** native child-purchase + onboarding polish only; onboarding rebuild, web changes, pricing, and the consent matrix are explicitly out.
- **Ambiguity:** the `.pending` "no early unlock" rule, the teen household-key fallback, and the "gate is friction not auth" stance are stated explicitly to prevent misimplementation.
