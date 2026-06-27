# Offline support — Phase 1 design (Goal 4)

**Date:** 2026-06-27
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Make the app reliably usable offline for previously-seen content, with automatic
sync when the connection returns, and a clear "as of" freshness label on cached
prices. Frontend-only; no backend or native-plugin code beyond adding
`@capacitor/network`.

## Context — what already exists

- TanStack Query persistence is wired: `PersistQueryClientProvider` in
  `frontend/src/main.tsx`, `createAppPersister()` (localStorage, degrades to
  in-memory in private mode) + `PERSISTED_QUERY_KEYS` allowlist +
  `shouldDehydrateQuery` in `frontend/src/lib/queryPersistence.ts`, 24h
  `PERSIST_MAX_AGE`.
- An `OfflineNotice` banner (`src/components/child/OfflineNotice.tsx`) and a
  `useOnline()` hook (`src/hooks/useOnline.ts`, reads `navigator.onLine` +
  window online/offline events) exist. Several `*.offline.test.tsx` suites
  exist (Market, Stock, TradeForm).
- A web manifest exists; native bundles the shell.

## Problem (the Phase-1 gaps the review names)

1. **`onlineManager` is unwired** — TanStack Query falls back to its default
   `navigator.onLine`, which is unreliable in iOS WKWebView (it often reports
   stale/incorrect connectivity), so auto-pause-offline / auto-refetch-on-
   reconnect doesn't fire reliably on native.
2. **Allowlist ↔ key drift** — `PERSISTED_QUERY_KEYS` persists `market-movers`
   (DEAD after Goal 5 — the Simulator now uses `market-snapshot`) and omits
   `market-snapshot`, `quote`, `trades`, `stock-history`. So the Simulator's
   current data does not survive offline.
3. **No freshness label** — when cached prices are shown offline, nothing tells
   the child the data isn't live.

## Non-goals (later phases)

- Phase 2: `vite-plugin-pwa` web app-shell offline; caching question banks for
  offline answering; a sync outbox with idempotency keys for offline writes.
- Phase 3: moving the cache off localStorage to Capacitor Preferences / SQLite.
- Offline *trading* (writes) — trades still require a connection; only reads are
  served offline in Phase 1.

## Architecture (3 units)

### Unit 1 — Connectivity: `@capacitor/network` → `onlineManager`
**Files:** add dep `@capacitor/network`; create `src/lib/connectivity.ts`;
modify `src/main.tsx`, `src/hooks/useOnline.ts`.

- `initConnectivity()` (called once, early in `main.tsx`):
  - `const status = await Network.getStatus(); onlineManager.setOnline(status.connected);`
  - `Network.addListener('networkStatusChange', s => onlineManager.setOnline(s.connected));`
  - Wrapped in try/catch: any failure leaves `onlineManager` at its default
    (`navigator.onLine`-based), so the app still works.
- `@capacitor/network` has a web implementation (uses `navigator.onLine` +
  events), so this is one code path for web + native; on native it uses the OS
  connectivity API (reliable).
- Wiring `onlineManager` gives TanStack Query the behavior we want for free:
  queries pause while offline and **refetch stale data on reconnect**.
- `useOnline()` is refactored to read from `onlineManager`
  (`onlineManager.isOnline()` snapshot + `onlineManager.subscribe` for the
  store subscription) so `OfflineNotice` and TanStack share ONE source of
  truth. The hook's public signature (`(): boolean`) is unchanged.

### Unit 2 — Persistence allowlist fix
**Files:** modify `src/lib/queryPersistence.ts`.

`PERSISTED_QUERY_KEYS` becomes (head segments):
```
modules, module-levels, level-lessons, lesson, module, me, progress,
portfolio, trade-config, market-snapshot, quote, trades, stock-history
```
- Removed: `market-movers` (dead).
- Added: `market-snapshot`, `quote`, `trades`, `stock-history`.
- Still excluded (deliberately): `market-search` (arbitrary search), news /
  news-summary (per-user, AI), coach / tutor (AI), admin / parent.

`shouldDehydrateQuery` is unchanged (still persists only `status === 'success'`
queries whose key head is allowlisted).

### Unit 3 — Offline staleness label
**Files:** create `src/components/child/StaleAsOf.tsx` + a `formatAsOf` util
(co-located or in `src/lib/`); mount it on the two price surfaces
(`src/pages/child/Market.tsx`, `src/pages/child/Stock.tsx`).

- `<StaleAsOf updatedAt={number} />`: renders **only when `!useOnline()`** AND
  `updatedAt > 0`; otherwise renders nothing.
- Copy: `Prices as of {time}` where `time = formatAsOf(updatedAt)` →
  `2:34 PM` if today, else `Jun 26, 2:34 PM` (local time). New i18n key under
  `child.json` (e.g. `simulator.pricesAsOf`).
- `updatedAt` comes from the relevant query's `dataUpdatedAt`
  (the snapshot query on Market; the `['quote', …]` query on Stock).
- The existing `OfflineNotice` banner still announces the offline state app-wide;
  `StaleAsOf` adds the price-specific freshness timestamp.

## Data flow

1. Boot: `initConnectivity()` seeds `onlineManager` from `Network.getStatus()`.
2. Online: queries fetch + persist (allowlisted keys) to localStorage.
3. Connection drops: `networkStatusChange` → `onlineManager.setOnline(false)` →
   TanStack serves cached data, pauses refetches; `OfflineNotice` shows;
   `StaleAsOf` shows "Prices as of <time>" on Market/Stock.
4. Reconnect: `onlineManager.setOnline(true)` → TanStack auto-refetches stale
   allowlisted queries → fresh data + labels disappear.

## Error handling

- Network plugin failure → caught; `onlineManager` stays on its default; app
  unaffected.
- localStorage unusable → existing `createAppPersister()` returns null →
  in-memory cache (no persistence, no crash).
- `StaleAsOf` with `updatedAt` 0/undefined → renders nothing (no cached data to
  caveat).

## Testing

- **connectivity:** `initConnectivity` sets `onlineManager` from a mocked
  `Network.getStatus`, and a `networkStatusChange` event updates it; a thrown
  plugin error is swallowed.
- **useOnline:** reflects `onlineManager` state transitions (online→offline→
  online).
- **allowlist:** `shouldDehydrateQuery` returns true for the four new heads
  (`market-snapshot`/`quote`/`trades`/`stock-history`) and the retained ones,
  and false for `market-movers`, `market-search`, a news/coach key, and a
  non-success query.
- **StaleAsOf:** shows "Prices as of <time>" when offline + `updatedAt>0`;
  hidden when online; hidden when `updatedAt` is 0. `formatAsOf` returns
  time-only for today and date+time otherwise.
- **offline integration:** the existing `Market.offline` / `Stock.offline` /
  `TradeForm.offline` suites still pass (extend Market/Stock to assert the
  `StaleAsOf` label appears while offline).

## Implementation phasing (single plan)

1. `@capacitor/network` dep + `connectivity.ts` + `main.tsx` wiring + `useOnline`
   refactor (+ `npx cap sync`).
2. `PERSISTED_QUERY_KEYS` allowlist fix.
3. `StaleAsOf` component + `formatAsOf` + i18n + mount on Market/Stock.
4. Verify (tsc + lint + vitest + build) → ship (CI → Railway no-op backend;
   manual Vercel; `cap sync` already done) → docs.

## Future (out of scope, noted)

- Phase 2 / Phase 3 as above.
- Offline write queue (trades) — needs the sync outbox + idempotency keys from
  Phase 2.
