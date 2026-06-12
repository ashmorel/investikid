# Pricing & Packaging (M5) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M5 of `docs/2026-06-12-market-leader-roadmap.md` · Owner decisions: annual-led two-plan structure; **family SKU dropped** (the entitlement model is already household-wide — one subscription covers every child of the parent — so "covers the whole family" becomes a headline benefit, not a separate price).

## Plans (the catalog)

| plan | interval | USD | GBP | HKD | notes |
|---|---|---|---|---|---|
| `annual` | year | $39.99 | £29.99 | HK$298 | **lead plan**, picker default, "Save 33%" badge |
| `monthly` | month | $4.99 | £3.99 | HK$38 | secondary |

Both plans: 7-day first-time trial (existing behaviour), whole-household entitlement
(existing `recompute_household_premium`), cancel anytime. Regional prices are **App
Store Connect / Play / Stripe price points** (operator-configured); the table above is
the in-app *display* catalog, single source `backend/app/services/plan_catalog.py`.

## Backend

1. **Settings** (env per environment):
   - `stripe_price_id_monthly` (falls back to legacy `stripe_price_id` if unset), `stripe_price_id_annual`.
   - `apple_iap_product_id_annual`, `google_play_product_id_annual` (existing `*_product_id` stays = monthly).
2. **`plan_catalog.py`**: `PLANS` dict (price display strings per currency, interval,
   savings copy, per-store product-id resolution from settings with `premium_monthly`/
   `premium_annual` fallbacks); `resolve_stripe_price(plan)`; `allowed_apple_products()`,
   `allowed_google_products()` (non-empty configured values).
3. **`GET /billing/plans`** (parent-authed): resolves the household display currency
   (currency_code of the parent's first child, default USD) and returns
   `{currency, plans: [{plan, interval, display_price, savings_pct?, apple_product_id, google_product_id}]}`
   — annual first.
4. **`POST /billing/checkout`** accepts optional JSON `{plan: 'annual'|'monthly'}`
   (default `annual`); picks the matching Stripe price; if the annual price id is not
   yet configured, falls back to monthly (graceful rollout); plan recorded in checkout
   `metadata`.
5. **Apple/Google verify**: product check becomes membership of the configured allowed
   set (monthly OR annual) instead of a single id. Empty set ⇒ no check (existing
   permissive default preserved).

## Frontend

1. `billingApi.getPlans()`; `createCheckout(plan)`.
2. **SubscriptionCard plan picker** (web + native, unsubscribed state): two selectable
   cards — annual preselected ("$39.99/yr · Save 33%"), monthly below; one line under
   the picker: "One subscription unlocks Premium for **all** your children." CTA stays
   one button; on web → Stripe checkout with the chosen plan; on iOS/Android → StoreKit/
   PlayBilling purchase with the chosen plan's product id from the plans endpoint
   (replaces the hardcoded `premium_monthly` constants). Prices/currency come from the
   endpoint — no client-side price table.
3. A11y: picker is a radiogroup with labelled radios, ≥44px targets, axe test; loading/
   error states keep the existing card patterns.

## Out of scope

Family SKU / per-child caps (dropped) · price A/B testing (M6 copy variants instead) ·
Apple Small Business Program, App Store Connect & Play product creation, Stripe price
creation + env vars (operator hand-off list in the plan) · plan analytics prop (defer).

## Operator hand-off (USER, dashboards — required before prod use)

1. **Stripe**: create `premium_annual` recurring Price ($39.99/yr with £29.99 + HK$298
   currency options) and ensure the monthly Price carries the same currency options; set
   `STRIPE_PRICE_ID_MONTHLY` + `STRIPE_PRICE_ID_ANNUAL` on Railway (all 3 envs).
2. **App Store Connect**: add auto-renewable `premium_annual` (same subscription group
   as `premium_monthly`), set regional price points (US/UK/HK), submit with next build;
   **enrol in the Apple Small Business Program** (15% rate).
3. **Play Console**: add `premium_annual` subscription with regional prices.
4. Set `APPLE_IAP_PRODUCT_ID_ANNUAL=premium_annual`, `GOOGLE_PLAY_PRODUCT_ID_ANNUAL=premium_annual` on Railway.

## Testing

Backend: plan catalog resolution (fallbacks, allowed sets); /billing/plans (currency
resolution from first child, default USD, annual first, auth required); checkout plan
param (annual default, monthly, fallback when annual unconfigured — assert the price id
passed to the stubbed Stripe call); apple/google verify accept the annual product and
still reject foreign products. Frontend: picker renders both plans with endpoint prices,
annual preselected, selection switches CTA payload (web checkout arg + native productId),
household line present, axe. Full gates per repo convention.
