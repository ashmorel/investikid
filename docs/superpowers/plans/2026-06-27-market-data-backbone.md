# Market-data Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Redis the authoritative, cron-warmed cache for shared market data (featured quotes + movers) behind a clean `PriceProvider` seam, and serve it from a single `GET /market/snapshot?region=` that the Home screen preloads so the Simulator opens instantly.

**Architecture:** Add a Redis L2 layer to the provider methods that lack it (movers/news/history), add a warm path (`warm_region`) that writes featured+movers with a long TTL, drive it from a `/internal/market-warm/run` cron, expose a `snapshot(region)` service + endpoint that reads the warm cache, and prefetch that endpoint from Home behind online/idle/visited gates.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), `price_cache` (fail-safe sync Redis), yfinance, React 18 + TanStack Query 5 (frontend), GitHub Actions cron.

## Global Constraints

- yfinance stays the data source; all new code sits behind the `PriceProvider` Protocol so a paid API is a later swap. No new paid dependency.
- Reuse the existing fail-safe `app/services/price_cache.py` (`get_json`/`set_json(key, value, ttl)`); never add a second Redis client.
- Cache keys (exact): featured quote `mkt:quote:{TICKER}:{EXCHANGE}` (already used by `_fetch_quote`); movers `mkt:movers:{region}`; news `mkt:news:{sorted "t:e" joined by ","}`; history `mkt:history:{ticker}:{exchange}:{period}`.
- Warm TTL `_WARM_TTL = 1200` (20 min) > cron cadence (10 min). Normal read-path TTLs unchanged (`_CACHE_TTL=300`, `_HISTORY_CACHE_TTL=600`).
- Regions are `Literal["US","GB","HK"]`; `REGION_EXCHANGES` maps them to exchanges; featured-for-region = `_FEATURED` entries whose exchange ∈ `REGION_EXCHANGES[region]`.
- Endpoints never 5xx on a yfinance failure — fall back to static `_FEATURED` prices + empty movers.
- Sync provider calls run off the event loop via `asyncio.to_thread` (matches the #4 convention).
- New `/internal/*` cron POST path must be added to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py` (else the GitHub Actions cron gets 403).
- Backend verify: `ruff check` + `pytest`. Frontend verify: `npx tsc --noEmit` + `npx eslint` + `npx vitest run` + `npm run build`. New UI gets a vitest test.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- `backend/app/services/price_provider.py` (modify) — Redis L2 for movers/news/history; `cache_ttl` param on fetch; `warm_region`; Protocol completion; serialization helpers.
- `backend/app/services/market_warm_service.py` (create) — `warm_all(provider)` orchestrator.
- `backend/app/services/market_snapshot_service.py` (create) — `snapshot(provider, region)`.
- `backend/app/routers/internal.py` (modify) — `POST /internal/market-warm/run`.
- `backend/app/core/csrf.py` (modify) — allowlist the new cron path.
- `backend/app/schemas/simulator.py` (modify) — `MarketSnapshotOut`.
- `backend/app/routers/simulator.py` (modify) — `GET /market/snapshot`.
- `.github/workflows/market-warm-cron.yml` (create) — 10-min cron.
- `frontend/src/api/simulator.ts` (modify) — `getSnapshot` + `MarketSnapshot` type.
- `frontend/src/pages/child/Market.tsx` (modify) — featured from snapshot.
- `frontend/src/components/child/simulator/MarketMovers.tsx` (modify) — movers from snapshot.
- `frontend/src/lib/simulatorVisited.ts` (create) — visited-Simulator flag helpers.
- `frontend/src/pages/child/Home.tsx` (modify) — gated snapshot prefetch.
- Tests alongside each.

---

## Task 1: Provider — Redis L2 for movers/news/history + warm hook

**Files:**
- Modify: `backend/app/services/price_provider.py`
- Test: `backend/tests/test_price_provider_cache.py` (create)

**Interfaces:**
- Consumes: `app.services.price_cache.get_json/set_json`; existing `_FEATURED`, `REGION_EXCHANGES`, `_quote_to_dict`, `_to_yahoo_symbol`.
- Produces:
  - `LivePriceProvider._fetch_quote(ticker, exchange, *, cache_ttl=_CACHE_TTL)` (add kwarg)
  - `LivePriceProvider.get_market_movers` / `get_news` / `get_history` now read/write Redis L2
  - `LivePriceProvider.warm_region(region: str) -> dict` (keys: `region`, `featured`, `movers`)
  - `StaticPriceProvider.warm_region(region: str) -> dict` (no-op zeros)
  - module helpers `_movers_to_dict`, `_movers_from_dict`, `_news_to_dict`, `_news_from_dict`, `_history_to_dict`, `_history_from_dict`
  - `_WARM_TTL = 1200`
  - `PriceProvider` Protocol gains `get_news`, `get_history`, `warm_region`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_price_provider_cache.py
from decimal import Decimal
from unittest.mock import patch

from app.services import price_provider as pp
from app.services.price_provider import (
    LivePriceProvider, MarketMover, PricePoint, StockNewsItem, _WARM_TTL,
)


def _mover(t="AAPL", e="NASDAQ", pct=1.5):
    return MarketMover(ticker=t, exchange=e, name="Apple Inc.",
                       price=Decimal("190.50"), currency="USD", change_percent=pct)


def test_movers_round_trip_serialization():
    raw = {"NASDAQ": {"winners": [_mover()], "losers": []}}
    restored = pp._movers_from_dict(pp._movers_to_dict(raw))
    assert restored == raw


def test_get_market_movers_reads_redis_l2_without_fetch():
    """A warm Redis entry is served without calling yfinance."""
    provider = LivePriceProvider()
    cached = pp._movers_to_dict({"NASDAQ": {"winners": [_mover()], "losers": []}})
    with patch.object(pp.price_cache, "get_json", return_value=cached) as g, \
         patch.object(provider, "_fetch_market_movers") as fetch:
        out = provider.get_market_movers("US")
    g.assert_called_once_with("mkt:movers:US")
    fetch.assert_not_called()
    assert out["NASDAQ"]["winners"][0].ticker == "AAPL"


def test_fetch_market_movers_writes_redis_l2():
    provider = LivePriceProvider()
    with patch.object(provider, "_quote_change", return_value=(Decimal("190.50"), "USD", 1.5)), \
         patch.object(pp.price_cache, "set_json") as s:
        provider._fetch_market_movers("US", cache_ttl=_WARM_TTL)
    # movers key written with the warm TTL
    assert any(c.args[0] == "mkt:movers:US" and c.args[2] == _WARM_TTL for c in s.call_args_list)


def test_warm_region_writes_featured_and_movers_with_warm_ttl():
    provider = LivePriceProvider()
    calls = []
    with patch.object(provider, "_fetch_quote",
                      side_effect=lambda t, e, *, cache_ttl=None: calls.append(("q", t, e, cache_ttl))), \
         patch.object(provider, "_fetch_market_movers",
                      side_effect=lambda r, *, cache_ttl=None: calls.append(("m", r, cache_ttl)) or {}):
        out = provider.warm_region("US")
    assert out["region"] == "US"
    assert out["featured"] > 0 and out["movers"] is True
    assert all(c[-1] == _WARM_TTL for c in calls)  # everything written with warm TTL
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_price_provider_cache.py -q`
Expected: FAIL (`_movers_to_dict`/`warm_region`/`_WARM_TTL` undefined).

- [ ] **Step 3: Implement**

Add near the other TTLs:
```python
_WARM_TTL = 1200  # 20 min — cron-warm entries outlive the ~10-min warm cadence
```

Add serialization helpers (module level, after `_quote_from_dict`):
```python
def _mover_to_dict(m: MarketMover) -> dict:
    return {"ticker": m.ticker, "exchange": m.exchange, "name": m.name,
            "price": str(m.price), "currency": m.currency,
            "change_percent": m.change_percent}


def _mover_from_dict(d: dict) -> MarketMover:
    return MarketMover(ticker=d["ticker"], exchange=d["exchange"], name=d["name"],
                       price=Decimal(d["price"]), currency=d["currency"],
                       change_percent=d["change_percent"])


def _movers_to_dict(raw: dict) -> dict:
    return {exch: {"winners": [_mover_to_dict(m) for m in side["winners"]],
                   "losers": [_mover_to_dict(m) for m in side["losers"]]}
            for exch, side in raw.items()}


def _movers_from_dict(d: dict) -> dict:
    return {exch: {"winners": [_mover_from_dict(m) for m in side["winners"]],
                   "losers": [_mover_from_dict(m) for m in side["losers"]]}
            for exch, side in d.items()}


def _news_to_dict(items: list) -> list:
    return [dict(i.__dict__) for i in items]


def _news_from_dict(d: list) -> list:
    return [StockNewsItem(**i) for i in d]


def _history_to_dict(points: list) -> list:
    return [dict(p.__dict__) for p in points]


def _history_from_dict(d: list) -> list:
    return [PricePoint(**p) for p in d]
```

In `get_market_movers`, after the in-memory L1 block and before `return self._fetch_market_movers(region)`, insert the Redis L2 read:
```python
    def get_market_movers(self, region: str) -> dict[str, dict[str, list[MarketMover]]]:
        cache_key = f"_movers:{region}"
        cached = self._history_cache.get(cache_key)
        if cached:
            if (time.monotonic() - cached[1]) < _CACHE_TTL:
                return cached[0]
            self._schedule_refresh(("movers", region), lambda: self._fetch_market_movers(region))
            return cached[0]

        rkey = f"mkt:movers:{region}"
        l2 = price_cache.get_json(rkey)
        if l2 is not None:
            result = _movers_from_dict(l2)
            self._history_cache[cache_key] = (result, time.monotonic())
            return result

        return self._fetch_market_movers(region)
```

Change `_fetch_market_movers` signature + write Redis:
```python
    def _fetch_market_movers(self, region: str, *, cache_ttl: int = _CACHE_TTL) -> dict[str, dict[str, list[MarketMover]]]:
        ...  # unchanged body until the final cache write
        self._history_cache[cache_key] = (result, time.monotonic())
        price_cache.set_json(f"mkt:movers:{region}", _movers_to_dict(result), cache_ttl)
        return result
```

Add the `cache_ttl` kwarg to `_fetch_quote` and use it on its `set_json`:
```python
    def _fetch_quote(self, ticker: str, exchange: str, *, cache_ttl: int = _CACHE_TTL) -> PriceQuote:
        ...
        price_cache.set_json(rkey, _quote_to_dict(quote), cache_ttl)
        return quote
```

Give `get_news` a Redis L2 (mirror movers): read `mkt:news:{cache_key suffix}`; on miss `_fetch_news`; have `_fetch_news` write `price_cache.set_json(rkey, _news_to_dict(items[:20]), _CACHE_TTL)` where `rkey = "mkt:news:" + ",".join(f"{t}:{e}" for t, e in sorted(holdings))`.

Give `get_history` a Redis L2: `rkey = f"mkt:history:{ticker}:{exchange}:{period}"`; read on entry; on a successful fetch write `price_cache.set_json(rkey, _history_to_dict(points), _HISTORY_CACHE_TTL)`.

Add `warm_region`:
```python
    def warm_region(self, region: str) -> dict:
        """Fetch the region's featured quotes + movers and write them to Redis
        with the long warm TTL so user requests stay cache-warm between crons."""
        exchanges = REGION_EXCHANGES.get(region, [])
        featured = [(t, e) for (t, e) in _FEATURED if e in exchanges]
        for t, e in featured:
            try:
                self._fetch_quote(t, e, cache_ttl=_WARM_TTL)
            except Exception:
                logger.warning("warm: quote failed for %s:%s", t, e)
        try:
            self._fetch_market_movers(region, cache_ttl=_WARM_TTL)
            movers_ok = True
        except Exception:
            logger.warning("warm: movers failed for %s", region)
            movers_ok = False
        return {"region": region, "featured": len(featured), "movers": movers_ok}
```

Add `StaticPriceProvider.warm_region`:
```python
    def warm_region(self, region: str) -> dict:
        return {"region": region, "featured": 0, "movers": False}
```

Extend the Protocol:
```python
class PriceProvider(Protocol):
    def get_quote(self, ticker: str, exchange: str) -> PriceQuote: ...
    def search(self, query: str) -> list[PriceQuote]: ...
    def is_free_tier(self, ticker: str, exchange: str) -> bool: ...
    def get_market_movers(self, region: str) -> dict[str, dict[str, list[MarketMover]]]: ...
    def get_news(self, holdings: list[tuple[str, str]]) -> list[StockNewsItem]: ...
    def get_history(self, ticker: str, exchange: str, period: str = "1mo") -> list[PricePoint]: ...
    def warm_region(self, region: str) -> dict: ...
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_price_provider_cache.py tests/test_simulator.py -q`
Expected: PASS.

- [ ] **Step 5: Ruff + commit**

```bash
cd backend && ../../Local\ Repo/.venv/bin/ruff check app/services/price_provider.py
git add backend/app/services/price_provider.py backend/tests/test_price_provider_cache.py
git commit -m "feat(market): Redis L2 for movers/news/history + warm_region hook (#3)"
```

---

## Task 2: Warm service

**Files:**
- Create: `backend/app/services/market_warm_service.py`
- Test: `backend/tests/test_market_warm_service.py` (create)

**Interfaces:**
- Consumes: `provider.warm_region(region)`; `REGION_EXCHANGES` keys.
- Produces: `warm_all(provider) -> dict` (`{"regions": [<warm_region dicts>]}`), best-effort per region.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_market_warm_service.py
from app.services import market_warm_service


class _FakeProvider:
    def __init__(self): self.calls = []
    def warm_region(self, region):
        self.calls.append(region)
        if region == "GB":
            raise RuntimeError("boom")
        return {"region": region, "featured": 3, "movers": True}


def test_warm_all_is_best_effort_per_region():
    p = _FakeProvider()
    out = market_warm_service.warm_all(p)
    assert set(p.calls) == {"US", "GB", "HK"}          # all attempted
    regions = {r["region"]: r for r in out["regions"]}
    assert regions["US"]["featured"] == 3
    assert regions["GB"]["error"] is True               # failure captured, not raised
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_market_warm_service.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/market_warm_service.py
"""Cron-warm the shared market surfaces (featured quotes + movers) per region so
user requests hit Redis instead of fanning out to yfinance."""
from __future__ import annotations

import logging

from app.services.price_provider import REGION_EXCHANGES

logger = logging.getLogger(__name__)


def warm_all(provider) -> dict:
    """Warm every region. Best-effort: one region's failure never aborts the rest."""
    results = []
    for region in REGION_EXCHANGES:
        try:
            results.append(provider.warm_region(region))
        except Exception as exc:  # noqa: BLE001 — one region must not abort the batch
            logger.warning("warm_all failed for %s: %s", region, exc)
            results.append({"region": region, "error": True})
    return {"regions": results}
```

- [ ] **Step 4: Run tests** — `python -m pytest tests/test_market_warm_service.py -q` → PASS.

- [ ] **Step 5: Ruff + commit**

```bash
cd backend && ../../Local\ Repo/.venv/bin/ruff check app/services/market_warm_service.py
git add backend/app/services/market_warm_service.py backend/tests/test_market_warm_service.py
git commit -m "feat(market): warm_all service for cron-warming regions (#3)"
```

---

## Task 3: Warm cron endpoint + CSRF allowlist + workflow

**Files:**
- Modify: `backend/app/routers/internal.py`, `backend/app/core/csrf.py`
- Create: `.github/workflows/market-warm-cron.yml`
- Test: `backend/tests/test_internal_market_warm.py` (create)

**Interfaces:**
- Consumes: `market_warm_service.warm_all`; `get_price_provider` from `app.routers.simulator`; `settings.cron_secret`.
- Produces: `POST /internal/market-warm/run` (cron-secret gated, CSRF-exempt) → warm summary.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_internal_market_warm.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")
_PATH = "/internal/market-warm/run"


async def test_503_when_secret_unset(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "x"})).status_code == 503


async def test_401_when_secret_wrong(client, monkeypatch):
    """No CSRF token sent — 401 (not 403) proves the path is CSRF-exempt."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "nope"})).status_code == 401


async def test_200_runs_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    monkeypatch.setattr(internal.market_warm_service, "warm_all",
                        lambda provider: {"regions": [{"region": "US", "featured": 3, "movers": True}]})
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    assert r.json()["regions"][0]["region"] == "US"
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_internal_market_warm.py -q` → FAIL (404 → not exempt / no route).

- [ ] **Step 3: Implement**

In `app/core/csrf.py` `_DEFAULT_EXEMPT_PATHS`, add after `"/internal/purge-accounts/run"`:
```python
    "/internal/market-warm/run",
```

In `app/routers/internal.py`, add `market_warm_service` to the `from app.services import (...)` tuple, then add the endpoint (mirror the existing cron-secret guard):
```python
@router.post("/market-warm/run")
async def trigger_market_warm(
    x_cron_secret: str | None = Header(default=None),
):
    """Warm the shared market cache (featured quotes + movers) for all regions."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    from app.routers.simulator import get_price_provider
    provider = get_price_provider()
    return await asyncio.to_thread(market_warm_service.warm_all, provider)
```
Add `import asyncio` at the top of `internal.py` if not present.

Create `.github/workflows/market-warm-cron.yml` (mirror `video-health-cron.yml`):
```yaml
name: Market warm cron

on:
  schedule:
    - cron: "*/10 * * * *"   # every 10 min — keep featured+movers warm in Redis
  workflow_dispatch: {}

permissions:
  contents: read

jobs:
  warm:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      BACKEND_URL: ${{ vars.BACKEND_URL || 'https://investikid.up.railway.app' }}
    steps:
      - name: Trigger market warm
        env:
          CRON_SECRET: ${{ secrets.CRON_SECRET }}
        run: |
          set -uo pipefail
          if [ -z "${CRON_SECRET:-}" ]; then
            echo "::error::CRON_SECRET is empty."; exit 1
          fi
          code=$(curl -sS -o /tmp/resp.txt -w "%{http_code}" -X POST \
            --retry 4 --retry-delay 5 --connect-timeout 15 --max-time 120 \
            -H "X-Cron-Secret: $CRON_SECRET" \
            "$BACKEND_URL/internal/market-warm/run" || echo "000")
          echo "HTTP $code"; cat /tmp/resp.txt 2>/dev/null; echo
          [ "$code" = "200" ] || { echo "::error::market-warm got $code"; exit 1; }
```

- [ ] **Step 4: Run tests** — `python -m pytest tests/test_internal_market_warm.py -q` → PASS.

- [ ] **Step 5: Ruff + commit**

```bash
cd backend && ../../Local\ Repo/.venv/bin/ruff check app/routers/internal.py app/core/csrf.py
git add backend/app/routers/internal.py backend/app/core/csrf.py backend/tests/test_internal_market_warm.py .github/workflows/market-warm-cron.yml
git commit -m "feat(market): /internal/market-warm/run cron + 10-min workflow (#3)"
```

---

## Task 4: Snapshot service + endpoint + schema

**Files:**
- Create: `backend/app/services/market_snapshot_service.py`
- Modify: `backend/app/schemas/simulator.py`, `backend/app/routers/simulator.py`
- Test: `backend/tests/test_market_snapshot.py` (create)

**Interfaces:**
- Consumes: `provider.get_quote`, `provider.get_market_movers`; `_FEATURED`, `REGION_EXCHANGES`; `QuoteOut`, `ExchangeMoversOut`, `MarketMoverOut`.
- Produces: `snapshot(provider, region) -> dict` (`{"region", "featured": [quote dicts], "movers": {exch: {winners, losers}}}`); `MarketSnapshotOut`; `GET /market/snapshot?region=`.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_market_snapshot.py
import pytest
from app.services import market_snapshot_service
from app.services.price_provider import StaticPriceProvider

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_snapshot_featured_is_region_scoped():
    snap = market_snapshot_service.snapshot(StaticPriceProvider(), "GB")
    assert snap["region"] == "GB"
    assert snap["featured"]                                   # non-empty
    assert all(q["exchange"] == "LSE" for q in snap["featured"])  # GB → LSE only
    assert isinstance(snap["movers"], dict)


def test_snapshot_never_raises_on_provider_error():
    class _Boom(StaticPriceProvider):
        def get_market_movers(self, region): raise RuntimeError("yf down")
    snap = market_snapshot_service.snapshot(_Boom(), "US")
    assert snap["movers"] == {}                               # movers degrade to empty
    assert snap["featured"]                                   # featured still served


async def test_snapshot_endpoint_returns_shape(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="snap@example.com", username="snap")
    r = await client.get("/market/snapshot?region=US")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "US" and "featured" in body and "movers" in body


async def test_snapshot_endpoint_rejects_bad_region(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="snap2@example.com", username="snap2")
    assert (await client.get("/market/snapshot?region=MARS")).status_code == 422
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_market_snapshot.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# backend/app/services/market_snapshot_service.py
"""Assemble the Simulator-entry snapshot (region featured quotes + movers) from
the warm cache. Never raises — a provider failure degrades to static fallbacks."""
from __future__ import annotations

import logging

from app.services.price_provider import (
    _FEATURED, REGION_EXCHANGES, _mover_to_dict, _quote_to_dict,
)

logger = logging.getLogger(__name__)


def snapshot(provider, region: str) -> dict:
    exchanges = REGION_EXCHANGES.get(region, [])
    featured_keys = [(t, e) for (t, e) in _FEATURED if e in exchanges]

    featured = []
    for t, e in featured_keys:
        try:
            featured.append(_quote_to_dict(provider.get_quote(t, e)))
        except Exception:
            logger.warning("snapshot: quote failed for %s:%s", t, e)

    try:
        movers_raw = provider.get_market_movers(region)
    except Exception:
        logger.warning("snapshot: movers failed for %s", region)
        movers_raw = {}

    movers = {
        exch: {
            "winners": [_mover_to_dict(m) for m in side.get("winners", [])],
            "losers": [_mover_to_dict(m) for m in side.get("losers", [])],
        }
        for exch, side in movers_raw.items()
    }
    return {"region": region, "featured": featured, "movers": movers}
```

In `app/schemas/simulator.py`, after `ExchangeMoversOut`:
```python
class MarketSnapshotOut(BaseModel):
    region: str
    featured: list[QuoteOut] = []
    movers: dict[str, ExchangeMoversOut] = {}
```

In `app/routers/simulator.py`, import the service + schema and add the endpoint near the other `/market/*` reads:
```python
from app.services import market_snapshot_service
# ... and add MarketSnapshotOut to the schemas import block

@router.get("/market/snapshot", response_model=MarketSnapshotOut)
async def get_market_snapshot(
    region: Literal["US", "GB", "HK"] = "US",
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    snap = await asyncio.to_thread(market_snapshot_service.snapshot, provider, region)
    return MarketSnapshotOut(
        region=snap["region"],
        featured=[QuoteOut(**q) for q in snap["featured"]],
        movers={exch: ExchangeMoversOut(
            winners=[MarketMoverOut(**m) for m in side["winners"]],
            losers=[MarketMoverOut(**m) for m in side["losers"]],
        ) for exch, side in snap["movers"].items()},
    )
```

- [ ] **Step 4: Run tests** — `python -m pytest tests/test_market_snapshot.py -q` → PASS.

- [ ] **Step 5: Ruff + commit**

```bash
cd backend && ../../Local\ Repo/.venv/bin/ruff check app/services/market_snapshot_service.py app/routers/simulator.py app/schemas/simulator.py
git add backend/app/services/market_snapshot_service.py backend/app/schemas/simulator.py backend/app/routers/simulator.py backend/tests/test_market_snapshot.py
git commit -m "feat(market): GET /market/snapshot (region featured + movers) (#3, Goal5 P2)"
```

---

## Task 5: Frontend — snapshot client + Simulator consumes it

**Files:**
- Modify: `frontend/src/api/simulator.ts`, `frontend/src/pages/child/Market.tsx`, `frontend/src/components/child/simulator/MarketMovers.tsx`
- Test: update `frontend/src/pages/child/__tests__/Market.test.tsx`, `frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx`

**Interfaces:**
- Consumes: `GET /market/snapshot?region=`.
- Produces: `simulatorApi.getSnapshot(region) -> Promise<MarketSnapshot>`; `MarketSnapshot` type; query key `['market-snapshot', region]`.

- [ ] **Step 1: Write failing test** (api shape + Market featured from snapshot)

```ts
// add to frontend/src/api/__tests__/... or Market.test.tsx — assert getSnapshot URL
it('getSnapshot calls /market/snapshot with region', async () => {
  const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ region: 'US', featured: [], movers: {} });
  await simulatorApi.getSnapshot('US');
  expect(spy).toHaveBeenCalledWith('/market/snapshot?region=US');
});
```
In `Market.test.tsx`, change the featured mock to drive the snapshot: mock `simulatorApi.getSnapshot` to return `{ region:'GB', featured:[{ticker:'VOD',exchange:'LSE',...}], movers:{} }` and assert the featured stock renders.

- [ ] **Step 2: Run to verify failure** — `npx vitest run src/pages/child/__tests__/Market.test.tsx` → FAIL.

- [ ] **Step 3: Implement**

In `src/api/simulator.ts` add the type + method:
```ts
export interface MarketSnapshot {
  region: RegionCode;
  featured: QuoteOut[];
  movers: Record<string, ExchangeMovers>;
}
// inside simulatorApi:
  getSnapshot: (region: RegionCode) =>
    apiFetch<MarketSnapshot>(`/market/snapshot?region=${region}`),
```

In `Market.tsx`, replace the `['market-featured']` query with a region-scoped snapshot query and derive featured from it:
```tsx
const { data: snapshot, isLoading: featuredLoading } = useQuery<MarketSnapshot | null>({
  queryKey: ['market-snapshot', region],
  queryFn: () => simulatorApi.getSnapshot(region),
  retry: false,
  staleTime: 5 * 60 * 1000,
  gcTime: 10 * 60 * 1000,
});
const featuredStocks = snapshot?.featured ?? null;
```
(Leave the `['market-search', debouncedQuery]` query untouched — arbitrary search still uses `searchMarket`.)

In `MarketMovers.tsx`, replace its `getMarketMovers(region)` query with the same `['market-snapshot', region]` key and read `snapshot.movers` (TanStack dedupes — both components share the one cached snapshot):
```tsx
const { data: snapshot, isLoading } = useQuery<MarketSnapshot | null>({
  queryKey: ['market-snapshot', region],
  queryFn: () => simulatorApi.getSnapshot(region),
  retry: false,
  staleTime: 5 * 60 * 1000,
});
const movers = snapshot?.movers ?? {};
```
Update `MarketMovers.test.tsx` to mock `getSnapshot` instead of `getMarketMovers`.

- [ ] **Step 4: Run tests + tsc + lint**

Run: `cd frontend && npx vitest run src/pages/child/__tests__/Market.test.tsx src/components/child/simulator/__tests__/MarketMovers.test.tsx && npx tsc --noEmit`
Expected: PASS / clean. (Note: api-* and offline baseline failures are pre-existing local-env, ignore.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/simulator.ts frontend/src/pages/child/Market.tsx frontend/src/components/child/simulator/MarketMovers.tsx frontend/src/pages/child/__tests__/Market.test.tsx frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx
git commit -m "feat(market): Simulator featured+movers consume /market/snapshot (Goal5 P2)"
```

---

## Task 6: Frontend — gated Home prefetch + visited flag

**Files:**
- Create: `frontend/src/lib/simulatorVisited.ts`
- Modify: `frontend/src/pages/child/Home.tsx`, `frontend/src/pages/child/Market.tsx` (set the visited flag on mount)
- Test: `frontend/src/lib/__tests__/simulatorVisited.test.ts` (create), update `Home.test.tsx` for the prefetch gate

**Interfaces:**
- Consumes: `simulatorApi.getSnapshot`; `toRegionCode(me.content_region ?? me.country_code)`; `queryClient.prefetchQuery`.
- Produces: `markSimulatorVisited()`, `hasVisitedSimulator(): boolean`.

- [ ] **Step 1: Write failing test**

```ts
// frontend/src/lib/__tests__/simulatorVisited.test.ts
import { markSimulatorVisited, hasVisitedSimulator } from '@/lib/simulatorVisited';

beforeEach(() => localStorage.clear());

it('records and reports a simulator visit', () => {
  expect(hasVisitedSimulator()).toBe(false);
  markSimulatorVisited();
  expect(hasVisitedSimulator()).toBe(true);
});
```

- [ ] **Step 2: Run to verify failure** — `npx vitest run src/lib/__tests__/simulatorVisited.test.ts` → FAIL (module missing).

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/simulatorVisited.ts
const KEY = 'ik:visitedSimulator';

export function markSimulatorVisited(): void {
  try { localStorage.setItem(KEY, '1'); } catch { /* private mode — best effort */ }
}

export function hasVisitedSimulator(): boolean {
  try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
}
```

In `Market.tsx`, call `markSimulatorVisited()` once on mount:
```tsx
useEffect(() => { markSimulatorVisited(); }, []);
```

In `Home.tsx`, add a gated idle prefetch effect (uses the existing `me` query for region):
```tsx
import { useQueryClient } from '@tanstack/react-query';
import { simulatorApi } from '@/api/simulator';
import { toRegionCode } from '@/lib/region';
import { hasVisitedSimulator } from '@/lib/simulatorVisited';
// ...
const queryClient = useQueryClient();
useEffect(() => {
  if (!navigator.onLine || !hasVisitedSimulator()) return;
  const region = toRegionCode(me?.content_region ?? me?.country_code);
  const run = () => queryClient.prefetchQuery({
    queryKey: ['market-snapshot', region],
    queryFn: () => simulatorApi.getSnapshot(region),
    staleTime: 5 * 60 * 1000,
  });
  const ric = (window as any).requestIdleCallback;
  const id = ric ? ric(run) : window.setTimeout(run, 1500);
  return () => { if (ric && (window as any).cancelIdleCallback) (window as any).cancelIdleCallback(id); else clearTimeout(id); };
}, [me?.content_region, me?.country_code, queryClient]);
```
(`me` is the existing `['me']` query in Home; if Home doesn't already read it, add the same `useQuery(['me'], usersApi.me)` the other pages use.)

- [ ] **Step 4: Run tests + tsc + lint + build**

Run: `cd frontend && npx vitest run src/lib/__tests__/simulatorVisited.test.ts src/pages/child/__tests__/Home.test.tsx && npx tsc --noEmit && npx eslint src/pages/child/Home.tsx src/lib/simulatorVisited.ts && npm run build`
Expected: PASS / clean / built. Confirm no new boot-chunk warnings.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/simulatorVisited.ts frontend/src/lib/__tests__/simulatorVisited.test.ts frontend/src/pages/child/Home.tsx frontend/src/pages/child/Market.tsx frontend/src/pages/child/__tests__/Home.test.tsx
git commit -m "feat(market): Home idle-prefetches the market snapshot (Goal5 P1)"
```

---

## Task 7: Full verification + ship + docs

**Files:**
- Modify: `docs/MASTER-BACKLOG.md`, `AGENTS.md` (if it references market data), `.cursor/rules/` (if a simulator/market rule exists)

- [ ] **Step 1: Full backend verify**

Run: `cd backend && ../../Local\ Repo/.venv/bin/ruff check app/ && ../../Local\ Repo/.venv/bin/python -m pytest tests/ -q -k "price_provider or market_warm or market_snapshot or internal_market or simulator"`
Expected: PASS.

- [ ] **Step 2: Full frontend verify**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run src/components/child/simulator src/pages/child/__tests__/Market.test.tsx src/lib && npm run build`
Expected: clean / PASS / built (api-* + *.offline baseline failures are pre-existing local-env — verify they match clean HEAD before dismissing).

- [ ] **Step 3: Push + watch CI**

```bash
git push
# poll: gh run view <id> -R ashmorel/investikid --json conclusion,jobs  (NOT `gh run watch | tail`)
```
Expected: all 6 jobs green → Railway deploys backend.

- [ ] **Step 4: Manual Vercel prod (frontend changed) + native sync**

```bash
cd frontend && vercel --prod --yes
vercel alias set <new-hash>-investikid.vercel.app app.investikid.ai
curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai   # expect 200
npx cap sync ios && npx cap sync android
```

- [ ] **Step 5: Verify warm endpoint live + docs + commit**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.investikid.ai/internal/market-warm/run  # expect 401 (deployed + CSRF-exempt), NOT 404/403
```
Set repo secret `CRON_SECRET` already exists (shared). Optionally trigger the workflow once via `workflow_dispatch`.
Update `docs/MASTER-BACKLOG.md`: mark #3 (caching/cron-warm backbone done; paid-API still an open operator decision) + Goal 5 (P1+P2) shipped. Note `BACKEND_URL`/`CRON_SECRET` already configured.
```bash
git add docs/MASTER-BACKLOG.md AGENTS.md
git commit -m "docs: market-data backbone (#3 hardening + Goal 5) shipped"
git push
```

---

## Notes / decisions baked in

- **yfinance stays**; the `PriceProvider` Protocol is the swap point for a paid API later. A paid provider implements the Protocol and reuses the same keys + warm cron + snapshot — no caller changes.
- **News is not cron-warmed** (per-holdings, per-user) — it only gets a shared Redis L2 (Task 1) + the existing #9 summary cache.
- **Region UX:** the Simulator's featured set becomes region-scoped via the snapshot; the existing region selector drives the `['market-snapshot', region]` key, refetching on change.
- **Prefetch is conservative:** only when online + idle + the child has opened the Simulator before, so non-trading kids never pay for it.
