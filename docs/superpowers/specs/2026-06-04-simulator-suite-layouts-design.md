# Simulator Suite Layouts (SP-C) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-C of 6** (SP-0 v4 ✅ · SP-A foundation ✅ · SP-B child core ✅ · **SP-C simulator** · SP-D auth/account · SP-E parent/admin).

## Goal

Bring the kids' paper-trading **simulator** screens up to the prototype's investing-first look — a bold "Practice Portfolio" hero on the dashboard, polished stock-detail and browse screens — reusing all market-data hooks, paper-trading logic, routes, and SP-A tokens. **Layout/structure only**; no routes/data/IA/behaviour change; market data + trade logic untouched; play-money framing preserved.

Reference: prototype `/tmp/yasminschoice/src/app/components/` (`Dashboard`, `StockDetail`, `TradingFlow`, `ExplorePage`, `PortfolioPage`). Current screens: `src/pages/child/{Simulator,Stock,Market}.tsx`; components in `src/components/child/simulator/`.

## Scope (approved)

All three simulator screens in one sub-project: **Simulator dashboard** (real work — new portfolio hero), **Stock detail** (moderate polish), **Market/Browse** (light polish), plus the simulator components they use. Decisions: **bold portfolio-value hero** labelled "Practice Portfolio" (play money); weekly-change badge derived from portfolio history.

Out of scope: SP-D (auth — incl. the new parent social-login feature) and SP-E (parent/admin). No backend changes. No new endpoints/data.

## Data (existing — reused, not changed)

- `usePortfolio()` → `{ virtual_cash, total_value, currency_code, holdings[] }` (string money values; `formatCurrency(value, code)`).
- `usePortfolioHistory()` → `PortfolioSnapshot[]` `{ date, value:number }`.
- `useTrades()`, quote/search queries, `QuoteOut`. `formatCurrency` in `src/lib/currency.ts`.

## Components

**New (presentational; unit + `vitest-axe` tested):**
- **`PortfolioHero`** — `{ totalValue, currencyCode, history, showChange }`. Bold `bg-brand-gradient` card: eyebrow "Practice Portfolio · play money", big total value (white, large/bold — AA large-text), a **weekly-change badge** computed from `history` (first vs last snapshot: `+$Δ · ▲y%` in a translucent success/danger pill; **hidden when `history.length < 2`**), and the portfolio area chart embedded on the gradient. Reuses `PortfolioChart` via a new `variant` prop (below) so the a11y `ChartDescription` is preserved. White-on-gradient text only at large/bold sizes.
- **`QuickStatCard`** — `{ label, value, emoji?, tone? }`. A compact stat tile (`rounded-2xl border border-brand-100 bg-card shadow-sm`) used for the "Available Cash" / "This Week" row. `tone` tints the value (`ink`/`success`/`danger`).

**Enhanced (existing):**
- **`PortfolioChart`** — add a `variant?: 'card' | 'onGradient'` prop. `'card'` = today's white card (default, unchanged). `'onGradient'` = white stroke + translucent-white fill + light ticks, no card border, for embedding in `PortfolioHero`. Keep the `role="img"` summary + `ChartDescription` in both.
- **`CashCard`** → repurposed into the **quick-stats row** (two `QuickStatCard`s: Available Cash = `virtual_cash`; This Week = the history delta) + the "Browse stocks" CTA as a `GradientButton`. Keep the multi-currency approximate-rate note. (If cleaner, replace `CashCard`'s body with the new row in place; keep the file/name.)
- **`HoldingsTable`** — restyle rows toward the prototype's holdings list (symbol tile + name + shares; right-aligned price + gain/loss colour using `success`/`danger`). Keep data, links, and any a11y table semantics.
- **`StockHeader`** — cleaner card: name + ticker/exchange chips (`bg-brand-100 text-brand-800`) + big price; keep the EduTooltip + "you own…" line.
- **Market blocks** (`MarketMovers`, `InvestingTips`, `MarketNews`, the per-exchange stock grid cards, search bar) — align to the card aesthetic (`rounded-2xl border border-brand-100 bg-card shadow-sm`); no behaviour change to search/refresh/debounce.

## Per-screen layout

**Simulator dashboard (`Simulator.tsx`)** — `PortfolioHero` (replaces the plain centered header **and** the separate light `PortfolioChart` card — the chart now lives in the hero) → quick-stats row (`QuickStatCard` ×2) + Browse CTA → Holdings/History tabs (unchanged structure; `HoldingsTable` restyled). Keep the loading + multi-currency logic.

**Stock detail (`Stock.tsx`)** — restyle `StockHeader` + wrap the chart and `TradeForm` in consistent cards; keep `ChartGuide`, `InvestmentTimeMachine`, `InvestingTips`, `StockNews`, `ChartCoachPanel`, the buy/sell mutation, and EduTooltips exactly. Trade inputs stay ≥16px on touch.

**Market/Browse (`Market.tsx`)** — card-consistent search + section headers; restyle the stock-grid cards + movers/tips/news blocks. Search/refresh/debounce logic unchanged.

## Accessibility

- New components ship `vitest-axe` tests. Charts keep `role="img"` + summary + `ChartDescription` (both variants). Decorative emojis `aria-hidden`.
- White-on-gradient text in the hero stays large/bold (AA large-text); change/gain-loss colours use `success-700`/`danger-700` where on light, translucent-white pills on the gradient.
- Trade-form inputs ≥16px on touch; no `maximum-scale`; safe-area preserved. `ChartCoachPanel` LLM output stays moderated (untouched).

## Testing

- New `PortfolioHero` + `QuickStatCard`: unit (value/change-badge/empty-history) + axe.
- `PortfolioChart` variant: a test that `onGradient` still renders the chart + `ChartDescription`.
- Updated screens/components: adapt existing tests to new markup; keep behavioural assertions (trade flow, search, tabs).
- Before/after mocked-API screenshots (dashboard, stock detail, market). `tsc -b`, lint, test, build; backend untouched. All 5 CI jobs green. iOS rebuild deferred to programme end.

## Plan shape

Task per unit, low-risk order: `QuickStatCard` → `PortfolioChart` `onGradient` variant → `PortfolioHero` → wire `Simulator.tsx` (hero + quick stats) → `HoldingsTable` restyle → Stock detail (`StockHeader` + cards) → Market polish → final a11y/regression. Each a green-CI checkpoint; new components land with their consumer.

## Decisions captured

Bold "Practice Portfolio" gradient hero (play money) · weekly-change badge from portfolio history (graceful when <2 points) · chart embedded in hero via a `PortfolioChart` variant (a11y preserved) · all three screens · layout-only, no data/trade-logic change.
