# Simulator Suite Layouts (SP-C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the kids' paper-trading simulator the prototype's investing look — a bold "Practice Portfolio" gradient hero on the dashboard, quick-stat cards, and polished stock-detail + browse screens — reusing all market-data hooks, trade logic, and SP-A tokens.

**Architecture:** Two new presentational components (`QuickStatCard`, `PortfolioHero`) + a `variant` prop on `PortfolioChart` to embed it on the gradient + targeted restyles of `Simulator`/`Stock`/`Market` and their components (`CashCard`, `HoldingsTable`, `StockHeader`, Market blocks). Pure presentation. **No routes/data/trade-logic/behaviour change.**

**Tech Stack:** React 18 + Vite + TS + Tailwind v4 + recharts; SP-A tokens (`brand-*`, `success-*`, `danger-*`, `bg-brand-gradient`, `muted-foreground`, `ink`).

**Spec:** `docs/superpowers/specs/2026-06-04-simulator-suite-layouts-design.md`

**Conventions:** Frontend commands from `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` warning is baseline), `npm test`, `npm run build`. Backend untouched. Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs). iOS rebuild deferred to programme end. **Restyle only.** **READ each file before editing (SP-B lesson).**

**Verified data/APIs (reuse):** `usePortfolio()`→`PortfolioOut {virtual_cash, total_value, currency_code, holdings: HoldingOut[]}` (string money). `HoldingOut {ticker, exchange, shares, avg_buy_price, current_price, market_value, unrealized_pl}` (strings). `usePortfolioHistory()`→`PortfolioSnapshot[] {date:string, value:number}`. `useTrades()`. `formatCurrency(value: string|number, code: string)` in `src/lib/currency.ts`. `GradientButton {to?, full?, ...button}` in `src/components/child/ui/`. `ChartDescription` a11y component (already used by `PortfolioChart`). `PortfolioChart` is currently consumed only by `Simulator.tsx`.

## Screenshot harness

Reuse the SP-A/B mocked-API capturer (`invest-ed/frontend/tmp-shot.mjs`, untracked — never commit; removed in the final task). For SP-C, mock: `/portfolio` → `{virtual_cash:'250.00', total_value:'1080.00', currency_code:'USD', holdings:[{ticker:'AAPL',exchange:'NASDAQ',shares:'5',avg_buy_price:'170.00',current_price:'175.50',market_value:'877.50',unrealized_pl:'27.50'},{ticker:'TSCO',exchange:'LSE',shares:'3',avg_buy_price:'2.50',current_price:'2.40',market_value:'7.20',unrealized_pl:'-0.30'}]}`; `/portfolio/history` → `[{date:'Mon',value:950},{date:'Tue',value:980},{date:'Wed',value:1020},{date:'Thu',value:1050},{date:'Fri',value:1080}]`; `/portfolio/trades` → `[]`; `/market/search*`,`/market/news*`,`/market/movers*`,`/market/quote/*` as needed per screen (return `[]`/minimal objects so the screen renders). Run pattern: `(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; OUTDIR=/tmp/spc/<tag> node tmp-shot.mjs ; pkill -f "port 5188"`. If lint flags the untracked `tmp-shot.mjs`, that's fine (not committed/CI); do NOT add an eslint ignore for it (removed at the end anyway).

---

### Task 1: `QuickStatCard` component (new) + tests

**Files:** Create `src/components/child/simulator/QuickStatCard.tsx` + `__tests__/QuickStatCard.test.tsx`.

- [ ] **Step 1: Failing test** — `src/components/child/simulator/__tests__/QuickStatCard.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { QuickStatCard } from '../QuickStatCard';

describe('QuickStatCard', () => {
  it('renders label and value', () => {
    render(<QuickStatCard label="Available Cash" value="$250.00" />);
    expect(screen.getByText('Available Cash')).toBeInTheDocument();
    expect(screen.getByText('$250.00')).toBeInTheDocument();
  });

  it('applies the success tone class to the value', () => {
    render(<QuickStatCard label="This Week" value="+$130" tone="success" />);
    expect(screen.getByText('+$130')).toHaveClass('text-success-700');
  });

  it('has no axe violations', async () => {
    const { container } = render(<QuickStatCard label="Available Cash" value="$250.00" emoji="💵" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run, verify FAIL** — `npm test -- src/components/child/simulator/__tests__/QuickStatCard.test.tsx`
- [ ] **Step 3: Implement** — `src/components/child/simulator/QuickStatCard.tsx`:
```tsx
import { cn } from '@/lib/utils';

const TONE: Record<'ink' | 'success' | 'danger', string> = {
  ink: 'text-ink',
  success: 'text-success-700',
  danger: 'text-danger-700',
};

export function QuickStatCard({
  label,
  value,
  emoji,
  tone = 'ink',
}: {
  label: string;
  value: string;
  emoji?: string;
  tone?: 'ink' | 'success' | 'danger';
}) {
  return (
    <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-muted-foreground">{label}</p>
        {emoji && <span className="text-xl" aria-hidden="true">{emoji}</span>}
      </div>
      <p className={cn('mt-0.5 text-lg font-extrabold', TONE[tone])}>{value}</p>
    </div>
  );
}
```
- [ ] **Step 4: Run, verify 3 PASS.**
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/simulator/QuickStatCard.tsx invest-ed/frontend/src/components/child/simulator/__tests__/QuickStatCard.test.tsx
git commit -m "feat(simulator): add QuickStatCard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `PortfolioChart` — add `variant` prop (`card` | `onGradient`)

**Files:** Modify `src/components/child/simulator/PortfolioChart.tsx` + add/extend `__tests__/PortfolioChart.test.tsx`.

- [ ] **Step 1: READ** `src/components/child/simulator/PortfolioChart.tsx`. It returns a `<div className="mt-4 rounded-2xl border-2 border-brand-200 bg-white p-4" role="img" aria-label={summary}>` with an `<h3>Portfolio Value</h3>`, a recharts `AreaChart` (sky `#0ea5e9` stroke + `url(#portfolioGrad)` fill), and a `<ChartDescription>`. It returns `null` when `history.length < 2`.

- [ ] **Step 2: Write a test asserting the onGradient variant still renders chart + a11y** — append to (or create) `src/components/child/simulator/__tests__/PortfolioChart.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PortfolioChart } from '../PortfolioChart';

const history = [
  { date: 'Mon', value: 950 },
  { date: 'Tue', value: 1080 },
];

describe('PortfolioChart variant', () => {
  it('card variant keeps the heading + role=img summary', () => {
    render(<PortfolioChart history={history} />);
    expect(screen.getByText('Portfolio Value')).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('Portfolio'));
  });

  it('onGradient variant drops the heading but keeps the role=img summary', () => {
    render(<PortfolioChart history={history} variant="onGradient" />);
    expect(screen.queryByText('Portfolio Value')).not.toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('Portfolio'));
  });

  it('renders nothing for <2 points', () => {
    const { container } = render(<PortfolioChart history={[{ date: 'Mon', value: 1 }]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```
- [ ] **Step 3: Run, verify the onGradient test FAILS** (prop not handled yet).
- [ ] **Step 4: Implement the variant.** Change the signature to `export function PortfolioChart({ history, variant = 'card' }: { history: PortfolioSnapshot[]; variant?: 'card' | 'onGradient' })`. Compute `const onGrad = variant === 'onGradient';`. Then:
  - Wrapper className: `onGrad ? '' : 'mt-4 rounded-2xl border-2 border-brand-200 bg-white p-4'` (keep `role="img" aria-label={summary}`).
  - Render the `<h3>Portfolio Value</h3>` only when `!onGrad`.
  - Give the gradient `<linearGradient>` an id derived from the variant (e.g. `const gradId = onGrad ? 'portfolioGradLight' : 'portfolioGrad';`) and use it in both the `<stop>`s and the `Area fill`. For `onGrad`: stops `stopColor="#ffffff"` (top `stopOpacity={0.35}`, bottom `stopOpacity={0}`); for card: keep `#0ea5e9` 0.3→0.
  - `Area stroke={onGrad ? '#ffffff' : '#0ea5e9'}`.
  - `XAxis tick={{ fontSize: 11, fill: onGrad ? 'rgba(255,255,255,0.85)' : undefined }}` (keep the existing `interval` logic).
  - Keep `<YAxis hide />`, the `<Tooltip>`, and `<ChartDescription>` exactly.
- [ ] **Step 5: Run the test file, verify all PASS.** Then `npx tsc -b && npm run lint`.
- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/simulator/PortfolioChart.tsx invest-ed/frontend/src/components/child/simulator/__tests__/PortfolioChart.test.tsx
git commit -m "feat(simulator): PortfolioChart onGradient variant

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `PortfolioHero` component (new) + tests

**Files:** Create `src/components/child/simulator/PortfolioHero.tsx` + `__tests__/PortfolioHero.test.tsx`.

- [ ] **Step 1: Failing test** — `src/components/child/simulator/__tests__/PortfolioHero.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { PortfolioHero } from '../PortfolioHero';

const history = [
  { date: 'Mon', value: 950 },
  { date: 'Fri', value: 1080 },
];

describe('PortfolioHero', () => {
  it('shows the Practice Portfolio label and total value', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    expect(screen.getByText(/Practice Portfolio/i)).toBeInTheDocument();
    expect(screen.getByText('$1,080.00')).toBeInTheDocument();
  });

  it('shows an up change pill from history first→last', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    // +130 over 950 = +13.7%
    expect(screen.getByText(/13\.7%/)).toBeInTheDocument();
    expect(screen.getByText(/this week/i)).toBeInTheDocument();
  });

  it('hides the change pill when history has <2 points', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={[{ date: 'Mon', value: 1080 }]} />);
    expect(screen.queryByText(/this week/i)).not.toBeInTheDocument();
    expect(screen.getByText('$1,080.00')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run, verify FAIL.**
- [ ] **Step 3: Implement** — `src/components/child/simulator/PortfolioHero.tsx`:
```tsx
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/currency';
import { PortfolioChart } from './PortfolioChart';
import type { PortfolioSnapshot } from '@/api/simulator';

export function PortfolioHero({
  totalValue,
  currencyCode,
  history,
}: {
  totalValue: string;
  currencyCode: string;
  history: PortfolioSnapshot[];
}) {
  const showChange = Array.isArray(history) && history.length >= 2;
  let pill: React.ReactNode = null;
  if (showChange) {
    const first = history[0].value;
    const last = history[history.length - 1].value;
    const delta = last - first;
    const pct = first > 0 ? (delta / first) * 100 : 0;
    const up = delta >= 0;
    pill = (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-lg border bg-white/15 px-2.5 py-1 text-sm font-bold text-white',
          up ? 'border-success-200/60' : 'border-danger-200/60',
        )}
      >
        <span aria-hidden="true">{up ? '▲' : '▼'}</span>
        {formatCurrency(Math.abs(delta), currencyCode)} · {Math.abs(pct).toFixed(1)}% this week
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
      <p className="text-xs font-bold uppercase tracking-wider text-white/90">
        Practice Portfolio <span className="font-medium normal-case opacity-80">· play money</span>
      </p>
      <p className="mt-1 text-4xl font-extrabold leading-tight">{formatCurrency(totalValue, currencyCode)}</p>
      {pill && <div className="mt-2">{pill}</div>}
      {showChange && (
        <div className="mt-4 -mx-1">
          <PortfolioChart history={history} variant="onGradient" />
        </div>
      )}
    </div>
  );
}
```
- [ ] **Step 4: Run, verify 4 PASS.** Then `npx tsc -b`.
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/simulator/PortfolioHero.tsx invest-ed/frontend/src/components/child/simulator/__tests__/PortfolioHero.test.tsx
git commit -m "feat(simulator): add PortfolioHero (Practice Portfolio gradient hero)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Wire Simulator dashboard (hero + quick-stats) + repurpose CashCard

**Files:** Modify `src/pages/child/Simulator.tsx`, `src/components/child/simulator/CashCard.tsx`. Tests: existing Simulator/CashCard tests.

- [ ] **Step 1: READ** both files. `Simulator.tsx` renders the plain `<div className="rounded-2xl border-2 … text-center">` header, then `<CashCard …/>`, then `{history && <PortfolioChart history={history} />}`, then the tabs. `CashCard` shows Virtual Cash + Total Portfolio Value + multi-currency note + "Browse stocks →" link.

- [ ] **Step 2: Repurpose `CashCard` into a quick-stats row.** Keep the props (`virtualCash, totalValue, currencyCode, hasMultiCurrency, showTotalValue`) — but render a two-up `QuickStatCard` row + a `GradientButton`. Add a `weekChange?: { value: string; up: boolean } | null` optional prop for the "This Week" card (passed from Simulator; when absent, show only Available Cash full-width). New body:
```tsx
import { GradientButton } from '@/components/child/ui/GradientButton';
import { QuickStatCard } from './QuickStatCard';
import { formatCurrency } from '@/lib/currency';

type CashCardProps = {
  virtualCash: string;
  totalValue: string;
  currencyCode: string;
  hasMultiCurrency: boolean;
  showTotalValue?: boolean;
  weekChange?: { value: string; up: boolean } | null;
};

export function CashCard({ virtualCash, currencyCode, hasMultiCurrency, weekChange }: CashCardProps) {
  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        <QuickStatCard label="Available Cash" value={formatCurrency(virtualCash, currencyCode)} emoji="💵" />
        {weekChange ? (
          <QuickStatCard label="This Week" value={weekChange.value} emoji="📈" tone={weekChange.up ? 'success' : 'danger'} />
        ) : (
          <QuickStatCard label="This Week" value="—" />
        )}
      </div>
      {hasMultiCurrency && (
        <p className="mt-2 text-xs italic text-muted-foreground">Total is approximate — converted at today's rates</p>
      )}
      <GradientButton to="/simulator/market" full className="mt-3">Browse stocks <span aria-hidden="true">→</span></GradientButton>
    </div>
  );
}
```
(Drop the now-unused `totalValue`/`showTotalValue` from the body but keep them in the prop type for caller compatibility — or remove from both and update the caller in Step 3. Prefer removing unused props cleanly and updating the caller.)

- [ ] **Step 3: Rewire `Simulator.tsx`.** Add imports `import { PortfolioHero } from '@/components/child/simulator/PortfolioHero';`. Compute the week change from `history`:
```tsx
const weekChange = history && history.length >= 2
  ? (() => {
      const d = history[history.length - 1].value - history[0].value;
      return { value: `${d >= 0 ? '+' : '−'}${formatCurrency(Math.abs(d), portfolio.currency_code)}`, up: d >= 0 };
    })()
  : null;
```
(Import `formatCurrency`.) Replace the plain header `<div>` AND the `{history && <PortfolioChart …/>}` line with:
```tsx
{history && history.length >= 2 ? (
  <PortfolioHero totalValue={portfolio.total_value} currencyCode={portfolio.currency_code} history={history} />
) : (
  <div className="rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
    <p className="text-xs font-bold uppercase tracking-wider text-white/90">Practice Portfolio <span className="font-medium normal-case opacity-80">· play money</span></p>
    <p className="mt-1 text-4xl font-extrabold">{formatCurrency(portfolio.total_value, portfolio.currency_code)}</p>
  </div>
)}
```
Then the quick-stats row: `<div className="mt-4"><CashCard virtualCash={portfolio.virtual_cash} totalValue={portfolio.total_value} currencyCode={portfolio.currency_code} hasMultiCurrency={hasMultiCurrency} weekChange={weekChange} /></div>`. Keep the tabs block (Holdings/History) unchanged.

- [ ] **Step 4: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update Simulator/CashCard tests that asserted the old "Your Portfolio"/"Virtual Cash"/"Total Portfolio Value" markup to the new copy ("Practice Portfolio", "Available Cash"). Keep behavioural assertions (tabs switch, holdings render). Expected: green.

- [ ] **Step 5: Screenshot** — capture `/tmp/spc/dashboard` (goto `${BASE}/simulator`). VIEW: bold gradient hero with "$1,080.00" + "▲ … this week" pill + white area chart; quick-stat row (Available Cash 💵 / This Week 📈 green) + Browse button; Holdings/History tabs below. If broken, fix + re-capture.

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Simulator.tsx invest-ed/frontend/src/components/child/simulator/CashCard.tsx invest-ed/frontend/src/components/child/simulator/__tests__ invest-ed/frontend/tests
git commit -m "feat(simulator): Practice Portfolio hero + quick-stat dashboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `HoldingsTable` restyle

**Files:** Modify `src/components/child/simulator/HoldingsTable.tsx`. Tests: existing HoldingsTable test.

- [ ] **Step 1: READ** the file. It has an empty state, a mobile card list (`border-2 border-brand-200` cards), and a desktop table. P/L uses `text-success-600`/`text-danger-600` + Trending icons with `data-pl` attributes (tests rely on these — keep them).

- [ ] **Step 2: Restyle (markup/classes only).** Mobile cards: `border-2 border-brand-200` → `border border-brand-100 shadow-sm`; add a symbol tile before the ticker: `<span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-100 text-xs font-extrabold text-brand-700" aria-hidden="true">{h.ticker.slice(0,2)}</span>`. Empty state: `border-2 border-brand-200` → `border border-brand-100 shadow-sm`. Desktop table: outer `rounded-lg border` → `rounded-2xl border border-brand-100 shadow-sm`. Keep the `data-pl` icons, `success-600`/`danger-600` P/L colours, all links, `EduTooltip`, and the `useMediaQuery` desktop/mobile split.

- [ ] **Step 3: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update HoldingsTable test only if it asserts the old border class (it likely queries `data-pl`/text — unchanged). Expected: green.

- [ ] **Step 4: Screenshot** — reuse `/tmp/spc/dashboard` capture (holdings tab) or capture again; confirm holdings rows show the symbol tile + shares + P/L colour. 

- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/simulator/HoldingsTable.tsx invest-ed/frontend/src/components/child/simulator/__tests__ invest-ed/frontend/tests
git commit -m "feat(simulator): restyle HoldingsTable rows

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Stock detail (`Stock.tsx` + `StockHeader`)

**Files:** Modify `src/components/child/simulator/StockHeader.tsx`, `src/pages/child/Stock.tsx`. Tests: existing.

- [ ] **Step 1: READ** both. `StockHeader` = name + ticker/exchange `bg-muted` chips + big price + EduTooltip + "you own" line. `Stock.tsx` composes StockHeader, StockChart, ChartGuide, InvestmentTimeMachine, InvestingTips, TradeForm, StockNewsSection, ChartCoachPanel with back links.

- [ ] **Step 2: Restyle `StockHeader`.** Wrap the header in a card `rounded-2xl border border-brand-100 bg-card p-4 shadow-sm`; change the ticker/exchange chips `bg-muted` → `bg-brand-100 text-brand-800 font-semibold`; keep the name `<h1>`, the big price + `EduTooltip`, and the "you own … avg buy …" line exactly. Keep `formatCurrency`.

- [ ] **Step 3: Group Stock.tsx sections into consistent cards.** Wrap the StockChart block and the `TradeForm` block each in `rounded-2xl border border-brand-100 bg-card p-4 shadow-sm` (if not already carded). Change the back-link `text-primary` → `text-brand-700`. Do NOT change `ChartGuide`, `InvestmentTimeMachine`, `InvestingTips`, `StockNewsSection`, `ChartCoachPanel`, the `tradeMutation`, the `chartPeriod` state, `onAskPenny`, or any handler/payload. Verify `TradeForm` inputs keep `text-base`/≥16px (do not shrink). READ `TradeForm.tsx` to confirm input sizing is untouched.

- [ ] **Step 4: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update StockHeader/Stock tests only for changed chip/card markup; keep trade-flow assertions. Expected: green.

- [ ] **Step 5: Screenshot** — capture `/tmp/spc/stock` (goto `${BASE}/simulator/stock/NASDAQ/AAPL`; mock `/market/quote/NASDAQ/AAPL` → a QuoteOut, `/portfolio`, `/market/history*`, `/market/news*`). VIEW: carded stock header with brand chips + big price; chart card; trade card; the rich blocks below. If a mocked endpoint 404s and the page errors, extend the mock + re-capture.

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/simulator/StockHeader.tsx invest-ed/frontend/src/pages/child/Stock.tsx invest-ed/frontend/src/components/child/simulator/__tests__ invest-ed/frontend/src/pages/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(simulator): restyle Stock detail header + section cards

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Market/Browse (`Market.tsx` + blocks)

**Files:** Modify `src/pages/child/Market.tsx`, `src/components/child/simulator/{MarketMovers,InvestingTips,MarketNews,MarketSearchBar}.tsx`. Tests: existing.

- [ ] **Step 1: READ** `Market.tsx` and the four block files. `Market.tsx` = `<h1>Browse Stocks</h1>` + refresh button + search input + `MarketMovers`/`InvestingTips`/`MarketNews` + per-exchange stock grids (`<Link>` cards).

- [ ] **Step 2: Card-align the blocks + grid cards (markup/classes only).** In `MarketMovers`, `InvestingTips`, `MarketNews`: wrap each block's container in `rounded-2xl border border-brand-100 bg-card shadow-sm` (replace any `border-2 border-brand-200`/ad-hoc borders). In `Market.tsx`: the per-exchange stock-grid `<Link>` cards → `rounded-2xl border border-brand-100 bg-card p-4 shadow-sm hover:border-brand-400 hover:shadow-md transition-all`; section `<h2>` → `text-sm font-extrabold uppercase tracking-wider text-gray-700`. Keep the search input (ensure `text-base`/≥16px), the refresh button, the debounce/`useEffect`/query logic, and `MarketSearchBar` behaviour unchanged.

- [ ] **Step 3: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update Market/block tests only for changed markup; keep search/refresh assertions. Expected: green.

- [ ] **Step 4: Screenshot** — capture `/tmp/spc/market` (goto `${BASE}/simulator/market`; mock `/market/search*`, `/market/movers*`, `/market/news*` with a couple items). VIEW: carded search + movers/tips/news + stock grid cards. If broken, fix + re-capture.

- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Market.tsx invest-ed/frontend/src/components/child/simulator invest-ed/frontend/src/components/child/simulator/__tests__ invest-ed/frontend/tests
git commit -m "feat(simulator): card-align Market browse blocks + grid

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Final a11y + regression + push

**Files:** any a11y fix; remove `tmp-shot.mjs`.

- [ ] **Step 1: Contrast/a11y sweep**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rnE "text-(brand|info)-(300|400)" src/components/child/simulator src/pages/child/Simulator.tsx src/pages/child/Stock.tsx src/pages/child/Market.tsx
```
Bump any text-on-white to `-600/700` (leave labels on the gradient hero — those are white). Confirm: the hero total value + change pill are white on `bg-brand-gradient` at large/bold (AA large-text); both `PortfolioChart` variants keep `role="img"` + `ChartDescription`; gain/loss uses `success`/`danger`; decorative emojis/▲▼ are `aria-hidden`; trade + search inputs are ≥16px.

- [ ] **Step 2: Full regression**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: tsc clean; lint = only the `button.tsx` warning; vitest green (incl. the 3 new simulator component test files); build OK. Backend untouched.

- [ ] **Step 3: Cleanup + push**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && rm -f tmp-shot.mjs
cd "/Users/leeashmore/Local Repo"
git status --porcelain   # only intended files; tmp-shot.mjs gone
git add -A invest-ed/frontend/src
git commit -m "a11y(simulator): contrast pass for SP-C layouts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "no a11y fixes needed"
git push origin main
```

- [ ] **Step 4: Confirm green CI** — watch `main`; all 5 jobs green (a11y job guards the new components/charts). Fix any failure before declaring SP-C done.

- [ ] **Step 5: Report SP-C complete** — Practice Portfolio hero + quick stats + polished Stock/Market; CI green. iOS rebuild still deferred. Next: SP-D (auth + the parents-only Apple/Google/magic-link social login feature).

---

## Self-Review

**1. Spec coverage:** QuickStatCard → T1; PortfolioChart variant → T2; PortfolioHero → T3; Simulator dashboard (hero + quick stats, CashCard repurpose) → T4; HoldingsTable → T5; Stock detail (StockHeader + cards) → T6; Market polish → T7; a11y + regression → T8. All spec sections covered. ✓

**2. Placeholder scan:** New components carry full code + tests. Screen/component restyles give exact files, the specific class/markup changes, READ-first steps, and a screenshot+build+test gate. No "restyle appropriately". ✓

**3. Type consistency:** `QuickStatCard {label,value,emoji?,tone?:'ink'|'success'|'danger'}` used the same in T1/T4. `PortfolioHero {totalValue,currencyCode,history}` (matches `PortfolioOut.total_value`+`PortfolioSnapshot[]`) in T3/T4. `PortfolioChart {history,variant?}` consistent T2/T3. `CashCard` adds `weekChange?:{value,up}` — defined in T4 and passed from Simulator in T4. `formatCurrency(value: string|number, code)` signature respected. `HoldingOut` fields (`unrealized_pl`, `data-pl`) preserved in T5. ✓
