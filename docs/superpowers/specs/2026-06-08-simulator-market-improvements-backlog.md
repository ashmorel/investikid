# Simulator / Market Page — Improvements Backlog

**Date:** 2026-06-08
**Status:** Backlog (feedback captured — NOT yet designed/approved)
**Repo:** `ashmorel/investikid` · branch `testing`
**Surface:** the child **Simulator** experience — `frontend/src/pages/child/Simulator.tsx` (dashboard) and `frontend/src/pages/child/Market.tsx` (Browse Stocks). Market data comes from Yahoo Finance via `backend/app/services/price_provider.py`; tips/news summaries from the LLM.

> Each item below is a **backlog entry**, not an approved design. When one is picked up it should go through the normal pipeline: **brainstorming → spec → plan → TDD build**. It's a kids' app — every LLM output stays moderated (fail-closed), premium-gated where relevant, WCAG 2.2 AA, iOS-friendly (≥16px touch). The keystone item (#2 Country/Region selector) unlocks #1 and much of #4/#5, so sequence accordingly.

---

## Current state (verified in code)

| Area | File(s) | Data source today |
|---|---|---|
| "Exchange" label | `Market.tsx:115–120` → `components/child/simulator/EduTooltip.tsx` | Static educational tooltip ("what is an exchange") — **no control wired to it** |
| Today's market movers | `components/child/simulator/MarketMovers.tsx` → `GET /market/movers` → `price_provider.get_market_movers()` | Yahoo `screen("day_gainers"/"day_losers")` — **global screeners, US-skewed**; FE renders whatever exchanges return |
| Investing Tips | `components/child/simulator/InvestingTips.tsx` → `GET /market/tips` (`simulator.py:529–621`) | **LLM-generated, 6 tips, 1-hour global cache**, 3 hardcoded fallbacks; UI shows them statically (no rotation) |
| News for your stocks | `components/child/simulator/MarketNews.tsx` → `GET /market/news` (+ `/market/news-summary`) | Yahoo news for the **child's actual holdings**; LLM age-aware summary |
| Country stock groups | `Market.tsx:26–43, 179–209` + `lib/region.ts` | Grouped by exchange; **order prioritised by `content_region`** (US→NASDAQ/NYSE, GB→LSE, HK→HKEX); labels hardcoded |

**Region influence today:** only the *browse-list ordering* is region-aware. Movers and tips are **not** region-aware; news is holdings-based.

---

## Item 1 — Remove or repurpose the dead "Exchange" label

**Problem:** Next to the "Browse Stocks" heading, the word **"Exchange"** is an `EduTooltip` (info-bubble definition). It reads as a control but does nothing → confusing clutter.

**Recommended approach:** **Repurpose, don't just delete.** Replace the decorative tooltip with the real **Country/Region selector** from Item 2. Keep the educational "what is an exchange/market?" explanation as a tooltip *inside* that control so we lose nothing pedagogically.

**If Item 2 is deferred:** at minimum remove the standalone tooltip from the heading (or move the definition into the search helper text) so it stops looking interactive.

**Scope:** FE only (`Market.tsx`, `EduTooltip` usage). **Effort:** XS (folds into Item 2).

---

## Item 2 — Country/Region selector driving movers + browse (keystone)

**Problem:** "Today's market movers" effectively only shows **NASDAQ/NYSE**, because the backend uses Yahoo's *global* gainers/losers screeners, which are US-skewed. Other major exchanges (LSE, HKEX, etc.) rarely appear. There's no way to choose a market.

**Recommended approach:** Add a **Country/Region picker** at the top of the Market page that:
1. **Defaults to the child's `content_region`** (US / GB / HK — already stored on the user).
2. **Drives the movers** — show gainers/losers for that country's **major exchange(s)** (GB→LSE, HK→HKEX, US→NASDAQ+NYSE), not the global screener.
3. **Drives the browse list ordering/filter** below (selected country first, consistent with the labels in `lib/region.ts`).
4. Replaces the dead "Exchange" tooltip (Item 1).

**Open design questions (for brainstorming):**
- **Backend movers by region:** Yahoo's predefined global screeners won't give per-exchange movers cleanly. Options to evaluate: region-scoped screeners, a curated per-exchange ticker universe we compute gainers/losers over, or a different data source. Needs spiking — this is the main unknown.
- **Country vs exchange granularity:** pick *country* (maps to one-or-more exchanges) for kid-friendliness, with the exchange shown as secondary detail.
- **Which countries to support at launch:** start with the three we already model (US/GB/HK); make the list data-driven so it extends.
- **Caching:** movers cache key becomes per-region (today it's a single `_movers` 5-min cache).

**Scope:** BE (`price_provider.get_market_movers` → region-aware; new query param on `/market/movers`) + FE (selector component, wire to movers + browse). **Effort:** L (backend data-sourcing is the risk). **Premium/safety:** no LLM; respects existing gating.

---

## Item 3 — Rotating / fresher Investing Tips (fast win)

**Problem:** Tips *feel* static. In reality they're LLM-generated and refresh hourly — but the cache is **global + 1-hour** and the UI renders the same set with **no rotation**, so within any session they never change.

**Recommended approach (incremental):**
1. **Rotate on screen** — the backend already returns ~6 tips; cycle them in the UI (auto-advance every few seconds, and/or show a different tip on each visit). Pure FE, no backend change. *Fastest win.*
2. **Make it feel personal** — optionally tailor tips to the child's **holdings** ("Since you own Apple…") or current **lesson level**. Needs a backend tweak (pass context to the tip prompt) + keeps moderation fail-closed.
3. **Per-child freshness** — consider a per-user cache or a "new tips" affordance instead of the single global 1-hour cache, balanced against LLM cost/rate limits.

**Scope:** Item 3.1 is FE-only. 3.2/3.3 touch `simulator.py:_generate_tips` + caching. **Effort:** 3.1 = S; 3.2/3.3 = M. **Safety:** existing `moderate_output` path stays.

---

## Item 4 — Tidy the "News for your stocks" + per-country sections

**Problem:** Below the fold the page stacks **News-for-your-stocks** and then the **per-country stock groups** (Hong Kong / UK / US) as flat, full-width blocks. Ordering is region-prioritised but the **visual hierarchy is weak** and the country sections feel arbitrary/unbalanced (e.g. a section with one stock looks broken).

**Recommended approach:**
- **Consistent card system** across movers, news, and browse groups (one card component, one grid).
- **Clear section headers** with counts; collapse/hide empty or single-item country groups, or merge them under a "More markets" affordance.
- **Make news contextual, not a wall** — see Item 5 (move it to a secondary rail / collapsible card rather than a full-width block that interrupts browsing).
- **Country grouping driven by the Item 2 selector** so the order is obvious (selected country's stocks first; others behind a toggle).

**Scope:** FE layout refactor (`Market.tsx`, card components). **Effort:** M. Depends on Item 2 for the selector-driven ordering.

---

## Item 5 — Overall page restructure (information hierarchy)

**Problem:** The Market page is one long vertical scroll that mixes **discovery** (movers, tips, news) with **browsing** (country stock lists) with no clear zones. The Simulator dashboard (`Simulator.tsx`: mission → portfolio hero → cash → holdings/history tabs) is reasonable, but the **Market** page needs the work.

**Recommended target structure:**
- **Top bar:** Search **+** the Country/Region selector (Item 2) — one clear control strip.
- **Zone A — "What's moving today":** movers for the selected country (Item 2).
- **Zone B — "Browse stocks":** per-exchange groups, consistent cards, selected country first (Item 4).
- **Secondary rail (desktop) / collapsible cards (mobile):** rotating **Tips** (Item 3) + **News for your stocks** — contextual content that shouldn't break the main browse flow.
- **Region-aware end-to-end:** movers, browse order, and labels all keyed off `content_region` (today only browse ordering is).

**Scope:** FE layout/IA refactor tying the above together; ideally tackled *after* Items 2–4 land so it composes finished pieces. **Effort:** M–L. **A11y:** re-run `vitest-axe` + Playwright a11y on the rebuilt page; keep keyboard order logical and touch targets ≥16px.

---

## Suggested sequencing
1. **Item 3.1** (rotate tips) — fastest standalone win, FE-only.
2. **Item 2** (Country/Region selector + region-aware movers) — keystone; absorbs Item 1; spike the backend movers data source first.
3. **Item 4** (tidy news + country sections) — builds on the selector.
4. **Item 5** (overall restructure) — composes 2–4 into a clean IA.

## Out of scope (for now)
Changing the market-data provider wholesale; real-money anything; new premium gates; the Simulator *dashboard* layout (only the **Market/Browse** page needs rework). Each item gets its own brainstorm → spec → plan when scheduled.
