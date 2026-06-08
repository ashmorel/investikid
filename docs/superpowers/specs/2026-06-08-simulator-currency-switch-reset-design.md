# Simulator Currency Switch (real conversion) + Start-Fresh Reset — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** Country/region switcher (feature). **Most of it already shipped** — this spec covers only the remaining gap.

## Already shipped (do NOT rebuild)

- `RegionSwitcher` (US/UK/HK) in the child ProfileMenu → `PATCH /users/me {content_region}`; invalidates lessons/recommendations/market. Drives content filtering via `content_region_for(user)`.
- `CurrencySelector` (practice-currency dropdown) → currently `PATCH /users/me {currency_code}`.
- `REGION_EXCHANGES` wired into `Market.tsx` `priorityExchanges` (simulator leads with the region's exchange).
- `lib/region.ts` (regions, flags, exchanges, `MAJOR_CURRENCIES = USD/GBP/HKD`); backend `content_region` validated to `{US, GB, HK}`.

**Region switching is unchanged by this spec.** `content_region` and the practice currency stay as two separate controls; `country_code` (legal/consent) is never touched.

## The gap this spec fixes

1. **Changing the practice currency is currently inert for an existing portfolio.** `CurrencySelector` only updates the *user's* `currency_code` preference, but the simulator portfolio reads its **own** `portfolio.currency_code` + `virtual_cash` (set once at creation, never updated). So an existing child who switches currency sees no change. Fix: switching currency must **convert the portfolio's cash** into the new currency (value-preserving, using the simulator's existing approx FX rates) and update `portfolio.currency_code` — **holdings (shares) and trade history untouched**.
2. **No "Start fresh" option.** Add an opt-in, confirmation-gated reset that clears holdings + trades and resets cash to the new currency's starting amount, **preserving `UserProgress` (XP / badges / coins / streaks)**.

## Section 1 — Backend

### 1a. Shared FX helper (small DRY refactor)
Today `_APPROX_USD_RATES` lives in `app/routers/simulator.py` (USD 1.0, GBP 1.27, HKD 0.128, EUR, JPY, CAD, AUD — "USD value of one unit"). Extract into `app/services/fx.py`:
- `APPROX_USD_RATES: dict[str, float]` (moved verbatim).
- `convert(amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal` — `usd = amount * rate[from]; result = usd / rate[to]`; unknown currency → rate `1.0`; quantize to `Decimal("0.01")`. If `from == to`, return `amount` unchanged.
Update `simulator.py` to import `APPROX_USD_RATES` from `app/services/fx.py` (keep its existing display usage working).

### 1b. Portfolio currency conversion + reset services (`app/services/simulator_service.py`)
- `async def set_portfolio_currency(session, user, new_currency: str) -> Portfolio | None`:
  - Set `user.currency_code = new_currency`.
  - Load the user's `Portfolio`; if none, return `None` (nothing to convert — the next `get_or_create_portfolio` will use the new currency).
  - If `portfolio.currency_code != new_currency`: `portfolio.virtual_cash = fx.convert(portfolio.virtual_cash, portfolio.currency_code, new_currency)`; `portfolio.currency_code = new_currency`. **Holdings + Trades are not touched.**
  - Flush; return the portfolio.
- `async def reset_portfolio(session, user) -> Portfolio`:
  - Load (or `get_or_create`) the user's `Portfolio`.
  - Delete all `Holding` rows for `portfolio.id` and all `Trade` rows for `portfolio.id` (bulk `delete()` statements).
  - `cash_map = await get_starting_cash(session)`; `portfolio.virtual_cash = cash_map.get(user.currency_code, Decimal("1000.00"))`; `portfolio.currency_code = user.currency_code`.
  - **Do not touch `UserProgress`** (XP/badges/coins/streak persist).
  - Flush; return the portfolio.

### 1c. Endpoints (`app/routers/simulator.py`, child auth via `get_current_user`, normal session+CSRF like `place_trade`)
- `POST /simulator/portfolio/currency` — body `SetCurrencyRequest { currency_code: str }` validated to `MAJOR = {USD, GBP, HKD}` (reject others with 422). Calls `set_portfolio_currency`, `session.commit()`.
- `POST /simulator/portfolio/reset` — no body. Calls `reset_portfolio`, `session.commit()`.
- **Response shape:** both return a **minimal** `PortfolioSummaryOut { id, virtual_cash, currency_code }` (NOT the enriched `PortfolioOut`, which needs the price provider to value holdings). The frontend invalidates `['portfolio']` and refetches the full `GET /portfolio` for the valued view, so the mutation responses stay cheap and provider-free.
- Schemas in `app/schemas/simulator.py` (or wherever the portfolio schemas live): add `SetCurrencyRequest` + `PortfolioSummaryOut`.

**No DB migration** (reuses existing `Portfolio`/`Holding`/`Trade` columns).

## Section 2 — Frontend

- **`src/api/simulator.ts`:** add `setCurrency(currency_code: string)` → `POST /simulator/portfolio/currency`; `resetPortfolio()` → `POST /simulator/portfolio/reset`. Both via `apiFetch` (session + CSRF).
- **`CurrencySelector`:** change the mutation from `authApi.updatePreferences({ currency_code })` to `simulatorApi.setCurrency(currency_code)`. Keep invalidating `['me']`, `['portfolio']`, `['portfolio-history']` (now the portfolio genuinely changes). Copy/label unchanged.
- **Start-fresh control (ProfileMenu, in the existing Preferences section under the region/currency controls):** a **"Start fresh"** button → opens the existing `ConfirmDialog` (`src/components/admin/ConfirmDialog.tsx`) with copy: *"Start your practice portfolio over in {currency}? This clears your current play holdings and history. Your XP and badges are safe."* → on confirm, `simulatorApi.resetPortfolio()` → invalidate `['portfolio']`, `['portfolio-history']`. Accessible (labelled trigger, dialog focus handling per the existing component), ≥16px / ≥44px touch targets, Penny/sky styling consistent with the section.

## Section 3 — Testing

**Backend pytest** (`loop_scope="session"`, `db_session`/`client`; reuse simulator test setup for creating a portfolio + holdings/trades; the existing simulator tests show how to seed a portfolio and place trades):
- `fx.convert`: USD↔GBP↔HKD round-trips at the table rates; `from==to` is identity; unknown currency treated as rate 1.0.
- `set_portfolio_currency`: converts `virtual_cash` to the new currency (value-preserving within rounding), updates `portfolio.currency_code`, **leaves Holding + Trade rows unchanged**, updates `user.currency_code`; no-portfolio → returns None + sets `user.currency_code`.
- `reset_portfolio`: deletes holdings + trades, sets cash to the starting amount for `user.currency_code`, sets `portfolio.currency_code`; a pre-existing `UserProgress` with XP/badges/coins is **unchanged** after reset.
- Endpoints: `POST /simulator/portfolio/currency` rejects an unsupported currency (422); both endpoints require auth (401 anon) and return the updated `PortfolioOut`.

**Frontend vitest + vitest-axe:**
- `CurrencySelector` calls `simulatorApi.setCurrency` on change and invalidates the portfolio queries (mock `simulatorApi`).
- ProfileMenu "Start fresh" → opens ConfirmDialog → confirm calls `simulatorApi.resetPortfolio`; cancel does not. No axe violations.

**Verify:** backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. Child simulator surface (web + iOS shell) but logic/UX only — standard build; `cap sync` only at an iOS checkpoint.

## Out of scope
Region switching itself (already shipped); coupling region→currency (they remain separate controls); FX accuracy beyond the existing approx play-money rates; any change to `country_code`, consent, or `UserProgress`.
