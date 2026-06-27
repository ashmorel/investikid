# Market-data backbone — design (#3 yfinance hardening + Goal 5 stock preload)

**Date:** 2026-06-27
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Decouple user-facing market requests from yfinance by making Redis the
authoritative cache for all shared market surfaces, kept warm by a cron, and
expose a single `GET /market/snapshot?region=` that the Home screen preloads so
the Simulator opens instantly. yfinance stays the data source for now, behind a
formalized `PriceProvider` seam so a paid quote API is a later config swap.

## Problem (today)

`backend/app/services/price_provider.py` (`LivePriceProvider`):

- `get_quote` / `search` have a Redis L2 layer (`price_cache`) shared across
  instances.
- **`get_market_movers`, `get_news`, `get_history` are L1 in-memory only** — so
  every backend instance independently fans out to yfinance for them. Load on
  the (unofficial, no-SLA, IP-blockable) Yahoo endpoint multiplies by instance
  count, and a cold request blocks on a per-ticker fan-out (movers fan out over
  the ~6–23 featured tickers for a region; news fans out per holding).
- Nothing keeps the hot, shared surfaces (featured quotes, movers) warm, so the
  first user after a TTL expiry pays the full yfinance latency.

This is the root scale/cost/availability risk and the source of the Simulator's
cold-start latency that Goal 5 targets.

## Non-goals

- Adopting a paid quote API in this work (decided: harden yfinance now, seam for
  later). The snapshot endpoint is the plug-in point when that happens.
- Market-hours gating of the warm cron (warm always for now — cheap; revisit if
  cost warrants).
- Changing the per-user news-summary path (already cached per code-review #9).
- Offline support (Goal 4 — separate).

## Architecture (Approach A: cron-warmed Redis snapshot)

```
                ┌─────────────── GitHub Actions cron (~10 min) ───────────────┐
                │  POST /internal/market-warm/run (cron-secret + CSRF-exempt)  │
                └───────────────────────────┬─────────────────────────────────┘
                                            ▼
                         market_warm_service.warm_region(region)
                              fetch featured quotes + movers
                              write Redis (warm TTL ~20 min)
                                            │
                                            ▼
   GET /market/snapshot?region=  ◀── market_snapshot_service.snapshot(region)
        (authed, warm-served)          read warm Redis  ─┐ cold miss → best-effort
                                            ▲             └─ live fetch → static fallback
                                            │
   Home mount: prefetchQuery(['market-snapshot', region])
        gated: online + idle + has-visited-Simulator
                                            │
   Simulator/Market read ['market-snapshot', region]  (featured + movers)
```

## Components

### 1. Provider seam + shared Redis cache
**File:** `backend/app/services/price_provider.py`

- Extend the `PriceProvider` Protocol to include `get_news` and `get_history`
  (already implemented on the concrete classes) so the Protocol is the complete
  swap point for a future paid provider.
- Add a Redis L2 (via `price_cache.get_json`/`set_json`) to `get_market_movers`,
  `get_news`, and `get_history`, mirroring the existing `get_quote` pattern:
  in-memory L1 (SWR) → Redis L2 → yfinance fetch (which writes both layers).
  Stable keys:
  - movers: `mkt:movers:{region}`
  - news: `mkt:news:{sorted "t:e,..." holdings}`
  - history: `mkt:history:{ticker}:{exchange}:{period}`
- TTLs unchanged in spirit (`_CACHE_TTL=300` movers, `_HISTORY_CACHE_TTL=600`),
  but now shared across instances.

### 2. Warm service + cron
**Files:** `backend/app/services/market_warm_service.py` (new),
`backend/app/routers/internal.py`, `backend/app/core/csrf.py`,
`.github/workflows/market-warm-cron.yml` (new).

- `warm_region(provider, region) -> dict`: fetch featured quotes for the
  region's exchanges (`REGION_EXCHANGES`) + `get_market_movers(region)` and
  write each into Redis under the snapshot's keys with a **warm TTL of 20 min**
  (`_WARM_TTL = 1200`), longer than the cron cadence so an occasional missed run
  still leaves a served entry. Returns `{region, featured, movers}` counts.
- `warm_all(provider) -> dict`: loop US/GB/HK, best-effort per region (one
  region's failure never aborts the others), return per-region counts.
- `POST /internal/market-warm/run`: cron-secret gated (same pattern as the other
  internal endpoints), added to `_DEFAULT_EXEMPT_PATHS` in `core/csrf.py`,
  returns the warm summary.
- New workflow `market-warm-cron.yml`: `schedule: */10 * * * *` +
  `workflow_dispatch`, posts to the endpoint with `X-Cron-Secret`, mirrors the
  retry/error handling in `video-health-cron.yml`.

### 3. Snapshot service + endpoint
**Files:** `backend/app/services/market_snapshot_service.py` (new),
`backend/app/routers/simulator.py`, `backend/app/schemas/simulator.py`.

- `snapshot(provider, region) -> dict`: build `{region, featured: [...],
  movers: {...}}`. **Featured = the `_FEATURED` entries whose exchange is in
  `REGION_EXCHANGES[region]`** (the region's curated stocks). Read each featured
  quote via `provider.get_quote` (warm-hit on `mkt:quote:{t}:{e}`, the same key
  the warm cron populates) and movers via `provider.get_market_movers` (warm-hit
  on `mkt:movers:{region}`). Both are read-through, so a cold miss does a
  best-effort live fetch; if yfinance fails, `get_quote` already returns the
  static `_FEATURED` fallback price and movers returns `{}`. The endpoint
  therefore never 5xxs.
- `GET /market/snapshot?region=` (region `Literal["US","GB","HK"]`, default
  `"US"`), `response_model=MarketSnapshotOut` (new schema: `region: str`,
  `featured: list[QuoteOut]`, `movers: dict[str, ExchangeMoversOut]`).
  Authenticated like the other `/market/*` reads.

### 4. Frontend: Simulator consumes snapshot + Home preload
**Files:** `frontend/src/api/simulator.ts`, the Simulator/Market pages,
`frontend/src/pages/child/Home.tsx` (or a small prefetch hook).

- Add `simulatorApi.getSnapshot(region)` → `GET /market/snapshot?region=`.
- Repoint the Simulator/Market featured + movers reads to a single
  `['market-snapshot', region]` query (replacing the separate `['market-featured']`
  and movers queries on the entry surface; per-stock detail pages keep their own
  quote/history calls).
- On Home mount, `queryClient.prefetchQuery(['market-snapshot', region])` gated
  to: `navigator.onLine` + `requestIdleCallback` (fallback `setTimeout`) +
  a `hasVisitedSimulator` flag persisted in `localStorage` (set on first
  Simulator open). So we never prefetch for a child who hasn't used the
  Simulator.
- News-summary unchanged (already cached per #9); optionally idle-prefetched in a
  later pass — out of scope here.

## Data flow

1. Cron (~10 min) → `/internal/market-warm/run` → `warm_all` writes
   `mkt:movers:{region}` and `mkt:quote:{t}:{e}` (featured) into Redis (20-min
   TTL).
2. Home mount (gated) prefetches `['market-snapshot', region]` →
   `GET /market/snapshot` → reads warm Redis → returns instantly.
3. Child opens Simulator → the page reads the already-populated
   `['market-snapshot', region]` cache → instant render.
4. Cold/arbitrary tickers (search, a specific stock's quote/history/news) keep
   the existing read-through path (now Redis-shared for history/news too).

## Error handling

- `price_cache` already no-ops on Redis-down (fail-safe) — every cache read/write
  degrades to the live path.
- Snapshot cold miss: best-effort live fetch; featured falls back to static
  `_FEATURED` prices, movers to `{}`. Endpoint never 5xxs.
- Cron-warm: per-region best-effort; failures logged, non-fatal; the prior warm
  entry's TTL covers a missed cycle.
- Home prefetch: fire-and-forget; a failure is invisible to the user (the
  Simulator falls back to a normal on-entry fetch).

## Testing

**Backend**
- Provider: movers/news/history now read-through + write Redis L2 (mock
  `price_cache`; assert hit returns cached, miss fetches + writes).
- `market_warm_service`: `warm_region` writes the expected keys for each region;
  `warm_all` is best-effort (one region raising doesn't abort the rest).
- `market_snapshot_service`: assembles featured+movers from cache; cold-miss
  fallback returns static prices + empty movers, never raises.
- Endpoints: `GET /market/snapshot?region=` returns the right shape and rejects a
  bad region (422); `/internal/market-warm/run` returns 401 without the secret,
  503 when unset, 200 with it (and is CSRF-exempt — 401 not 403).

**Frontend**
- `getSnapshot` hits `/market/snapshot?region=`.
- Home prefetch fires only when all gates pass (online + visited-Simulator);
  no-ops otherwise.
- Simulator/Market read from `['market-snapshot', region]`.

## Implementation phasing (single plan)

1. Provider: Redis L2 for movers/news/history + Protocol completion.
2. Warm service + `/internal/market-warm/run` + CSRF allowlist + cron workflow.
3. Snapshot service + `GET /market/snapshot` + schema.
4. Frontend: `getSnapshot`, repoint Simulator/Market, Home gated prefetch.
5. Verify (ruff + pytest; tsc + lint + vitest + build) → ship → docs.

## Future (out of scope, seam-ready)

- Swap yfinance for a paid quote API: implement the `PriceProvider` Protocol
  against the new provider, keep the same Redis keys + warm cron + snapshot. No
  caller changes.
- Market-hours-gated warm cron to trim off-hours calls.
- Idle-prefetch the per-user news-summary from Home.
