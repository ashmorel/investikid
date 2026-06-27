# Offline Support — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make previously-seen content reliably usable offline with automatic sync on reconnect and an "as of <time>" freshness label on cached prices.

**Architecture:** Wire `@capacitor/network` into TanStack Query's `onlineManager` (reliable WKWebView detection + auto pause-offline/refetch-on-reconnect) with `useOnline` reading the same source; fix the persistence allowlist to match the real query keys; add a `<StaleAsOf>` label shown only while offline on the price surfaces.

**Tech Stack:** React 18, TanStack Query 5 (`onlineManager`, persistence), Capacitor 8 (`@capacitor/network`), Vite, TypeScript, vitest.

## Global Constraints

- Frontend-only. The single new dependency is `@capacitor/network` (Capacitor-maintained; has a web implementation). No backend changes.
- One source of truth for connectivity: TanStack's `onlineManager`. `useOnline()` reads from it; `@capacitor/network` feeds it. Public hook signature stays `(): boolean`.
- Persist allowlist (`PERSISTED_QUERY_KEYS` heads) becomes: `modules, module-levels, level-lessons, lesson, module, me, progress, portfolio, trade-config, market-snapshot, quote, trades, stock-history`. Remove `market-movers`. Keep excluding `market-search`, news/news-summary, coach/tutor, admin/parent.
- `StaleAsOf` renders ONLY when offline AND `updatedAt > 0`; copy `Prices as of {{time}}`; `time` = local time if today, else `Mon D, time`. i18n: namespace `simulator` (the ns Market/Stock already use), top-level key `pricesAsOf` in `src/locales/en/simulator.json`.
- Offline is READ-only in Phase 1 (no offline trades). PWA/question-banks/sync-outbox/SQLite are out of scope (Phases 2/3).
- Verify: `npx tsc --noEmit` + `npx eslint <files>` (0 errors) + `npx vitest run <files>` + `npm run build`. New UI gets a vitest test. Known baseline: `tests/unit/api-*.test.ts` and other `*.offline`/`child-*` failures are pre-existing local-env (prod-API-base `.env`); verify only target files and compare against clean HEAD if unsure.
- Commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. iOS-visible native changes need `npx cap sync ios`.

---

## File Structure

- `frontend/package.json` (modify) — add `@capacitor/network`.
- `frontend/src/lib/connectivity.ts` (create) — `initConnectivity()` feeding `onlineManager` from `@capacitor/network`.
- `frontend/src/main.tsx` (modify) — call `initConnectivity()` at boot.
- `frontend/src/hooks/useOnline.ts` (modify) — read from `onlineManager`.
- `frontend/src/lib/queryPersistence.ts` (modify) — allowlist fix.
- `frontend/src/components/child/StaleAsOf.tsx` (create) — offline freshness label + `formatAsOf`.
- `frontend/src/pages/child/Market.tsx`, `frontend/src/pages/child/Stock.tsx` (modify) — mount `<StaleAsOf>`.
- `frontend/src/locales/en/simulator.json` (modify) — `simulator.pricesAsOf` key.
- Tests alongside each.

---

## Task 1: Connectivity — `@capacitor/network` → `onlineManager`

**Files:**
- Modify: `frontend/package.json` (add dep)
- Create: `frontend/src/lib/connectivity.ts`
- Modify: `frontend/src/main.tsx`, `frontend/src/hooks/useOnline.ts`
- Test: `frontend/src/lib/__tests__/connectivity.test.ts` (create), `frontend/src/hooks/__tests__/useOnline.test.ts` (create or extend)

**Interfaces:**
- Produces: `initConnectivity(): Promise<void>`; `useOnline(): boolean` (now backed by `onlineManager`).
- Consumes: `onlineManager` from `@tanstack/react-query`; `Network` from `@capacitor/network`.

- [ ] **Step 1: Install the dependency**

```bash
cd frontend && npm install @capacitor/network@^8
```
Expected: `@capacitor/network` added to `package.json` dependencies.

- [ ] **Step 2: Write the failing connectivity test**

```ts
// frontend/src/lib/__tests__/connectivity.test.ts
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { onlineManager } from '@tanstack/react-query';

const listeners: Array<(s: { connected: boolean }) => void> = [];
vi.mock('@capacitor/network', () => ({
  Network: {
    getStatus: vi.fn(async () => ({ connected: false })),
    addListener: vi.fn((_e: string, cb: (s: { connected: boolean }) => void) => {
      listeners.push(cb);
      return Promise.resolve({ remove: vi.fn() });
    }),
  },
}));

import { initConnectivity } from '../connectivity';

describe('initConnectivity', () => {
  beforeEach(() => { listeners.length = 0; onlineManager.setOnline(true); });

  it('seeds onlineManager from Network.getStatus and updates on change', async () => {
    await initConnectivity();
    expect(onlineManager.isOnline()).toBe(false);   // seeded from getStatus
    listeners[0]({ connected: true });               // simulate reconnect
    expect(onlineManager.isOnline()).toBe(true);
  });

  it('swallows a plugin error and leaves onlineManager usable', async () => {
    const { Network } = await import('@capacitor/network');
    (Network.getStatus as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('no plugin'));
    await expect(initConnectivity()).resolves.toBeUndefined();
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd frontend && npx vitest run src/lib/__tests__/connectivity.test.ts`
Expected: FAIL (`../connectivity` not found).

- [ ] **Step 4: Implement `connectivity.ts`**

```ts
// frontend/src/lib/connectivity.ts
import { onlineManager } from '@tanstack/react-query';
import { Network } from '@capacitor/network';

/**
 * Feed TanStack Query's onlineManager from @capacitor/network. On iOS WKWebView
 * navigator.onLine is unreliable; the native plugin uses the OS connectivity
 * API (and a web implementation on the web build). Wiring onlineManager makes
 * queries pause offline and auto-refetch stale data on reconnect. Best-effort:
 * any failure leaves onlineManager on its navigator.onLine-based default.
 */
export async function initConnectivity(): Promise<void> {
  try {
    const status = await Network.getStatus();
    onlineManager.setOnline(status.connected);
    void Network.addListener('networkStatusChange', (s) => {
      onlineManager.setOnline(s.connected);
    });
  } catch {
    // plugin unavailable — keep onlineManager's default detection
  }
}
```

- [ ] **Step 5: Refactor `useOnline.ts` to read from onlineManager**

```ts
// frontend/src/hooks/useOnline.ts
import { useSyncExternalStore } from 'react';
import { onlineManager } from '@tanstack/react-query';

function subscribe(onChange: () => void) {
  return onlineManager.subscribe(() => onChange());
}

function getSnapshot() {
  return onlineManager.isOnline();
}

/** True while TanStack's onlineManager reports connectivity (fed by
 * @capacitor/network — see lib/connectivity.ts). */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
```

- [ ] **Step 6: Write/extend the useOnline test**

```ts
// frontend/src/hooks/__tests__/useOnline.test.ts
import { renderHook, act } from '@testing-library/react';
import { onlineManager } from '@tanstack/react-query';
import { useOnline } from '../useOnline';

it('reflects onlineManager transitions', () => {
  onlineManager.setOnline(true);
  const { result } = renderHook(() => useOnline());
  expect(result.current).toBe(true);
  act(() => onlineManager.setOnline(false));
  expect(result.current).toBe(false);
  act(() => onlineManager.setOnline(true));
  expect(result.current).toBe(true);
});
```

- [ ] **Step 7: Wire `initConnectivity()` into `main.tsx`**

After `const persister = createAppPersister();` add:
```ts
import { initConnectivity } from './lib/connectivity';
// ...
void initConnectivity();
```

- [ ] **Step 8: Run tests + tsc + lint + build + cap sync**

Run: `cd frontend && npx vitest run src/lib/__tests__/connectivity.test.ts src/hooks/__tests__/useOnline.test.ts && npx tsc --noEmit && npx eslint src/lib/connectivity.ts src/hooks/useOnline.ts src/main.tsx && npm run build && npx cap sync ios && npx cap sync android`
Expected: tests PASS, tsc/lint clean, build ok, cap sync registers `@capacitor/network` on both platforms.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/lib/connectivity.ts frontend/src/hooks/useOnline.ts frontend/src/main.tsx frontend/src/lib/__tests__/connectivity.test.ts frontend/src/hooks/__tests__/useOnline.test.ts frontend/ios frontend/android
git commit -m "feat(offline): @capacitor/network → onlineManager + useOnline (Goal4 P1)"
```

---

## Task 2: Persistence allowlist fix

**Files:**
- Modify: `frontend/src/lib/queryPersistence.ts`
- Test: `frontend/src/lib/__tests__/queryPersistence.test.ts` (extend)

**Interfaces:**
- Consumes/produces: `PERSISTED_QUERY_KEYS`, `shouldDehydrateQuery` (signatures unchanged).

- [ ] **Step 1: Write the failing test**

```ts
// add to frontend/src/lib/__tests__/queryPersistence.test.ts
import type { Query } from '@tanstack/react-query';
import { shouldDehydrateQuery, PERSISTED_QUERY_KEYS } from '../queryPersistence';

function q(key: unknown[], status = 'success'): Query {
  return { state: { status }, queryKey: key } as unknown as Query;
}

it('persists the current simulator + content keys, drops dead/excluded ones', () => {
  for (const head of ['market-snapshot', 'quote', 'trades', 'stock-history', 'portfolio', 'lesson', 'me']) {
    expect(shouldDehydrateQuery(q([head, 'x']))).toBe(true);
  }
  expect(shouldDehydrateQuery(q(['market-movers', 'US']))).toBe(false); // dead key removed
  expect(shouldDehydrateQuery(q(['market-search', 'aapl']))).toBe(false); // excluded
  expect(shouldDehydrateQuery(q(['coach']))).toBe(false);                 // excluded
  expect(shouldDehydrateQuery(q(['quote', 'x'], 'error'))).toBe(false);   // non-success
  expect(PERSISTED_QUERY_KEYS).not.toContain('market-movers');
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run src/lib/__tests__/queryPersistence.test.ts`
Expected: FAIL (`market-snapshot`/`quote`/`trades`/`stock-history` not persisted; `market-movers` still present).

- [ ] **Step 3: Implement the allowlist change**

In `frontend/src/lib/queryPersistence.ts`, replace the `PERSISTED_QUERY_KEYS` array with:
```ts
export const PERSISTED_QUERY_KEYS: readonly string[] = [
  'modules',
  'module-levels',
  'level-lessons',
  'lesson',
  'module',
  'me',
  'progress',
  'portfolio',
  'trade-config',
  // Simulator data the child has already seen — kept readable offline.
  // `market-movers` was removed (dead after Goal 5; the Simulator now reads
  // `market-snapshot`). `market-search` / news / coach stay excluded.
  'market-snapshot',
  'quote',
  'trades',
  'stock-history',
];
```

- [ ] **Step 4: Run tests** — `npx vitest run src/lib/__tests__/queryPersistence.test.ts` → PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd frontend && npx eslint src/lib/queryPersistence.ts
git add frontend/src/lib/queryPersistence.ts frontend/src/lib/__tests__/queryPersistence.test.ts
git commit -m "fix(offline): persist market-snapshot/quote/trades/stock-history, drop dead market-movers (Goal4 P1)"
```

---

## Task 3: `StaleAsOf` offline freshness label

**Files:**
- Create: `frontend/src/components/child/StaleAsOf.tsx`
- Modify: `frontend/src/pages/child/Market.tsx`, `frontend/src/pages/child/Stock.tsx`, `frontend/src/locales/en/simulator.json`
- Test: `frontend/src/components/child/__tests__/StaleAsOf.test.tsx` (create)

**Interfaces:**
- Consumes: `useOnline()` (Task 1); `useTranslation('child')`.
- Produces: `StaleAsOf({ updatedAt: number, className?: string })`; `formatAsOf(updatedAt: number, now?: Date): string`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/child/__tests__/StaleAsOf.test.tsx
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { I18nextProvider } from 'react-i18next';
import { i18n } from '@/i18n';
import { StaleAsOf, formatAsOf } from '../StaleAsOf';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn() }));
import { useOnline } from '@/hooks/useOnline';
const mockOnline = vi.mocked(useOnline);

function renderLabel(updatedAt: number) {
  return render(<I18nextProvider i18n={i18n}><StaleAsOf updatedAt={updatedAt} /></I18nextProvider>);
}

describe('formatAsOf', () => {
  it('shows time only for today, date+time otherwise', () => {
    const now = new Date('2026-06-27T15:00:00');
    expect(formatAsOf(new Date('2026-06-27T14:34:00').getTime(), now)).toMatch(/2:34/);
    expect(formatAsOf(new Date('2026-06-26T14:34:00').getTime(), now)).toMatch(/Jun 26/);
  });
});

describe('StaleAsOf', () => {
  it('shows "Prices as of <time>" when offline with data', () => {
    mockOnline.mockReturnValue(false);
    renderLabel(new Date('2026-06-27T14:34:00').getTime());
    expect(screen.getByText(/Prices as of/i)).toBeInTheDocument();
  });
  it('renders nothing when online', () => {
    mockOnline.mockReturnValue(true);
    const { container } = renderLabel(Date.now());
    expect(container).toBeEmptyDOMElement();
  });
  it('renders nothing when there is no cached data', () => {
    mockOnline.mockReturnValue(false);
    const { container } = renderLabel(0);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run src/components/child/__tests__/StaleAsOf.test.tsx`
Expected: FAIL (`../StaleAsOf` not found).

- [ ] **Step 3: Add the i18n key**

In `frontend/src/locales/en/simulator.json` (the `simulator` namespace; Market/Stock use `useTranslation('simulator')`), add a top-level key (sibling of `portfolio`/`market`):
```json
"pricesAsOf": "Prices as of {{time}}",
```

- [ ] **Step 4: Implement `StaleAsOf.tsx`**

```tsx
// frontend/src/components/child/StaleAsOf.tsx
import { useTranslation } from 'react-i18next';
import { useOnline } from '@/hooks/useOnline';

/** Local "as of" string: time only if today, else "Mon D, time". */
export function formatAsOf(updatedAt: number, now: Date = new Date()): string {
  const d = new Date(updatedAt);
  const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  if (d.toDateString() === now.toDateString()) return time;
  return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${time}`;
}

/** Freshness caveat shown ONLY while offline and only when data exists. */
export function StaleAsOf({ updatedAt, className }: { updatedAt: number; className?: string }) {
  const online = useOnline();
  const { t } = useTranslation('simulator');
  if (online || !updatedAt) return null;
  return (
    <p className={className ?? 'text-xs text-muted-foreground'}>
      {t('pricesAsOf', { time: formatAsOf(updatedAt) })}
    </p>
  );
}
```

- [ ] **Step 5: Mount on Stock.tsx**

In `frontend/src/pages/child/Stock.tsx`, import `StaleAsOf` and render it using the quote query's `dataUpdatedAt` near the price/`OfflineNotice`:
```tsx
import { StaleAsOf } from '@/components/child/StaleAsOf';
// quoteQ already exists: const quoteQ = useQuery(['quote', exchange, ticker], ...)
// near the price block:
<StaleAsOf updatedAt={quoteQ.dataUpdatedAt} />
```

- [ ] **Step 6: Mount on Market.tsx**

In `frontend/src/pages/child/Market.tsx`, capture `dataUpdatedAt` from the snapshot query and render the label above the featured grid:
```tsx
const { data: snapshot, isLoading: featuredLoading, dataUpdatedAt } = useQuery<MarketSnapshot | null>({
  queryKey: ['market-snapshot', region],
  queryFn: () => simulatorApi.getSnapshot(region),
  retry: false, staleTime: 5 * 60 * 1000, gcTime: 10 * 60 * 1000,
});
// near the featured grid heading:
<StaleAsOf updatedAt={dataUpdatedAt} />
```
(import `StaleAsOf` at the top.)

- [ ] **Step 7: Run tests + tsc + lint + build**

Run: `cd frontend && npx vitest run src/components/child/__tests__/StaleAsOf.test.tsx && npx tsc --noEmit && npx eslint src/components/child/StaleAsOf.tsx src/pages/child/Stock.tsx src/pages/child/Market.tsx && npm run build`
Expected: PASS / clean / built.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/child/StaleAsOf.tsx frontend/src/components/child/__tests__/StaleAsOf.test.tsx frontend/src/pages/child/Stock.tsx frontend/src/pages/child/Market.tsx frontend/src/locales/en/child.json
git commit -m "feat(offline): 'Prices as of <time>' staleness label on Market + Stock (Goal4 P1)"
```

---

## Task 4: Verify + ship + docs

**Files:** modify `docs/MASTER-BACKLOG.md`.

- [ ] **Step 1: Full frontend verify**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run src/lib src/hooks src/components/child/__tests__/StaleAsOf.test.tsx src/pages/child/__tests__/Market.test.tsx src/pages/child/__tests__/Market.offline.test.tsx src/pages/child/__tests__/Stock.offline.test.tsx && npm run build`
Expected: tsc clean, eslint 0 errors, target tests PASS, build ok. (Known baseline `api-*`/MSW-dependent `child-*` failures are pre-existing — compare against clean HEAD if unsure.)

- [ ] **Step 2: Push + watch CI**

```bash
git push
# poll: gh run view <id> -R ashmorel/investikid --json conclusion,jobs   (NOT `gh run watch | tail`)
```
Expected: all 6 CI jobs green.

- [ ] **Step 3: Manual Vercel prod + confirm native synced**

```bash
cd frontend && vercel --prod --yes
vercel alias set <new-hash>-investikid.vercel.app app.investikid.ai
curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai   # expect 200
# cap sync already run in Task 1; a full native rebuild (Xcode/Gradle) is operator follow-up to ship @capacitor/network natively.
```

- [ ] **Step 4: Docs + commit**

Update `docs/MASTER-BACKLOG.md` Goal 4: mark Phase 1 done (onlineManager via @capacitor/network + allowlist fix + StaleAsOf), note Phases 2/3 remain and that a native rebuild is needed to ship the new plugin on device.
```bash
git add docs/MASTER-BACKLOG.md
git commit -m "docs: offline Phase 1 (Goal 4) shipped"
git push
```

---

## Notes / decisions baked in

- `@capacitor/network` has a web implementation, so web + native share one path; native gets reliable OS-level detection.
- Wiring `onlineManager` (not just `useOnline`) is what gives auto pause-offline + refetch-on-reconnect for free.
- Offline is read-only in Phase 1; offline trades need the Phase-2 sync outbox.
- Persisting `stock-history` (chosen) increases localStorage use per viewed stock — acceptable until the Phase-3 SQLite move; `market-search`/news stay excluded to bound size + avoid stale-AI.
- Shipping the plugin on device requires a native rebuild (operator follow-up); the web build + `cap sync` are done in-plan.
