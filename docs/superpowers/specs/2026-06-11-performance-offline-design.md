# P-1 — Performance & Offline — Design Spec + Plan

**Date:** 2026-06-11 · **Status:** Approved · **Branch:** `testing`
**Trigger:** user-reported slow stock loading + offline request. Diagnosis: `get_market_movers` fetches ~20 featured quotes from Yahoo **serially** on a 5-min cache (price_provider.py:425-461) → ~10s cold loads; same serial pattern in get_news (per holding), holdings refresh (simulator.py ~600), portfolio_history (~790). Stock.tsx refetches on focus with no staleTime; 1.1MB bundle; no offline behaviour.

## A. Backend speed (one task)
1. **Bounded parallel fan-outs.** Inside `LivePriceProvider`: `get_market_movers` and `get_news` per-ticker loops run via `concurrent.futures.ThreadPoolExecutor(max_workers=8)` (provider stays sync; result order/behaviour identical). Router-level loops (holdings ~600, portfolio_history ~790): bounded `asyncio.gather` over `asyncio.to_thread(get_quote, ...)` with `asyncio.Semaphore(8)`.
2. **Serve-stale-while-revalidate.** `get_quote`/`get_market_movers`/`get_news`: when the in-memory entry is EXPIRED but present, return the stale value immediately and refresh in a daemon background thread (an in-flight key set prevents thundering herd). Fresh-miss (no entry at all) still fetches synchronously. Redis L2 unchanged.
3. **Startup warm.** FastAPI lifespan kicks a fire-and-forget background task priming `get_market_movers` for US/GB/HK (which primes the featured quotes). Failures logged, never block startup.
4. Tests: executor used for movers (≥2 quotes fetched concurrently — timing or spy), SWR returns stale instantly + triggers one refresh (no herd), warm task survives provider errors, all existing provider/simulator tests green.

## B. Frontend speed + offline (one task)
1. **Query-cache persistence.** `@tanstack/react-query-persist-client` + `createSyncStoragePersister` (localStorage; Capacitor persists it). `PersistQueryClientProvider` with `maxAge` ~24h and a `dehydrateOptions.shouldDehydrateQuery` allowlist: modules/module-levels/level-lessons/progress/me/portfolio/market-movers/trade-config (NOT admin, NOT parent dashboards, NOT search). Result: every previously-seen screen renders instantly from disk, revalidates in background, and is readable offline.
2. **Offline awareness.** A `useOnline()` hook (navigator.onLine + online/offline events). Live-price surfaces (Market, Stock, TradeForm) show a friendly inline notice when offline ("You're offline — live prices need the internet. Your lessons still work!") instead of error states; lesson surfaces need no change (persisted cache serves them).
3. **Polish:** `staleTime: 60_000` on Stock.tsx quote/history queries (keep refetchOnWindowFocus); `React.lazy` + Suspense for the `/admin` route tree (admin out of the child bundle).
4. Tests: persister wired (provider renders, allowlist excludes admin keys), useOnline hook, offline notice on Market/Stock, lazy admin route still renders behind Suspense, axe on the notice; full suite + build (assert main chunk shrinks — note size before/after).

## Out of scope
Offline write-queueing (lesson completion sync); HLS/CDN; multi-replica work; service workers (persist-client covers the need with less risk in Capacitor WKWebView).

## Verify
Backend: ruff + pytest (~925). Frontend: tsc, lint, vitest, build. Push `testing`, CI green (pip-audit flake → one re-run).
