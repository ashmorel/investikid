# Simulator Ticker Search — Loading State + Redis Cache (Fix #4) — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`

## Background / symptoms

1. **"No stocks found" flash.** In `frontend/src/pages/child/Market.tsx`, while a search request is in flight the query data is `undefined`; the component renders `searchResults ?? []` → empty → it shows *"No stocks found for '…'"* **before** results arrive (no loading-vs-empty distinction). After the debounce + network round-trip the stocks appear, so it looks like nothing happened.
2. **Slow load.** `backend/app/services/price_provider.py::LivePriceProvider` hits Yahoo Finance live (`yfinance`): featured-stock load fetches ~12 quotes; a search does 1 `yf.Search` + up to ~15 quote lookups, sequentially. Caching today is a **per-process in-memory** quote cache (`_CACHE_TTL = 300s`) + a 1-min frontend `staleTime`; both are cold after restart / on a new instance.

## Goal

Make the search feel responsive (clear loading state) and reduce repeat latency via a shared **Redis** cache layered behind the existing in-memory cache, with **graceful fallback** so nothing breaks when Redis is absent (local, CI, tests, or not yet provisioned).

## Section 1 — Frontend (UX + cache longevity)

**`src/pages/child/Market.tsx`:**
- Distinguish loading from empty. When a search is active (`debouncedQuery.length >= 2`) and the query `isFetching` with no usable results yet, render a **loading indicator** (spinner or skeleton rows) with `role="status"` and accessible text (e.g. *"Searching…"*). Only render the *"No stocks found for '…'"* message when the search query has **settled** (`!isFetching`) and the result set is genuinely empty.
- Keep `placeholderData: (prev) => prev` so re-searches keep showing prior results while refetching.
- Raise cache longevity on the search query: `staleTime: 5 * 60 * 1000` and an explicit `gcTime` (e.g. `10 * 60 * 1000`) so results survive navigating away and back. Featured-stocks query keeps its 5-min `staleTime` (optionally add matching `gcTime`).

**`src/hooks/usePortfolio.ts`:**
- Add an explicit `staleTime: 30_000` (currently inherits the global default of 0, so it always refetches).

**Accessibility:** loading indicator announced via `role="status"`; no layout shift that traps focus; touch targets unaffected (≥16px inputs preserved). vitest-axe must pass.

## Section 2 — Backend (Redis cache with graceful fallback)

**New helper `app/services/price_cache.py`:**
- A tiny synchronous Redis wrapper (the project already depends on `redis==5.0.4`; use `redis.from_url(settings.redis_url)`), exposing `get_json(key) -> dict | list | None` and `set_json(key, value, ttl_seconds)`.
- **Lazy + fail-safe:** the client is created on first use; every operation is wrapped in `try/except Exception`. On any error (connection refused, timeout), the helper logs once at debug level, sets a process-level `_disabled = True` flag, and thereafter returns `None`/no-ops so callers fall through to their existing behaviour. No Redis available → behaves exactly as today.
- Keys are namespaced: `mkt:search:{q_normalised}` and `mkt:quote:{ticker}:{exchange}`. `q_normalised` = trimmed, lower-cased query.
- TTLs: search results **120 s**; quotes **300 s** (matches the existing in-memory `_CACHE_TTL`).

**`app/services/price_provider.py::LivePriceProvider`:**
- `search(q)`: before doing any Yahoo work, check `price_cache.get_json("mkt:search:" + norm)`; on hit, reconstruct and return the `SearchResult` list. On miss, run the existing logic, then `set_json(...)` the serialisable result with the 120 s TTL. The existing in-memory L1 cache stays as-is (L1 = in-memory, L2 = Redis).
- `get_quote(ticker, exchange)`: keep the existing in-memory cache as L1; consult Redis as L2 on an L1 miss before calling Yahoo, and write back to both on a live fetch. (Serialise the quote's public fields — ticker, exchange, name, price, currency — to JSON.)
- Behaviour is identical when Redis is disabled; Redis only ever *short-circuits* a live call.

**Config:** `settings.redis_url` already exists (`redis://localhost:6379/0` default). No new config.

**Deliberately out of scope (noted as future perf items):**
- Batching the per-ticker yfinance lookups (`yf.download`/threadpool) — higher risk, separate change.
- Fixing the synchronous yfinance/Redis calls blocking the async event loop — pre-existing, out of scope here.

## Section 3 — Operator setup (runbook)

Add to `docs/deployment-environments.md`: to gain the cross-restart / multi-replica benefit, provision a **Redis** service on Railway per environment and set `REDIS_URL` on the backend. Until then the app runs exactly as today (in-memory only) — the cache layer is a safe no-op without Redis.

## Section 4 — Testing

**Backend pytest** (the existing simulator tests mock the price provider / yfinance; add focused cache tests with a **fake Redis** via monkeypatch — an in-dict stub implementing `get`/`setex`, plus a stub that raises to exercise fallback):
- `price_cache`: `set_json` then `get_json` round-trips; a raising client → `get_json`/`set_json` return `None`/no-op and disable the client (no exception propagates).
- `LivePriceProvider.search`: on a Redis hit, the underlying Yahoo search/quote functions are **not** called and the cached result is returned; on a miss, Yahoo is called once and the result is written to Redis.
- Fallback: with Redis disabled/raising, `search`/`get_quote` behave exactly as the current tests expect (no regression).

**Frontend vitest + vitest-axe** (`Market`):
- While the search query `isFetching` with no results, the loading indicator renders and *"No stocks found"* does **not**.
- After the fetch settles with an empty result, *"No stocks found"* renders.
- After the fetch settles with results, the stock rows render.
- No axe violations in the loading and empty states.

**Verify:** backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. The simulator/Market page is part of the child app (web + iOS shell), but these are logic/UX changes with no native-plugin impact → standard build; a `cap sync` is only needed when bundling for an iOS checkpoint, not for this change to land on `testing`.

## Success criteria

- Typing a valid ticker shows a loading state, never a false "No stocks found", then the result.
- A repeated search for the same query (within TTL) returns from cache without a live Yahoo call (verified in tests; observable as faster repeat loads when Redis is provisioned).
- With no Redis configured, behaviour and tests are unchanged from today.
