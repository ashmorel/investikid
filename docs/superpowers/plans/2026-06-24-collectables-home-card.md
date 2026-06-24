# Collectables B3 — Home Featured-Drop Card — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact "featured drop" card to the child Home screen that spotlights the soonest-ending, not-yet-earned live limited drop with its live progress, tapping through to the shop's Limited shelf.

**Architecture:** Frontend-only, reusing the existing B1 `useCollectables()` hook (no backend, no migration). First extract three reusable pieces (rarity styling, countdown formatter, progress bar) out of `LimitedShelf.tsx` into a shared module, then build the new card on top of them and mount it on Home.

**Tech Stack:** React + TanStack Query + react-i18next + vitest/vitest-axe.

## Global Constraints

- **Frontend-only.** No backend, no Alembic migration, no new endpoint. The data comes from the existing `GET /collectables` via `useCollectables()`.
- **i18n in tests:** `react-i18next` is globally mocked in `tests/setup.ts` — the mock returns the translation KEY (interpolation params are ignored). Tests assert on directly-rendered text (names, `current / threshold`) and on i18n-key substrings (e.g. the countdown key), NOT on interpolated sentences.
- **Selection rule (exact):** among `data.active`, filter to `earned === false`, then pick the smallest `ends_at`; a `null` `ends_at` sorts LAST. Feature that one; if none, render `null`.
- **Hide conditions:** render `null` when `data` is undefined, when `active` is empty, or when every live drop is `earned`.
- **WCAG 2.2 AA:** the card is a single `<Link>` with an `aria-label`; the progress bar keeps `role="progressbar"` + `aria-valuenow/min/max`; emoji `aria-hidden`; rarity by text label (not colour alone); ≥44px tap height. New UI ships a `vitest-axe` check.
- **Behaviour-preserving refactor:** after extracting shared bits, `LimitedShelf.tsx`'s existing test file must pass UNCHANGED.
- **Countdown keys** live in the `child` namespace as `limited.endsInDays` / `limited.endsInHours` / `limited.endsInLessThanHour` (already present). The shared `formatCountdown` keeps using them; the card passes the `child` `t` into it.
- **Never read or modify any `.env`.**
- **Commits** end with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## File Structure

**Create**
- `frontend/src/components/child/shop/collectableBits.tsx` — shared `RARITY_STYLE`/`rarityClass`, `formatCountdown`, `ProgressBar` (Task 1).
- `frontend/src/components/child/home/FeaturedDropCard.tsx` — the card + `pickFeatured` selection helper (Task 2).
- `frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx` — tests (Task 2).

**Modify**
- `frontend/src/components/child/shop/LimitedShelf.tsx` — import the shared bits instead of its inline copies (Task 1).
- `frontend/src/pages/child/Home.tsx` — mount `<FeaturedDropCard />` above `ArcadeDailyCard` (Task 2).
- `frontend/src/locales/en/home.json` — `featuredDrop` copy (Task 2).
- `frontend/src/pages/child/__tests__/Home.test.tsx` — assert the card renders when a live drop is mocked (Task 2).

---

### Task 1: Extract shared `collectableBits` and refactor `LimitedShelf`

**Files:**
- Create: `frontend/src/components/child/shop/collectableBits.tsx`
- Modify: `frontend/src/components/child/shop/LimitedShelf.tsx`
- Test (must stay green, unchanged): `frontend/src/components/child/shop/__tests__/LimitedShelf.test.tsx`

**Interfaces:**
- Consumes: nothing new.
- Produces (from `collectableBits.tsx`):
  - `RARITY_STYLE: Record<string, string>`
  - `rarityClass(rarity: string | null): string`
  - `formatCountdown(endsAt: string | null, now: number, t: (key: string, opts?: Record<string, unknown>) => string): string`
  - `ProgressBar({ current, threshold }: { current: number; threshold: number }): JSX.Element`

- [ ] **Step 1: Create the shared module**

Create `frontend/src/components/child/shop/collectableBits.tsx`:

```tsx
// Shared presentation bits for limited-edition collectables, used by both the
// shop's LimitedShelf and the Home FeaturedDropCard. Behaviour is identical to
// the original inline copies in LimitedShelf.

export const RARITY_STYLE: Record<string, string> = {
  legendary: 'bg-amber-100 text-amber-800',
  epic:      'bg-purple-100 text-purple-800',
  rare:      'bg-sky-100 text-sky-800',
  common:    'bg-gray-100 text-gray-700',
};

export function rarityClass(rarity: string | null): string {
  return rarity ? (RARITY_STYLE[rarity] ?? RARITY_STYLE.common) : RARITY_STYLE.common;
}

// Pure: no side-effects, `now` passed in so it is stable across renders.
export function formatCountdown(
  endsAt: string | null,
  now: number,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  if (!endsAt) return '';
  const ms = new Date(endsAt).getTime() - now;
  if (ms <= 0) return '';
  const days = Math.floor(ms / 86_400_000);
  const hours = Math.floor((ms % 86_400_000) / 3_600_000);
  if (days > 0) return t('limited.endsInDays', { count: days });
  if (hours > 0) return t('limited.endsInHours', { count: hours });
  return t('limited.endsInLessThanHour');
}

export function ProgressBar({ current, threshold }: { current: number; threshold: number }) {
  const pct = threshold > 0 ? Math.min(100, (current / threshold) * 100) : 0;
  return (
    <div
      className="h-2 overflow-hidden rounded-full bg-gray-100"
      role="progressbar"
      aria-label={`${current} / ${threshold}`}
      aria-valuenow={current}
      aria-valuemin={0}
      aria-valuemax={threshold}
    >
      <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}
```

- [ ] **Step 2: Run the LimitedShelf tests to confirm the baseline is green BEFORE refactoring**

Run: `cd frontend && npx vitest run src/components/child/shop/__tests__/LimitedShelf.test.tsx`
Expected: all pass (this is the unchanged baseline).

- [ ] **Step 3: Refactor `LimitedShelf.tsx` to import the shared bits**

In `frontend/src/components/child/shop/LimitedShelf.tsx`:
1. Add the import near the top: `import { rarityClass, formatCountdown, ProgressBar } from './collectableBits';`
2. DELETE the local `RARITY_STYLE` const and the local `rarityClass` function.
3. DELETE the local `formatCountdown` function.
4. Replace the inline progress-bar markup (the `<div role="progressbar" …>…</div>` block in `ActiveDrop`) with `<ProgressBar current={drop.goal.current} threshold={drop.goal.threshold} />`.
5. Leave everything else (the `RARITY_STYLE` references via `rarityClass`, the `ActiveDrop`/`OwnedCard`/`LimitedShelf` components, the `data?.active ?? []` guards) unchanged. The `formatCountdown` call site in `ActiveDrop` keeps its existing argument shape (`drop.ends_at, now, t as Parameters<typeof formatCountdown>[2]`).

- [ ] **Step 4: Run the LimitedShelf tests to confirm the refactor is behaviour-preserving**

Run: `cd frontend && npx vitest run src/components/child/shop/__tests__/LimitedShelf.test.tsx`
Expected: all pass, UNCHANGED from Step 2 (same test file, no edits to it).

- [ ] **Step 5: tsc + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: tsc 0 errors; lint 0 errors on the changed files.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/child/shop/collectableBits.tsx frontend/src/components/child/shop/LimitedShelf.tsx
git commit -m "refactor(collectables): extract shared rarity/countdown/progress bits (B3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: FeaturedDropCard + Home mount + copy + tests

**Files:**
- Create: `frontend/src/components/child/home/FeaturedDropCard.tsx`
- Create: `frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx`
- Modify: `frontend/src/pages/child/Home.tsx`
- Modify: `frontend/src/locales/en/home.json`
- Modify: `frontend/src/pages/child/__tests__/Home.test.tsx`

**Interfaces:**
- Consumes: `useCollectables`, `CollectableDrop` from `@/api/collectables`; `rarityClass`, `formatCountdown`, `ProgressBar` from `@/components/child/shop/collectableBits` (Task 1).
- Produces:
  - `pickFeatured(active: CollectableDrop[]): CollectableDrop | undefined` (exported, pure).
  - `FeaturedDropCard` (default export).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import FeaturedDropCard, { pickFeatured } from '../FeaturedDropCard';
import type { CollectableDrop, CollectablesState } from '@/api/collectables';

// i18n is globally mocked in tests/setup.ts (returns the key).
vi.mock('@/api/collectables', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/collectables')>();
  return { ...actual, useCollectables: vi.fn() };
});

import { useCollectables } from '@/api/collectables';

function drop(over: Partial<CollectableDrop>): CollectableDrop {
  return {
    slug: 's', name: 'Drop', emoji: '👑', type: 'accessory', rarity: 'rare',
    ends_at: '2099-01-01T00:00:00Z', goal: { type: 'streak_days', threshold: 7, current: 5 },
    earned: false, ...over,
  };
}

function mockState(state: CollectablesState | undefined) {
  vi.mocked(useCollectables).mockReturnValue(
    { data: state, isLoading: false } as unknown as UseQueryResult<CollectablesState | null, Error>,
  );
}

function renderCard() {
  return render(<MemoryRouter><FeaturedDropCard /></MemoryRouter>);
}

describe('pickFeatured', () => {
  it('ignores earned drops and picks the soonest-ending', () => {
    const a = drop({ slug: 'a', name: 'A', ends_at: '2099-03-01T00:00:00Z' });
    const b = drop({ slug: 'b', name: 'B', ends_at: '2099-01-01T00:00:00Z' });
    const earned = drop({ slug: 'c', name: 'C', ends_at: '2098-01-01T00:00:00Z', earned: true });
    expect(pickFeatured([a, b, earned])?.slug).toBe('b');
  });

  it('sorts a null ends_at last', () => {
    const dated = drop({ slug: 'd', ends_at: '2099-05-01T00:00:00Z' });
    const undated = drop({ slug: 'u', ends_at: null });
    expect(pickFeatured([undated, dated])?.slug).toBe('d');
  });

  it('returns undefined when all are earned', () => {
    expect(pickFeatured([drop({ earned: true })])).toBeUndefined();
  });
});

describe('FeaturedDropCard', () => {
  it('renders the featured drop name and progress', () => {
    mockState({ active: [drop({ name: 'Streak Legend', goal: { type: 'streak_days', threshold: 7, current: 5 } })], owned: [] });
    renderCard();
    expect(screen.getByText('Streak Legend')).toBeInTheDocument();
    expect(screen.getByText('5 / 7')).toBeInTheDocument();
    expect(screen.getByRole('link')).toBeInTheDocument();
  });

  it('features the soonest-ending of several live drops', () => {
    mockState({ active: [
      drop({ slug: 'late', name: 'Later', ends_at: '2099-09-01T00:00:00Z' }),
      drop({ slug: 'soon', name: 'Sooner', ends_at: '2099-02-01T00:00:00Z' }),
    ], owned: [] });
    renderCard();
    expect(screen.getByText('Sooner')).toBeInTheDocument();
    expect(screen.queryByText('Later')).toBeNull();
  });

  it('renders nothing when there are no active drops', () => {
    mockState({ active: [], owned: [] });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when every live drop is earned', () => {
    mockState({ active: [drop({ earned: true })], owned: [] });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when data is undefined', () => {
    mockState(undefined);
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('has no axe violations', async () => {
    mockState({ active: [drop({ name: 'Streak Legend' })], owned: [] });
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd frontend && npx vitest run src/components/child/home/__tests__/FeaturedDropCard.test.tsx`
Expected: FAIL — module `../FeaturedDropCard` not found.

- [ ] **Step 3: Write the component**

Create `frontend/src/components/child/home/FeaturedDropCard.tsx`:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useCollectables, type CollectableDrop } from '@/api/collectables';
import { rarityClass, formatCountdown, ProgressBar } from '@/components/child/shop/collectableBits';

// Pure: soonest-ending, not-yet-earned live drop; a null ends_at sorts last.
export function pickFeatured(active: CollectableDrop[]): CollectableDrop | undefined {
  return active
    .filter((d) => !d.earned)
    .sort((a, b) => {
      if (a.ends_at === b.ends_at) return 0;
      if (a.ends_at === null) return 1;
      if (b.ends_at === null) return -1;
      return new Date(a.ends_at).getTime() - new Date(b.ends_at).getTime();
    })[0];
}

export default function FeaturedDropCard() {
  const { t } = useTranslation('home');
  const { t: tChild } = useTranslation('child');
  const { data } = useCollectables();
  // Capture now once per mount so the countdown is stable across re-renders
  // (and Date.now() is not called during render — satisfies react-hooks/purity).
  const [now] = useState(() => Date.now());

  const featured = pickFeatured(data?.active ?? []);
  if (!featured) return null;

  const countdown = formatCountdown(
    featured.ends_at, now, tChild as Parameters<typeof formatCountdown>[2],
  );
  const rarity = featured.rarity ?? 'common';

  return (
    <Link
      to="/shop"
      aria-label={t('featuredDrop.ariaLabel', {
        name: featured.name, current: featured.goal.current, threshold: featured.goal.threshold,
      })}
      className="block rounded-xl border border-line bg-card p-4 min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
    >
      <div className="flex items-center gap-2">
        <span className="text-2xl" aria-hidden="true">{featured.emoji}</span>
        <div className="min-w-0 flex-1">
          <div className="text-base font-extrabold text-ink">{featured.name}</div>
          <span className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${rarityClass(featured.rarity)}`}>
            {rarity}
          </span>
        </div>
        {countdown && <span className="shrink-0 text-xs text-muted-foreground">{countdown}</span>}
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
        <span>{t('featuredDrop.title')}</span>
        <span>{featured.goal.current} / {featured.goal.threshold}</span>
      </div>
      <div className="mt-1">
        <ProgressBar current={featured.goal.current} threshold={featured.goal.threshold} />
      </div>
    </Link>
  );
}
```

- [ ] **Step 4: Add the copy keys**

In `frontend/src/locales/en/home.json`, add a top-level `featuredDrop` block (valid JSON — mind the commas):

```json
  "featuredDrop": {
    "title": "Limited drop",
    "ariaLabel": "Limited drop: {{name}}, {{current}} of {{threshold}} — see it in the shop"
  }
```

Sanity-check it parses: `node -e "JSON.parse(require('fs').readFileSync('src/locales/en/home.json','utf8')); console.log('ok')"` (from `frontend/`).

- [ ] **Step 5: Run the component tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/child/home/__tests__/FeaturedDropCard.test.tsx`
Expected: PASS (all `pickFeatured` + `FeaturedDropCard` cases, incl. axe).

- [ ] **Step 6: Mount the card on Home**

In `frontend/src/pages/child/Home.tsx`:
1. Add the import after the other home-card imports (after line 26, the `ArcadeDailyCard` import):

```tsx
import FeaturedDropCard from '@/components/child/home/FeaturedDropCard';
```

2. Mount it immediately ABOVE the existing `ArcadeDailyCard` block. Find this block (around lines 141-143):

```tsx
          <div className="mt-4">
            <ArcadeDailyCard />
          </div>
```

and insert directly before it:

```tsx
          <div className="mt-4">
            <FeaturedDropCard />
          </div>
```

- [ ] **Step 7: Add the Home.test assertion**

In `frontend/src/pages/child/__tests__/Home.test.tsx`:
1. Add a module mock near the other `vi.mock` calls at the top of the file:

```tsx
vi.mock('@/api/collectables', () => ({
  useCollectables: () => ({
    data: {
      active: [{
        slug: 'home-feat', name: 'Home Featured', emoji: '👑', type: 'accessory',
        rarity: 'legendary', ends_at: '2099-01-01T00:00:00Z',
        goal: { type: 'streak_days', threshold: 7, current: 3 }, earned: false,
      }],
      owned: [],
    },
    isLoading: false,
  }),
}));
```

2. Add a test inside the existing `describe` block:

```tsx
  it('shows the featured-drop card above the arcade daily card when a drop is live', () => {
    renderHome();
    const featured = screen.getByText('Home Featured');
    expect(featured).toBeInTheDocument();
    // ArcadeDailyCard renders the i18n key 'dailyCard.title' (react-i18next is mocked to echo keys).
    const arcade = screen.getByText(/dailyCard\.title/);
    // The featured card must appear before the arcade daily card in the DOM.
    expect(featured.compareDocumentPosition(arcade) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
```

- [ ] **Step 8: Run the Home tests + the card tests**

Run: `cd frontend && npx vitest run src/pages/child/__tests__/Home.test.tsx src/components/child/home/__tests__/FeaturedDropCard.test.tsx`
Expected: all pass (existing Home assertions still green; the new ordering assertion passes).

- [ ] **Step 9: tsc + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: tsc 0 errors; lint 0 errors on the new/changed files.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/child/home/FeaturedDropCard.tsx frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx frontend/src/pages/child/Home.tsx frontend/src/locales/en/home.json frontend/src/pages/child/__tests__/Home.test.tsx
git commit -m "feat(collectables): Home featured-drop card (B3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Full verification + ship + docs

**Files:** none new — verification, deploy, docs.

- [ ] **Step 1: Full frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/child/home src/components/child/shop && npm run build`
Expected: tsc 0; lint 0; the home + shop tests pass (incl. the unchanged LimitedShelf tests, the new FeaturedDropCard tests, and Home.test); build clean.

- [ ] **Step 2: Confirm the full suite is at the env-only baseline**

Run: `cd frontend && npx vitest run 2>&1 | grep -iE "Test Files|Tests |Unhandled"`
Expected: no `Unhandled` line; failure count no higher than the known env-only timeout baseline (the child-Lesson/Module/Simulator/Stock/Level timeout files).

- [ ] **Step 3: Push (no migration → no prod-snapshot question)**

This change is frontend-only — no backend, no Alembic migration — so the prod-snapshot rule does not apply. Push:

```bash
git push origin main
```

- [ ] **Step 4: Watch CI green**

Wait for the CI run on the pushed HEAD to complete `success` (`gh run list --branch main --limit 1`, or monitor).

- [ ] **Step 5: Deploy the web frontend (two-step) + verify live**

```bash
cd frontend && vercel --prod --force
# then alias the printed deployment hash to the pinned domain:
vercel alias set <deployment-hash>-investikid.vercel.app app.investikid.ai
```

Then verify: `curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai/` → expect `200`. (The card itself is gated behind a live drop + login, so there's no unauthenticated URL to probe; a 200 home page confirms the deploy.)

- [ ] **Step 6: cap sync ios**

Run: `cd frontend && npm run build && npx cap sync ios`
Expected: sync finished (carries the new card into the native shell).

- [ ] **Step 7: Update docs**

Add a "Limited-Edition Collectables B3" entry to `docs/MASTER-BACKLOG.md` (live-in-prod section) noting: frontend-only Home featured-drop card (no migration), reuses `useCollectables`, soonest-ending-unearned spotlight, shared `collectableBits` extraction, and that **the limited-edition collectables programme (B1+B2+B3) is now complete**. Commit + push:

```bash
git add docs/MASTER-BACKLOG.md
git commit -m "docs: record Collectables B3 Home featured-drop card live in prod

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```

(Also refresh the `project_arcade` memory entry + the MEMORY.md index line to mark B3 live / the collectables programme complete — done by the controller, outside the repo.)

---

## Notes for the implementer

- **DRY/YAGNI:** the card reuses `useCollectables` and the shared `collectableBits` — do NOT add a new endpoint, a new query, or a second copy of the countdown/rarity/progress logic. No carousel, no multi-drop view, no push notification — all out of scope.
- **Behaviour-preserving refactor:** Task 1's success criterion is that `LimitedShelf.test.tsx` passes UNCHANGED. Do not edit that test file.
- **Purity:** capture `now` via `useState(() => Date.now())` — do not call `Date.now()` directly in render.
