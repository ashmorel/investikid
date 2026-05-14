# Simulator UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a paper-trading interface (3 pages) in the child SPA consuming 5 existing backend simulator endpoints, with educational tooltips, multi-currency display, and a two-step trade confirmation flow.

**Architecture:** Frontend-only — no backend changes. Three new routes (`/simulator`, `/simulator/market`, `/simulator/stock/:exchange/:ticker`) each backed by TanStack Query hooks calling a typed API client. Six new components in `src/components/child/simulator/`.

**Tech Stack:** React 18 + TypeScript 5, TanStack Query 5, React Router 6, Tailwind CSS 3, shadcn/ui (Radix Tooltip), lucide-react icons, Vitest + RTL, Playwright E2E.

---

## File Structure

| Path | Responsibility |
|------|---------------|
| `src/api/simulator.ts` | Typed fetch wrappers for 5 backend endpoints |
| `src/hooks/usePortfolio.ts` | TanStack Query hook for `GET /portfolio` |
| `src/hooks/useTrades.ts` | TanStack Query hook for `GET /portfolio/trades` |
| `src/components/child/simulator/CashCard.tsx` | Virtual cash + total value display |
| `src/components/child/simulator/HoldingsTable.tsx` | Holdings with P/L, clickable rows |
| `src/components/child/simulator/TradeHistoryTab.tsx` | Recent trades list |
| `src/components/child/simulator/MarketSearchBar.tsx` | Search input with client-side filtering |
| `src/components/child/simulator/StockHeader.tsx` | Stock name/price/existing holding |
| `src/components/child/simulator/TradeForm.tsx` | Two-step buy/sell form |
| `src/components/child/simulator/EduTooltip.tsx` | Reusable educational tooltip wrapper |
| `src/lib/currency.ts` | Currency formatting utility |
| `src/pages/child/Simulator.tsx` | Portfolio overview page |
| `src/pages/child/Market.tsx` | Market browse/search page |
| `src/pages/child/Stock.tsx` | Stock detail + trade page |

### Modified Files

| Path | Change |
|------|--------|
| `src/App.tsx` | Add 3 route entries inside Shell |
| `src/components/child/TopNav.tsx` | Promote Simulator to active NavLink |
| `vite.config.ts` | Add `/market` and `/portfolio` proxy entries |

---

### Task 1: API Client + Types

**Files:**
- Create: `src/api/simulator.ts`
- Test: `tests/unit/api-simulator.test.ts`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api-simulator.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { simulatorApi } from '@/api/simulator';

beforeEach(() => vi.restoreAllMocks());

function mockFetch(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
}

describe('simulatorApi', () => {
  it('searchMarket calls GET /market/search?q=AAPL', async () => {
    const spy = mockFetch([{ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' }]);
    const result = await simulatorApi.searchMarket('AAPL');
    expect(spy).toHaveBeenCalledWith('/market/search?q=AAPL', expect.objectContaining({ method: 'GET' }));
    expect(result).toEqual([{ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' }]);
  });

  it('getQuote calls GET /market/quote/NASDAQ/AAPL', async () => {
    const spy = mockFetch({ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' });
    await simulatorApi.getQuote('NASDAQ', 'AAPL');
    expect(spy).toHaveBeenCalledWith('/market/quote/NASDAQ/AAPL', expect.objectContaining({ method: 'GET' }));
  });

  it('getPortfolio calls GET /portfolio', async () => {
    const spy = mockFetch({ id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] });
    await simulatorApi.getPortfolio();
    expect(spy).toHaveBeenCalledWith('/portfolio', expect.objectContaining({ method: 'GET' }));
  });

  it('listTrades calls GET /portfolio/trades', async () => {
    const spy = mockFetch([]);
    await simulatorApi.listTrades();
    expect(spy).toHaveBeenCalledWith('/portfolio/trades', expect.objectContaining({ method: 'GET' }));
  });

  it('placeTrade calls POST /portfolio/trades with body', async () => {
    const spy = mockFetch({ id: 't1', ticker: 'AAPL', type: 'buy', shares: '2', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }, 201);
    await simulatorApi.placeTrade({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 2 });
    expect(spy).toHaveBeenCalledWith('/portfolio/trades', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 2 }),
    }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/api-simulator.test.ts`
Expected: FAIL — cannot resolve `@/api/simulator`

- [ ] **Step 3: Write the API client**

Create `src/api/simulator.ts`:

```typescript
import { apiFetch } from './client';

export type QuoteOut = {
  ticker: string;
  exchange: string;
  name: string;
  price: string; // Decimal as string from backend
  currency: string;
};

export type HoldingOut = {
  ticker: string;
  exchange: string;
  shares: string;
  avg_buy_price: string;
  current_price: string;
  market_value: string;
  unrealized_pl: string;
};

export type PortfolioOut = {
  id: string;
  virtual_cash: string;
  currency_code: string;
  total_value: string;
  holdings: HoldingOut[];
};

export type TradeType = 'buy' | 'sell';

export type TradeRequest = {
  ticker: string;
  exchange: string;
  type: TradeType;
  shares: number;
};

export type TradeOut = {
  id: string;
  ticker: string;
  type: TradeType;
  shares: string;
  price: string;
  executed_at: string;
};

export const simulatorApi = {
  searchMarket: (q: string) =>
    apiFetch<QuoteOut[]>(`/market/search?q=${encodeURIComponent(q)}`),

  getQuote: (exchange: string, ticker: string) =>
    apiFetch<QuoteOut>(`/market/quote/${exchange}/${ticker}`),

  getPortfolio: () => apiFetch<PortfolioOut>('/portfolio'),

  listTrades: () => apiFetch<TradeOut[]>('/portfolio/trades'),

  placeTrade: (req: TradeRequest) =>
    apiFetch<TradeOut>('/portfolio/trades', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/api-simulator.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/api/simulator.ts tests/unit/api-simulator.test.ts
git commit -m "feat(simulator): add typed API client for 5 simulator endpoints"
```

---

### Task 2: Currency Formatting Utility

**Files:**
- Create: `src/lib/currency.ts`
- Test: `tests/unit/lib-currency.test.ts`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/lib-currency.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { formatCurrency, getCurrencySymbol } from '@/lib/currency';

describe('formatCurrency', () => {
  it('formats USD', () => {
    expect(formatCurrency('185.42', 'USD')).toBe('$185.42 USD');
  });
  it('formats GBP', () => {
    expect(formatCurrency('12.34', 'GBP')).toBe('£12.34 GBP');
  });
  it('formats HKD', () => {
    expect(formatCurrency('234.00', 'HKD')).toBe('HK$234.00 HKD');
  });
  it('formats unknown currency with code only', () => {
    expect(formatCurrency('100.00', 'JPY')).toBe('¥100.00 JPY');
  });
  it('handles whole numbers', () => {
    expect(formatCurrency('10000', 'USD')).toBe('$10,000.00 USD');
  });
});

describe('getCurrencySymbol', () => {
  it('returns $ for USD', () => expect(getCurrencySymbol('USD')).toBe('$'));
  it('returns £ for GBP', () => expect(getCurrencySymbol('GBP')).toBe('£'));
  it('returns HK$ for HKD', () => expect(getCurrencySymbol('HKD')).toBe('HK$'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/lib-currency.test.ts`
Expected: FAIL — cannot resolve `@/lib/currency`

- [ ] **Step 3: Write implementation**

Create `src/lib/currency.ts`:

```typescript
const SYMBOLS: Record<string, string> = {
  USD: '$',
  GBP: '£',
  HKD: 'HK$',
  EUR: '€',
  JPY: '¥',
};

export function getCurrencySymbol(code: string): string {
  return SYMBOLS[code] ?? code;
}

export function formatCurrency(value: string | number, currencyCode: string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${getCurrencySymbol(currencyCode)}${formatted} ${currencyCode}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/lib-currency.test.ts`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/lib/currency.ts tests/unit/lib-currency.test.ts
git commit -m "feat(simulator): add currency formatting utility"
```

---

### Task 3: TanStack Query Hooks (usePortfolio, useTrades)

**Files:**
- Create: `src/hooks/usePortfolio.ts`
- Create: `src/hooks/useTrades.ts`
- Test: `tests/unit/hooks-usePortfolio.test.tsx`
- Test: `tests/unit/hooks-useTrades.test.tsx`

- [ ] **Step 1: Write the failing test for usePortfolio**

Create `tests/unit/hooks-usePortfolio.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { usePortfolio } from '@/hooks/usePortfolio';

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('usePortfolio', () => {
  it('returns portfolio data from GET /portfolio', async () => {
    const body = { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => usePortfolio(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});
```

- [ ] **Step 2: Write the failing test for useTrades**

Create `tests/unit/hooks-useTrades.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTrades } from '@/hooks/useTrades';

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useTrades', () => {
  it('returns trades from GET /portfolio/trades', async () => {
    const body = [{ id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useTrades(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/hooks-usePortfolio.test.tsx tests/unit/hooks-useTrades.test.tsx`
Expected: FAIL — cannot resolve hooks

- [ ] **Step 4: Write usePortfolio hook**

Create `src/hooks/usePortfolio.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type PortfolioOut } from '@/api/simulator';

export function usePortfolio() {
  return useQuery<PortfolioOut | null>({
    queryKey: ['portfolio'],
    queryFn: () => simulatorApi.getPortfolio(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

- [ ] **Step 5: Write useTrades hook**

Create `src/hooks/useTrades.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type TradeOut } from '@/api/simulator';

export function useTrades() {
  return useQuery<TradeOut[] | null>({
    queryKey: ['trades'],
    queryFn: () => simulatorApi.listTrades(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/hooks-usePortfolio.test.tsx tests/unit/hooks-useTrades.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add src/hooks/usePortfolio.ts src/hooks/useTrades.ts tests/unit/hooks-usePortfolio.test.tsx tests/unit/hooks-useTrades.test.tsx
git commit -m "feat(simulator): add usePortfolio and useTrades query hooks"
```

---

### Task 4: EduTooltip Component

**Files:**
- Create: `src/components/child/simulator/EduTooltip.tsx`
- Test: `tests/unit/child-EduTooltip.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-EduTooltip.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EduTooltip } from '@/components/child/simulator/EduTooltip';

describe('EduTooltip', () => {
  it('renders the term and shows tooltip content on hover', async () => {
    render(
      <EduTooltip term="Unrealized P/L" explanation="This is how much you'd gain or lose if you sold now." />
    );
    expect(screen.getByText('Unrealized P/L')).toBeInTheDocument();
    // The info icon trigger should be present
    expect(screen.getByRole('button', { name: /info about Unrealized P\/L/i })).toBeInTheDocument();
  });

  it('renders children when provided instead of term text', () => {
    render(
      <EduTooltip term="Price" explanation="Current price per share.">
        <span>$185.42</span>
      </EduTooltip>
    );
    expect(screen.getByText('$185.42')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-EduTooltip.test.tsx`
Expected: FAIL — cannot resolve EduTooltip

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/EduTooltip.tsx`:

```typescript
import { Info } from 'lucide-react';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';

type EduTooltipProps = {
  term: string;
  explanation: string;
  children?: React.ReactNode;
};

export function EduTooltip({ term, explanation, children }: EduTooltipProps) {
  return (
    <TooltipProvider>
      <span className="inline-flex items-center gap-1">
        {children ?? <span>{term}</span>}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground"
              aria-label={`Info about ${term}`}
            >
              <Info className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-sm">
            {explanation}
          </TooltipContent>
        </Tooltip>
      </span>
    </TooltipProvider>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-EduTooltip.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/EduTooltip.tsx tests/unit/child-EduTooltip.test.tsx
git commit -m "feat(simulator): add reusable EduTooltip component"
```

---

### Task 5: CashCard Component

**Files:**
- Create: `src/components/child/simulator/CashCard.tsx`
- Test: `tests/unit/child-CashCard.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-CashCard.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CashCard } from '@/components/child/simulator/CashCard';

function renderCard(props: Partial<Parameters<typeof CashCard>[0]> = {}) {
  const defaults = {
    virtualCash: '10000.00',
    totalValue: '12500.00',
    currencyCode: 'USD',
    hasMultiCurrency: false,
  };
  return render(
    <MemoryRouter>
      <CashCard {...defaults} {...props} />
    </MemoryRouter>,
  );
}

describe('CashCard', () => {
  it('renders virtual cash and total value', () => {
    renderCard();
    expect(screen.getByText(/\$10,000\.00 USD/)).toBeInTheDocument();
    expect(screen.getByText(/\$12,500\.00 USD/)).toBeInTheDocument();
  });

  it('shows multi-currency footnote when hasMultiCurrency is true', () => {
    renderCard({ hasMultiCurrency: true });
    expect(screen.getByText(/approximate/i)).toBeInTheDocument();
  });

  it('hides multi-currency footnote when hasMultiCurrency is false', () => {
    renderCard({ hasMultiCurrency: false });
    expect(screen.queryByText(/approximate/i)).not.toBeInTheDocument();
  });

  it('renders Browse stocks link to /simulator/market', () => {
    renderCard();
    const link = screen.getByRole('link', { name: /browse stocks/i });
    expect(link).toHaveAttribute('href', '/simulator/market');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-CashCard.test.tsx`
Expected: FAIL — cannot resolve CashCard

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/CashCard.tsx`:

```typescript
import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/currency';

type CashCardProps = {
  virtualCash: string;
  totalValue: string;
  currencyCode: string;
  hasMultiCurrency: boolean;
};

export function CashCard({ virtualCash, totalValue, currencyCode, hasMultiCurrency }: CashCardProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Virtual Cash</p>
          <p className="text-xl font-semibold">{formatCurrency(virtualCash, currencyCode)}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Total Portfolio Value</p>
          <p className="text-xl font-semibold">{formatCurrency(totalValue, currencyCode)}</p>
        </div>
      </div>
      {hasMultiCurrency && (
        <p className="mt-2 text-xs text-muted-foreground italic">
          Total is approximate — converted at today's rates
        </p>
      )}
      <div className="mt-3">
        <Link
          to="/simulator/market"
          className="text-sm font-medium text-primary hover:underline"
        >
          Browse stocks →
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-CashCard.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/CashCard.tsx tests/unit/child-CashCard.test.tsx
git commit -m "feat(simulator): add CashCard component with multi-currency footnote"
```

---

### Task 6: HoldingsTable Component

**Files:**
- Create: `src/components/child/simulator/HoldingsTable.tsx`
- Test: `tests/unit/child-HoldingsTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-HoldingsTable.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import type { HoldingOut } from '@/api/simulator';

const holdings: HoldingOut[] = [
  { ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' },
  { ticker: 'VOD', exchange: 'LSE', shares: '10', avg_buy_price: '13.00', current_price: '12.34', market_value: '123.40', unrealized_pl: '-6.60' },
];

function renderTable(h: HoldingOut[] = holdings) {
  return render(
    <MemoryRouter>
      <HoldingsTable holdings={h} />
    </MemoryRouter>,
  );
}

describe('HoldingsTable', () => {
  it('renders a row per holding with ticker and exchange badge', () => {
    renderTable();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText('VOD')).toBeInTheDocument();
    expect(screen.getByText('LSE')).toBeInTheDocument();
  });

  it('shows green icon for positive P/L and red for negative', () => {
    renderTable();
    // positive P/L row gets ▲ indicator
    const positiveRow = screen.getByText('27.10').closest('tr')!;
    expect(positiveRow.querySelector('[data-pl="positive"]')).toBeInTheDocument();
    // negative P/L row gets ▼ indicator
    const negativeRow = screen.getByText('-6.60').closest('tr')!;
    expect(negativeRow.querySelector('[data-pl="negative"]')).toBeInTheDocument();
  });

  it('renders rows as links to stock detail page', () => {
    renderTable();
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveAttribute('href', '/simulator/stock/NASDAQ/AAPL');
    expect(links[1]).toHaveAttribute('href', '/simulator/stock/LSE/VOD');
  });

  it('renders empty state when no holdings', () => {
    renderTable([]);
    expect(screen.getByText(/haven't bought any stocks/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /browsing the market/i })).toHaveAttribute('href', '/simulator/market');
  });

  it('includes EduTooltip for Unrealized P/L column header', () => {
    renderTable();
    expect(screen.getByRole('button', { name: /info about Unrealized P\/L/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-HoldingsTable.test.tsx`
Expected: FAIL — cannot resolve HoldingsTable

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/HoldingsTable.tsx`:

```typescript
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import type { HoldingOut } from '@/api/simulator';

// Map exchanges to currencies for display
const EXCHANGE_CURRENCY: Record<string, string> = {
  NASDAQ: 'USD', LSE: 'GBP', HKEX: 'HKD',
};

type Props = { holdings: HoldingOut[] };

export function HoldingsTable({ holdings }: Props) {
  if (holdings.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center">
        <p className="text-sm text-muted-foreground">
          You haven't bought any stocks yet. Start by{' '}
          <Link to="/simulator/market" className="font-medium text-primary hover:underline">
            browsing the market
          </Link>!
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Ticker</th>
            <th className="px-3 py-2 text-right font-medium">Shares</th>
            <th className="px-3 py-2 text-right font-medium">Avg Buy</th>
            <th className="px-3 py-2 text-right font-medium">Current</th>
            <th className="px-3 py-2 text-right font-medium">Value</th>
            <th className="px-3 py-2 text-right font-medium">
              <EduTooltip
                term="Unrealized P/L"
                explanation="This is how much you'd gain or lose if you sold now. It's 'unrealized' because you haven't sold yet."
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const pl = parseFloat(h.unrealized_pl);
            const plSign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
            const currency = EXCHANGE_CURRENCY[h.exchange] ?? 'USD';
            return (
              <tr key={`${h.exchange}-${h.ticker}`} className="border-b last:border-0 hover:bg-muted/30">
                <td className="px-3 py-2" colSpan={6}>
                  <Link
                    to={`/simulator/stock/${h.exchange}/${h.ticker}`}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{h.ticker}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{h.exchange}</span>
                    </span>
                    <span className="flex items-center gap-4 text-right">
                      <span>{h.shares}</span>
                      <span>{formatCurrency(h.avg_buy_price, currency)}</span>
                      <span>{formatCurrency(h.current_price, currency)}</span>
                      <span>{formatCurrency(h.market_value, currency)}</span>
                      <span className={`flex items-center gap-1 ${plSign === 'positive' ? 'text-green-600' : plSign === 'negative' ? 'text-red-600' : ''}`}>
                        {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
                        {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
                        {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
                        {h.unrealized_pl}
                      </span>
                    </span>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-HoldingsTable.test.tsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/HoldingsTable.tsx tests/unit/child-HoldingsTable.test.tsx
git commit -m "feat(simulator): add HoldingsTable with P/L colours and edu tooltip"
```

---

### Task 7: TradeHistoryTab Component

**Files:**
- Create: `src/components/child/simulator/TradeHistoryTab.tsx`
- Test: `tests/unit/child-TradeHistoryTab.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-TradeHistoryTab.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';
import type { TradeOut } from '@/api/simulator';

const trades: TradeOut[] = [
  { id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T10:30:00Z' },
  { id: 't2', ticker: 'VOD', type: 'sell', shares: '3', price: '12.34', executed_at: '2026-05-04T09:00:00Z' },
];

describe('TradeHistoryTab', () => {
  it('renders each trade with ticker, type badge, shares, and price', () => {
    render(<TradeHistoryTab trades={trades} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Buy')).toBeInTheDocument();
    expect(screen.getByText('VOD')).toBeInTheDocument();
    expect(screen.getByText('Sell')).toBeInTheDocument();
  });

  it('renders empty state when no trades', () => {
    render(<TradeHistoryTab trades={[]} />);
    expect(screen.getByText(/no trades yet/i)).toBeInTheDocument();
  });

  it('includes EduTooltip for Trade term', () => {
    render(<TradeHistoryTab trades={trades} />);
    expect(screen.getByRole('button', { name: /info about Trade/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-TradeHistoryTab.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/TradeHistoryTab.tsx`:

```typescript
import { EduTooltip } from './EduTooltip';
import type { TradeOut } from '@/api/simulator';

type Props = { trades: TradeOut[] };

export function TradeHistoryTab({ trades }: Props) {
  return (
    <div>
      <div className="mb-2">
        <EduTooltip
          term="Trade"
          explanation="A trade is when you buy or sell shares of a stock."
        />
      </div>
      {trades.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">No trades yet.</p>
      ) : (
        <div className="space-y-2">
          {trades.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t.ticker}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  t.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {t.type === 'buy' ? 'Buy' : 'Sell'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span>{t.shares} shares</span>
                <span>@ {t.price}</span>
                <span>{new Date(t.executed_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-TradeHistoryTab.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/TradeHistoryTab.tsx tests/unit/child-TradeHistoryTab.test.tsx
git commit -m "feat(simulator): add TradeHistoryTab component"
```

---

### Task 8: Portfolio Overview Page (Simulator.tsx)

**Files:**
- Create: `src/pages/child/Simulator.tsx`
- Test: `tests/unit/child-Simulator.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-Simulator.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Simulator from '@/pages/child/Simulator';

beforeEach(() => vi.restoreAllMocks());

function mockFetchRoutes(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url.startsWith(path)) return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response('not mocked', { status: 500 });
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Simulator />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Simulator page', () => {
  it('renders practice mode badge', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/practice mode/i)).toBeInTheDocument();
    });
  });

  it('shows empty holdings state and CashCard', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/\$10,000\.00 USD/)).toBeInTheDocument();
      expect(screen.getByText(/haven't bought any stocks/i)).toBeInTheDocument();
    });
  });

  it('renders holdings when present', async () => {
    mockFetchRoutes({
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings: [{ ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' }],
      },
      '/portfolio/trades': [{ id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
  });

  it('switches between Holdings and Trade History tabs', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [{ id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }],
    });
    renderPage();
    await waitFor(() => expect(screen.getByRole('tab', { name: /holdings/i })).toBeInTheDocument());

    const historyTab = screen.getByRole('tab', { name: /trade history/i });
    await userEvent.click(historyTab);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('Buy')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Simulator.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/pages/child/Simulator.tsx`:

```typescript
import { useState } from 'react';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useTrades } from '@/hooks/useTrades';
import { CashCard } from '@/components/child/simulator/CashCard';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';

type Tab = 'holdings' | 'history';

export default function Simulator() {
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: trades } = useTrades();
  const [activeTab, setActiveTab] = useState<Tab>('holdings');

  if (portfolioLoading || !portfolio) {
    return <div className="mx-auto max-w-4xl p-6"><p className="text-sm text-muted-foreground">Loading portfolio…</p></div>;
  }

  const holdings = portfolio.holdings ?? [];
  const hasMultiCurrency = holdings.some(
    (h) => {
      const hCurrency = h.exchange === 'LSE' ? 'GBP' : h.exchange === 'HKEX' ? 'HKD' : 'USD';
      return hCurrency !== portfolio.currency_code;
    }
  );

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
        🎮 Practice Mode — no real money
      </div>

      <CashCard
        virtualCash={portfolio.virtual_cash}
        totalValue={portfolio.total_value}
        currencyCode={portfolio.currency_code}
        hasMultiCurrency={hasMultiCurrency}
      />

      <div className="mt-6">
        <div role="tablist" className="mb-3 flex gap-1 border-b">
          <button
            role="tab"
            aria-selected={activeTab === 'holdings'}
            onClick={() => setActiveTab('holdings')}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'holdings' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Holdings
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'history' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Trade History
          </button>
        </div>

        <div role="tabpanel">
          {activeTab === 'holdings' ? (
            <HoldingsTable holdings={holdings} />
          ) : (
            <TradeHistoryTab trades={trades ?? []} />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Simulator.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pages/child/Simulator.tsx tests/unit/child-Simulator.test.tsx
git commit -m "feat(simulator): add portfolio overview page with tabs"
```

---

### Task 9: MarketSearchBar Component

**Files:**
- Create: `src/components/child/simulator/MarketSearchBar.tsx`
- Test: `tests/unit/child-MarketSearchBar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-MarketSearchBar.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarketSearchBar } from '@/components/child/simulator/MarketSearchBar';

describe('MarketSearchBar', () => {
  it('renders search input with label', () => {
    render(<MarketSearchBar value="" onChange={vi.fn()} />);
    expect(screen.getByRole('searchbox', { name: /search stocks/i })).toBeInTheDocument();
  });

  it('calls onChange when user types', async () => {
    const onChange = vi.fn();
    render(<MarketSearchBar value="" onChange={onChange} />);
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'A');
    expect(onChange).toHaveBeenCalledWith('A');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-MarketSearchBar.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/MarketSearchBar.tsx`:

```typescript
import { Search } from 'lucide-react';

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function MarketSearchBar({ value, onChange }: Props) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        type="search"
        role="searchbox"
        aria-label="Search stocks"
        placeholder="Search by name or ticker…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border bg-background py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-MarketSearchBar.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/MarketSearchBar.tsx tests/unit/child-MarketSearchBar.test.tsx
git commit -m "feat(simulator): add MarketSearchBar component"
```

---

### Task 10: Market Page

**Files:**
- Create: `src/pages/child/Market.tsx`
- Test: `tests/unit/child-Market.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-Market.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Market from '@/pages/child/Market';
import type { QuoteOut } from '@/api/simulator';

beforeEach(() => vi.restoreAllMocks());

const allQuotes: QuoteOut[] = [
  { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
  { ticker: 'MSFT', exchange: 'NASDAQ', name: 'Microsoft Corp.', price: '420.10', currency: 'USD' },
  { ticker: 'VOD', exchange: 'LSE', name: 'Vodafone Group', price: '12.34', currency: 'GBP' },
  { ticker: '0700', exchange: 'HKEX', name: 'Tencent Holdings', price: '350.00', currency: 'HKD' },
];

function renderPage() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(allQuotes), { status: 200 }),
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Market />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Market page', () => {
  it('renders all stocks grouped by exchange', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
      expect(screen.getByText('Tencent Holdings')).toBeInTheDocument();
    });
    // Exchange group headings
    expect(screen.getByText(/US Stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/UK Stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/Hong Kong Stocks/i)).toBeInTheDocument();
  });

  it('filters stocks client-side as user types', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'vod');
    expect(screen.queryByText('Apple Inc.')).not.toBeInTheDocument();
    expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
  });

  it('shows no-matches message when filter yields nothing', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'xyz');
    expect(screen.getByText(/no stocks match/i)).toBeInTheDocument();
  });

  it('each stock card links to stock detail page', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const aaplLink = screen.getByText('Apple Inc.').closest('a');
    expect(aaplLink).toHaveAttribute('href', '/simulator/stock/NASDAQ/AAPL');
  });

  it('includes EduTooltip for Exchange', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole('button', { name: /info about Exchange/i })).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Market.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/pages/child/Market.tsx`:

```typescript
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type QuoteOut } from '@/api/simulator';
import { MarketSearchBar } from '@/components/child/simulator/MarketSearchBar';
import { EduTooltip } from '@/components/child/simulator/EduTooltip';
import { formatCurrency } from '@/lib/currency';

const EXCHANGE_GROUPS = [
  { key: 'NASDAQ', label: 'US Stocks (NASDAQ)' },
  { key: 'LSE', label: 'UK Stocks (LSE)' },
  { key: 'HKEX', label: 'Hong Kong Stocks (HKEX)' },
] as const;

const EXCHANGE_BADGE_COLORS: Record<string, string> = {
  NASDAQ: 'bg-blue-100 text-blue-800',
  LSE: 'bg-purple-100 text-purple-800',
  HKEX: 'bg-orange-100 text-orange-800',
};

export default function Market() {
  const [query, setQuery] = useState('');

  const { data: allStocks, isLoading, isError } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-search'],
    queryFn: () => simulatorApi.searchMarket(''),
    retry: false,
    staleTime: Infinity,
  });

  const stocks = allStocks ?? [];
  const filtered = query.trim()
    ? stocks.filter(
        (s) =>
          s.ticker.toLowerCase().includes(query.toLowerCase()) ||
          s.name.toLowerCase().includes(query.toLowerCase()),
      )
    : stocks;

  const resultCount = filtered.length;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-muted-foreground">Loading stocks…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-red-600">Couldn't load stocks. Try again.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-1 flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Browse Stocks</h1>
        <EduTooltip
          term="Exchange"
          explanation="A stock exchange is a marketplace where stocks are bought and sold. Different countries have different exchanges."
        />
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        {stocks.length} stocks available in practice mode
      </p>

      <MarketSearchBar value={query} onChange={setQuery} />

      <div aria-live="polite" className="sr-only">
        {resultCount} stocks available
      </div>

      {resultCount === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          No stocks match '{query}'. Try AAPL, VOD, or 0700.
        </p>
      ) : (
        <div className="mt-6 space-y-6">
          {EXCHANGE_GROUPS.map((group) => {
            const groupStocks = filtered.filter((s) => s.exchange === group.key);
            if (groupStocks.length === 0) return null;
            return (
              <section key={group.key}>
                <h2 className="mb-2 text-sm font-medium text-muted-foreground">{group.label}</h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {groupStocks.map((s) => (
                    <Link
                      key={`${s.exchange}-${s.ticker}`}
                      to={`/simulator/stock/${s.exchange}/${s.ticker}`}
                      className="rounded-lg border bg-card p-3 transition-shadow hover:shadow-md"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{s.ticker}</span>
                        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${EXCHANGE_BADGE_COLORS[s.exchange] ?? 'bg-muted'}`}>
                          {s.exchange}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{s.name}</p>
                      <p className="mt-1 text-sm font-medium">{formatCurrency(s.price, s.currency)}</p>
                    </Link>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Market.test.tsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pages/child/Market.tsx tests/unit/child-Market.test.tsx
git commit -m "feat(simulator): add market browse page with search and exchange grouping"
```

---

### Task 11: StockHeader Component

**Files:**
- Create: `src/components/child/simulator/StockHeader.tsx`
- Test: `tests/unit/child-StockHeader.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-StockHeader.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StockHeader } from '@/components/child/simulator/StockHeader';

describe('StockHeader', () => {
  it('renders company name, ticker, exchange, and price', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText(/\$185\.42 USD/)).toBeInTheDocument();
  });

  it('shows existing holding info when user owns shares', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares="5"
        existingAvgPrice="180.00"
      />
    );
    expect(screen.getByText(/You own 5 shares/)).toBeInTheDocument();
    expect(screen.getByText(/Avg buy \$180\.00/)).toBeInTheDocument();
  });

  it('does not show holding info when user has no shares', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.queryByText(/You own/)).not.toBeInTheDocument();
  });

  it('includes EduTooltip about Price', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.getByRole('button', { name: /info about Price/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-StockHeader.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/StockHeader.tsx`:

```typescript
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';

type StockHeaderProps = {
  name: string;
  ticker: string;
  exchange: string;
  price: string;
  currency: string;
  existingShares: string | null;
  existingAvgPrice: string | null;
};

export function StockHeader({
  name, ticker, exchange, price, currency, existingShares, existingAvgPrice,
}: StockHeaderProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">{name}</h1>
        <span className="rounded bg-muted px-2 py-0.5 text-sm font-medium">{ticker}</span>
        <span className="rounded bg-muted px-2 py-0.5 text-sm">{exchange}</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <p className="text-3xl font-bold">{formatCurrency(price, currency)}</p>
        <EduTooltip
          term="Price"
          explanation="This is the current price for one share. In practice mode, prices stay the same so you can learn without surprises."
        />
      </div>
      {existingShares && existingAvgPrice && (
        <p className="mt-2 text-sm text-muted-foreground">
          You own {existingShares} shares · Avg buy {formatCurrency(existingAvgPrice, currency)}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-StockHeader.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/StockHeader.tsx tests/unit/child-StockHeader.test.tsx
git commit -m "feat(simulator): add StockHeader component with edu tooltip"
```

---

### Task 12: TradeForm Component

**Files:**
- Create: `src/components/child/simulator/TradeForm.tsx`
- Test: `tests/unit/child-TradeForm.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-TradeForm.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TradeForm } from '@/components/child/simulator/TradeForm';

beforeEach(() => vi.restoreAllMocks());

const baseProps = {
  ticker: 'AAPL',
  exchange: 'NASDAQ',
  price: '185.42',
  currency: 'USD',
  availableCash: '10000.00',
  ownedShares: '0',
  onSubmit: vi.fn().mockResolvedValue(undefined),
  isSubmitting: false,
  submitError: null as string | null,
};

describe('TradeForm', () => {
  it('renders Buy/Sell toggle with Sell disabled when 0 shares owned', () => {
    render(<TradeForm {...baseProps} />);
    expect(screen.getByRole('radio', { name: /buy/i })).toBeInTheDocument();
    const sellBtn = screen.getByRole('radio', { name: /sell/i });
    expect(sellBtn).toBeDisabled();
  });

  it('enables Sell when user owns shares', () => {
    render(<TradeForm {...baseProps} ownedShares="5" />);
    expect(screen.getByRole('radio', { name: /sell/i })).not.toBeDisabled();
  });

  it('shows live cost preview as user types shares', async () => {
    render(<TradeForm {...baseProps} />);
    const input = screen.getByLabelText(/number of shares/i);
    await userEvent.type(input, '5');
    expect(screen.getByText(/5 shares × \$185\.42 = \$927\.10/)).toBeInTheDocument();
  });

  it('advances to step 2 on Review click and shows confirmation', async () => {
    render(<TradeForm {...baseProps} />);
    const input = screen.getByLabelText(/number of shares/i);
    await userEvent.type(input, '2');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/Buy 2 shares of AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/Cash after trade/i)).toBeInTheDocument();
  });

  it('calls onSubmit with correct payload on Confirm', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<TradeForm {...baseProps} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '3');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onSubmit).toHaveBeenCalledWith({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 3 });
  });

  it('Go back button returns to step 1', async () => {
    render(<TradeForm {...baseProps} />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '1');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /go back/i }));
    expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
  });

  it('shows insufficient cash error for Buy exceeding available cash', async () => {
    render(<TradeForm {...baseProps} availableCash="100.00" />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '5');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/insufficient/i)).toBeInTheDocument();
  });

  it('shows Max button for Sell that fills shares owned', async () => {
    render(<TradeForm {...baseProps} ownedShares="10" />);
    await userEvent.click(screen.getByRole('radio', { name: /sell/i }));
    await userEvent.click(screen.getByRole('button', { name: /max/i }));
    expect(screen.getByLabelText(/number of shares/i)).toHaveValue(10);
  });

  it('displays submitError when present', () => {
    render(<TradeForm {...baseProps} submitError="Insufficient virtual cash" />);
    expect(screen.getByText(/insufficient virtual cash/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-TradeForm.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/components/child/simulator/TradeForm.tsx`:

```typescript
import { useState } from 'react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import type { TradeRequest, TradeType } from '@/api/simulator';
import { Button } from '@/components/ui/button';

type TradeFormProps = {
  ticker: string;
  exchange: string;
  price: string;
  currency: string;
  availableCash: string;
  ownedShares: string;
  onSubmit: (req: TradeRequest) => Promise<void>;
  isSubmitting: boolean;
  submitError: string | null;
};

type Step = 'input' | 'review';

export function TradeForm({
  ticker, exchange, price, currency, availableCash, ownedShares,
  onSubmit, isSubmitting, submitError,
}: TradeFormProps) {
  const [side, setSide] = useState<TradeType>('buy');
  const [shares, setShares] = useState('');
  const [step, setStep] = useState<Step>('input');
  const [validationError, setValidationError] = useState<string | null>(null);

  const priceNum = parseFloat(price);
  const sharesNum = parseInt(shares, 10) || 0;
  const totalCost = (priceNum * sharesNum);
  const cashNum = parseFloat(availableCash);
  const ownedNum = parseInt(ownedShares, 10) || 0;
  const canSell = ownedNum > 0;

  function handleReview() {
    setValidationError(null);
    if (sharesNum < 1) {
      setValidationError('Enter at least 1 share');
      return;
    }
    if (side === 'buy' && totalCost > cashNum) {
      setValidationError('Insufficient cash for this trade');
      return;
    }
    if (side === 'sell' && sharesNum > ownedNum) {
      setValidationError('Insufficient shares');
      return;
    }
    setStep('review');
  }

  function handleBack() {
    setStep('input');
  }

  async function handleConfirm() {
    await onSubmit({ ticker, exchange, type: side, shares: sharesNum });
  }

  if (step === 'review') {
    const cashAfter = side === 'buy' ? cashNum - totalCost : cashNum + totalCost;
    return (
      <div aria-live="assertive">
        <div className="rounded-lg border bg-muted/50 p-4">
          <p className="font-medium">{side === 'buy' ? 'Buy' : 'Sell'} {sharesNum} shares of {ticker}</p>
          <div className="mt-2 space-y-1 text-sm">
            <p>Price per share: {formatCurrency(price, currency)}</p>
            <p>Total {side === 'buy' ? 'cost' : 'proceeds'}: {formatCurrency(totalCost.toFixed(2), currency)}</p>
            <p>Cash after trade: {formatCurrency(cashAfter.toFixed(2), currency)}</p>
          </div>
          <div className="mt-2">
            <EduTooltip
              term="Review"
              explanation="Always review your trades before confirming. In real investing, you can't undo a trade!"
            />
          </div>
        </div>
        {submitError && (
          <p className="mt-2 text-sm text-red-600">{submitError}</p>
        )}
        <div className="mt-4 flex gap-2">
          <Button onClick={handleConfirm} disabled={isSubmitting}>
            {isSubmitting ? 'Submitting…' : `Confirm ${side} of ${sharesNum} shares`}
          </Button>
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>Go back</Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div role="radiogroup" aria-label="Trade type" className="mb-4 flex gap-1">
        <button
          role="radio"
          aria-checked={side === 'buy'}
          onClick={() => setSide('buy')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'buy' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
        >
          Buy
        </button>
        <button
          role="radio"
          aria-checked={side === 'sell'}
          aria-label="Sell"
          disabled={!canSell}
          onClick={() => canSell && setSide('sell')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'sell' ? 'bg-primary text-primary-foreground' : 'bg-muted'} ${!canSell ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          Sell
        </button>
      </div>

      <div className="mb-4">
        <label htmlFor="shares-input" className="mb-1 block text-sm font-medium">
          Number of shares
        </label>
        <div className="flex gap-2">
          <input
            id="shares-input"
            type="number"
            min={1}
            step={1}
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            className="w-32 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {side === 'sell' && canSell && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShares(String(ownedNum))}
              aria-label="Max"
            >
              Max
            </Button>
          )}
        </div>
      </div>

      {sharesNum > 0 && (
        <p className="mb-4 text-sm text-muted-foreground">
          {sharesNum} shares × {formatCurrency(price, currency)} = {formatCurrency(totalCost.toFixed(2), currency)}
        </p>
      )}

      {validationError && (
        <p className="mb-2 text-sm text-red-600">{validationError}</p>
      )}
      {submitError && (
        <p className="mb-2 text-sm text-red-600">{submitError}</p>
      )}

      <Button onClick={handleReview}>Review trade</Button>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-TradeForm.test.tsx`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/TradeForm.tsx tests/unit/child-TradeForm.test.tsx
git commit -m "feat(simulator): add two-step TradeForm component"
```

---

### Task 13: Stock Detail Page

**Files:**
- Create: `src/pages/child/Stock.tsx`
- Test: `tests/unit/child-Stock.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/child-Stock.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Stock from '@/pages/child/Stock';

beforeEach(() => vi.restoreAllMocks());

function mockFetchRoutes(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url.startsWith(path)) {
        const status = path === '/portfolio/trades' && init?.method === 'POST' ? 201 : 200;
        return new Response(JSON.stringify(body), { status });
      }
    }
    return new Response('not mocked', { status: 500 });
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/simulator/stock/NASDAQ/AAPL']}>
        <Routes>
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
          <Route path="/simulator" element={<div>portfolio page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Stock page', () => {
  it('renders stock header and trade form', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText(/\$185\.42 USD/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
    });
  });

  it('shows Back to market link', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /back to market/i })).toHaveAttribute('href', '/simulator/market');
    });
  });

  it('shows existing holding info from portfolio', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings: [{ ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' }],
      },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/You own 5 shares/)).toBeInTheDocument();
    });
  });

  it('shows 404 state for unknown ticker', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.startsWith('/market/quote')) return new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 });
      if (url.startsWith('/portfolio')) return new Response(JSON.stringify({ id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] }), { status: 200 });
      return new Response('', { status: 500 });
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/stock not found/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Stock.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Create `src/pages/child/Stock.tsx`:

```typescript
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { simulatorApi, type TradeRequest, type QuoteOut, type PortfolioOut } from '@/api/simulator';
import { ApiError } from '@/api/client';
import { StockHeader } from '@/components/child/simulator/StockHeader';
import { TradeForm } from '@/components/child/simulator/TradeForm';
import { useToast } from '@/hooks/use-toast';

export default function Stock() {
  const { exchange, ticker } = useParams<{ exchange: string; ticker: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const quoteQ = useQuery<QuoteOut | null, ApiError>({
    queryKey: ['quote', exchange, ticker],
    queryFn: () => simulatorApi.getQuote(exchange!, ticker!),
    retry: false,
    refetchOnWindowFocus: true,
  });

  const portfolioQ = useQuery<PortfolioOut | null>({
    queryKey: ['portfolio'],
    queryFn: () => simulatorApi.getPortfolio(),
    retry: false,
    refetchOnWindowFocus: true,
  });

  const tradeMutation = useMutation({
    mutationFn: (req: TradeRequest) => simulatorApi.placeTrade(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      toast({ title: 'Trade executed!', description: `Your ${ticker} trade was successful.` });
      navigate('/simulator');
    },
    onError: (err: unknown) => {
      const msg = err instanceof ApiError ? err.detail : 'Trade failed. Try again.';
      setSubmitError(msg);
    },
  });

  if (quoteQ.isLoading || portfolioQ.isLoading) {
    return <div className="mx-auto max-w-3xl p-6"><p className="text-sm text-muted-foreground">Loading…</p></div>;
  }

  if (quoteQ.error?.status === 404) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm">Stock not found.</p>
        <Link to="/simulator/market" className="text-sm text-primary hover:underline">← Back to market</Link>
      </div>
    );
  }

  if (quoteQ.error?.status === 403) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm">This stock isn't available in practice mode.</p>
        <Link to="/simulator/market" className="text-sm text-primary hover:underline">← Back to market</Link>
      </div>
    );
  }

  const quote = quoteQ.data;
  const portfolio = portfolioQ.data;
  if (!quote || !portfolio) return null;

  const existingHolding = portfolio.holdings.find(
    (h) => h.ticker === ticker && h.exchange === exchange,
  );

  return (
    <div className="mx-auto max-w-3xl p-6">
      <Link to="/simulator/market" className="mb-4 inline-block text-sm text-primary hover:underline">
        ← Back to market
      </Link>

      <StockHeader
        name={quote.name}
        ticker={quote.ticker}
        exchange={quote.exchange}
        price={quote.price}
        currency={quote.currency}
        existingShares={existingHolding?.shares ?? null}
        existingAvgPrice={existingHolding?.avg_buy_price ?? null}
      />

      <TradeForm
        ticker={quote.ticker}
        exchange={quote.exchange}
        price={quote.price}
        currency={quote.currency}
        availableCash={portfolio.virtual_cash}
        ownedShares={existingHolding?.shares ?? '0'}
        onSubmit={async (req) => { setSubmitError(null); await tradeMutation.mutateAsync(req); }}
        isSubmitting={tradeMutation.isPending}
        submitError={submitError}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-Stock.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pages/child/Stock.tsx tests/unit/child-Stock.test.tsx
git commit -m "feat(simulator): add stock detail page with trade flow"
```

---

### Task 14: Routing, TopNav, and Vite Proxy

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/components/child/TopNav.tsx`
- Modify: `vite.config.ts`
- Test: `tests/unit/child-TopNav.test.tsx` (existing, update)

- [ ] **Step 1: Update App.tsx to add 3 new routes**

Edit `src/App.tsx` — add imports and routes inside the Shell group:

```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { Shell } from '@/components/child/Shell';
import Login from '@/pages/child/Login';
import Signup from '@/pages/child/Signup';
import PendingConsent from '@/pages/child/PendingConsent';
import Home from '@/pages/child/Home';
import Lessons from '@/pages/child/Lessons';
import Module from '@/pages/child/Module';
import Lesson from '@/pages/child/Lesson';
import Simulator from '@/pages/child/Simulator';
import Market from '@/pages/child/Market';
import Stock from '@/pages/child/Stock';
import ConsentVerify from '@/pages/ConsentVerify';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';
import ParentDashboard from '@/pages/ParentDashboard';

function RootRedirect() {
  return <Navigate to="/home" replace />;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<RootRedirect />} />

        {/* Public child routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/pending-consent" element={<PendingConsent />} />

        {/* Authed child routes inside Shell */}
        <Route element={<Shell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/lessons" element={<Lessons />} />
          <Route path="/lessons/:moduleId" element={<Module />} />
          <Route path="/lessons/:moduleId/:lessonId" element={<Lesson />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/simulator/market" element={<Market />} />
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
        </Route>

        {/* Existing parent + consent routes (untouched) */}
        <Route path="/consent/verify" element={<ConsentVerify />} />
        <Route path="/parent/login" element={<ParentLogin />} />
        <Route path="/parent/auth/callback" element={<ParentAuthCallback />} />
        <Route path="/parent" element={<ParentDashboard />} />

        <Route path="*" element={<div className="p-6">Not found</div>} />
      </Routes>
      <Toaster />
    </>
  );
}
```

- [ ] **Step 2: Update TopNav.tsx — promote Simulator to active NavLink**

Edit `src/components/child/TopNav.tsx`:

```typescript
import { Link, NavLink } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

const COMING_SOON: ReadonlyArray<{ label: string }> = [
  { label: 'Stats' },
];

export function TopNav({ username }: { username: string }) {
  return (
    <TooltipProvider>
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
          <Link to="/home" className="text-lg font-semibold">Invest-Ed</Link>

          <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Primary">
            <NavLink to="/home"
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )}>Home</NavLink>
            <NavLink to="/lessons"
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )}>Lessons</NavLink>
            <NavLink to="/simulator"
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )}>Simulator</NavLink>
            {COMING_SOON.map((item) => (
              <Tooltip key={item.label}>
                <TooltipTrigger asChild>
                  <button
                    type="button" disabled aria-disabled="true"
                    className="cursor-not-allowed px-3 py-1.5 text-sm text-muted-foreground"
                  >{item.label}</button>
                </TooltipTrigger>
                <TooltipContent>Coming soon</TooltipContent>
              </Tooltip>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left">
                <nav className="mt-6 flex flex-col gap-1" aria-label="Primary mobile">
                  <NavLink to="/home"
                    className={({ isActive }) => cn(
                      'rounded-md px-3 py-2 text-sm hover:bg-muted',
                      isActive && 'bg-muted font-medium',
                    )}>Home</NavLink>
                  <NavLink to="/lessons"
                    className={({ isActive }) => cn(
                      'rounded-md px-3 py-2 text-sm hover:bg-muted',
                      isActive && 'bg-muted font-medium',
                    )}>Lessons</NavLink>
                  <NavLink to="/simulator"
                    className={({ isActive }) => cn(
                      'rounded-md px-3 py-2 text-sm hover:bg-muted',
                      isActive && 'bg-muted font-medium',
                    )}>Simulator</NavLink>
                  {COMING_SOON.map((item) => (
                    <span key={item.label} aria-disabled="true"
                      className="rounded-md px-3 py-2 text-sm text-muted-foreground">
                      {item.label} <span className="text-xs">(coming soon)</span>
                    </span>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
            <ProfileMenu username={username} />
          </div>
        </div>
      </header>
    </TooltipProvider>
  );
}
```

- [ ] **Step 3: Update vite.config.ts — add proxy entries**

Add `/market` and `/portfolio` proxy entries with HTML bypass to `vite.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/modules': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/lessons': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/market': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/portfolio': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/consent': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/parent': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/health': 'http://localhost:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: false,
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
});
```

- [ ] **Step 4: Update existing TopNav test**

Read the existing `tests/unit/child-TopNav.test.tsx` and update assertions. The test should now expect:
- "Simulator" as an active NavLink (not in COMING_SOON)
- Only "Stats" in COMING_SOON

The key changes: replace any assertion that Simulator is disabled with one that it's a clickable link pointing to `/simulator`.

- [ ] **Step 5: Run all unit tests to verify nothing is broken**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/App.tsx src/components/child/TopNav.tsx vite.config.ts tests/unit/child-TopNav.test.tsx
git commit -m "feat(simulator): add routes, promote Simulator in nav, configure proxy"
```

---

### Task 15: E2E Smoke Test

**Files:**
- Create: `tests/e2e/simulator-flow.spec.ts`

- [ ] **Step 1: Write E2E test**

Create `tests/e2e/simulator-flow.spec.ts`:

```typescript
import { test, expect, type Page } from '@playwright/test';
import { registerMinor, readLatestEmailToken, uniq } from './helpers';

async function loginAsChild(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill('SecurePass123!');
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/home');
}

async function approveConsent(page: Page, parentEmail: string) {
  const token = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${token}`);
  await page.getByRole('button', { name: /approve/i }).click();
  await page.waitForURL(/\/consent\/verify/);
}

test('simulator: browse market, buy stock, verify portfolio', async ({ page }) => {
  const id = uniq('sim');
  const childEmail = `${id}@test.example`;
  const parentEmail = `parent-${id}@test.example`;

  // Register + approve
  await registerMinor({ email: childEmail, username: id, parentEmail });
  await approveConsent(page, parentEmail);

  // Log in as child
  await loginAsChild(page, childEmail);

  // Navigate to simulator
  await page.getByRole('link', { name: /simulator/i }).click();
  await page.waitForURL('/simulator');
  await expect(page.getByText(/practice mode/i)).toBeVisible();
  await expect(page.getByText(/\$10,000\.00 USD/)).toBeVisible();
  await expect(page.getByText(/haven't bought any stocks/i)).toBeVisible();

  // Browse stocks
  await page.getByRole('link', { name: /browse stocks/i }).click();
  await page.waitForURL('/simulator/market');
  await expect(page.getByText('Apple Inc.')).toBeVisible();

  // Click AAPL
  await page.getByText('Apple Inc.').click();
  await page.waitForURL('/simulator/stock/NASDAQ/AAPL');
  await expect(page.getByText(/\$185\.42 USD/)).toBeVisible();

  // Buy 2 shares — step 1
  await page.getByLabel(/number of shares/i).fill('2');
  await expect(page.getByText(/2 shares × \$185\.42/)).toBeVisible();
  await page.getByRole('button', { name: /review trade/i }).click();

  // Step 2 — confirm
  await expect(page.getByText(/Buy 2 shares of AAPL/)).toBeVisible();
  await page.getByRole('button', { name: /confirm/i }).click();

  // Should redirect to portfolio with updated holdings
  await page.waitForURL('/simulator');
  await expect(page.getByText('AAPL')).toBeVisible();
  // Cash should be reduced: 10000 - (2 * 185.42) = 9629.16
  await expect(page.getByText(/\$9,629\.16 USD/)).toBeVisible();
});
```

- [ ] **Step 2: Run E2E test (requires running backend + frontend)**

Run: `cd invest-ed/frontend && npx playwright test tests/e2e/simulator-flow.spec.ts --headed`
Expected: PASS (1 test). If backend isn't running, start it first: `cd invest-ed/backend && uvicorn app.main:app --port 8000` and frontend: `cd invest-ed/frontend && npm run dev`.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/simulator-flow.spec.ts
git commit -m "test(simulator): add E2E smoke test for full trade flow"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- ✅ API client with all 5 endpoints (Task 1)
- ✅ Currency formatting utility (Task 2)
- ✅ TanStack Query hooks (Task 3)
- ✅ Educational tooltips — reusable component + 5 specific tooltips placed in components (Tasks 4, 5, 6, 7, 11, 12)
- ✅ CashCard with multi-currency footnote (Task 5)
- ✅ HoldingsTable with P/L colours + icons (Task 6)
- ✅ Trade history tab (Task 7)
- ✅ Portfolio overview page with tabs (Task 8)
- ✅ Market search with exchange grouping (Tasks 9, 10)
- ✅ Stock header with existing holding info (Task 11)
- ✅ Two-step trade form (Task 12)
- ✅ Stock detail page (Task 13)
- ✅ Routing + nav + proxy (Task 14)
- ✅ E2E smoke test (Task 15)

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code.

**3. Type consistency:**
- `QuoteOut`, `HoldingOut`, `PortfolioOut`, `TradeOut`, `TradeRequest`, `TradeType` — consistent across all tasks
- `formatCurrency(value, code)` signature used consistently
- `EduTooltip` props `{ term, explanation, children? }` used consistently
- `TradeForm` props match exactly between Task 12 (definition) and Task 13 (usage)
- `usePortfolio()` returns `PortfolioOut | null` — used in Tasks 8 and 13
