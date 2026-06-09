# Market Page IA Restructure (Items 4+5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the child Market page into clear zones with a unified card system and selected-region-first browsing — discovery-first layout "A", composing the shipped region selector.

**Architecture:** A new shared `SectionCard` (icon + title + optional count pill + optional collapse) wraps Movers, Tips, News, and a new collapsible "More markets" browse group. `Market.tsx` reorders to: control strip → Movers → Browse (selected region first, others under collapsible "More markets") → Tips (open) → News (closed). Frontend-only; no backend, LLM, or DB.

**Tech Stack:** React 18 + TS + Tailwind v4 + lucide-react; TanStack Query; vitest + vitest-axe.

**Conventions:** TDD. Explicit `git add <paths>` only — never `git add -A`; **leave the unrelated working-tree changes alone** (the `.gitignore` mod and uncommitted iOS build files: `frontend/ios/App/App.xcodeproj/project.pbxproj`, `frontend/ios/App/App/Info.plist`, `…/project.xcworkspace/contents.xcworkspacedata`). Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync`. Work on `testing`; do NOT promote.

**Verified facts:**
- `Market.tsx` (full file read): default export `Market()`. `me=useQuery(['me'])→authApi.me()`; `region = selectedRegion ?? toRegionCode(me?.content_region ?? me?.country_code)`; `priorityExchanges = REGION_EXCHANGES[region] ?? []`. Featured query `['market-featured']→searchMarket('')`; search query `['market-search', debouncedQuery]` enabled at ≥2 chars; `isSearching = debouncedQuery.length >= 2`; `stocks = isSearching ? searchResults : featuredStocks`. Exported helper `groupByExchange(stocks, priority)` returns `[exchange, QuoteOut[]][]` sorted priority-first. Constants `EXCHANGE_BADGE_COLORS`, `EXCHANGE_GROUP_LABELS` (NASDAQ/NYSE→"US Stocks", LSE→"UK Stocks", HKEX→"Hong Kong Stocks"). Current render: BackButton; header row (`<h1>Browse Stocks</h1>` + `RegionSelector` + Refresh); count `<p>`; search `<input role="searchbox">`; `aria-live` sr-only; `{!isSearching && (<div className="mt-4 space-y-4"><MarketMovers region={region}/><InvestingTips/><MarketNews/></div>)}`; then empty/loading states or `<div className="mt-4 space-y-6">{groups.map(([exchange, groupStocks]) => <section>…grid of Link tiles…</section>)}</div>`. Stock tile: `<Link to={`/simulator/stock/${s.exchange}/${s.ticker}`} className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm hover:border-brand-400 hover:shadow-md transition-all min-h-[44px]">` with ticker + exchange badge + name + `formatCurrency(s.price, s.currency)`.
- `MarketMovers.tsx`: `MarketMovers({region})`; outer card `<div className="rounded-2xl border-2 border-brand-200 bg-white p-4"><h2 className="mb-4 text-lg font-semibold text-gray-800">Today's Market Movers</h2><div className="space-y-5">{exchanges.map(ExchangeSection)}</div></div>`. Loading → `<div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-4"><p>Loading market movers…</p></div>`. Returns `null` when `data` empty. Imports `TrendingUp, TrendingDown` from lucide.
- `InvestingTips.tsx`: `InvestingTips({contextTicker?, contextExchange?})`. Loaded render: `<div className="rounded-2xl border-2 border-brand-200 bg-white p-4">` → header `<div className="mb-3 flex items-center gap-2"><Lightbulb/><h3 …>Investing Tips</h3>{!reducedMotion && count>1 && <button aria-label={isPlaying?'Pause tips':'Play tips'} className="ml-auto …">…</button>}</div>` → scroll region `<div ref={scrollRef} … role="group" aria-label="Investing tips" …>` → dots `<div className="mt-2 flex justify-center gap-1">{tips.map(button aria-label="Go to tip N")}</div>`. `if (!tips) return <skeleton card>`. `if (tips.length === 0) return null`. Uses `useMediaQuery('(prefers-reduced-motion: reduce)')`.
- `MarketNews.tsx`: `MarketNews()`; loaded render `<div className="rounded-2xl border-2 border-brand-200 bg-white p-4"><div className="mb-3 flex items-center gap-2"><Newspaper/><h2 …>News for Your Stocks</h2></div><AiSummary/><div className="-mx-1 divide-y divide-gray-100">{data.map(NewsCard)}</div></div>`. Loading → minimal card "Loading news…". Returns `null` when no data. `AiSummary` internally queries `['news-summary']`.
- Tests: page test `src/pages/child/__tests__/Market.test.tsx` mocks `@/api/simulator` + `@/api/auth` (me → `{id:1, role:'child', country_code:'US', content_region:'GB'}`), **stubs** `MarketMovers` (region-capturing `<div data-testid="movers">movers:{region}</div>`), `MarketNews`/`InvestingTips` as `() => null`; featured `searchMarket('')→[]`. Integration test `tests/unit/child-Market.test.tsx` uses a real `fetch` spy (no me mock → me null → region 'US'), real child components; `allQuotes` = AAPL/MSFT (NASDAQ), VOD (LSE), 0700 (HKEX). Component tests in `src/components/child/simulator/__tests__/`: `MarketMovers.test.tsx`, `InvestingTips.test.tsx` exist; **no** `MarketNews.test.tsx`.

---

## File Structure
- **Create** `frontend/src/components/child/simulator/SectionCard.tsx` + `__tests__/SectionCard.test.tsx`.
- **Modify** `frontend/src/components/child/simulator/MarketMovers.tsx` (adopt SectionCard, rename heading).
- **Modify** `frontend/src/components/child/simulator/InvestingTips.tsx` (adopt SectionCard collapsible) + `__tests__/InvestingTips.test.tsx` (add collapse test).
- **Modify** `frontend/src/components/child/simulator/MarketNews.tsx` (adopt SectionCard collapsible) + **Create** `__tests__/MarketNews.test.tsx`.
- **Modify** `frontend/src/pages/child/Market.tsx` (BrowseGroup helper, selected/other split, More markets, reorder) + **Modify** `tests/unit/child-Market.test.tsx`.

---

## Task 1: Shared `SectionCard` component

**Files:** Create `frontend/src/components/child/simulator/SectionCard.tsx`; Create `frontend/src/components/child/simulator/__tests__/SectionCard.test.tsx`.

- [ ] **Step 1: Write the failing test** — `__tests__/SectionCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { Lightbulb } from 'lucide-react';
import { SectionCard } from '../SectionCard';

describe('SectionCard', () => {
  it('renders the title, an icon, and a count pill', () => {
    render(<SectionCard title="My Section" icon={Lightbulb} count={7}><p>Body</p></SectionCard>);
    expect(screen.getByRole('heading', { name: /my section/i })).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
  });

  it('non-collapsible: no button, content always visible', () => {
    render(<SectionCard title="Static"><p>Always</p></SectionCard>);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByText('Always')).toBeVisible();
  });

  it('collapsible defaultOpen: content shown, toggles closed', async () => {
    render(<SectionCard title="Tips" collapsible defaultOpen><p>Inside</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /tips/i });
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Inside')).toBeInTheDocument();
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Inside')).toBeNull();
  });

  it('collapsible defaultOpen=false: content hidden until expanded', async () => {
    render(<SectionCard title="News" collapsible defaultOpen={false}><p>Hidden</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /news/i });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Hidden')).toBeNull();
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Hidden')).toBeInTheDocument();
  });

  it('collapsible header controls the content region via aria-controls', async () => {
    render(<SectionCard title="Region" collapsible defaultOpen><p>RegionBody</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /region/i });
    const controls = btn.getAttribute('aria-controls');
    expect(controls).toBeTruthy();
    expect(document.getElementById(controls as string)).toContainHTML('RegionBody');
  });

  it('has no axe violations (open and collapsed)', async () => {
    const open = render(<SectionCard title="A" collapsible defaultOpen><p>x</p></SectionCard>);
    expect(await axe(open.container)).toHaveNoViolations();
    const closed = render(<SectionCard title="B" collapsible defaultOpen={false}><p>y</p></SectionCard>);
    expect(await axe(closed.container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- SectionCard` → FAIL (module missing).

- [ ] **Step 3: Implement** — Create `SectionCard.tsx`:

```tsx
import { useId, useState, type ReactNode } from 'react';
import { ChevronDown, type LucideIcon } from 'lucide-react';

type Props = {
  title: string;
  icon?: LucideIcon;
  count?: number;
  collapsible?: boolean;
  defaultOpen?: boolean;
  headingLevel?: 2 | 3;
  children: ReactNode;
};

export function SectionCard({
  title,
  icon: Icon,
  count,
  collapsible = false,
  defaultOpen = true,
  headingLevel = 2,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const Heading = headingLevel === 3 ? 'h3' : 'h2';
  const isOpen = collapsible ? open : true;

  const inner = (
    <>
      {Icon && <Icon className="h-5 w-5 flex-shrink-0 text-brand-700" aria-hidden="true" />}
      <span className="text-lg font-semibold text-gray-800">{title}</span>
      {typeof count === 'number' && (
        <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
          {count}
        </span>
      )}
    </>
  );

  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
      <Heading className="m-0">
        {collapsible ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={isOpen}
            aria-controls={contentId}
            className="flex min-h-[44px] w-full items-center gap-2 rounded-lg text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            {inner}
            <ChevronDown
              className={`ml-auto h-5 w-5 flex-shrink-0 text-brand-700 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              aria-hidden="true"
            />
          </button>
        ) : (
          <span className="flex items-center gap-2">{inner}</span>
        )}
      </Heading>
      {isOpen && (
        <div id={contentId} className="mt-3">
          {children}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- SectionCard` → PASS (6).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/SectionCard.tsx frontend/src/components/child/simulator/__tests__/SectionCard.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): shared SectionCard (icon/title/count/collapsible)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: MarketMovers adopts SectionCard

**Files:** Modify `frontend/src/components/child/simulator/MarketMovers.tsx`.

- [ ] **Step 1: Update the component** — replace the loaded-state outer card. Add `import { SectionCard } from './SectionCard';`. Change the return from:

```tsx
  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Today's Market Movers</h2>
      <div className="space-y-5">
        {exchanges.map(([exchange, movers]) => (
          <ExchangeSection key={exchange} exchange={exchange} data={movers} />
        ))}
      </div>
    </div>
  );
```

to:

```tsx
  return (
    <SectionCard title="What's moving today" icon={TrendingUp}>
      <div className="space-y-5">
        {exchanges.map(([exchange, movers]) => (
          <ExchangeSection key={exchange} exchange={exchange} data={movers} />
        ))}
      </div>
    </SectionCard>
  );
```

Leave the loading state (`Loading market movers…`) and the `return null` branch unchanged. `TrendingUp` is already imported.

- [ ] **Step 2: Run the movers test** — `cd frontend && npm run test -- MarketMovers`
Expected: PASS. The existing test matches `/market movers|loading market movers/i` via the unchanged loading text, then asserts `getMarketMovers` called with `'GB'`. If the rename trips any assertion, update that test to match `What's moving today` for the loaded heading (loading text stays "Loading market movers…").

- [ ] **Step 3: Typecheck** — `cd frontend && npx tsc -b` → clean.

- [ ] **Step 4: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/MarketMovers.tsx
git commit -m "$(cat <<'EOF'
refactor(simulator): MarketMovers uses SectionCard ("What's moving today")

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: InvestingTips adopts SectionCard (collapsible, open)

**Files:** Modify `frontend/src/components/child/simulator/InvestingTips.tsx`; Modify `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx`.

- [ ] **Step 1: Add a collapse test FIRST** — append to `InvestingTips.test.tsx` inside the `describe`:

```tsx
  it('is collapsible and open by default; collapsing hides the tips', async () => {
    await renderTips();
    const toggle = screen.getByRole('button', { name: /^investing tips$/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Tip One')).toBeInTheDocument();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Tip One')).toBeNull();
  });
```

(The existing tests already import `userEvent` and `screen`. The collapse toggle's accessible name is exactly "Investing Tips"; the regex `/^investing tips$/i` avoids matching the play/pause or dot buttons.)

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- InvestingTips` → the new test FAILS (no collapse button yet).

- [ ] **Step 3: Refactor the component** — Add `import { SectionCard } from './SectionCard';`. Replace the loaded-state return. From the current:

```tsx
  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-brand-700" />
        <h3 className="text-base font-semibold text-gray-800">Investing Tips</h3>
        {!reducedMotion && count > 1 && (
          <button
            type="button"
            onClick={() => setIsPlaying((p) => !p)}
            aria-label={isPlaying ? 'Pause tips' : 'Play tips'}
            className="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-brand-700 hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
        )}
      </div>

      <div
        ref={scrollRef}
        /* …scroll region… */
      >
        {/* tip cards */}
      </div>

      <div className="mt-2 flex justify-center gap-1">
        {/* dots */}
      </div>
    </div>
  );
```

to (wrap everything BELOW the old header in SectionCard, and move the play/pause control into a small right-aligned toolbar row inside the card body):

```tsx
  return (
    <SectionCard title="Investing Tips" icon={Lightbulb} collapsible defaultOpen>
      {!reducedMotion && count > 1 && (
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            onClick={() => setIsPlaying((p) => !p)}
            aria-label={isPlaying ? 'Pause tips' : 'Play tips'}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-brand-700 hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
        </div>
      )}

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onBlur={() => setPaused(false)}
        role="group"
        aria-label="Investing tips"
        className="flex gap-3 overflow-x-auto scroll-smooth pb-2"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {/* unchanged tip cards map */}
      </div>

      <div className="mt-2 flex justify-center gap-1">
        {/* unchanged dots map */}
      </div>
    </SectionCard>
  );
```

Preserve the tip-cards map and dots map exactly. Keep the skeleton (`if (!tips) return …`) and `if (tips.length === 0) return null` branches unchanged (NOT wrapped in SectionCard). The rotation `useEffect`, `scrollToIndex`, `goToIndex`, `handleScroll`, and all state stay as-is.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- InvestingTips` → PASS (all, incl. the new collapse test and the existing rotation/reduced-motion/dots/axe tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/InvestingTips.tsx frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx
git commit -m "$(cat <<'EOF'
refactor(simulator): InvestingTips uses collapsible SectionCard (open)

Play/pause moves into the card body; rotation/a11y behaviour unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: MarketNews adopts SectionCard (collapsible, closed) + test

**Files:** Modify `frontend/src/components/child/simulator/MarketNews.tsx`; Create `frontend/src/components/child/simulator/__tests__/MarketNews.test.tsx`.

- [ ] **Step 1: Write the failing test** — Create `__tests__/MarketNews.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketNews } from '../MarketNews';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getMarketNews: vi.fn(),
    getNewsSummary: vi.fn(() => Promise.resolve(null)),
  },
}));
import { simulatorApi } from '@/api/simulator';

const NEWS = [
  { title: 'Apple climbs on earnings', url: 'https://x.test/a', publisher: 'Wire', published: '', related_ticker: 'AAPL', summary: '', thumbnail: '' },
];

function renderNews() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MarketNews />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(simulatorApi.getMarketNews).mockResolvedValue(NEWS as never);
  vi.mocked(simulatorApi.getNewsSummary).mockResolvedValue(null as never);
});

describe('MarketNews', () => {
  it('is collapsed by default and reveals news when expanded', async () => {
    renderNews();
    const toggle = await screen.findByRole('button', { name: /news for your stocks/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/apple climbs on earnings/i)).toBeNull();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/apple climbs on earnings/i)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderNews();
    await screen.findByRole('button', { name: /news for your stocks/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- MarketNews` → FAIL (no collapse button; news visible).

- [ ] **Step 3: Refactor the component** — Add `import { SectionCard } from './SectionCard';`. Replace the loaded-state return. From:

```tsx
  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Newspaper className="h-5 w-5 text-brand-700" />
        <h2 className="text-lg font-semibold text-gray-800">News for Your Stocks</h2>
      </div>
      <AiSummary />
      <div className="-mx-1 divide-y divide-gray-100">
        {data.map((item, i) => (
          <NewsCard key={`${item.related_ticker}-${i}`} item={item} />
        ))}
      </div>
    </div>
  );
```

to:

```tsx
  return (
    <SectionCard title="News for your stocks" icon={Newspaper} collapsible defaultOpen={false}>
      <AiSummary />
      <div className="-mx-1 divide-y divide-gray-100">
        {data.map((item, i) => (
          <NewsCard key={`${item.related_ticker}-${i}`} item={item} />
        ))}
      </div>
    </SectionCard>
  );
```

Leave the loading state and `return null` branch unchanged.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- MarketNews` → PASS (2).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/MarketNews.tsx frontend/src/components/child/simulator/__tests__/MarketNews.test.tsx
git commit -m "$(cat <<'EOF'
refactor(simulator): MarketNews uses collapsible SectionCard (closed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Restructure Market.tsx (zones + More markets)

**Files:** Modify `frontend/src/pages/child/Market.tsx`; Modify `frontend/tests/unit/child-Market.test.tsx`.

- [ ] **Step 1: Update the integration test FIRST** — In `tests/unit/child-Market.test.tsx`, replace the first test ("renders all stocks grouped by exchange") because non-selected regions now live under a collapsed "More markets" (me is null → region 'US' → NASDAQ selected; LSE/HKEX hidden):

```tsx
  it('shows the selected region first and other markets under a collapsible group', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    // Selected region (US) is shown directly
    expect(screen.getByText(/US Stocks/i)).toBeInTheDocument();
    // Other regions start hidden behind "More markets"
    expect(screen.queryByText('Vodafone Group')).not.toBeInTheDocument();
    expect(screen.queryByText('Tencent Holdings')).not.toBeInTheDocument();
    const more = screen.getByRole('button', { name: /more markets/i });
    await userEvent.click(more);
    expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
    expect(screen.getByText('Tencent Holdings')).toBeInTheDocument();
    expect(screen.getByText(/UK Stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/Hong Kong Stocks/i)).toBeInTheDocument();
  });
```

Leave the other four tests unchanged (search shows all groups; no-matches; links; region selector). Note the search test relies on `searchMarket` returning all matching quotes across regions — the search view does NOT split into "More markets", so Vodafone appears directly.

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- child-Market` → the rewritten test FAILS (no "More markets" button yet; other-region stocks currently visible).

- [ ] **Step 3: Add a `BrowseGroup` helper + imports** — In `Market.tsx`, add `import { SectionCard } from '@/components/child/simulator/SectionCard';`. Below `groupByExchange`, add a presentational helper (reuses the existing tile markup):

```tsx
function BrowseGroup({
  exchange,
  stocks,
  headingLevel = 2,
}: {
  exchange: string;
  stocks: QuoteOut[];
  headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 3 ? 'h3' : 'h2';
  return (
    <section>
      <Heading className="mb-2 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wider text-gray-700">
        {EXCHANGE_GROUP_LABELS[exchange] ?? exchange}
        <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
          {stocks.length}
        </span>
      </Heading>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stocks.map((s) => (
          <Link
            key={`${s.exchange}-${s.ticker}`}
            to={`/simulator/stock/${s.exchange}/${s.ticker}`}
            className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm hover:border-brand-400 hover:shadow-md transition-all min-h-[44px]"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold">{s.ticker}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${EXCHANGE_BADGE_COLORS[s.exchange] ?? 'bg-muted text-muted-foreground'}`}
              >
                {s.exchange}
              </span>
            </div>
            <p className="mt-1 truncate text-sm text-muted-foreground">{s.name}</p>
            <p className="mt-1 text-sm font-medium">{formatCurrency(s.price, s.currency)}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Split groups + reorder the render** — In `Market()`, after `const groups = groupByExchange(stocks, priorityExchanges);` compute the split:

```tsx
  const selectedSet = new Set(priorityExchanges);
  const selectedGroups = isSearching ? groups : groups.filter(([ex]) => selectedSet.has(ex));
  const otherGroups = isSearching ? [] : groups.filter(([ex]) => !selectedSet.has(ex));
  const otherCount = otherGroups.reduce((n, [, s]) => n + s.length, 0);
```

Then change the render so Movers sits ABOVE browse and Tips/News BELOW it. Replace the existing `{!isSearching && (<div className="mt-4 space-y-4"><MarketMovers …/><InvestingTips/><MarketNews/></div>)}` block with **just** the movers:

```tsx
      {!isSearching && (
        <div className="mt-4">
          <MarketMovers region={region} />
        </div>
      )}
```

Replace the browse results block (the `stocks.length === 0 …` ternary's final branch) so it renders `selectedGroups` then the collapsible "More markets":

```tsx
      ) : (
        <div className="mt-4 space-y-6">
          {selectedGroups.map(([exchange, groupStocks]) => (
            <BrowseGroup key={exchange} exchange={exchange} stocks={groupStocks} />
          ))}
          {otherGroups.length > 0 && (
            <SectionCard title="More markets" count={otherCount} collapsible defaultOpen={false}>
              <div className="space-y-6">
                {otherGroups.map(([exchange, groupStocks]) => (
                  <BrowseGroup key={exchange} exchange={exchange} stocks={groupStocks} headingLevel={3} />
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      )}
```

(Keep the two earlier branches of the ternary — the "Searching…" and "No stocks found" states — exactly as they are.) Finally, add Tips + News BELOW the browse block, before the closing `</div>` of the page:

```tsx
      {!isSearching && (
        <div className="mt-4 space-y-4">
          <InvestingTips />
          <MarketNews />
        </div>
      )}
```

Remove the now-unused inline `<section>`/grid markup that the old results block contained (it's replaced by `BrowseGroup`).

- [ ] **Step 5: Run to verify it passes** — `cd frontend && npm run test -- child-Market Market` → PASS. The page test (`src/pages/child/__tests__/Market.test.tsx`) is unaffected (its featured list is empty and Movers/Tips/News are stubbed), so its 5 tests stay green.

- [ ] **Step 6: Typecheck + lint** — `cd frontend && npx tsc -b && npm run lint` → tsc clean; lint 0 errors (pre-existing warnings only).

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/pages/child/Market.tsx frontend/tests/unit/child-Market.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): Market zones — movers, region-first browse, More markets

Selected region's groups render first; other regions collapse under a
"More markets" SectionCard (closed by default). Tips/News move below browse
so they stop interrupting it. Adds BrowseGroup helper with count pills.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Frontend gate** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: tsc clean; lint 0 errors (3 pre-existing fast-refresh warnings OK); all tests pass; build succeeds (pre-existing chunk-size warning OK).

- [ ] **Step 2: Push + report** — `cd /Users/leeashmore/investikid && git push origin testing`; report CI status (all 5 jobs). No `cap sync`. Do NOT promote to staging/main. Leave the unrelated `.gitignore` + iOS build-number working-tree files uncommitted.

---

## Self-Review

**1. Spec coverage:** §1 SectionCard → Task 1. §2 adopt in Movers/Tips/News → Tasks 2–4 (rename, collapsible open/closed, play/pause relocated). §3 reorder + selected/other split + "More markets" → Task 5 (movers above, tips/news below, `BrowseGroup`, collapse default closed, search shows all). §4 counts/labels → `BrowseGroup` count pill + SectionCard `count`. Testing (SectionCard, MarketNews new, InvestingTips collapse, child-Market More-markets toggle) → Tasks 1,3,4,5. A11y (aria-expanded/controls, ≥44px, headings h2/h3, axe) → SectionCard + BrowseGroup headingLevel. ✓

**2. Placeholder scan:** Full code given for SectionCard, its test, MarketNews test, BrowseGroup, and every edit. "unchanged map" notes point at concrete existing markup quoted in Verified facts. ✓

**3. Type consistency:** `SectionCard` props identical across all call sites (`title`, `icon`, `count`, `collapsible`, `defaultOpen`, `headingLevel`). `BrowseGroup({exchange, stocks, headingLevel})` consistent. `groupByExchange` return shape `[string, QuoteOut[]][]` consumed identically in split + render. Movers/Tips/News keep their existing prop signatures (`MarketMovers({region})`, `InvestingTips()`, `MarketNews()`). ✓
