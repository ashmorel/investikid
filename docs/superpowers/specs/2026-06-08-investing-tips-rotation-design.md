# Investing Tips Carousel Auto-Rotation — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Backlog ref:** Simulator/Market improvements — **Item 3.1** (`docs/superpowers/specs/2026-06-08-simulator-market-improvements-backlog.md`).
**Scope:** **Frontend only.** One file: `frontend/src/components/child/simulator/InvestingTips.tsx` (+ its test). No backend, no new endpoint, no data-model change.

## Goal
The "Investing Tips" card already renders the LLM-generated tips as a horizontal **scroll-snap carousel** (swipeable cards + dot indicators that track the active card via scroll position). It never advances on its own and has no explicit controls, so on desktop it reads as static. Make it **auto-advance** so the already-fetched tips feel alive within a session — accessibly.

Explicitly **out of scope** (backlog 3.2/3.3): changing how often the backend serves new tips (global 1-hour cache), per-child/holdings personalisation, any backend change. The same `useQuery(['investing-tips'])` fetch is untouched.

## Current behaviour (verified)
`InvestingTips.tsx`:
- `useQuery(['investing-tips'])` → `simulatorApi.getInvestingTips()` (`GET /market/tips`).
- Cards rendered in a `scrollRef` div with `overflow-x-auto`, `scroll-snap-type: x mandatory`, `scroll-snap-align: start` per card.
- `onScroll` → `handleScroll()` computes `activeIndex` from `scrollLeft / (clientWidth * 0.65)`.
- Dot indicators are decorative `<span>`s reflecting `activeIndex`.
- Loading skeleton when `!tips`; renders `null` when `tips.length === 0`.

## Design

### Behavior
- Auto-advance the carousel to the **next card every ~7 seconds**; after the last tip, **loop** back to the first.
- Advance by programmatically scrolling `scrollRef` to the target card's offset (reuse the existing card-width math so scroll-snap + `activeIndex`/dots keep working). No change to the card markup or the scroll-snap mechanism.
- No-op when there is `< 2` tips (nothing to rotate).

### Controls (WCAG 2.2.2 "Pause, Stop, Hide")
- **Play/Pause toggle** in the card header (lucide `Play`/`Pause`), default **playing**. Real `<button>`, `aria-label` toggling between "Pause tips"/"Play tips", visible focus ring, hit area ≥24px.
- **Dots become `<button>`s** — tapping one jumps the carousel to that tip. Each: `aria-label="Go to tip {n}"`, `aria-current="true"` on the active dot, hit area ≥24px (keep the small visual dot, expand the tappable area via padding). Keyboard-focusable.

### Pause logic
- While **playing**, auto-advance pauses when the pointer **hovers** the carousel region OR when **focus is within** it, and resumes on leave/blur — so a child reading a tip isn't yanked forward.
- An **explicit Pause** press sticks: it stays paused regardless of hover/focus until the child presses **Play**.
- State model: `isPlaying` (explicit user intent, default `true`) and a derived "effectively paused" = `!isPlaying || hovered || focusWithin || reducedMotion`.

### Reduced motion
- Under `prefers-reduced-motion: reduce`: auto-advance is **disabled entirely** and the **Play/Pause control is hidden**. Dots still navigate; manual swipe still works. (Detect via `window.matchMedia('(prefers-reduced-motion: reduce)')`.)

### Structure
- Keep all logic in `InvestingTips.tsx` (it stays small). Timer via `setInterval`/`setTimeout` in a `useEffect` keyed on `isPlaying`, `hovered`, `focusWithin`, `reducedMotion`, `tips.length`, and `activeIndex`; cleared on unmount and on every dependency change. No new files.
- Reuse the existing `scrollRef`, `activeIndex`, `handleScroll`. Add: `isPlaying`, `hovered`, `focusWithin`, `reducedMotion` state; a `goToIndex(i)` helper that scrolls to card `i`.

### Tokens / iOS
- Semantic Tailwind v4 tokens (brand/muted/foreground) consistent with the existing card. Control touch targets ≥24px (clears the ≥16px iOS rule). No raw palette.

## Testing (`InvestingTips.test.tsx`, vitest + vitest-axe)
Mock `simulatorApi.getInvestingTips` to return ≥3 tips; mock `getStockHistory` (MiniChart) to a stub; use **fake timers**; stub `Element.prototype.scrollTo` and `matchMedia`.
1. Auto-advance: after ~7s the active index advances; after the last it loops to 0.
2. Pause: pressing Pause halts advancing across subsequent timer ticks; Play resumes.
3. Hover/focus pause: hovering (or focusing within) the carousel stops advancing; leaving resumes (when not explicitly paused).
4. Reduced motion: with `matchMedia('(prefers-reduced-motion: reduce)') = matches`, no auto-advance occurs and **no Play/Pause control** renders.
5. Dots: rendered as buttons; clicking a dot calls the scroll-to for that index.
6. **vitest-axe:** the rendered card has no violations (loaded state).

## Verification
`cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. Web/native surface, no `cap sync`. (Native iOS picks it up at the next scheduled rebuild — not part of this task.)

## Out of scope
Backend tip frequency/personalisation (3.2/3.3); the Country/Region selector (backlog Item 2, designed separately next); any change to the carousel's card content, the MiniChart, or the `/market/tips` contract.
