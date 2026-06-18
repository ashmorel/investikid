# Multi-Market Frontend — Design Spec (Sub-project C2b)

**Date:** 2026-06-18
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project C, part 2b of 2)

---

## Programme context

Predecessors live in prod: **0** Gemini lineup, **A** i18n, **B** AI-language, **C1** market foundation, **C2a** multi-market backend (live APIs: `GET /markets` → `{code,name,currency_code,has_content,enrolled,is_selected}`; `POST /me/active-market` → switch + lazy-enroll; `GET /me/markets` → per-market `xp` + `total_xp` + `level`; `active_market_code` on `/users/me`).

**C2b (this spec)** is the visible frontend that surfaces C2a: the market chip, picker, coming-soon state, and per-market progress. **No backend changes** — it rides the live APIs, so a Vercel deploy with **no migration** (no snapshot question).

**Locked decisions (from the C/C2/C2b brainstorm):**
- **Show all 10 markets**; the picker lists them all — GB is content-ready, the other 9 show a friendly **"Coming soon"** but are still tappable.
- **Lazy enrollment** on switch (handled server-side by C2a).
- **Active market drives content**; engagement (level/streak/coins/goal) stays **global**.
- **Placement:** an **active-market chip on the Home header** → opens a full **"Choose your market" picker** screen; also linked from the settings sheet.
- **Design language = the sky-blue + Penny rebrand** (live `frontend/src/index.css` tokens: brand sky→blue ramp `brand-50…brand-900`, gradient sky→blue→indigo, amber kept only as accent). Build against the live components/tokens; verify by screenshotting the running app. (The canonical design is the Figma Make file `2u6PjDFLS8gfc60Ggwzx5Y`, which the codebase already realizes.)

## Goal

Let a child see and switch their learning market from the Home screen, browse all 10 markets (GB learns; others show "coming soon"), land gracefully on a coming-soon state for empty markets, and see per-market XP — all in the sky-blue rebrand style, fully i18n'd, with global engagement unchanged.

## Non-goals (deferred)

- **No backend changes** (C2a is done). No migration.
- **Currency-follows-market** — display stays on `user.currency_code` (deferred per C2).
- **Unifying with the simulator's trading-region switcher** (`RegionSwitcher`/`content_region`) — that's a separate axis; left as-is.
- **Parent-side market controls** and **un-enrolling** — deferred.
- **Penny artwork** — use the existing Penny asset/component if one is referenced; otherwise a simple market badge for v1 (no new illustration work).

---

## Architecture

### Unit 1 — Market API client + query hooks (`src/api/market.ts` + hooks)

A typed client over the live endpoints, with TanStack Query hooks:
- `type MarketSummary = { code; name; currency_code; has_content; enrolled; is_selected }`.
- `useMarkets()` → `GET /markets` (query key `['markets']`).
- `useMarketProgress()` → `GET /me/markets` (key `['me','markets']`) → `{ markets: {market_code, xp}[]; total_xp; level }`.
- `useSwitchMarket()` → mutation `POST /me/active-market { market_code }`. **On success, invalidate the content-driving queries** so the curriculum re-filters — mirror `RegionSwitcher`'s invalidation set: `['me']`, `['modules']`, `['module-levels']`, `['level-lessons']`, `['recommendations']`, `['next-lesson']`, `['revise*']` (revise hub/session/due), `['me','markets']`. Use `apiFetch` (returns `T | null`).

### Unit 2 — Active-market chip on Home (`MarketChip` + Home header)

A small pill in the Home header (near the greeting): the active market's **flag + name** (active code from `/users/me` `active_market_code`, resolved against `useMarkets()` for the name; flag from a `code→flag` map). Tapping navigates to the picker (`/markets`). Reuses the existing flag set; the 10 ISO markets get a small `MARKET_FLAGS: Record<string,string>` map (emoji, like `RegionSwitcher`). Keyboard-operable, ≥44px, labelled (`aria-label="Change learning market"`).

### Unit 3 — "Choose your market" picker (`src/pages/child/Markets.tsx`, route `/markets`)

A screen listing all 10 markets from `useMarkets()` as cards (mirrors the LanguageSwitcher/card patterns + the sky-blue mockup):
- Each card: flag chip + name + currency. **Selected** (`is_selected`) card gets the brand accent (sky border + a brand "Learning" pill). Content-ready (`has_content`) non-selected cards are normal-selectable; the rest show a muted **"Coming soon"** pill but remain tappable.
- Tapping a card → `useSwitchMarket().mutate(code)` → on success, navigate back to Home (queries already invalidated).
- A back control in the header. Linked from the Home chip and from the settings sheet (`ProfileMenu`, next to the `LanguageSwitcher`).

### Unit 4 — Coming-soon empty state (`ComingSoonMarket`)

When the active market has `has_content === false`, the Home/Lessons content area renders a friendly panel instead of an (empty) curriculum:
- Heading: "New lessons for *{market name}* are on the way!"; body explaining content is being built; a primary CTA **"Switch back to United Kingdom"** (resolve the content-ready market — GB — from `useMarkets()` where `has_content`) that calls `useSwitchMarket()`.
- Penny asset if available; else a market badge. The Home chip still shows the chosen market so the child isn't stuck.
- Gate: the Home page checks `active market.has_content` (from `useMarkets()`); if false, render `ComingSoonMarket` in place of the lesson/module content. The market chip + global engagement header stay visible.

### Unit 5 — Per-market progress display

- **Home:** show the **active market's XP** (from `useMarketProgress()` for the active code) alongside the unchanged **global** level/streak/coins (existing `HomeHero`/`StatsCard` data). No change to global engagement display.
- **Stats page (`Stats.tsx`):** add a small **"XP by market"** breakdown from `useMarketProgress().markets` (market name + XP per enrolled market), under the existing global headline. Markets with 0 XP / not-yet-enrolled are simply absent.

### Unit 6 — i18n + a11y + iOS

- All new copy via `react-i18next` in a new **`markets`** namespace (`src/locales/en/markets.json`); the `no-literal-string` lint guard is enforced.
- All new controls keyboard-operable, ≥44px touch targets, labelled; `vitest-axe` on `MarketChip`, the picker cards, and `ComingSoonMarket`.
- iOS: UI-visible → `npm run build && npx cap sync ios` + Xcode rebuild as part of verification; controls ≥16px text (no zoom).

---

## Data flow

```
Home → useMarkets() + /users/me.active_market_code
     → MarketChip shows active flag+name
     → if active market.has_content === false → render ComingSoonMarket
Tap chip → /markets picker (useMarkets list)
Tap a market card → useSwitchMarket(code)
     → POST /me/active-market → invalidate [me, modules, recommendations, next-lesson, revise*, me/markets]
     → navigate Home → content re-filters to the new active market
Stats → useMarketProgress() → "XP by market" breakdown + global level/total
```

## Error handling / edge cases

- **Switch failure (network):** the mutation surfaces a non-blocking error toast; the active market is unchanged (server is the source of truth). On success the optimistic nav happens after the 200.
- **Active market with no content:** handled by `ComingSoonMarket` (not an error) with an easy way back.
- **`/markets` returns the 10 with flags:** any market code lacking a flag in the map falls back to the ISO code in a chip (defensive).
- **Offline:** reuse the existing `OfflineNotice`/`useOnline` pattern on the picker; switching requires connectivity.
- **A user whose `active_market_code` isn't in `useMarkets()`** (shouldn't happen — server validates): the chip falls back to showing the code; the picker still renders the 10.

## Testing strategy

- **API/hooks:** `useSwitchMarket` posts the code and invalidates the expected query keys (mock `apiFetch` + a spy on `queryClient.invalidateQueries`); `useMarkets`/`useMarketProgress` shape.
- **MarketChip:** renders the active market's flag+name; tap navigates to `/markets`; a11y (`vitest-axe`).
- **Picker:** lists all 10; the selected market shows "Learning" + accent; coming-soon markets show the badge and are still tappable; tapping switches + navigates; a11y.
- **ComingSoonMarket:** renders when active `has_content=false`; the "switch back" CTA targets the content-ready (GB) market and switches; a11y.
- **Stats per-market:** renders the "XP by market" breakdown from `useMarketProgress`.
- **Regression:** a default (GB, active=home) user sees the Home/Stats exactly as before (chip shows GB, no coming-soon, content unchanged) — existing Home/Stats tests stay green.
- **Pseudo-locale / no-literal-string:** all new strings extracted (the C1 guard fails CI on any literal).
- **Verify:** `tsc -b` + `lint` + `vitest` (incl. axe) + `build`; then run the app and screenshot the real screens (chip, picker, coming-soon) to confirm the sky-blue look; `npx cap sync ios` + Xcode rebuild.

## Definition of done

1. The Home header shows the active-market chip; tapping it opens the "Choose your market" picker.
2. The picker lists all 10 markets (GB "Learning"/selected; others "Coming soon", still tappable); switching changes the active market and re-filters content.
3. An empty (coming-soon) active market shows the friendly panel with a working "switch back to UK" CTA — the child is never stuck.
4. Per-market XP shows on Home (active) and Stats ("XP by market"); global level/streak/coins are unchanged.
5. Everything is in the sky-blue rebrand style, fully i18n'd (`markets` namespace, guard passes), a11y-clean; a default GB user's experience is unchanged.
6. All 6 CI jobs green; iOS synced; Vercel prod deploy (no migration).

## Rollout / safety

- **Frontend-only**, on C2a's live APIs → **no DB migration, no prod snapshot question.** Promote testing → staging → main on green CI; then the manual Vercel prod web deploy (`app.investikid.ai`).
- Behaviorally inert for current users until they open the picker (everyone starts active=home=GB; the chip shows GB; no coming-soon).
