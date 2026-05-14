# Plan 5C: Simulator UI — Paper-Trading Interface

## Goal

Build a paper-trading interface in the child SPA that consumes the 5 existing backend simulator endpoints, giving kids 12–18 a safe, educational environment to practice buying and selling stocks with virtual cash.

## Scope

- No backend changes — all 5 endpoints already exist and are tested
- Three new pages in the child SPA
- Educational tooltips on financial terms throughout
- Multi-currency display with approximate-total footnote
- Two-step trade confirmation (input → review → confirm)
- Static price provider: 12 hardcoded tickers across 3 exchanges (NASDAQ/USD, LSE/GBP, HKEX/HKD)

## Architecture

### New Files

| Path | Responsibility |
|------|---------------|
| `src/api/simulator.ts` | Typed fetch wrappers for all 5 simulator endpoints |
| `src/hooks/usePortfolio.ts` | TanStack Query hook for `GET /portfolio` |
| `src/hooks/useTrades.ts` | TanStack Query hook for `GET /portfolio/trades` |
| `src/pages/child/Simulator.tsx` | Portfolio overview page |
| `src/pages/child/Market.tsx` | Market search/browse page |
| `src/pages/child/Stock.tsx` | Stock detail + trade form page |
| `src/components/child/simulator/CashCard.tsx` | Virtual cash + total value display |
| `src/components/child/simulator/HoldingsTable.tsx` | Holdings with P/L |
| `src/components/child/simulator/TradeHistoryTab.tsx` | Recent trades list |
| `src/components/child/simulator/MarketSearchBar.tsx` | Search input for stocks |
| `src/components/child/simulator/StockHeader.tsx` | Stock name/price/holding summary |
| `src/components/child/simulator/TradeForm.tsx` | Two-step buy/sell form |

### Modified Files

| Path | Change |
|------|--------|
| `src/App.tsx` | Add 3 new routes: `/simulator`, `/simulator/market`, `/simulator/stock/:exchange/:ticker` |
| `src/components/child/TopNav.tsx` | Promote Simulator from `COMING_SOON` to active `<NavLink>` |
| `vite.config.ts` | Add proxy entries for `/market` and `/portfolio` with HTML bypass |

### Routes

| Route | Page | Data |
|-------|------|------|
| `/simulator` | Portfolio overview | `GET /portfolio`, `GET /portfolio/trades` |
| `/simulator/market` | Browse/search stocks | `GET /market/search?q=` |
| `/simulator/stock/:exchange/:ticker` | Stock detail + trade | `GET /market/quote/:exchange/:ticker`, `GET /portfolio`, `POST /portfolio/trades` |

## Page Designs

### 1. Portfolio Overview (`/simulator`)

**Top → bottom:**

1. **Practice-mode badge** — Pill: "Practice Mode — no real money". Muted info banner, not dismissible.

2. **CashCard** — Shows:
   - Virtual cash with currency (e.g. `$10,000.00 USD`)
   - Total portfolio value (cash + holdings market value)
   - Multi-currency footnote: "Total is approximate — converted at today's rates" — shown only when holdings span multiple currencies
   - "Browse stocks" link → `/simulator/market`

3. **HoldingsTable** — Columns: Ticker (with exchange badge), Shares, Avg Buy Price, Current Price, Market Value, Unrealized P/L.
   - P/L colour-coded green/red/neutral, supplemented with `▲`/`▼` icons (not colour-only)
   - Each row clickable → `/simulator/stock/:exchange/:ticker`
   - Educational tooltip on "Unrealized P/L": "This is how much you'd gain or lose if you sold now. It's 'unrealized' because you haven't sold yet."
   - Mobile: card-per-holding (ticker + shares + P/L), tap to navigate
   - Empty state: "You haven't bought any stocks yet. Start by browsing the market!" + CTA to `/simulator/market`

4. **Tab toggle: Holdings (default) | Trade History**
   - Trade history: reverse chronological — date, ticker, buy/sell badge, shares, price, total
   - Educational tooltip on "Trade": "A trade is when you buy or sell shares of a stock."
   - Empty state: "No trades yet."

**Accessibility:** Proper `<table>` semantics, `role="tablist"`/`role="tab"`/`role="tabpanel"` for the toggle.

### 2. Market Search (`/simulator/market`)

**Top → bottom:**

1. **Header** — "Browse Stocks" + caption: "12 stocks available in practice mode"

2. **MarketSearchBar** — Text input with search icon.
   - Loads all 12 tickers on mount via `GET /market/search?q=` (empty string returns all)
   - Client-side filtering as user types (debounced 300ms input update, no server round-trips per keystroke)

3. **Results grid** — Grouped by exchange with headings:
   - "US Stocks (NASDAQ)", "UK Stocks (LSE)", "Hong Kong Stocks (HKEX)"
   - Each result card: Ticker (bold), Exchange badge (colour-coded), Company name, Current price with currency
   - Cards clickable → `/simulator/stock/:exchange/:ticker`

4. **Educational tooltip** on "Exchange": "A stock exchange is a marketplace where stocks are bought and sold. Different countries have different exchanges."

**States:**
- Loading: skeleton cards
- No matches: "No stocks match '{query}'. Try AAPL, VOD, or 0700."
- Error: "Couldn't load stocks. Try again."

**Mobile:** Single-column card layout, search bar sticky at top.

**Accessibility:** `aria-label="Search stocks"` on input, `aria-live="polite"` announcing result count.

### 3. Stock Detail & Trade (`/simulator/stock/:exchange/:ticker`)

**Top → bottom:**

1. **Back link** — "← Back to market" → `/simulator/market`

2. **StockHeader** — From `GET /market/quote/:exchange/:ticker`:
   - Company name (large) + ticker badge + exchange badge
   - Current price, prominent, with currency symbol
   - If user holds shares: "You own 5 shares · Avg buy £11.80"
   - Educational tooltip on "Price": "This is the current price for one share. In practice mode, prices stay the same so you can learn without surprises."

3. **TradeForm** — Two-step, inline (no modal):

   **Step 1 — Input:**
   - Buy/Sell toggle (two-button group). Sell only enabled if user holds shares.
   - Shares input — number, min 1, integer only
   - Sell: "Max" button fills shares owned
   - Live cost preview: "5 shares × $185.42 = **$927.10**"
   - "Review trade" button → step 2
   - Validation: inline errors for insufficient cash/shares

   **Step 2 — Confirmation:**
   - Summary card (grey background):
     - Action: "Buy 5 shares of AAPL"
     - Price per share
     - Total cost
     - Cash after trade
   - Educational tooltip: "Always review your trades before confirming. In real investing, you can't undo a trade!"
   - "Confirm trade" (primary) + "Go back" (secondary)
   - On success: toast "Trade executed!" + navigate to `/simulator`
   - On error (race condition): show error, return to step 1

**States:**
- Quote loading: skeleton header + disabled form
- 404: "Stock not found" + link back
- 403: "This stock isn't available in practice mode"

**Accessibility:** `role="radiogroup"` for Buy/Sell, explicit `<label>` on shares input, `aria-live="assertive"` on confirmation panel, descriptive button labels ("Confirm buy of 5 shares").

## Data Flow

| Hook | Endpoint | Query Key | Refetch Strategy |
|------|----------|-----------|-----------------|
| `usePortfolio()` | `GET /portfolio` | `['portfolio']` | Window focus + after trade mutation |
| `useTrades()` | `GET /portfolio/trades` | `['trades']` | Window focus + after trade mutation |
| `useMarketSearch(q)` | `GET /market/search?q=` | `['market-search']` | Once on mount (stale-time: Infinity for static data) |
| `useQuote(exchange, ticker)` | `GET /market/quote/:exchange/:ticker` | `['quote', exchange, ticker]` | Window focus |

Trade mutation (`POST /portfolio/trades`) invalidates `['portfolio']` and `['trades']` on success.

## Educational Tooltips

| Term | Tooltip Text | Location |
|------|-------------|----------|
| Unrealized P/L | "This is how much you'd gain or lose if you sold now. It's 'unrealized' because you haven't sold yet." | HoldingsTable |
| Trade | "A trade is when you buy or sell shares of a stock." | TradeHistoryTab |
| Exchange | "A stock exchange is a marketplace where stocks are bought and sold. Different countries have different exchanges." | Market page |
| Price | "This is the current price for one share. In practice mode, prices stay the same so you can learn without surprises." | StockHeader |
| Review | "Always review your trades before confirming. In real investing, you can't undo a trade!" | TradeForm step 2 |

Implementation: A reusable `<Tooltip>` wrapper (or use existing Radix `Tooltip` from shadcn/ui) with an info-circle icon trigger.

## Multi-Currency Display

- Each price/value shown with its native currency symbol and code (e.g. `$185.42 USD`, `£12.34 GBP`, `HK$234.00 HKD`)
- `PortfolioOut.total_value` is in the portfolio's base currency (USD by default, from `currency_code`)
- CashCard shows total in base currency
- Footnote appears when at least one holding has a different currency than the portfolio's `currency_code`: "Total is approximate — converted at today's rates"

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

Each component tested in isolation with mocked data:
- `CashCard` — renders cash, total, footnote visibility logic
- `HoldingsTable` — renders rows, P/L colours/icons, empty state, row click navigation
- `TradeHistoryTab` — renders trades, empty state
- `MarketSearchBar` — filtering behaviour
- `StockHeader` — renders quote data, existing holding line
- `TradeForm` — step 1 validation, step 2 review content, confirm calls mutation, error handling

### Integration Test

- TradeForm full flow in jsdom: input shares → review → confirm → assert mutation called with correct `TradeRequest` payload

### E2E (Playwright)

One smoke test covering the happy path:
1. Register + log in as child
2. Navigate to `/simulator` — verify empty portfolio state
3. Click "Browse stocks" → on market page, verify 12 stocks visible
4. Click a stock (e.g. AAPL) → verify stock detail page renders
5. Buy 2 shares → complete two-step flow
6. Verify redirect to `/simulator` with updated portfolio (holding shows, cash reduced)
