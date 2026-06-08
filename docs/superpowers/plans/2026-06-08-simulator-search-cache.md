# Simulator Ticker Search — Loading State + Redis Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the "No stocks found" flash during in-flight searches and add a fail-safe Redis cache layer (behind the existing in-memory cache) so repeat searches/quotes avoid live Yahoo calls.

**Architecture:** Frontend distinguishes loading from empty and lengthens TanStack cache windows. Backend adds a tiny synchronous, fail-safe Redis wrapper (`price_cache`) used as an L2 behind `LivePriceProvider`'s in-memory L1; if Redis is unavailable it silently no-ops so behaviour is identical to today.

**Tech Stack:** React 18 + Vite + TS + TanStack Query + vitest/vitest-axe (frontend); FastAPI + `redis==5.0.4` (sync) + yfinance + pytest (backend).

**Conventions (MANDATORY):**
- Branch `testing`. Explicit `git add <paths>` only — never `git add -A`. Leave the unrelated modified `.gitignore` untouched.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Backend tools (run from `backend/`): pytest `/Users/leeashmore/Local Repo/.venv/bin/pytest`, ruff `/Users/leeashmore/Local Repo/.venv/bin/ruff`.
- Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` where DB is involved; the cache tests here are plain sync unit tests (no DB).

---

### Task 1: `price_cache` — fail-safe sync Redis wrapper

**Files:**
- Create: `backend/app/services/price_cache.py`
- Test: `backend/tests/test_price_cache.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_price_cache.py`

```python
import app.services.price_cache as pc


class _FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def setex(self, key, ttl, value):
        self.store[key] = value


class _RaisingRedis:
    def get(self, key):
        raise RuntimeError("redis down")
    def setex(self, key, ttl, value):
        raise RuntimeError("redis down")


def setup_function():
    pc.reset()


def test_set_then_get_roundtrips(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(pc, "_make_client", lambda: fake)
    pc.set_json("k", {"a": 1, "b": ["x"]}, 60)
    assert pc.get_json("k") == {"a": 1, "b": ["x"]}


def test_missing_key_returns_none(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _FakeRedis())
    assert pc.get_json("absent") is None


def test_raising_client_disables_and_noops(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _RaisingRedis())
    # First op hits the error, swallows it, disables the cache.
    assert pc.get_json("k") is None
    pc.set_json("k", {"a": 1}, 60)  # must not raise
    assert pc._disabled is True


def test_client_build_failure_disables(monkeypatch):
    def boom():
        raise RuntimeError("cannot connect")
    monkeypatch.setattr(pc, "_make_client", boom)
    assert pc.get_json("k") is None
    assert pc._disabled is True
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_price_cache.py -v`
Expected: FAIL (`ModuleNotFoundError: app.services.price_cache`).

- [ ] **Step 3: Implement** `backend/app/services/price_cache.py`

```python
"""Fail-safe synchronous Redis cache for market data.

Used as an optional L2 behind LivePriceProvider's in-memory L1. Every operation
is wrapped so that if Redis is unreachable (local/CI/tests/not provisioned) the
cache silently no-ops and callers fall back to their existing behaviour.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: "redis.Redis | None" = None
_disabled = False


def _make_client() -> "redis.Redis":
    # Patched in tests. socket_timeout keeps a dead Redis from blocking requests.
    return redis.from_url(
        settings.redis_url,
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
        decode_responses=True,
    )


def _get_client() -> "redis.Redis | None":
    global _client, _disabled
    if _disabled:
        return None
    if _client is None:
        try:
            _client = _make_client()
        except Exception:
            logger.debug("price_cache: client init failed; disabling", exc_info=True)
            _disabled = True
            return None
    return _client


def get_json(key: str) -> Any | None:
    global _disabled
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception:
        logger.debug("price_cache: get failed; disabling", exc_info=True)
        _disabled = True
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    global _disabled
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        logger.debug("price_cache: set failed; disabling", exc_info=True)
        _disabled = True


def reset() -> None:
    """Test hook: clear the cached client + disabled flag."""
    global _client, _disabled
    _client = None
    _disabled = False
```

- [ ] **Step 4: Run tests, expect PASS + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_price_cache.py -v` → expect 4 PASS.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/price_cache.py tests/test_price_cache.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/price_cache.py backend/tests/test_price_cache.py
git commit -m "feat(simulator): fail-safe Redis cache helper for market data

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Wire Redis L2 into `LivePriceProvider`

**Files:**
- Modify: `backend/app/services/price_provider.py` (`get_quote`, `search`)
- Test: `backend/tests/test_price_provider_cache.py`

Context — current `get_quote` (L1 only) and `search` (no whole-result cache):
```python
def get_quote(self, ticker, exchange):
    key = (ticker.upper(), exchange.upper())
    cached = self._cache.get(key)
    if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
        return cached[0]
    yf_symbol = _to_yahoo_symbol(ticker, exchange)
    featured = _FEATURED.get(key)
    try:
        info = yf.Ticker(yf_symbol).fast_info
        ...
        live_price = Decimal(str(round(raw_price, 2)))
    except Exception:
        ...
    quote = PriceQuote(ticker=key[0], exchange=key[1], name=name, price=live_price, currency=display_currency)
    self._cache[key] = (quote, time.monotonic())
    return quote

def search(self, query):
    q = query.strip()
    if not q:
        ... featured ...
    try:
        results = yf.Search(q); quotes = results.quotes[:15]
    except Exception:
        quotes = []
    ... build out: list[PriceQuote] ...
    return out
```

First read `backend/tests/test_price_provider.py` to see exactly how `yf.Ticker`/`yf.Search` are monkeypatched; reuse that pattern in the new test.

- [ ] **Step 1: Add (de)serialise helpers + define cache constants** at module level in `price_provider.py` (near `_CACHE_TTL = 300`). Add `_SEARCH_CACHE_TTL = 120`. Add:

```python
def _quote_to_dict(q: "PriceQuote") -> dict:
    return {
        "ticker": q.ticker, "exchange": q.exchange, "name": q.name,
        "price": str(q.price), "currency": q.currency,
    }


def _quote_from_dict(d: dict) -> "PriceQuote":
    return PriceQuote(
        ticker=d["ticker"], exchange=d["exchange"], name=d["name"],
        price=Decimal(d["price"]), currency=d["currency"],
    )
```

Add the import at the top of the file (with the other imports): `from app.services import price_cache`.

- [ ] **Step 2: Write the failing test** `backend/tests/test_price_provider_cache.py`

```python
from decimal import Decimal

import app.services.price_cache as pc
import app.services.price_provider as ppmod
from app.services.price_provider import LivePriceProvider, PriceQuote


class _FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def setex(self, key, ttl, value):
        self.store[key] = value


def setup_function():
    pc.reset()


def test_search_hit_skips_yahoo(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _FakeRedis())
    provider = LivePriceProvider()

    calls = {"search": 0}

    def fake_search(q):
        calls["search"] += 1
        raise AssertionError("yf.Search should not be called on cache hit")

    # Pre-populate the cache via a first run with a stubbed Yahoo search returning one featured-style quote.
    # Simplest: directly seed the redis search key with a serialised result.
    import json
    pc.set_json(
        "mkt:search:nvda",
        [{"ticker": "NVDA", "exchange": "NASDAQ", "name": "NVIDIA Corp.", "price": "525.40", "currency": "USD"}],
        120,
    )
    monkeypatch.setattr(ppmod.yf, "Search", fake_search)

    out = provider.search("NVDA")
    assert calls["search"] == 0
    assert len(out) == 1
    assert isinstance(out[0], PriceQuote)
    assert out[0].ticker == "NVDA"
    assert out[0].price == Decimal("525.40")


def test_search_miss_writes_cache(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(pc, "_make_client", lambda: fake)
    provider = LivePriceProvider()

    # Stub Yahoo search to return no equity results so search() returns featured matches only,
    # and stub get_quote to avoid live calls.
    class _EmptySearch:
        quotes = []
    monkeypatch.setattr(ppmod.yf, "Search", lambda q: _EmptySearch())
    monkeypatch.setattr(
        provider, "get_quote",
        lambda t, e: PriceQuote(ticker=t.upper(), exchange=e, name="X", price=Decimal("1"), currency="USD"),
    )

    out = provider.search("AAPL")
    # AAPL is a featured ticker -> at least one result, and the cache key is now populated.
    assert fake.store.get("mkt:search:aapl") is not None
    assert isinstance(out, list)


def test_search_fallback_when_redis_disabled(monkeypatch):
    # No client -> disabled path; search must still work via existing logic.
    def boom():
        raise RuntimeError("no redis")
    monkeypatch.setattr(pc, "_make_client", boom)
    provider = LivePriceProvider()

    class _EmptySearch:
        quotes = []
    monkeypatch.setattr(ppmod.yf, "Search", lambda q: _EmptySearch())
    monkeypatch.setattr(
        provider, "get_quote",
        lambda t, e: PriceQuote(ticker=t.upper(), exchange=e, name="X", price=Decimal("1"), currency="USD"),
    )
    out = provider.search("AAPL")
    assert isinstance(out, list)  # no exception, behaves as today
```

(Adjust the featured-ticker assumption only if `AAPL`/`NVDA` are no longer in `_FEATURED`; they are per the current file.)

- [ ] **Step 3: Run it, expect FAIL**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_price_provider_cache.py -v`
Expected: FAIL (search doesn't consult Redis yet — hit test still calls through / no key written).

- [ ] **Step 4: Wire `search`** — at the very top of `search`, after `q = query.strip()`, add the L2 lookup for non-empty queries; and before `return out`, write the result. Concretely:

```python
    def search(self, query: str) -> list[PriceQuote]:
        q = query.strip()
        norm = q.lower()
        if q:
            cached = price_cache.get_json(f"mkt:search:{norm}")
            if cached is not None:
                return [_quote_from_dict(d) for d in cached]
        if not q:
            out: list[PriceQuote] = []
            for (ticker, exchange) in _FEATURED:
                try:
                    out.append(self.get_quote(ticker, exchange))
                except Exception:
                    pass
            return out
        # ... existing yf.Search + featured-match logic unchanged, building `out` ...
        price_cache.set_json(f"mkt:search:{norm}", [_quote_to_dict(x) for x in out], _SEARCH_CACHE_TTL)
        return out
```

(Only add the three new pieces: the `norm` line, the cache-hit check, and the `set_json` before the final `return out`. Leave the empty-query branch and the search-building logic exactly as-is.)

- [ ] **Step 5: Wire `get_quote`** — consult Redis on L1 miss, write back on live fetch. After the existing L1 check block and before computing `yf_symbol`, add the L2 read; and after building `quote`, write to Redis as well as L1:

```python
        cached = self._cache.get(key)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

        rkey = f"mkt:quote:{key[0]}:{key[1]}"
        l2 = price_cache.get_json(rkey)
        if l2 is not None:
            quote = _quote_from_dict(l2)
            self._cache[key] = (quote, time.monotonic())
            return quote

        # ... existing yfinance fetch building `quote` ...
        self._cache[key] = (quote, time.monotonic())
        price_cache.set_json(rkey, _quote_to_dict(quote), _CACHE_TTL)
        return quote
```

- [ ] **Step 6: Run tests, expect PASS + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_price_provider_cache.py -v` → expect 3 PASS.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_price_provider.py -v` → expect PASS (no regression).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/price_provider.py tests/test_price_provider_cache.py` → clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/price_provider.py backend/tests/test_price_provider_cache.py
git commit -m "feat(simulator): Redis L2 cache for quotes + search results

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — loading state + cache windows

**Files:**
- Modify: `frontend/src/pages/child/Market.tsx`
- Modify: `frontend/src/hooks/usePortfolio.ts`
- Test: `frontend/src/pages/child/__tests__/Market.test.tsx` (create; or extend an existing Market test if present — check `frontend/src/pages/child/__tests__/` and `frontend/tests/` first)

- [ ] **Step 1: Write the failing test.** First check for an existing Market test and a render-with-providers helper: `cd frontend && grep -rl "Market" src --include=*.test.tsx; grep -rl "QueryClientProvider" src --include=*.test.tsx | head`. Reuse the provider/render pattern. Create `frontend/src/pages/child/__tests__/Market.test.tsx`:

Mock `@/api/simulator` so `simulatorApi.searchMarket` is controllable. Use a manually-resolved promise (deferred) to hold the search in flight, so the component is in `isFetching` with no results.

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';

vi.mock('@/api/simulator', () => ({
  simulatorApi: { searchMarket: vi.fn() },
}));
// ... import simulatorApi (mocked), Market, and renderWithProviders (QueryClientProvider + MemoryRouter) ...

const QUOTE = { ticker: 'NVDA', exchange: 'NASDAQ', name: 'NVIDIA Corp.', price: '525.40', currency: 'USD' };

describe('Market search loading vs empty', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows a loading indicator (not "No stocks found") while a search is in flight', async () => {
    // featured load resolves empty-ish; search hangs.
    let resolveSearch: (v: unknown) => void = () => {};
    (simulatorApi.searchMarket as any).mockImplementation((q: string) =>
      q === '' ? Promise.resolve([]) : new Promise((res) => { resolveSearch = res; }),
    );
    renderWithProviders('/simulator/market'); // use the route Market is mounted at
    await userEvent.type(screen.getByRole('searchbox', { name: /search stocks/i }), 'NVDA');

    // While in flight: loading status visible, no "No stocks found".
    expect(await screen.findByText(/searching/i)).toBeInTheDocument();
    expect(screen.queryByText(/no stocks found/i)).not.toBeInTheDocument();

    resolveSearch([QUOTE]);
    expect(await screen.findByText(/NVIDIA Corp\./)).toBeInTheDocument();
  });

  it('shows "No stocks found" only after a search settles empty', async () => {
    (simulatorApi.searchMarket as any).mockImplementation((q: string) => Promise.resolve([]));
    renderWithProviders('/simulator/market');
    await userEvent.type(screen.getByRole('searchbox', { name: /search stocks/i }), 'ZZZZ');
    expect(await screen.findByText(/no stocks found/i)).toBeInTheDocument();
  });

  it('has no axe violations in the loading state', async () => {
    (simulatorApi.searchMarket as any).mockImplementation((q: string) =>
      q === '' ? Promise.resolve([]) : new Promise(() => {}),
    );
    const { container } = renderWithProviders('/simulator/market');
    await userEvent.type(screen.getByRole('searchbox', { name: /search stocks/i }), 'NVDA');
    await screen.findByText(/searching/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

Note: the search debounce is 400ms. Either wrap the assertion in `waitFor` with a generous timeout, or (preferred) use fake timers / `vi.useFakeTimers()` + advance, OR set `userEvent.setup({ advanceTimers })`. Use whichever the existing tests use; if none, use `await screen.findByText(..., {}, { timeout: 2000 })` to ride out the debounce. The query is enabled at length ≥ 2.

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd frontend && npm run test -- Market`
Expected: FAIL (during fetch the component currently renders "No stocks found", and there is no "Searching" text).

- [ ] **Step 3: Implement the loading/empty split in `Market.tsx`.** Replace the existing empty-state block:

```tsx
      {stocks.length === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          {isSearching
            ? `No stocks found for "${debouncedQuery}". Try a different name or ticker.`
            : 'No stocks available.'}
        </p>
      ) : (
```

with one that shows a loading state while the search is fetching with no results yet:

```tsx
      {stocks.length === 0 && isSearching && searchFetching ? (
        <p role="status" className="mt-6 text-center text-sm text-muted-foreground">
          Searching…
        </p>
      ) : stocks.length === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          {isSearching
            ? `No stocks found for "${debouncedQuery}". Try a different name or ticker.`
            : 'No stocks available.'}
        </p>
      ) : (
```

(Leave the `) : (` results branch and everything after it unchanged.)

- [ ] **Step 4: Lengthen the search cache window** in `Market.tsx` — update the `['market-search', ...]` query options:

```tsx
  const { data: searchResults, isFetching: searchFetching } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-search', debouncedQuery],
    queryFn: () => simulatorApi.searchMarket(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    retry: false,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    placeholderData: (prev) => prev,
  });
```

And add `gcTime: 10 * 60 * 1000,` to the `['market-featured']` query options (keep its existing `staleTime: 5 * 60 * 1000`).

- [ ] **Step 5: Add `staleTime` to `usePortfolio.ts`:**

```typescript
export function usePortfolio() {
  return useQuery<PortfolioOut | null>({
    queryKey: ['portfolio'],
    queryFn: () => simulatorApi.getPortfolio(),
    retry: false,
    refetchOnWindowFocus: true,
    staleTime: 30_000,
  });
}
```

- [ ] **Step 6: Run tests, expect PASS**

Run: `cd frontend && npm run test -- Market` → expect PASS (3).

- [ ] **Step 7: Typecheck + lint touched files**

Run: `npx tsc -b && npm run lint` → expect clean (fix only issues in touched files).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/child/Market.tsx frontend/src/hooks/usePortfolio.ts frontend/src/pages/child/__tests__/Market.test.tsx
git commit -m "fix(simulator): loading state for in-flight search + longer cache windows

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Runbook note + full regression + close-out

**Files:**
- Modify: `docs/deployment-environments.md`

- [ ] **Step 1: Add the Redis operator note** to `docs/deployment-environments.md` (under the Railway env-vars section). Add a bullet:

```markdown
- **Redis (optional, for market-data caching)** — to gain cross-restart / multi-replica caching of simulator quotes + search results, provision a **Redis** service per environment and set `REDIS_URL` on the backend. Without it the app runs exactly as today (in-memory cache only); the Redis layer (`app/services/price_cache.py`) is a safe no-op when Redis is unreachable.
```

- [ ] **Step 2: Commit the doc**

```bash
git add docs/deployment-environments.md
git commit -m "docs(deploy): note optional Redis for market-data caching

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 3: Backend lint + full suite**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: ruff clean; tests pass (incl. the new price_cache + provider-cache tests). If the local Postgres hangs ~90s+, note it as environmental and rely on CI; the new cache tests are non-DB and must pass.

- [ ] **Step 4: Frontend full checks**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green.

- [ ] **Step 5: Push + confirm CI**

```bash
git push origin testing
```
Confirm the CI run for the new HEAD is green (frontend, backend, security, a11y, responsive). No `cap sync` needed.

---

## Out of scope (future perf items, deliberately not done here)
- Batching the per-ticker yfinance lookups (`yf.download` / threadpool).
- Fixing the synchronous yfinance/Redis calls that block the async event loop.

## Self-review notes
- Spec coverage: price_cache helper (Task 1), provider L2 wiring for search + get_quote (Task 2), frontend loading-state + cache windows + usePortfolio (Task 3), runbook + regression (Task 4). All spec sections covered.
- Type consistency: `_quote_to_dict`/`_quote_from_dict` use `price` as `str(Decimal)` consistently; cache keys `mkt:search:{norm}` and `mkt:quote:{ticker}:{exchange}` identical across provider + tests; `price_cache` API `get_json`/`set_json`/`reset`/`_make_client`/`_disabled` consistent across Tasks 1–2.
- Note for implementer: in Task 2 read `tests/test_price_provider.py` first and reuse its yfinance monkeypatch style; in Task 3 reuse the existing render-with-providers helper and the project's debounce/timer handling in tests.
