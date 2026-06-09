# Simulator Country/Region Selector + Region-Aware Movers — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Backlog ref:** Simulator/Market improvements — **Item 2** (keystone), folds in **Item 1** (`docs/superpowers/specs/2026-06-08-simulator-market-improvements-backlog.md`).
**Scope:** Frontend selector + state + Browse wiring; backend region-aware market movers computed from the curated featured set. **No DB migration. No LLM** (movers are price-only). Does **not** include the broader layout restructure (backlog Items 4/5).

## Goal
Add a **Region selector** (US / UK / HK) at the top of the Browse Stocks page that:
1. defaults to the child's `content_region` (falling back to `country_code`, then `US`),
2. drives **"Today's market movers"** to the selected region's exchanges (replacing the global, US-skewed Yahoo screener),
3. drives the **Browse stock list** ordering (selected region first),
4. **replaces the dead "Exchange" `EduTooltip`** (Item 1).

## Spike outcome (data source)
Decision: **compute region movers from our curated `_FEATURED` universe**, not a live Yahoo screener — safe, recognizable, deterministic, reuses the cached `get_quote` (which already carries `change_percent`). The current `_FEATURED` set is too small (NASDAQ 6 / LSE 4 / HKEX 2 / **no NYSE**), so we **expand it** (below) so movers and Browse are meaningful.

---

## Section 1 — Region selector (frontend)

**Component:** new `frontend/src/components/child/simulator/RegionSelector.tsx`.
- Props: `value: RegionCode`, `onChange: (r: RegionCode) => void`. Renders the three options from the existing `REGIONS` (`src/lib/region.ts`: `{code, flag, label}`) as a **segmented `radiogroup`** of buttons (flag + label).
- A11y: `role="radiogroup"` + `aria-label="Market region"`; each option a `role="radio"` button with `aria-checked`; **left/right arrow keys** move selection (roving tabindex); visible focus ring; each control ≥16px touch (use ≥40px height padding). Semantic Tailwind v4 tokens (brand for selected, muted for unselected) — no raw palette.
- Keep one small optional `?`/`EduTooltip` next to the group label ("A stock market is where shares are bought and sold — different countries have different markets.") to retain the education the old tooltip carried.

**Wiring in `Market.tsx`:**
- Today (lines ~54–58): `me = useQuery(['me'])`; `region = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode`; `priorityExchanges = REGION_EXCHANGES[region]`.
- Change to: `const [selectedRegion, setSelectedRegion] = useState<RegionCode | null>(null)` and a derived `region = selectedRegion ?? (me?.content_region ?? me?.country_code ?? 'US')`. (Seed lazily so the picker defaults to the child's region but the child can switch; **ephemeral** — never written back to `content_region`, which also gates learning modules.)
- Render `<RegionSelector value={region} onChange={setSelectedRegion} />` in the header where the `EduTooltip` was, and remove the `EduTooltip term="Exchange"` usage.
- `priorityExchanges = REGION_EXCHANGES[region]` (drives the existing `groupByExchange(stocks, priorityExchanges)` — unchanged otherwise).

## Section 2 — Region-aware movers (backend)

**Endpoint:** `GET /market/movers` gains an optional query param `region` (`app/routers/simulator.py`):
- `region: Literal["US", "GB", "HK"] = "US"` (invalid → 422 via the Literal; default keeps the old no-param native build working).
- Call `provider.get_market_movers(region)`; response unchanged: `dict[exchange, ExchangeMoversOut]` (`MarketMoverOut` already has `ticker, exchange, name, price, currency, change_percent`).

**Provider** (`app/services/price_provider.py`):
- Add a backend region→exchanges map: `REGION_EXCHANGES = {"US": ["NASDAQ", "NYSE"], "GB": ["LSE"], "HK": ["HKEX"]}`.
- Change `get_market_movers(self, region: str)`:
  - Featured keys whose exchange ∈ `REGION_EXCHANGES[region]`.
  - For each, `get_quote(ticker, exchange)` (cached) → build a `MarketMover` (it carries `change_percent`).
  - Group by exchange. Within each exchange: `winners` = movers sorted by `change_percent` **desc**, taking up to 5 (those with `change_percent >= 0` preferred; if fewer, fill from the top regardless); `losers` = sorted **asc**, up to 5 (prefer `< 0`). Keep the existing 5-minute movers cache, keyed per region (`f"_movers:{region}"`).
  - Empty/Yahoo-down safe: if `get_quote` falls back (flat `change_percent`), still returns the names (a "flat day"); never raises.
- The base/stub provider's `get_market_movers(self, region)` returns `{}`.

**Expand `_FEATURED`** (kid-safe, recognizable; fallback prices approximate — only used when Yahoo is down). Add:
| key | tuple `(name, fallback_price, currency, yahoo_symbol)` |
|---|---|
| `("DIS","NYSE")` | `("Walt Disney Co.", Decimal("95.00"), "USD", "DIS")` |
| `("KO","NYSE")` | `("Coca-Cola Co.", Decimal("62.00"), "USD", "KO")` |
| `("NKE","NYSE")` | `("Nike Inc.", Decimal("78.00"), "USD", "NKE")` |
| `("MCD","NYSE")` | `("McDonald's Corp.", Decimal("290.00"), "USD", "MCD")` |
| `("BARC","LSE")` | `("Barclays plc", Decimal("2.10"), "GBP", "BARC.L")` |
| `("GSK","LSE")` | `("GSK plc", Decimal("15.20"), "GBP", "GSK.L")` |
| `("RR","LSE")` | `("Rolls-Royce Holdings", Decimal("4.20"), "GBP", "RR.L")` |
| `("9988","HKEX")` | `("Alibaba Group", Decimal("75.00"), "HKD", "9988.HK")` |
| `("1810","HKEX")` | `("Xiaomi Corp.", Decimal("17.00"), "HKD", "1810.HK")` |
| `("1211","HKEX")` | `("BYD Company", Decimal("245.00"), "HKD", "1211.HK")` |
| `("0992","HKEX")` | `("Lenovo Group", Decimal("10.00"), "HKD", "0992.HK")` |

Resulting universe: **US 10** (6 NASDAQ + 4 NYSE), **GB 7** (LSE), **HK 6** (HKEX). All names are recognizable family brands. These flow into Browse too (it lists `_FEATURED` on empty search).

## Section 3 — Browse wiring (frontend)
No new logic — `selectedRegion` already feeds `priorityExchanges` into the existing `groupByExchange(stocks, priorityExchanges)` (Section 1). The selected region's exchanges sort first; labels come from the existing `EXCHANGE_GROUP_LABELS` (already maps NASDAQ/NYSE→"US Stocks", LSE→"UK Stocks", HKEX→"Hong Kong Stocks").

## Section 4 — Movers query is region-keyed (frontend)
`MarketMovers.tsx` takes a `region: RegionCode` prop (passed from `Market.tsx`):
- `useQuery({ queryKey: ['market-movers', region], queryFn: () => simulatorApi.getMarketMovers(region) })`.
- `simulatorApi.getMarketMovers(region)` → `apiFetch('/market/movers?region=' + region)` (`src/api/simulator.ts`). Switching region refetches.

---

## Testing
**Frontend (vitest + vitest-axe):**
- `RegionSelector.test.tsx`: renders 3 options; `aria-checked` reflects `value`; clicking / arrow-keying an option fires `onChange`; radiogroup labelled; axe-clean.
- `Market.test.tsx` (extend existing): defaults the selector to the mocked `me.content_region`; switching region updates the movers query (assert `getMarketMovers` called with the new region) and re-orders Browse groups (selected region's section first). The `EduTooltip term="Exchange"` is gone.
- `MarketMovers.test.tsx`: query key includes the region; calls `getMarketMovers(region)`.

**Backend (pytest):**
- `get_market_movers("GB")` returns only LSE movers built from `_FEATURED`, winners sorted desc / losers asc, ≤5 each (mock `get_quote` to return varied `change_percent`).
- `get_market_movers("US")` includes NASDAQ + NYSE.
- `GET /market/movers?region=HK` → 200, only HKEX; `?region=ZZ` → 422; no param → defaults to US.
- Flat/empty-safe: when `get_quote` returns `change_percent == 0` for all, still returns names without raising.

## Verification
Backend: `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` + `pytest`. Frontend: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync` (native picks it up at the next scheduled iOS rebuild).

## Out of scope
Layout restructure (Items 4/5); persisting the region to the profile / `content_region`; live Yahoo region screeners; any LLM; any DB migration; changes to news, tips, currency, or the Simulator dashboard.
