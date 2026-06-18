# Multi-Market Frontend Implementation Plan (Sub-project C2b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface C2a's multi-market backend in the UI — an active-market chip on Home, a "Choose your market" picker (GB learns, others "coming soon"), a coming-soon empty state, and per-market XP — in the sky-blue rebrand, fully i18n'd, with global engagement unchanged.

**Architecture:** Frontend-only on C2a's live APIs (`GET /markets`, `POST /me/active-market`, `GET /me/markets`, `active_market_code` on `/users/me`). A market API client + TanStack Query hooks (switch invalidates the content-driving queries), a `MarketChip` on Home, a `Markets` picker page, a `ComingSoonMarket` empty state reusing `<Penny>`, and a per-market XP breakdown on Stats. No backend changes, no migration.

**Tech Stack:** React 18 + Vite 7 + TypeScript + TanStack Query + Tailwind v4 + shadcn/ui + react-i18next + Capacitor iOS.

**Spec:** `docs/superpowers/specs/2026-06-18-multimarket-frontend-design.md`
**Branch:** `testing`. Frontend-only → no migration, no snapshot. Promote on green CI, then a manual Vercel prod deploy.

---

## File Structure

- Create `frontend/src/api/market.ts` — typed client (`list`/`progress`/`switch`).
- Create `frontend/src/hooks/useMarkets.ts` — `useMarkets`, `useMarketProgress`, `useSwitchMarket`.
- Create `frontend/src/lib/marketFlags.ts` — `MARKET_FLAGS` code→emoji map + `flagFor(code)`.
- Modify `frontend/src/api/auth.ts` — add `active_market_code` to `Me`.
- Create `frontend/src/components/child/MarketChip.tsx` — the Home header chip.
- Create `frontend/src/pages/child/Markets.tsx` — the picker screen (route `/markets`).
- Create `frontend/src/components/child/ComingSoonMarket.tsx` — empty state (uses `<Penny>`).
- Modify `frontend/src/pages/child/Home.tsx` — mount chip + coming-soon gate.
- Modify `frontend/src/pages/child/Stats.tsx` — "XP by market" breakdown.
- Modify `frontend/src/components/child/ProfileMenu.tsx` — link to the picker.
- Modify `frontend/src/App.tsx` — `/markets` route under `<Shell/>`.
- Create `frontend/src/locales/en/markets.json` + register `'markets'` in `src/i18n/index.ts` `NAMESPACES`.
- Tests under `frontend/tests/unit/` and component `__tests__/`.

---

### Task 1: Market API client + hooks + `Me.active_market_code` + i18n namespace

**Files:**
- Create: `frontend/src/api/market.ts`, `frontend/src/hooks/useMarkets.ts`, `frontend/src/lib/marketFlags.ts`, `frontend/src/locales/en/markets.json`
- Modify: `frontend/src/api/auth.ts`, `frontend/src/i18n/index.ts`
- Test: `frontend/tests/unit/useMarkets.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/useMarkets.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../src/api/market', () => ({
  marketApi: {
    list: vi.fn().mockResolvedValue([{ code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true }]),
    progress: vi.fn(),
    switch: vi.fn().mockResolvedValue({ active_market_code: 'US' }),
  },
}));

import { marketApi } from '../../src/api/market';
import { useSwitchMarket } from '../../src/hooks/useMarkets';

function wrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('useSwitchMarket', () => {
  it('posts the code and invalidates content queries', async () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useSwitchMarket(), { wrapper: wrapper(qc) });
    await act(async () => { await result.current.mutateAsync('US'); });
    expect(marketApi.switch).toHaveBeenCalledWith('US');
    const invalidated = spy.mock.calls.map((c) => (c[0] as { queryKey: string[] }).queryKey[0]);
    for (const k of ['me', 'modules', 'recommendations', 'next-lesson']) {
      expect(invalidated).toContain(k);
    }
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run tests/unit/useMarkets.test.tsx`
Expected: FAIL (no `useMarkets`/`market` module).

- [ ] **Step 3: Create the API client**

Create `frontend/src/api/market.ts`:

```typescript
import { apiFetch } from './client';

export type MarketSummary = {
  code: string;
  name: string;
  currency_code: string;
  has_content: boolean;
  enrolled: boolean;
  is_selected: boolean;
};

export type MarketProgress = {
  markets: { market_code: string; xp: number }[];
  total_xp: number;
  level: number;
};

export const marketApi = {
  list: () => apiFetch<MarketSummary[]>('/markets'),
  progress: () => apiFetch<MarketProgress>('/me/markets'),
  switch: (market_code: string) =>
    apiFetch<{ active_market_code: string }>('/me/active-market', {
      method: 'POST',
      body: JSON.stringify({ market_code }),
    }),
};
```

- [ ] **Step 4: Create the hooks**

Create `frontend/src/hooks/useMarkets.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { marketApi, type MarketProgress, type MarketSummary } from '../api/market';

// Queries whose results depend on the active market — invalidated on switch so
// the curriculum + Revise + recommendations re-filter (mirrors RegionSwitcher).
const CONTENT_KEYS: string[][] = [
  ['me'], ['markets'], ['me', 'markets'],
  ['modules'], ['module-levels'], ['level-lessons'],
  ['recommendations'], ['next-lesson'],
  ['revise'], ['revise-session'], ['revise-due'],
];

export function useMarkets() {
  return useQuery<MarketSummary[] | null>({ queryKey: ['markets'], queryFn: () => marketApi.list(), staleTime: 5 * 60_000 });
}

export function useMarketProgress() {
  return useQuery<MarketProgress | null>({ queryKey: ['me', 'markets'], queryFn: () => marketApi.progress(), staleTime: 60_000 });
}

export function useSwitchMarket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (market_code: string) => marketApi.switch(market_code),
    onSuccess: () => {
      for (const key of CONTENT_KEYS) qc.invalidateQueries({ queryKey: key });
    },
  });
}
```

> The exact revise/content query keys may differ — grep the codebase (`grep -rn "queryKey:" src/pages/child/Revise* src/hooks` and the modules/recommendations hooks) and include the REAL keys those queries use, so invalidation actually re-fetches. Keep `['me']`, `['markets']`, `['me','markets']` plus every content/Revise key. The test asserts `me/modules/recommendations/next-lesson` are present.

- [ ] **Step 5: Flag map + `Me` field + i18n namespace**

Create `frontend/src/lib/marketFlags.ts`:

```typescript
// Flag emoji per ISO market code (mirrors the simulator RegionSwitcher's flags).
export const MARKET_FLAGS: Record<string, string> = {
  GB: '🇬🇧', US: '🇺🇸', AU: '🇦🇺', CA: '🇨🇦', IE: '🇮🇪',
  ES: '🇪🇸', FR: '🇫🇷', DE: '🇩🇪', HK: '🇭🇰', SG: '🇸🇬',
};

export const flagFor = (code: string): string => MARKET_FLAGS[code] ?? code;
```

In `frontend/src/api/auth.ts`, add `active_market_code?: string;` to the `Me` type (after `currency_code`).

Create `frontend/src/locales/en/markets.json`:

```json
{
  "chip": { "label": "Change learning market" },
  "picker": {
    "title": "Choose your market",
    "subtitle": "Pick where you want to learn about money. You can switch anytime.",
    "learning": "Learning",
    "comingSoon": "Coming soon"
  },
  "comingSoon": {
    "title": "New lessons for {{market}} are on the way!",
    "body": "We're building this market's money lessons. In the meantime, keep learning in {{home}}.",
    "switchBack": "Switch back to {{home}}"
  },
  "stats": { "byMarket": "XP by market" }
}
```

In `frontend/src/i18n/index.ts`, add `'markets'` to the `NAMESPACES` array.

- [ ] **Step 6: Verify + commit**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run tests/unit/useMarkets.test.tsx && npx tsc -b && npm run lint`
Expected: PASS; tsc clean; lint clean (locale JSON is exempt from `no-literal-string`).

```bash
cd "/Users/leeashmore/investikid" && git add frontend/src/api/market.ts frontend/src/hooks/useMarkets.ts frontend/src/lib/marketFlags.ts frontend/src/api/auth.ts frontend/src/locales/en/markets.json frontend/src/i18n/index.ts frontend/tests/unit/useMarkets.test.tsx && git commit -m "feat(market): market API client + hooks + flags + markets i18n namespace

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `MarketChip` + mount on Home

**Files:**
- Create: `frontend/src/components/child/MarketChip.tsx`
- Modify: `frontend/src/pages/child/Home.tsx` (or `HomeHero.tsx` header)
- Test: `frontend/src/components/child/__tests__/MarketChip.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/child/__tests__/MarketChip.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [{ code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true }] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { MarketChip } from '../MarketChip';

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

describe('MarketChip', () => {
  it('shows the active market name and links to the picker', () => {
    render(wrap(<MarketChip activeCode="GB" />));
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /change learning market|united kingdom/i })).toHaveAttribute('href', '/markets');
  });
  it('has no a11y violations', async () => {
    const { container } = render(wrap(<MarketChip activeCode="GB" />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

> Adapt the role/markup to your implementation (a `<Link>` is a `link` role). If you implement the chip as a button that navigates, assert `role: button` + an `onClick`/navigate spy instead — keep the assertion consistent with the component.

- [ ] **Step 2: Run it — FAIL** (no `MarketChip`).

- [ ] **Step 3: Implement `MarketChip`**

Create `frontend/src/components/child/MarketChip.tsx` (sky-blue tokens; ≥44px; labelled). Read an existing small control (e.g. `RegionSwitcher`/`LanguageSwitcher`) to match class style:

```typescript
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMarkets } from '../../hooks/useMarkets';
import { flagFor } from '../../lib/marketFlags';

export function MarketChip({ activeCode }: { activeCode: string }) {
  const { t } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const active = markets?.find((m) => m.code === activeCode);
  const name = active?.name ?? activeCode;
  return (
    <Link
      to="/markets"
      aria-label={t('chip.label')}
      className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-brand-100 bg-white px-3 py-2 text-sm font-semibold text-brand-800"
    >
      <span aria-hidden="true">{flagFor(activeCode)}</span>
      <span>{name}</span>
      <span aria-hidden="true" className="text-muted-foreground">⌄</span>
    </Link>
  );
}
```

> Use the codebase's real brand utility classes (grep `RegionSwitcher.tsx`/`HomeHero.tsx` for `brand-`/`bg-card`/`text-`); the names above (`border-brand-100`, `text-brand-800`) follow the sky-blue ramp — adjust to the actual Tailwind tokens.

- [ ] **Step 4: Mount on Home**

Read `frontend/src/pages/child/Home.tsx` (and `HomeHero.tsx`). Render `<MarketChip activeCode={me?.active_market_code ?? 'GB'} />` in the Home header next to the greeting (the `me` object is already fetched via `useQuery<Me>` in Home; `active_market_code` was added to `Me` in Task 1). Place it where the mockup shows (top-right of the header row).

- [ ] **Step 5: Verify + commit**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run src/components/child/__tests__/MarketChip.test.tsx && npx tsc -b && npm run lint`
Expected: PASS; clean.

```bash
cd "/Users/leeashmore/investikid" && git add frontend/src/components/child/MarketChip.tsx frontend/src/pages/child/Home.tsx frontend/src/components/child/__tests__/MarketChip.test.tsx && git commit -m "feat(market): active-market chip on Home header

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: "Choose your market" picker page + route + settings link

**Files:**
- Create: `frontend/src/pages/child/Markets.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/child/ProfileMenu.tsx`
- Test: `frontend/src/pages/child/__tests__/Markets.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/child/__tests__/Markets.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const switchMock = vi.fn().mockResolvedValue({ active_market_code: 'US' });
vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: false, is_selected: false },
  ] }),
  useSwitchMarket: () => ({ mutate: switchMock, isPending: false }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { Markets } from '../Markets';

function wrap() {
  return <QueryClientProvider client={new QueryClient()}><MemoryRouter><Markets /></MemoryRouter></QueryClientProvider>;
}

describe('Markets picker', () => {
  it('lists all markets; selected shows Learning, empty shows Coming soon, both tappable', () => {
    render(wrap());
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
    expect(screen.getByText('picker.learning')).toBeInTheDocument();      // GB selected
    expect(screen.getByText('picker.comingSoon')).toBeInTheDocument();    // US coming soon
  });
  it('tapping a market switches to it', () => {
    render(wrap());
    fireEvent.click(screen.getByText('United States'));
    expect(switchMock).toHaveBeenCalledWith('US');
  });
});
```

- [ ] **Step 2: Run it — FAIL** (no `Markets`).

- [ ] **Step 3: Implement the picker**

Create `frontend/src/pages/child/Markets.tsx` (sky-blue cards per the approved mockup; flag chip + name + currency; selected = brand border + "Learning" pill; others = muted "Coming soon" pill, still tappable; back control; navigate Home after switch). Mirror the card/list styling from the mockup and existing card components. Use `useNavigate()` to go to `/` (or back) on a successful switch. Each market card is a `<button>` (role button, ≥44px, `aria-pressed={is_selected}`). Use `flagFor(code)`, `t('markets:…')`. (Provide the full JSX in the component, following the existing page layout pattern — header with back, then the list.)

- [ ] **Step 4: Route + settings link**

In `frontend/src/App.tsx`, add `<Route path="/markets" element={<Markets />} />` INSIDE the `<Shell/>` group (with the other child routes) + the import. In `frontend/src/components/child/ProfileMenu.tsx`, add a row/link to `/markets` ("Learning market") near the `LanguageSwitcher` (mirror how other settings rows link/navigate).

- [ ] **Step 5: Verify + commit**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run src/pages/child/__tests__/Markets.test.tsx && npx tsc -b && npm run lint`
Expected: PASS; clean.

```bash
cd "/Users/leeashmore/investikid" && git add frontend/src/pages/child/Markets.tsx frontend/src/App.tsx frontend/src/components/child/ProfileMenu.tsx frontend/src/pages/child/__tests__/Markets.test.tsx && git commit -m "feat(market): Choose your market picker page + route + settings link

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Coming-soon empty state + Home gate

**Files:**
- Create: `frontend/src/components/child/ComingSoonMarket.tsx`
- Modify: `frontend/src/pages/child/Home.tsx`
- Test: `frontend/src/components/child/__tests__/ComingSoonMarket.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/child/__tests__/ComingSoonMarket.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

const switchMock = vi.fn();
vi.mock('../../../hooks/useMarkets', () => ({
  useSwitchMarket: () => ({ mutate: switchMock, isPending: false }),
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: false },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: true, is_selected: true },
  ] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, string>) => (o ? `${k} ${JSON.stringify(o)}` : k) }) }));

import { ComingSoonMarket } from '../ComingSoonMarket';

describe('ComingSoonMarket', () => {
  it('switch-back CTA targets the content-ready (GB) market', () => {
    render(<ComingSoonMarket marketName="United States" />);
    fireEvent.click(screen.getByRole('button', { name: /switchBack/i }));
    expect(switchMock).toHaveBeenCalledWith('GB');
  });
  it('has no a11y violations', async () => {
    const { container } = render(<ComingSoonMarket marketName="United States" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run it — FAIL** (no `ComingSoonMarket`).

- [ ] **Step 3: Implement**

Create `frontend/src/components/child/ComingSoonMarket.tsx`:

```typescript
import { useTranslation } from 'react-i18next';
import { Penny } from './ui/Penny';
import { useMarkets, useSwitchMarket } from '../../hooks/useMarkets';

export function ComingSoonMarket({ marketName }: { marketName: string }) {
  const { t } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const switchMarket = useSwitchMarket();
  const home = markets?.find((m) => m.has_content); // the content-ready market (GB)

  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-brand-100 bg-white p-7 text-center">
      <Penny size={72} mood="thinking" />
      <p className="text-base font-bold text-gray-900">{t('comingSoon.title', { market: marketName })}</p>
      <p className="text-sm text-muted-foreground">{t('comingSoon.body', { home: home?.name ?? 'United Kingdom' })}</p>
      {home && (
        <button
          type="button"
          onClick={() => switchMarket.mutate(home.code)}
          disabled={switchMarket.isPending}
          className="min-h-[44px] rounded-full bg-brand-600 px-5 py-2.5 text-sm font-bold text-white"
        >
          {t('comingSoon.switchBack', { home: home.name })}
        </button>
      )}
    </div>
  );
}
```

> Adjust class tokens to the real sky-blue Tailwind utilities (grep an existing brand button, e.g. in `HomeHero`/`RegionSwitcher`). Keep `<Penny>` (size ~72, `mood="thinking"`).

- [ ] **Step 4: Gate it into Home**

In `frontend/src/pages/child/Home.tsx`: derive the active market from `useMarkets()` (`is_selected`) or `me.active_market_code`. If the active market's `has_content === false`, render `<ComingSoonMarket marketName={activeName} />` in place of the lesson/module content (keep the header, chip, and global engagement display visible). Read Home.tsx to find the content block to conditionally swap.

- [ ] **Step 5: Verify + commit**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run src/components/child/__tests__/ComingSoonMarket.test.tsx && npx tsc -b && npm run lint`
Expected: PASS; clean.

```bash
cd "/Users/leeashmore/investikid" && git add frontend/src/components/child/ComingSoonMarket.tsx frontend/src/pages/child/Home.tsx frontend/src/components/child/__tests__/ComingSoonMarket.test.tsx && git commit -m "feat(market): coming-soon empty state (Penny) + Home gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Per-market XP on Home + "XP by market" on Stats

**Files:**
- Modify: `frontend/src/pages/child/Home.tsx` (active-market XP), `frontend/src/pages/child/Stats.tsx` (breakdown)
- Test: `frontend/src/pages/child/__tests__/StatsMarkets.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/child/__tests__/StatsMarkets.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../../hooks/useMarkets', () => ({
  useMarketProgress: () => ({ data: { markets: [{ market_code: 'GB', xp: 110 }, { market_code: 'US', xp: 20 }], total_xp: 130, level: 2 } }),
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: true, is_selected: false },
  ] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { MarketXpBreakdown } from '../../../components/child/MarketXpBreakdown';

describe('MarketXpBreakdown', () => {
  it('lists per-market XP with market names', () => {
    render(<MarketXpBreakdown />);
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByText('110')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it — FAIL** (no `MarketXpBreakdown`).

- [ ] **Step 3: Implement the breakdown component**

Create `frontend/src/components/child/MarketXpBreakdown.tsx`:

```typescript
import { useTranslation } from 'react-i18next';
import { useMarketProgress, useMarkets } from '../../hooks/useMarkets';
import { flagFor } from '../../lib/marketFlags';

export function MarketXpBreakdown() {
  const { t } = useTranslation('markets');
  const { data: progress } = useMarketProgress();
  const { data: markets } = useMarkets();
  const rows = progress?.markets ?? [];
  if (rows.length === 0) return null;
  const nameFor = (code: string) => markets?.find((m) => m.code === code)?.name ?? code;
  return (
    <section aria-label={t('stats.byMarket')} className="rounded-2xl border border-brand-100 bg-white p-4">
      <h3 className="mb-2 text-sm font-bold text-gray-900">{t('stats.byMarket')}</h3>
      <ul className="space-y-1.5">
        {rows.map((r) => (
          <li key={r.market_code} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span aria-hidden="true">{flagFor(r.market_code)}</span>
              <span className="font-medium text-gray-800">{nameFor(r.market_code)}</span>
            </span>
            <span className="font-bold text-brand-700">{r.xp}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

> Match the real brand classes. Then **mount `<MarketXpBreakdown />` in `Stats.tsx`** under the global headline (read Stats.tsx for the insertion point). On **Home**, surface the active market's XP from `useMarketProgress()` next to the existing global level/streak (read Home/HomeHero to add it without changing the global engagement display).

- [ ] **Step 4: Verify + commit**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx vitest run src/pages/child/__tests__/StatsMarkets.test.tsx && npx tsc -b && npm run lint`
Expected: PASS; clean.

```bash
cd "/Users/leeashmore/investikid" && git add frontend/src/components/child/MarketXpBreakdown.tsx frontend/src/pages/child/Stats.tsx frontend/src/pages/child/Home.tsx frontend/src/pages/child/__tests__/StatsMarkets.test.tsx && git commit -m "feat(market): per-market XP on Home + 'XP by market' on Stats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full verification (incl. running-app screenshots) + promote

- [ ] **Step 1: Full frontend verification**

Run: `cd "/Users/leeashmore/investikid/frontend" && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green. `npm run lint` enforces `no-literal-string` (error) — every new string must be in `markets.json` (or another catalog); fix any literal it flags.

- [ ] **Step 2: Regression sanity**

Confirm a default (GB, active=home) user sees Home/Stats unchanged: the chip shows United Kingdom, no coming-soon state, content + global level/streak/coins identical. Existing Home/Stats/ProfileMenu tests stay green (run the full `npm run test`).

- [ ] **Step 3: Run the app + screenshot the real screens**

Run the dev app (`npm run dev`) or build+preview, and capture screenshots of: the Home chip, the "Choose your market" picker (GB Learning + others coming-soon), the coming-soon state (switch active to US via the picker, then Home), and the Stats "XP by market". Send them to the user to confirm the sky-blue look matches the rebrand before promoting. Fix any visual mismatch.

- [ ] **Step 4: iOS sync (UI-visible)**

Run: `cd "/Users/leeashmore/investikid/frontend" && npm run build && npx cap sync ios`. Rebuild in Xcode; confirm the chip/picker/coming-soon render and ≥16px controls in the WKWebView.

- [ ] **Step 5: Push to testing + green CI**

```bash
git push origin testing
```
Watch all 6 CI jobs green (Frontend, A11y, Responsive especially).

- [ ] **Step 6: Promote + Vercel deploy**

Merge testing → staging (watch CI green), then staging → main (watch CI green). **No DB migration → no snapshot question.** Then run the **manual Vercel prod web deploy** from the repo root (`vercel deploy --prod --archive=tgz --yes`), confirm it aliases to `app.investikid.ai`, and verify the chip + picker render in prod.

---

## Self-Review

**Spec coverage:**
- Unit 1 market API client + hooks (switch invalidation) → Task 1. ✓
- Unit 2 active-market chip on Home → Task 2. ✓
- Unit 3 "Choose your market" picker + route + settings link → Task 3. ✓
- Unit 4 coming-soon empty state (reuses `<Penny>`) + Home gate → Task 4. ✓
- Unit 5 per-market XP on Home + "XP by market" on Stats → Task 5. ✓
- Unit 6 i18n (`markets` namespace) + a11y (`vitest-axe` on chip/picker/coming-soon) → Tasks 1–5 (namespace in Task 1; axe tests in Tasks 2 & 4; picker cards keyboard/labelled in Task 3). ✓
- Non-goals respected: no backend changes, no migration, no currency-follows-market, no simulator-region unification, no new Penny artwork (reuses `<Penny>`). ✓
- Sky-blue rebrand via live tokens + running-app screenshot verification → Task 6 Step 3. ✓
- Rollout: frontend-only, no snapshot, CI + Vercel → Task 6. ✓

**Placeholder scan:** no TBD/TODO; full code for the API client, hooks, flag map, i18n catalog, `MarketChip`, `ComingSoonMarket`, `MarketXpBreakdown`. The picker page JSX and the Home/Stats integration points are precise read-then-mount instructions (the exact host-file internals vary; the implementer mounts at the identified spots) — consistent with how this codebase's plans handle integration into existing screens.

**Type/name consistency:** `MarketSummary`/`MarketProgress` (Task 1) used in hooks (Task 1) and all components (Tasks 2–5); `useMarkets`/`useMarketProgress`/`useSwitchMarket` (Task 1) consumed in Tasks 2–5; `flagFor` (Task 1) used in Tasks 2, 5; `Me.active_market_code` (Task 1) read in Tasks 2, 4; `markets` i18n namespace + keys (`chip.label`, `picker.*`, `comingSoon.*`, `stats.byMarket`) defined in Task 1 and used in Tasks 2–5; `<Penny>` props (`size`/`mood`) match the real component. Consistent.
