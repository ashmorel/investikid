# Investing Tips Carousel Auto-Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-advance the existing Investing Tips scroll-snap carousel (~7s, looping), with an accessible play/pause toggle and tappable dots, pausing on hover/focus and disabled under `prefers-reduced-motion`.

**Architecture:** One self-contained React component, `InvestingTips.tsx`. A `setInterval` (in a `useEffect`) advances `activeIndex` and scrolls the existing carousel; `activeIndex` is the single source of truth (also updated by manual scroll). Auto-rotation is gated by a derived `autoRotate = isPlaying && !paused && !reducedMotion && count > 1`. `prefers-reduced-motion` is read via the existing `useMediaQuery` hook.

**Tech Stack:** React 18 + TS, TanStack Query, lucide-react icons, Tailwind v4 semantic tokens; vitest + @testing-library/react + userEvent + vitest-axe.

**Conventions:** FE-only — no backend, no new endpoint, no `cap sync`. TDD. Explicit `git add <paths>` only — never `git add -A`; **leave the unrelated working-tree changes alone** (the `.gitignore` modification and the uncommitted iOS build-number files `frontend/ios/App/App.xcodeproj/project.pbxproj`, `frontend/ios/App/App/Info.plist`, `…/project.xcworkspace/contents.xcworkspacedata`). Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify from `frontend/`: `npx tsc -b && npm run lint && npm run test && npm run build`.

**Verified facts:**
- Component: `frontend/src/components/child/simulator/InvestingTips.tsx`. Today: `useRef(scrollRef)` + `useState(activeIndex)`; `useQuery(['investing-tips'])` → `simulatorApi.getInvestingTips()`; cards in an `overflow-x-auto` scroll-snap div with `onScroll → handleScroll` computing `activeIndex` from `scrollLeft / (clientWidth * 0.65)`; dots are decorative `<span>`s; nested `MiniChart` uses `useQuery(['stock-history',…])` → `simulatorApi.getStockHistory` and renders a plain "Loading chart…" div when history has `< 2` points (so mocking `getStockHistory → null` avoids recharts in tests).
- Test convention: `frontend/src/components/child/simulator/__tests__/<Name>.test.tsx` (e.g. `PortfolioChart.test.tsx`).
- `frontend/src/hooks/useMediaQuery.ts`: `useMediaQuery(query: string): boolean`.
- `frontend/tests/setup.ts` already stubs `window.matchMedia` (returns `matches:false` for non-`min-width` queries, so reduced-motion defaults to **false** in tests). jsdom lacks `Element.prototype.scrollTo` → tests must stub it.

---

## File Structure
- **Modify:** `frontend/src/components/child/simulator/InvestingTips.tsx` — add the rotation engine, play/pause control, button-ified dots, hover/focus pause, reduced-motion gating. `MiniChart` and the loading/empty states are unchanged.
- **Create:** `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx` — behavior + a11y tests.

No other files change. No new hooks/files (logic stays in the one component; it remains small).

---

## Task 1: Auto-rotation engine + accessible controls (TDD, one red→green cycle)

This component is small and its state is interlocking (auto-advance, explicit pause, hover/focus pause, reduced-motion all feed one `autoRotate` flag), so we write the full behavior spec first, watch it fail, then implement the complete component.

**Files:**
- Create: `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx`
- Modify: `frontend/src/components/child/simulator/InvestingTips.tsx`

- [ ] **Step 1: Write the failing test file**

Create `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvestingTips } from '../InvestingTips';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getInvestingTips: vi.fn(),
    getStockHistory: vi.fn(() => Promise.resolve(null)),
  },
}));

import { simulatorApi } from '@/api/simulator';

const TIPS = [
  { id: 't1', title: 'Tip One', description: 'First tip body', example_ticker: 'AAPL', example_exchange: 'NASDAQ' },
  { id: 't2', title: 'Tip Two', description: 'Second tip body', example_ticker: 'MSFT', example_exchange: 'NASDAQ' },
  { id: 't3', title: 'Tip Three', description: 'Third tip body', example_ticker: 'F', example_exchange: 'NYSE' },
];

function setReducedMotion(reduce: boolean) {
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: q.includes('prefers-reduced-motion') ? reduce : false,
    media: q,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

async function renderTips() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <InvestingTips />
    </QueryClientProvider>,
  );
  // Tips load (the carousel renders once data resolves)
  await screen.findByText('Tip One');
  return utils;
}

beforeEach(() => {
  vi.mocked(simulatorApi.getInvestingTips).mockResolvedValue(TIPS as never);
  vi.mocked(simulatorApi.getStockHistory).mockResolvedValue(null as never);
  setReducedMotion(false);
  // jsdom has no scrollTo
  Element.prototype.scrollTo = vi.fn() as unknown as typeof Element.prototype.scrollTo;
  // shouldAdvanceTime keeps findBy/userEvent working while we control the interval
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function activeDotLabel(): string | null {
  const dots = screen.getAllByRole('button', { name: /go to tip/i });
  const active = dots.find((d) => d.getAttribute('aria-current') === 'true');
  return active ? active.getAttribute('aria-label') : null;
}

describe('InvestingTips auto-rotation', () => {
  it('auto-advances through tips and loops back to the first', async () => {
    await renderTips();
    expect(activeDotLabel()).toBe('Go to tip 1');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 3');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // looped
  });

  it('pause halts advancing; play resumes', async () => {
    await renderTips();
    await userEvent.click(screen.getByRole('button', { name: /pause tips/i }));
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // still
    await userEvent.click(screen.getByRole('button', { name: /play tips/i }));
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
  });

  it('pauses while hovered, resumes on leave', async () => {
    const { container } = await renderTips();
    const card = container.firstChild as HTMLElement;
    fireEvent.mouseEnter(card);
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // paused by hover
    fireEvent.mouseLeave(card);
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
  });

  it('under prefers-reduced-motion: no auto-advance and no play/pause control', async () => {
    setReducedMotion(true);
    await renderTips();
    expect(screen.queryByRole('button', { name: /pause tips|play tips/i })).toBeNull();
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // never advanced
  });

  it('tapping a dot jumps to that tip', async () => {
    await renderTips();
    await userEvent.click(screen.getByRole('button', { name: 'Go to tip 3' }));
    expect(activeDotLabel()).toBe('Go to tip 3');
    expect(Element.prototype.scrollTo).toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = await renderTips();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- InvestingTips`
Expected: FAIL — there is no "Go to tip N" button yet (dots are `<span>`s) and no "Pause tips" control / auto-advance.

- [ ] **Step 3: Implement the component**

Replace `frontend/src/components/child/simulator/InvestingTips.tsx` with (the `MiniChart` sub-component and `Props` type are unchanged; the changes are the new imports, the rotation state/effect, the play/pause button, the button-ified dots, and the hover/focus handlers):

```tsx
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Lightbulb, Pause, Play } from 'lucide-react';
import { simulatorApi, type InvestingTip, type PricePoint } from '@/api/simulator';
import { useMediaQuery } from '@/hooks/useMediaQuery';

function MiniChart({ exchange, ticker }: { exchange: string; ticker: string }) {
  const { data } = useQuery<PricePoint[] | null>({
    queryKey: ['stock-history', exchange, ticker, '5y'],
    queryFn: () => simulatorApi.getStockHistory(exchange, ticker, '5y'),
    staleTime: 30 * 60 * 1000,
  });

  const points = data ?? [];
  if (points.length < 2) {
    return (
      <div className="flex h-12 items-center justify-center rounded-md bg-brand-100 text-xs text-brand-700">
        Loading chart…
      </div>
    );
  }

  const isPositive = points[points.length - 1].close >= points[0].close;
  const color = isPositive ? '#16a34a' : '#dc2626';

  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={points}>
        <defs>
          <linearGradient id={`tipGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#tipGrad-${ticker})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type Props = {
  contextTicker?: string;
  contextExchange?: string;
};

const ROTATE_MS = 7000;

export function InvestingTips({ contextTicker, contextExchange }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [paused, setPaused] = useState(false); // transient hover/focus pause
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  const { data: tips } = useQuery<InvestingTip[] | null>({
    queryKey: ['investing-tips'],
    queryFn: () => simulatorApi.getInvestingTips(),
    staleTime: 30 * 60 * 1000,
  });

  const count = tips?.length ?? 0;
  const autoRotate = isPlaying && !paused && !reducedMotion && count > 1;

  function scrollToIndex(i: number) {
    const el = scrollRef.current;
    if (el) el.scrollTo({ left: i * el.clientWidth * 0.65, behavior: 'smooth' });
  }

  function goToIndex(i: number) {
    setActiveIndex(i);
    scrollToIndex(i);
  }

  useEffect(() => {
    if (!autoRotate) return;
    const id = window.setInterval(() => {
      setActiveIndex((prev) => {
        const next = (prev + 1) % count;
        scrollToIndex(next);
        return next;
      });
    }, ROTATE_MS);
    return () => window.clearInterval(id);
  }, [autoRotate, count]);

  if (!tips) {
    return (
      <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-4">
        <div className="mb-3 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-brand-200" />
          <div className="h-4 w-28 animate-pulse rounded bg-brand-100" />
        </div>
        <div className="flex gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="min-w-[220px] rounded-xl border border-brand-200 bg-brand-50 p-3">
              <div className="mb-2 h-3 w-24 animate-pulse rounded bg-brand-200" />
              <div className="mb-1 h-2 w-full animate-pulse rounded bg-brand-100" />
              <div className="mb-2 h-2 w-3/4 animate-pulse rounded bg-brand-100" />
              <div className="h-12 animate-pulse rounded-md bg-brand-100" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (tips.length === 0) return null;

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, clientWidth } = scrollRef.current;
    const idx = Math.round(scrollLeft / (clientWidth * 0.65));
    setActiveIndex(Math.min(idx, tips.length - 1));
  };

  return (
    <div
      className="rounded-2xl border-2 border-brand-200 bg-white p-4"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
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
        onScroll={handleScroll}
        className="flex gap-3 overflow-x-auto scroll-smooth pb-2"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {tips.map((tip) => {
          const chartTicker = contextTicker ?? tip.example_ticker;
          const chartExchange = contextExchange ?? tip.example_exchange;
          return (
            <div
              key={tip.id}
              className="min-w-[220px] max-w-[260px] flex-shrink-0 rounded-xl border border-brand-200 bg-brand-50 p-3"
              style={{ scrollSnapAlign: 'start' }}
            >
              <h4 className="mb-1.5 text-xs font-bold text-brand-800">{tip.title}</h4>
              <p className="mb-2 text-xs leading-relaxed text-gray-700">{tip.description}</p>
              <div className="overflow-hidden rounded-md">
                <MiniChart exchange={chartExchange} ticker={chartTicker} />
              </div>
              <p className="mt-1 text-center text-[10px] text-gray-400">
                {chartTicker} · 5yr
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex justify-center gap-1">
        {tips.map((_, i) => (
          <button
            key={i}
            type="button"
            onClick={() => goToIndex(i)}
            aria-label={`Go to tip ${i + 1}`}
            aria-current={i === activeIndex}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                i === activeIndex ? 'bg-brand-500' : 'bg-gray-200'
              }`}
            />
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- InvestingTips`
Expected: PASS (6 tests).

- [ ] **Step 5: Typecheck + lint the changed files**

Run: `cd frontend && npx tsc -b && npm run lint`
Expected: tsc clean; lint 0 errors. (If `contextTicker`/`contextExchange` are flagged unused they are still used in the card map — they are; no change needed.)

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/simulator/InvestingTips.tsx frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): auto-rotate investing tips carousel (a11y)

The tips carousel now auto-advances every 7s and loops, with a play/pause
toggle and tappable dots (WCAG 2.2.2). Pauses on hover/focus; disabled and
control hidden under prefers-reduced-motion. FE-only — same /market/tips data.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Full frontend regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Full frontend gate**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: tsc clean; lint 0 errors (3 pre-existing fast-refresh warnings are unrelated); full vitest suite passes incl. the new `InvestingTips` tests; build succeeds.

- [ ] **Step 2: Push**

```bash
cd /Users/leeashmore/investikid && git push origin testing
```

- [ ] **Step 3: Report**

Report CI status on `testing` (frontend job in particular). No `cap sync` (the native app picks this up at the next scheduled iOS rebuild — out of scope). Do NOT promote to staging/main. Leave the unrelated `.gitignore` + iOS build-number working-tree changes uncommitted.

---

## Self-Review

**1. Spec coverage:**
- Auto-advance ~7s + loop → Task 1 (`ROTATE_MS`, interval effect, `% count`) + test "auto-advances…loops". ✓
- Play/pause toggle (WCAG 2.2.2), default playing → Task 1 (header `<button>` aria-label Pause/Play) + test "pause halts…play resumes". ✓
- Dots become buttons, ≥24px, aria-current, jump-to → Task 1 (`<button aria-label="Go to tip N" aria-current>` h-6 w-6 = 24px) + test "tapping a dot jumps". ✓
- Pause on hover/focus, explicit pause sticks → Task 1 (`paused` from mouseEnter/Leave + focus/blur; `autoRotate = isPlaying && !paused …`) + test "pauses while hovered". (Explicit-pause-sticks is covered by the `isPlaying` separation; the hover test + pause test together exercise both flags.) ✓
- prefers-reduced-motion disables + hides control → Task 1 (`useMediaQuery`, `autoRotate` includes `!reducedMotion`, control gated `!reducedMotion`) + test "under prefers-reduced-motion". ✓
- Reduced-motion detection via matchMedia/`useMediaQuery` → Task 1. ✓
- ≥16px iOS touch targets / semantic tokens → dots 24px, play/pause 28px, brand/gray tokens. ✓
- Tests: fake timers, mock getInvestingTips + getStockHistory, stub scrollTo + matchMedia, vitest-axe → Task 1 test file. ✓
- FE-only, no backend/endpoint/cap sync → no other files touched. ✓

**2. Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step has complete code. ✓

**3. Type consistency:** `goToIndex`/`scrollToIndex`/`activeIndex`/`isPlaying`/`paused`/`autoRotate`/`count`/`ROTATE_MS` are defined once and used consistently across the component and referenced by the tests via accessible names (`Go to tip N`, `Pause tips`/`Play tips`), not internals. `Props`, `MiniChart`, `simulatorApi.getInvestingTips/getStockHistory` match the existing module. ✓
