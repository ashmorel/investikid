# W6 — Simulator Long-Term Signals — Design Spec + Implementation Plan

**Date:** 2026-06-11 · **Status:** Approved (design) · **Repo:** `ashmorel/investikid` · branch `testing`
**Roadmap:** Phase 3, workstream W6. Small scope → spec and plan combined.

## Decisions (locked with user)
1. **Real commission** — percentage of trade value (default **1%**), actually charged; admin-configurable.
2. **Sell-at-loss reflection** — shown only when selling below average buy price; proceed always allowed.
3. **Portfolio growth projection** — forward-looking dashboard card (the existing per-stock Time Machine covers backward-looking).
4. Diversification meter on the dashboard.

## Verified ground
- `simulator_service.execute_trade(session, portfolio, quote, type, shares)` — the single trade-execution path (router `place_trade` ~line 618 calls it; raises InsufficientFunds/Shares). Commission lives HERE so every caller pays it.
- `HoldingOut.avg_buy_price` (schemas/simulator.py:24) already reaches the FE → loss detection is FE-side arithmetic.
- AppSetting pattern: `app/services/app_settings.py` (`get_starting_cash`/`set_starting_cash`, key `simulator.starting_cash`) + admin endpoints/form — clone for `simulator.trade_commission_pct`.
- Dashboard cards live in `frontend/src/pages/child/Simulator.tsx` composing `QuickStatCard`/`PortfolioHero`/`PortfolioSnapshotCard` etc.; TradeForm at `frontend/src/components/child/simulator/TradeForm.tsx` (side toggle ~line 132, onSubmit ~65).

## A. Commission (backend + admin + FE display)
- `app_settings.py`: `get_trade_commission_pct(session) -> Decimal` (default `Decimal("1.0")` percent; key `simulator.trade_commission_pct`), `set_trade_commission_pct` with bounds 0–10.
- `execute_trade`: compute `fee = trade_value * pct/100`, quantised like existing money maths. BUY: total cost = value + fee (InsufficientFunds accounts for it). SELL: proceeds = value − fee. Persist nothing new on Trade unless a `fee` column exists — expose the fee in the trade RESPONSE (extend `TradeResultOut`/place_trade response with `fee: Decimal` + `commission_pct`) and in a small `GET /market/trade-config` (or piggyback an existing config endpoint) so TradeForm can show the fee BEFORE confirming. No migration: fee is derived, not stored.
- Admin: extend the starting-cash admin endpoint/form with the commission percent field (same validation style).
- FE TradeForm: show "Fee (1%): £X · Total: £Y" line for the entered quantity, live.
- Tests: buy charges fee (cash decreases by value+fee), sell nets fee, insufficient-funds boundary includes fee, pct=0 → behaves exactly as today, admin set/get + bounds, response carries fee.

## B. Sell-at-loss reflection (FE-only)
- In TradeForm (or its parent Stock page where holding data lives): when `side === 'sell'` and `quote.price < holding.avg_buy_price`, the submit first shows a reflection step: "You'd be selling at a loss. What's your reason?" — three tappable reasons: "The company's story has changed" (response: "A real reason to rethink — stories matter more than prices.") / "I need the cash for something else" ("Fair — needing money is a real reason.") / "The price is falling and it scares me" ("That's the one to watch: falling prices alone are often the worst reason to sell. Markets wobble; selling locks in the loss."). After any choice → Confirm sell / Cancel. Selling at a gain: unchanged flow.
- Tier-aware copy not needed (already investor-appropriate). a11y: radio-style buttons, focus management, axe.
- Tests: loss-sell shows reflection, gain-sell doesn't, each reason shows its response, proceed completes the trade, cancel doesn't.

## C. Diversification meter (FE-only)
- `DiversificationCard` on the Simulator dashboard from the holdings list already fetched: distinct tickers n → label/progress: 0 "No investments yet", 1 "All eggs in one basket", 2–3 "Getting spread out", 4–5 "Nicely diversified", 6+ "Well spread". 5-step meter using brand tokens; one-line nudge ("Spreading across more companies lowers the damage any one can do").
- Tests: each band renders correct label/width; axe.

## D. Growth projection card (FE-only)
- `GrowthProjectionCard` on the dashboard: from total portfolio value V (already on PortfolioHero data), show V×1.07^10 / ^20 / ^30 ("If your portfolio kept growing ~7% a year…"), currency-formatted, with the disclaimer "An illustration of compounding — not a prediction or a promise." Hidden when V is 0.
- Tests: maths (1.07^n), zero-value hidden, disclaimer present, axe.

## Out of scope
Sector diversification; storing fees on trades (derived only); reward/mission changes; spread/FX fee modelling; backend reflection logging.

## Build plan (subagent tasks)
1. **BE:** commission in app_settings + execute_trade + response/config + admin endpoint+form field + tests. Commit `feat(w6): trade commission (charged, admin-configurable)`.
2. **FE:** TradeForm fee line + sell-at-loss reflection + the two dashboard cards + tests. Commit `feat(w6): fee display, sell-at-loss reflection, diversification + growth cards`.
3. Full regression both stacks; push; CI (re-run once on the known pip-audit PyPI flake).
