# Market Page IA Restructure (Items 4 + 5) — Design Spec

**Date:** 2026-06-09
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Backlog ref:** Simulator/Market improvements **Items 4 + 5** (combined), building on the shipped **Item 2** region selector (`docs/superpowers/specs/2026-06-08-simulator-market-improvements-backlog.md`).
**Scope:** Frontend only — restructure `frontend/src/pages/child/Market.tsx` and introduce a shared `SectionCard`. **No backend. No new endpoints. No LLM. No DB migration. No `cap sync`.**

## Goal
Replace the long, undifferentiated Market scroll with clear zones, a unified card system, and selected-region-first browsing, composing the region selector shipped in Item 2. Chosen structure: **A — discovery-first, tidied scroll** (mobile-first; this is the iOS/TestFlight surface).

## Current state (verified)
`Market.tsx` renders a single `max-w-4xl` column: BackButton → header (`<h1>Browse Stocks</h1>` + `RegionSelector` + Refresh) → count line → search box → `aria-live` SR line → **when `!isSearching`**: `<MarketMovers region>`, `<InvestingTips>`, `<MarketNews>` (stacked, full-width) → then the browse groups (`groupByExchange(stocks, priorityExchanges)` → `<section>` per exchange with a header + a `grid` of `Link` tiles). `MarketMovers`/`InvestingTips`/`MarketNews` each fetch their own data and render their own card shell (`rounded-2xl border-2 border-brand-200 bg-white p-4`) and **return `null` when empty/no data**. Tips/News currently sit **above** browse, interrupting it.

---

## Section 1 — Shared `SectionCard` component
**Create** `frontend/src/components/child/simulator/SectionCard.tsx`.

Props:
```ts
type SectionCardProps = {
  title: string;
  icon?: LucideIcon;          // optional leading icon
  count?: number;             // optional count pill rendered after the title
  collapsible?: boolean;      // default false
  defaultOpen?: boolean;      // default true (only meaningful when collapsible)
  children: React.ReactNode;
  headingLevel?: 2 | 3;       // default 2 — semantic heading level for the title
};
```
Behaviour:
- **Shell (always):** `rounded-2xl border-2 border-brand-200 bg-white p-4`. Semantic brand tokens only.
- **Non-collapsible:** header is a plain `<h{headingLevel}>` row: optional `icon` (`aria-hidden`) + `title` + optional `count` pill; then `children`.
- **Collapsible:** header is a `<button type="button" aria-expanded={open} aria-controls={contentId}>` spanning the row (icon + title + count pill on the left, rotating chevron on the right), min height ≥44px, visible focus ring. `children` live in `<div id={contentId} role="region" aria-labelledby={titleId}>` that is unmounted/hidden when `open` is false. `open` is local `useState(defaultOpen)` — per-session only, **no persistence**.
- The title still reads as a heading for AT even in collapsible mode: put the visible title text in a `<span id={titleId}>` inside the button, and give the content region `aria-labelledby={titleId}` (the button itself carries `aria-expanded`). (A plain button-as-disclosure is WCAG-valid; we add the labelled region for the content.)
- `count` pill style: small rounded brand chip, e.g. `rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700`, with an accessible suffix so it isn't a bare number (e.g. visually `10`, but the heading reads "US Stocks, 10" — achieve via the pill text being inside the heading, acceptable as-is since the section header text "US Stocks (10)" pattern is already used).

Unique ids: derive from a `useId()` so multiple cards don't collide.

## Section 2 — Adopt `SectionCard` in the three discovery components
Refactor each to render **through** `SectionCard` instead of its own bespoke shell. Keep all data-fetching, loading, and `return null` logic intact.

- **`MarketMovers.tsx`** — wrap in `<SectionCard title="What's moving today" icon={TrendingUp}>` (non-collapsible). Rename the visible heading from "Today's Market Movers" to "What's moving today" to match the zone language. Inner `ExchangeSection`/`MoverRow` unchanged. Loading state may stay as its own minimal card or move inside SectionCard — keep current loading text.
- **`InvestingTips.tsx`** — wrap the loaded state in `<SectionCard title="Investing Tips" icon={Lightbulb} collapsible defaultOpen>`. The existing play/pause control and rotation logic stay **inside** the card body (the play/pause button currently lives in the component header row — move it into the SectionCard body's top row, or keep the SectionCard header for title/collapse and render the carousel + controls as children). The carousel `role="group"` and dots are unchanged.
- **`MarketNews.tsx`** — wrap the loaded state in `<SectionCard title="News for your stocks" icon={Newspaper} collapsible defaultOpen={false}>`. `AiSummary` + the news list become children. (Lowercase "your stocks" to match copy; current is "News for Your Stocks" — keep existing casing if preferred, not load-bearing.)

Each component still returns `null` when there's no data, so a collapsed-but-empty card never appears.

## Section 3 — Restructure `Market.tsx` ordering + browse grouping
**New order in the featured (`!isSearching`) view:**
1. Control strip (unchanged): BackButton; header row with `<h1>Browse Stocks</h1>` + `RegionSelector` + Refresh; count/subtitle line; search box; `aria-live` SR line.
2. **Zone A:** `<MarketMovers region={region} />` (non-collapsible discovery headline).
3. **Zone B — Browse:**
   - Split `groups = groupByExchange(stocks, priorityExchanges)` into:
     - `selectedGroups` = groups whose `exchange ∈ REGION_EXCHANGES[region]`, rendered first, each as a plain `<section>` with header `EXCHANGE_GROUP_LABELS[exchange] ?? exchange` + a count pill, and the existing `Link` tile grid.
     - `otherGroups` = the remaining groups. If non-empty, render **one** `<SectionCard title="More markets" count={totalOtherStocks} collapsible defaultOpen={false}>` whose children are the other groups (same `<section>` + grid markup). The count is the sum of stocks across `otherGroups`.
4. **Tips:** `<InvestingTips />` (collapsible, open by default — per Section 2).
5. **News:** `<MarketNews />` (collapsible, closed by default — per Section 2).

**Search (`isSearching`) view:** unchanged in spirit — movers/tips/news hidden; render **all** result groups (selected region first via the existing `priority` ordering), **no** "More markets" split (search is intentional; show everything). Empty/loading/"no results" states unchanged.

Helper: extract a small `BrowseGroup` presentational piece (header + count + grid) reused by both `selectedGroups` and the contents of "More markets" and the search view, to avoid duplicating the `<section>`/grid markup. (Keep `groupByExchange` exported as-is.)

## Section 4 — Counts & labels
- Every browse group header shows a count pill (e.g. "US Stocks (10)" or label + pill).
- "More markets" shows the total hidden-stock count.
- Section titles: "What's moving today", "Browse Stocks" (existing h1), "More markets", "Investing Tips", "News for your stocks".

---

## Accessibility
- Collapsible disclosures: `aria-expanded` on the trigger button, `aria-controls` → content region `id`, content region `aria-labelledby` the title; chevron `aria-hidden`; ≥44px header touch target; visible `focus-visible` ring; logical DOM order preserved (trigger immediately before its content).
- Headings: keep a sensible hierarchy — `h1` page title, `h2` for zone/section titles (Movers, Browse groups, More markets, Tips, News). `SectionCard` `headingLevel` defaults to 2.
- Re-run `vitest-axe` on `SectionCard` and the rebuilt `Market` page; keyboard order logical; touch targets ≥16px (cards already `min-h-[44px]`).
- Kids' app: no new LLM surface, no new data; existing moderation/premium/rate-limit paths untouched.

## Testing
**New — `SectionCard.test.tsx` (vitest + vitest-axe):**
- Renders title (+ icon, + count pill when provided).
- Non-collapsible: no button, content always visible.
- Collapsible `defaultOpen`: content visible, button `aria-expanded="true"`; clicking toggles `aria-expanded` and hides/shows content (assert via `aria-controls` target).
- Collapsible `defaultOpen={false}`: content hidden initially, expands on click.
- axe-clean in both open and collapsed states.

**Extend `Market.test.tsx` (`src/pages/child/__tests__/Market.test.tsx` + mirror in `tests/unit/child-Market.test.tsx` if it asserts layout):**
- Featured view: selected region's group (e.g. "US Stocks") visible; a **"More markets"** disclosure present and **collapsed by default**; toggling it reveals the other regions' groups.
- Tips card present and **expanded** by default; News card present and **collapsed** by default.
- Movers still rendered with the region prop (existing assertion via the stub).
- Search view: typing a query hides movers/tips/news and "More markets"; shows result groups.
- Keep existing axe test green.

**Update existing component tests:** `MarketMovers.test.tsx`, `InvestingTips.test.tsx`, `MarketNews.test.tsx` — adjust any assertions affected by the SectionCard wrapper / the "What's moving today" rename. The InvestingTips rotation tests (play/pause, dots, reduced-motion) must still pass with controls inside the card body.

## Verification
Frontend (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. No backend changes; no `cap sync`. Work on `testing`; do **not** promote. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated working-tree `.gitignore` + uncommitted iOS build-number files alone.

## Out of scope
Backend movers/data; tips personalisation (Items 3.2/3.3); the Simulator **dashboard** layout; the stock-detail page; merging tiny groups within **search** results; persisting collapse state across sessions; any new premium gate or LLM.
