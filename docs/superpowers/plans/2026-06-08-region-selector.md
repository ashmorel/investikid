# Simulator Country/Region Selector + Region-Aware Movers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Region selector (US/UK/HK) to the Browse Stocks page that defaults to the child's `content_region` and drives region-aware "Today's market movers" (computed from our curated featured set) plus the browse ordering, retiring the dead "Exchange" tooltip.

**Architecture:** Backend computes movers per region from the curated `_FEATURED` map (day-change fetched per ticker via yfinance `fast_info`, *not* the price-display quote cache); `GET /market/movers?region=` selects the region. Frontend adds a `RegionSelector` radiogroup whose value (seeded from `content_region`, ephemeral) feeds the movers query key and the existing `groupByExchange` ordering.

**Tech Stack:** FastAPI + yfinance (backend); React 18 + TS + TanStack Query + Tailwind v4 (frontend); pytest; vitest + vitest-axe.

**Conventions:** No DB migration. No LLM. TDD. Explicit `git add <paths>` only — never `git add -A`; **leave the unrelated working-tree changes alone** (the `.gitignore` mod and the uncommitted iOS build-number files: `frontend/ios/App/App.xcodeproj/project.pbxproj`, `frontend/ios/App/App/Info.plist`, `…/project.xcworkspace/contents.xcworkspacedata`). Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify — backend (from `backend/`): `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest`; frontend (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync`.

**Verified facts:**
- `backend/app/services/price_provider.py`: `class PriceProvider(Protocol)` (l.59); `class StaticPriceProvider` (l.171, stub: `get_market_movers(self)` returns `{}`); `class LivePriceProvider` (l.209, real, uses `self._cache`, `self._history_cache`). `_FEATURED: dict[(ticker,exchange), (name, Decimal fallback_price, currency, yahoo_symbol)]` (l.111). `MarketMover` dataclass has `ticker, exchange, name, price: Decimal, currency, change_percent: float`. `PriceQuote`/`QuoteOut` do **NOT** have `change_percent`. Helpers: `_to_yahoo_symbol(ticker, exchange)`, `_normalise_currency(yf_currency, our_currency) -> (display_currency, needs_pence: bool)`. `_CACHE_TTL = 300`. Live `get_market_movers` currently uses `yf.screen(...)` and caches under `self._history_cache["_movers"]`.
- `backend/app/routers/simulator.py`: `_price_provider = LivePriceProvider()` (l.74); `get_price_provider()` dep (l.77); `@router.get("/market/movers", response_model=dict[str, ExchangeMoversOut])` (l.129) builds `ExchangeMoversOut(winners=[MarketMoverOut(**m.__dict__)...], losers=...)`. Schemas `MarketMoverOut`/`ExchangeMoversOut` in `app/schemas/simulator.py` (MarketMoverOut has `change_percent`).
- `frontend/src/lib/region.ts`: `RegionCode='US'|'GB'|'HK'`, `REGIONS: {code,flag,label}[]`, `REGION_EXCHANGES`.
- `frontend/src/pages/child/Market.tsx`: `me=useQuery(['me'])→authApi.me()`; `region` (l.57) + `priorityExchanges` (l.58); `groupByExchange(stocks, priorityExchanges)` (l.110); heading + `EduTooltip term="Exchange"` (l.114-117); `<MarketMovers />` (l.162) inside `{!isSearching && (…)}`.
- `frontend/src/components/child/simulator/MarketMovers.tsx`: `MarketMovers()` (no props) `useQuery(['market-movers'], () => simulatorApi.getMarketMovers())`.
- `frontend/src/api/simulator.ts`: `getMarketMovers: () => apiFetch<Record<string, ExchangeMovers>>('/market/movers')` (l.175); types `MarketMover`/`ExchangeMovers` (l.77-88).
- Tests: backend `backend/tests/test_simulator.py` (mirror its authenticated client + any `get_price_provider` override). Frontend sim tests in `src/components/child/simulator/__tests__/`; `src/pages/child/__tests__/Market.test.tsx` mocks `@/api/simulator`, `@/api/auth`, and stubs `MarketMovers`/`MarketNews`/`InvestingTips` as `() => null`.

---

## File Structure
- **Modify** `backend/app/services/price_provider.py` — add `REGION_EXCHANGES`, expand `_FEATURED` (+11), add `LivePriceProvider._quote_change`, rewrite `LivePriceProvider.get_market_movers(self, region)`, update `StaticPriceProvider.get_market_movers(self, region)` + `PriceProvider` protocol.
- **Modify** `backend/app/routers/simulator.py` — `region: Literal["US","GB","HK"] = "US"` query param on `/market/movers`.
- **Create** `backend/tests/test_market_movers.py`.
- **Modify** `frontend/src/api/simulator.ts` — `getMarketMovers(region)`.
- **Modify** `frontend/src/components/child/simulator/MarketMovers.tsx` — `region` prop + region-keyed query.
- **Create** `frontend/src/components/child/simulator/RegionSelector.tsx` + `__tests__/RegionSelector.test.tsx`.
- **Modify** `frontend/src/pages/child/Market.tsx` — selector + region state + wiring; remove `EduTooltip`.
- **Modify** `frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx` (create) and `frontend/src/pages/child/__tests__/Market.test.tsx` (extend).

---

## Task 1: Backend — region-aware movers + featured expansion

**Files:** Modify `backend/app/services/price_provider.py`; Create `backend/tests/test_market_movers.py`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_movers.py`:

```python
from decimal import Decimal

from app.services.price_provider import _FEATURED, REGION_EXCHANGES, LivePriceProvider


def _provider(changes: dict[str, float]) -> LivePriceProvider:
    """LivePriceProvider with _quote_change stubbed so no network is hit.
    `changes` maps ticker -> change_percent."""
    p = LivePriceProvider()

    def fake(ticker, exchange, fallback_price, currency):
        return Decimal("100.00"), currency, changes.get(ticker, 0.0)

    p._quote_change = fake  # type: ignore[assignment]
    return p


def test_region_exchanges_map():
    assert REGION_EXCHANGES == {"US": ["NASDAQ", "NYSE"], "GB": ["LSE"], "HK": ["HKEX"]}


def test_featured_expanded():
    for key in [("DIS", "NYSE"), ("KO", "NYSE"), ("NKE", "NYSE"), ("MCD", "NYSE"),
                ("BARC", "LSE"), ("GSK", "LSE"), ("RR", "LSE"),
                ("9988", "HKEX"), ("1810", "HKEX"), ("1211", "HKEX"), ("0992", "HKEX")]:
        assert key in _FEATURED


def test_movers_gb_only_lse_sorted():
    p = _provider({"VOD": 3.0, "BP": -2.0, "HSBA": 1.0, "TSCO": -0.5})
    res = p.get_market_movers("GB")
    assert set(res.keys()) == {"LSE"}
    winners = [m.ticker for m in res["LSE"]["winners"]]
    losers = [m.ticker for m in res["LSE"]["losers"]]
    assert winners[0] == "VOD"            # biggest gainer first
    assert losers[0] == "BP"              # biggest loser first
    assert "VOD" not in losers and "BP" not in winners


def test_movers_us_covers_both_exchanges():
    p = _provider({"AAPL": 5.0, "DIS": -3.0})
    res = p.get_market_movers("US")
    assert "NASDAQ" in res and "NYSE" in res
    assert [m.ticker for m in res["NASDAQ"]["winners"]][0] == "AAPL"
    assert [m.ticker for m in res["NYSE"]["losers"]][0] == "DIS"


def test_movers_hk_only_hkex():
    p = _provider({"0700": 2.0})
    res = p.get_market_movers("HK")
    assert set(res.keys()) == {"HKEX"}


def test_movers_flat_day_is_empty():
    p = _provider({})  # all 0.0 -> in neither winners nor losers
    assert p.get_market_movers("GB") == {}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_market_movers.py -q`
Expected: FAIL — `ImportError` (`REGION_EXCHANGES` undefined) / new `_FEATURED` keys missing / `get_market_movers()` takes no `region`.

- [ ] **Step 3: Add `REGION_EXCHANGES` + expand `_FEATURED`**

In `price_provider.py`, add the new featured rows **inside** the `_FEATURED` dict (before its closing `}`):

```python
    ("DIS", "NYSE"): ("Walt Disney Co.", Decimal("95.00"), "USD", "DIS"),
    ("KO", "NYSE"): ("Coca-Cola Co.", Decimal("62.00"), "USD", "KO"),
    ("NKE", "NYSE"): ("Nike Inc.", Decimal("78.00"), "USD", "NKE"),
    ("MCD", "NYSE"): ("McDonald's Corp.", Decimal("290.00"), "USD", "MCD"),
    ("BARC", "LSE"): ("Barclays plc", Decimal("2.10"), "GBP", "BARC.L"),
    ("GSK", "LSE"): ("GSK plc", Decimal("15.20"), "GBP", "GSK.L"),
    ("RR", "LSE"): ("Rolls-Royce Holdings", Decimal("4.20"), "GBP", "RR.L"),
    ("9988", "HKEX"): ("Alibaba Group", Decimal("75.00"), "HKD", "9988.HK"),
    ("1810", "HKEX"): ("Xiaomi Corp.", Decimal("17.00"), "HKD", "1810.HK"),
    ("1211", "HKEX"): ("BYD Company", Decimal("245.00"), "HKD", "1211.HK"),
    ("0992", "HKEX"): ("Lenovo Group", Decimal("10.00"), "HKD", "0992.HK"),
```

Immediately **after** the `_FEATURED` dict definition, add:

```python
REGION_EXCHANGES: dict[str, list[str]] = {
    "US": ["NASDAQ", "NYSE"],
    "GB": ["LSE"],
    "HK": ["HKEX"],
}
```

- [ ] **Step 4: Implement region-aware movers on `LivePriceProvider`**

Replace `LivePriceProvider.get_market_movers` with the two methods below (the new `_quote_change` helper + the region-aware `get_market_movers`):

```python
    def _quote_change(
        self, ticker: str, exchange: str, fallback_price: Decimal, currency: str
    ) -> tuple[Decimal, str, float]:
        """(price, display_currency, change_percent) for one featured ticker via
        fast_info (last vs previous close). Never raises; 0.0 change on any error."""
        try:
            info = yf.Ticker(_to_yahoo_symbol(ticker, exchange)).fast_info
            last = info["lastPrice"]
            prev = info.get("previousClose")
            display_currency, pence = _normalise_currency(str(info.get("currency", "")), currency)
            if pence:
                last = last / 100
                if prev:
                    prev = prev / 100
            price = Decimal(str(round(last, 2)))
            change = round((last - prev) / prev * 100, 2) if prev else 0.0
            return price, display_currency, change
        except Exception:
            logger.warning("movers quote failed for %s on %s", ticker, exchange)
            return fallback_price, currency, 0.0

    def get_market_movers(self, region: str) -> dict[str, dict[str, list[MarketMover]]]:
        exchanges = REGION_EXCHANGES.get(region, [])
        cache_key = f"_movers:{region}"
        cached = self._history_cache.get(cache_key)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

        movers: list[MarketMover] = []
        for (ticker, exchange), (name, fallback_price, currency, _yf) in _FEATURED.items():
            if exchange not in exchanges:
                continue
            price, disp_currency, change = self._quote_change(
                ticker, exchange, fallback_price, currency
            )
            movers.append(
                MarketMover(
                    ticker=ticker, exchange=exchange, name=name,
                    price=price, currency=disp_currency, change_percent=change,
                )
            )

        result: dict[str, dict[str, list[MarketMover]]] = {}
        for exch in exchanges:
            ex_movers = [m for m in movers if m.exchange == exch]
            winners = sorted(
                [m for m in ex_movers if m.change_percent > 0],
                key=lambda m: m.change_percent, reverse=True,
            )[:5]
            losers = sorted(
                [m for m in ex_movers if m.change_percent < 0],
                key=lambda m: m.change_percent,
            )[:5]
            if winners or losers:
                result[exch] = {"winners": winners, "losers": losers}

        self._history_cache[cache_key] = (result, time.monotonic())
        return result
```

Update `StaticPriceProvider.get_market_movers` signature:

```python
    def get_market_movers(self, region: str) -> dict[str, dict[str, list[MarketMover]]]:
        return {}
```

Update the `PriceProvider` Protocol method:

```python
    def get_market_movers(self, region: str) -> dict[str, dict[str, list[MarketMover]]]: ...
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_market_movers.py -q`
Expected: PASS (6).

- [ ] **Step 6: Lint**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check app/services/price_provider.py tests/test_market_movers.py`
Expected: clean (`ruff check --fix` for import-order if needed).

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/price_provider.py backend/tests/test_market_movers.py
git commit -m "$(cat <<'EOF'
feat(simulator): region-aware market movers from curated featured set

Compute per-region movers (winners>0 desc / losers<0 asc, <=5) from _FEATURED
filtered to REGION_EXCHANGES, day-change via fast_info (not the quote cache).
Expand _FEATURED (NYSE/LSE/HKEX, incl. BYD + Lenovo). No DB, no LLM.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Backend — `region` query param on `/market/movers`

**Files:** Modify `backend/app/routers/simulator.py`; extend `backend/tests/test_market_movers.py`.

- [ ] **Step 1: Write the failing endpoint tests**

Append to `backend/tests/test_market_movers.py` (mirror `tests/test_simulator.py` for the authenticated `client` fixture + `app`/`get_price_provider` import; the snippet below assumes the same `client` fixture used by the market endpoints and `app.dependency_overrides`):

```python
import pytest
from app.routers.simulator import get_price_provider

pytestmark_endpoint = pytest.mark.asyncio(loop_scope="session")


class _FakeMoversProvider:
    def get_market_movers(self, region):
        if region == "GB":
            return {"LSE": {"winners": [], "losers": []}}
        return {}


@pytest.mark.asyncio(loop_scope="session")
async def test_movers_endpoint_region_param(client):
    from app.main import app
    app.dependency_overrides[get_price_provider] = lambda: _FakeMoversProvider()
    try:
        r = await client.get("/market/movers?region=GB")
        assert r.status_code == 200
        assert set(r.json().keys()) == {"LSE"}

        r_default = await client.get("/market/movers")  # defaults to US
        assert r_default.status_code == 200
        assert r_default.json() == {}

        r_bad = await client.get("/market/movers?region=ZZ")
        assert r_bad.status_code == 422
    finally:
        app.dependency_overrides.pop(get_price_provider, None)
```

(If `tests/test_simulator.py` authenticates the market client differently, copy that exact fixture/headers — the market endpoints require `get_current_user`.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_market_movers.py -q -k endpoint`
Expected: FAIL — `?region=ZZ` is currently ignored (no 422); `provider.get_market_movers(region)` called with an arg the current code doesn't pass.

- [ ] **Step 3: Add the param**

In `backend/app/routers/simulator.py`: ensure `from typing import Literal` is imported. Change the movers route:

```python
@router.get("/market/movers", response_model=dict[str, ExchangeMoversOut])
async def get_market_movers(
    region: Literal["US", "GB", "HK"] = "US",
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    raw = provider.get_market_movers(region)
    return {
        exchange: ExchangeMoversOut(
            winners=[MarketMoverOut(**m.__dict__) for m in data.get("winners", [])],
            losers=[MarketMoverOut(**m.__dict__) for m in data.get("losers", [])],
        )
        for exchange, data in raw.items()
    }
```

(Keep the existing param names/order used by the current route — only add `region` as the first query param and pass it to `provider.get_market_movers`.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_market_movers.py -q`
Expected: PASS (all). If a DB-backed client test hangs ~90s it's the local Postgres (CLAUDE.md) — note it and rely on CI.

- [ ] **Step 5: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .
cd /Users/leeashmore/investikid
git add backend/app/routers/simulator.py backend/tests/test_market_movers.py
git commit -m "$(cat <<'EOF'
feat(simulator): /market/movers accepts ?region=US|GB|HK (default US)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Frontend — `getMarketMovers(region)` + region-keyed `MarketMovers`

**Files:** Modify `frontend/src/api/simulator.ts`, `frontend/src/components/child/simulator/MarketMovers.tsx`; Create `frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketMovers } from '../MarketMovers';

vi.mock('@/api/simulator', () => ({
  simulatorApi: { getMarketMovers: vi.fn(() => Promise.resolve({})) },
}));
import { simulatorApi } from '@/api/simulator';

function renderMovers(region: 'US' | 'GB' | 'HK') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MarketMovers region={region} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('MarketMovers', () => {
  it('fetches movers for the given region', async () => {
    renderMovers('GB');
    await screen.findByText(/market movers|loading market movers/i);
    expect(simulatorApi.getMarketMovers).toHaveBeenCalledWith('GB');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- MarketMovers`
Expected: FAIL — `getMarketMovers` is called with no args (current code) and TS errors on the new `region` prop.

- [ ] **Step 3: Add the region param to the API**

In `frontend/src/api/simulator.ts`: add `import { type RegionCode } from '@/lib/region';` (top, with other imports) and change the function:

```ts
  getMarketMovers: (region: RegionCode) =>
    apiFetch<Record<string, ExchangeMovers>>(`/market/movers?region=${region}`),
```

- [ ] **Step 4: Add the region prop to MarketMovers**

In `frontend/src/components/child/simulator/MarketMovers.tsx`: add `import { type RegionCode } from '@/lib/region';` and change the component signature + query:

```tsx
export function MarketMovers({ region }: { region: RegionCode }) {
  const { data, isLoading } = useQuery<Record<string, ExchangeMovers> | null>({
    queryKey: ['market-movers', region],
    queryFn: () => simulatorApi.getMarketMovers(region),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
```

(Leave the rest of the component unchanged.)

- [ ] **Step 5: Run to verify it passes**

Run: `cd frontend && npm run test -- MarketMovers`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/api/simulator.ts frontend/src/components/child/simulator/MarketMovers.tsx frontend/src/components/child/simulator/__tests__/MarketMovers.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): MarketMovers fetches per-region (/market/movers?region=)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Frontend — `RegionSelector` component

**Files:** Create `frontend/src/components/child/simulator/RegionSelector.tsx` + `__tests__/RegionSelector.test.tsx`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/child/simulator/__tests__/RegionSelector.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { RegionSelector } from '../RegionSelector';

describe('RegionSelector', () => {
  it('renders three options and marks the value selected', () => {
    render(<RegionSelector value="GB" onChange={vi.fn()} />);
    expect(screen.getByRole('radiogroup', { name: /market region/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /UK/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /US/i })).toHaveAttribute('aria-checked', 'false');
  });

  it('fires onChange when an option is clicked', async () => {
    const onChange = vi.fn();
    render(<RegionSelector value="US" onChange={onChange} />);
    await userEvent.click(screen.getByRole('radio', { name: /HK/i }));
    expect(onChange).toHaveBeenCalledWith('HK');
  });

  it('moves selection with arrow keys', async () => {
    const onChange = vi.fn();
    render(<RegionSelector value="US" onChange={onChange} />);
    const us = screen.getByRole('radio', { name: /US/i });
    us.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('GB');
  });

  it('has no axe violations', async () => {
    const { container } = render(<RegionSelector value="US" onChange={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- RegionSelector`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/child/simulator/RegionSelector.tsx`:

```tsx
import type { KeyboardEvent } from 'react';
import { REGIONS, type RegionCode } from '@/lib/region';

type Props = { value: RegionCode; onChange: (region: RegionCode) => void };

export function RegionSelector({ value, onChange }: Props) {
  const codes = REGIONS.map((r) => r.code);

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const idx = codes.indexOf(value);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      onChange(codes[(idx + 1) % codes.length]);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      onChange(codes[(idx - 1 + codes.length) % codes.length]);
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label="Market region"
      onKeyDown={onKeyDown}
      className="inline-flex rounded-full border border-brand-200 bg-brand-50 p-0.5"
    >
      {REGIONS.map((r) => {
        const selected = r.code === value;
        return (
          <button
            key={r.code}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(r.code)}
            className={`inline-flex min-h-[40px] items-center gap-1.5 rounded-full px-3 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
              selected ? 'bg-brand-600 text-white' : 'text-brand-700 hover:bg-brand-100'
            }`}
          >
            <span aria-hidden="true">{r.flag}</span>
            <span>{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- RegionSelector`
Expected: PASS (4).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/RegionSelector.tsx frontend/src/components/child/simulator/__tests__/RegionSelector.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): accessible RegionSelector radiogroup (US/UK/HK)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Frontend — wire the selector into Market.tsx

**Files:** Modify `frontend/src/pages/child/Market.tsx`; extend `frontend/src/pages/child/__tests__/Market.test.tsx`.

- [ ] **Step 1: Update the Market test**

In `frontend/src/pages/child/__tests__/Market.test.tsx`:
(a) Replace the `MarketMovers` stub mock so it records its `region` prop:

```tsx
vi.mock('@/components/child/simulator/MarketMovers', () => ({
  MarketMovers: ({ region }: { region: string }) => <div data-testid="movers">movers:{region}</div>,
}));
```

(b) Ensure the `authApi.me` mock returns a `content_region`. Find the existing `vi.mock('@/api/auth', …)` / `me` resolved value and set `content_region: 'GB'` (add the field if absent). Then add these tests inside the existing `describe`:

```tsx
  it('defaults the region selector to the child content_region and wires movers', async () => {
    renderWithProviders('/simulator/market');
    expect(await screen.findByRole('radio', { name: /UK/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('movers')).toHaveTextContent('movers:GB');
    // the dead "Exchange" tooltip is gone
    expect(screen.queryByText(/a stock exchange is a marketplace/i)).toBeNull();
  });

  it('switching region updates the movers query', async () => {
    const user = userEvent.setup();
    renderWithProviders('/simulator/market');
    await user.click(await screen.findByRole('radio', { name: /US/i }));
    expect(screen.getByTestId('movers')).toHaveTextContent('movers:US');
  });
```

(If `renderWithProviders`/`userEvent` aren't already imported in this file, mirror the existing harness — it already uses `QueryClientProvider`, `MemoryRouter`, and `userEvent`.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Market`
Expected: FAIL — no region radios yet; `movers:` has no region; the Exchange tooltip text still present.

- [ ] **Step 3: Wire Market.tsx**

In `frontend/src/pages/child/Market.tsx`:
- Add import: `import { RegionSelector } from '@/components/child/simulator/RegionSelector';`
- **Remove** the `EduTooltip` import (it becomes unused) — delete `import { EduTooltip } from '@/components/child/simulator/EduTooltip';`.
- Add `useState` region state and derive `region` from it (replace the current l.57 `region` derivation):

```tsx
  const [selectedRegion, setSelectedRegion] = useState<RegionCode | null>(null);
  const region = (selectedRegion ?? (me?.content_region ?? me?.country_code ?? 'US')) as RegionCode;
  const priorityExchanges = REGION_EXCHANGES[region] ?? [];
```

- In the heading block, **replace** the `<EduTooltip term="Exchange" … />` element with:

```tsx
        <RegionSelector value={region} onChange={setSelectedRegion} />
```

- Change the movers render from `<MarketMovers />` to `<MarketMovers region={region} />`.

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Market`
Expected: PASS.

- [ ] **Step 5: Typecheck + lint**

Run: `cd frontend && npx tsc -b && npm run lint`
Expected: tsc clean (no unused `EduTooltip`); lint 0 errors (pre-existing warnings only).

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/pages/child/Market.tsx frontend/src/pages/child/__tests__/Market.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): region selector on Browse Stocks drives movers + browse order

Replaces the dead "Exchange" tooltip with a RegionSelector seeded from the
child's content_region (ephemeral); region feeds the movers query + the
existing groupByExchange ordering.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Backend gate**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest -q`
Expected: ruff clean; tests pass (note any local-Postgres hang as environmental).

- [ ] **Step 2: Frontend gate**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green (3 pre-existing fast-refresh warnings unrelated).

- [ ] **Step 3: Push + report**

```bash
cd /Users/leeashmore/investikid && git push origin testing
```
Report CI status on `testing` (frontend + backend jobs). No `cap sync`. Do NOT promote to staging/main. Leave the unrelated `.gitignore` + iOS build-number working-tree files uncommitted.

---

## Self-Review

**1. Spec coverage:** §1 selector → Task 4 (component) + Task 5 (wire, default from `content_region`, ephemeral, retire EduTooltip). §2 region-aware movers + `_FEATURED` expansion + endpoint param → Tasks 1–2 (corrected mechanism: `_quote_change` via fast_info, winners>0 desc / losers<0 asc, per-region cache, `Literal` param). §3 browse wiring → Task 5 (`priorityExchanges` from selected region). §4 region-keyed movers query → Task 3. Testing (FE selector/movers/Market; BE provider + endpoint incl. 422 + default + flat-safe) → Tasks 1–5. ✓

**2. Placeholder scan:** Every code step has complete code. The two "mirror the existing harness" notes (Task 2 auth fixture, Task 5 imports) point at named existing files, not vague gaps. ✓

**3. Type consistency:** `REGION_EXCHANGES`, `_quote_change(ticker, exchange, fallback_price, currency) -> (Decimal, str, float)`, `get_market_movers(self, region: str)` used identically in provider + tests + endpoint. FE `RegionCode`, `RegionSelector({value,onChange})`, `MarketMovers({region})`, `getMarketMovers(region: RegionCode)` consistent across Tasks 3–5. Response shape `dict[exchange, {winners,losers}]` / `Record<string, ExchangeMovers>` unchanged end-to-end. ✓
