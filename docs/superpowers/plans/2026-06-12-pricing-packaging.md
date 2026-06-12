# Pricing & Packaging (M5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Annual-led two-plan packaging per `docs/superpowers/specs/2026-06-12-pricing-packaging-design.md` — plan catalog, plan-aware Stripe checkout, multi-product IAP verify, /billing/plans endpoint, SubscriptionCard plan picker. No migration.

**Tech Stack:** as M4. Branch `testing`. Commits end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

### Task 1: Plan catalog + settings
- [ ] `app/core/config.py`: add `stripe_price_id_annual`, `apple_iap_product_id_annual`, `google_play_product_id_annual` (all default ""); rename nothing (legacy fields stay).
- [ ] `app/services/plan_catalog.py`: `PLANS` (annual first; display prices USD/GBP/HKD per spec; savings_pct 33 on annual), `resolve_stripe_price(plan)` (annual→annual id, fallback legacy/monthly; monthly→monthly id fallback legacy), `apple_product_id(plan)` / `google_product_id(plan)` (fallback `premium_monthly`/`premium_annual`), `allowed_apple_products()` / `allowed_google_products()`.
- [ ] Tests `tests/test_plan_catalog.py` (resolution + fallbacks via monkeypatched settings).
- [ ] Commit `feat(m5): plan catalog + annual settings`.

### Task 2: /billing/plans + plan-aware checkout
- [ ] `billing_service.create_checkout_session(session, parent_email, plan)` uses `resolve_stripe_price`; metadata gains `plan`.
- [ ] Router: `POST /billing/checkout` body `{plan?: 'annual'|'monthly'}` (pydantic, default annual); `GET /billing/plans` resolving household currency (first child by parent_email, default USD) → `{currency, plans:[...]}`.
- [ ] Tests `tests/test_billing_plans.py`: plans auth/currency/order; checkout passes the right price id to a stubbed `stripe.checkout.Session.create` for each plan + fallback.
- [ ] Commit `feat(m5): /billing/plans + plan-aware checkout`.

### Task 3: IAP allowed-set verify
- [ ] `apple_billing_service`: product check → `allowed_apple_products()` membership (empty set ⇒ skip).
- [ ] `google_billing_service`: same with `allowed_google_products()`.
- [ ] Extend existing apple/google verify tests: annual product accepted, foreign product still rejected.
- [ ] Commit `feat(m5): IAP verify accepts annual product`.

### Task 4: SubscriptionCard plan picker
- [ ] `src/api/billing.ts`: `getPlans()`, `createCheckout(plan)` types.
- [ ] `SubscriptionCard`: unsubscribed state gets a radiogroup picker (annual preselected, savings badge, household line); selected plan drives Stripe checkout arg and StoreKit/PlayBilling productId (from plans data; constants deleted). Loading fallback: picker hidden until plans load (CTA disabled).
- [ ] Tests: picker render/selection/CTA payloads (mock billingApi + StoreKit/PlayBilling), axe.
- [ ] Commit `feat(m5): subscription plan picker (annual-led)`.

### Task 5: Verify + push + docs
- [ ] Backend ruff + pytest; frontend tsc + lint + vitest + build; cap sync ios.
- [ ] Push `testing`, CI green; roadmap M5 status + memory; operator hand-off list surfaced in the final report.
