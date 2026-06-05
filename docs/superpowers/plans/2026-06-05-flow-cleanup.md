# Flow Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove three flow-confusion points — literal Module→Level→Lesson vocabulary, a single "what's next" source on Home, and a light-brand re-skin of the Progress screen — plus the `TopNav` monogram vestige.

**Architecture:** Frontend-only string/label edits + one Home data-source change (`useNextLesson().moduleId` drives the grid highlight) + a token re-skin of `StrengthsGaps.tsx`. No backend, API, route, or data changes.

**Tech Stack:** React 18 + Vite + TypeScript + TanStack Query + Tailwind v4 (semantic tokens) + Vitest + vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-05-flow-cleanup-design.md`

**Working dir:** `/Users/leeashmore/Local Repo/invest-ed/frontend`. Git from repo root `/Users/leeashmore/Local Repo`, commit to `main`, end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Commands (from `invest-ed/frontend`):** `npx tsc -b` · `npm run lint` (one pre-existing `button.tsx` warning is acceptable) · `npm test` · `npm run build`.

**Notes for the implementer:**
- READ each file before editing — line numbers below are guides, match on the literal strings shown.
- Tailwind semantic tokens available (from `src/index.css` `@theme`): `surface #f0f9ff`, `card #ffffff`, `ink #0f172a`, `muted-foreground #475569`, `line #bae6fd`, plus `brand-*`, `success-*`, `accent-*`. Use `bg-card`, `text-muted-foreground`, `border-brand-100`, `bg-brand-100` to match sibling cards (e.g. the progress card in `Level.tsx`).
- Vercel auto-deploys the frontend on push; Railway backend unaffected. CI must stay green (6 jobs).

## File Structure

- `components/child/BottomTabBar.tsx`, `components/child/TopNav.tsx` — nav tab label + (TopNav) monogram.
- `pages/child/Lessons.tsx`, `pages/child/Home.tsx`, `pages/child/Level.tsx`, `pages/child/Module.tsx`, `components/child/ModuleCard.tsx`, `components/child/lesson/LessonChrome.tsx`, `components/child/lesson/CoachPennyPanel.tsx` — user-facing "quest" → "lesson"/"module" strings.
- `pages/child/Home.tsx` — highlight source change (Task 2).
- `pages/child/StrengthsGaps.tsx` — light re-skin (Task 3).
- Tests: `components/child/__tests__/BottomTabBar.test.tsx`, `components/child/__tests__/BackButton.test.tsx` (fixtures), new `pages/child/__tests__/Home.test.tsx`, new `pages/child/__tests__/StrengthsGaps.test.tsx`.

---

### Task 1: Literal vocabulary + TopNav monogram

**Files:**
- Modify: `components/child/BottomTabBar.tsx`, `components/child/TopNav.tsx`, `pages/child/Lessons.tsx`, `pages/child/Home.tsx`, `pages/child/Level.tsx`, `pages/child/Module.tsx`, `components/child/ModuleCard.tsx`, `components/child/lesson/LessonChrome.tsx`, `components/child/lesson/CoachPennyPanel.tsx`, `pages/child/Lesson.tsx` (comment only)
- Test: `components/child/__tests__/BottomTabBar.test.tsx`, `components/child/__tests__/BackButton.test.tsx`

- [ ] **Step 1: Update the failing nav test** — in `components/child/__tests__/BottomTabBar.test.tsx`, change the assertion in the "renders all five tab labels" test:

```tsx
    expect(screen.getByText('Learn')).toBeInTheDocument();
```
(replacing `expect(screen.getByText('Quests')).toBeInTheDocument();`).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- BottomTabBar`
Expected: FAIL — `Unable to find an element with the text: Learn` (code still renders "Quests").

- [ ] **Step 3: Rename the nav tab label in both nav components**

In `components/child/BottomTabBar.tsx`, change the `/lessons` tab:
```tsx
  { to: '/lessons', label: 'Learn', Icon: BookOpen },
```
In `components/child/TopNav.tsx`, change the `/lessons` link:
```tsx
  { to: '/lessons', label: 'Learn' },
```

- [ ] **Step 4: Run the nav test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- BottomTabBar`
Expected: PASS.

- [ ] **Step 5: Change the TopNav monogram**

In `components/child/TopNav.tsx`, change the logo monogram from `IE` to `IK`:
```tsx
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-gradient text-center text-sm font-extrabold text-white">IK</span>
```

- [ ] **Step 6: Apply the remaining literal-vocabulary string edits**

`pages/child/Lessons.tsx`:
- H1: `<h1 className="text-2xl font-extrabold text-gray-900">Quests</h1>` → `...>Modules</h1>`
- Subtitle: the `quests` word in `{...} quests</p>` → `lessons`:
```tsx
      <p className="mt-1 text-sm text-gray-500">{modules.length} modules · {modules.reduce((acc, m) => acc + (lessonsByModuleId.get(m.id)?.length ?? 0), 0)} lessons</p>
```

`pages/child/Home.tsx`:
- The grid comment `{/* Your quests module grid */}` → `{/* Your modules grid */}`
- `aria-label="Your quests"` → `aria-label="Your modules"`
- Heading `>Your quests</h2>` → `>Your modules</h2>`

`components/child/ModuleCard.tsx`:
- `<p className="text-xs text-gray-500">{completedCount} / {totalCount} quests</p>` → `... lessons</p>`

`pages/child/Level.tsx`:
- `<span>{completed} / {lessons.length} quests</span>` → `... lessons</span>`

`pages/child/Module.tsx` (two occurrences):
- `<BackButton to="/lessons" label="Quests" />` → `<BackButton to="/lessons" label="Modules" />` (both spots)

`components/child/lesson/LessonChrome.tsx`:
- `aria-label={total > 0 ? \`Quest ${position} of ${total}\` : \`Quest ${position}\`}` → use `Lesson` in both template strings:
```tsx
          aria-label={total > 0 ? `Lesson ${position} of ${total}` : `Lesson ${position}`}
```

`components/child/lesson/CoachPennyPanel.tsx`:
- `Ask me anything about this quest! 🎯` → `Ask me anything about this lesson! 🎯`

`pages/child/Lesson.tsx` (comment only, for consistency):
- `// Other quests in THIS level still incomplete ...` → `// Other lessons in THIS level still incomplete ...`

- [ ] **Step 7: Update the BackButton test fixture**

In `components/child/__tests__/BackButton.test.tsx`, change the fixture label on the `/lessons` example from `"Quests"` to `"Modules"`:
```tsx
    const { container } = wrap(<BackButton to="/lessons" label="Modules" />);
```

- [ ] **Step 8: Verify no stray user-facing "quest" strings remain**

Run:
```
cd "/Users/leeashmore/Local Repo/invest-ed/frontend/src" && grep -rniE "\bquest" pages components --include="*.tsx" | grep -viE "import|from |\brequest|\bquestion|querystring|requestAnimation"
```
Expected: no matches (every hit from the earlier audit is resolved). If any remain, convert them (user-facing "quest"→"lesson", "Quests" heading→"Modules") following the same rule; never rename route paths, query keys, or identifiers.

- [ ] **Step 9: Typecheck, lint, and run the touched tests**

Run:
```
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint && npm test -- BottomTabBar BackButton
```
Expected: tsc clean; lint clean (modulo the known `button.tsx` warning); tests pass.

- [ ] **Step 10: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src
git commit -m "refactor(ui): literal Module/Level/Lesson vocabulary + TopNav monogram

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Home — single source of truth for "what's next"

**Files:**
- Modify: `pages/child/Home.tsx`
- Test: `pages/child/__tests__/Home.test.tsx` (new)

- [ ] **Step 1: Write the failing test** — create `pages/child/__tests__/Home.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Home from '../Home';

// The highlight must follow the next-lesson resolver (m2), NOT the recommendations (m1).
vi.mock('@/hooks/useNextLesson', () => ({
  useNextLesson: () => ({
    mode: 'continue', moduleId: 'm2', levelId: 'l1', lessonId: 'q1',
    moduleTitle: 'Budgeting', moduleIcon: '💰', lessonLabel: 'Needs vs Wants',
    to: '/lessons/m2/l1/q1', isLoading: false,
  }),
}));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({
    data: { review_summary: { due_count: 0 }, continue_learning: [{ module_id: 'm1' }], something_new: [] },
  }),
}));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { level: 1, xp: 0, streak_count: 0, last_activity_date: null } }),
}));
vi.mock('@/hooks/useAllBadges', () => ({ useAllBadges: () => ({ data: [] }) }));
vi.mock('@/hooks/useBadges', () => ({ useBadges: () => ({ data: [] }) }));
// Stub the heavy child components so the test focuses on the module grid.
vi.mock('@/components/child/HomeHero', () => ({ default: () => null }));
vi.mock('@/components/child/StatsBar', () => ({ StatsBar: () => null }));
vi.mock('@/components/child/LevelProgressCard', () => ({ LevelProgressCard: () => null }));
vi.mock('@/components/child/AchievementsStrip', () => ({ AchievementsStrip: () => null }));
vi.mock('@/components/child/ReviewBanner', () => ({ ReviewBanner: () => null }));
vi.mock('@/api/content', () => ({
  contentApi: {
    listModules: () => Promise.resolve([
      { id: 'm1', order_index: 0, topic: 'stocks', icon: '📈', title: 'Stocks', locked: false },
      { id: 'm2', order_index: 1, topic: 'budgeting', icon: '💰', title: 'Budgeting', locked: false },
    ]),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

describe('Home module grid highlight', () => {
  it('marks the next-lesson module (m2) as "Next", not the recommendations module (m1)', async () => {
    render(wrap(<Home />));
    // Budgeting (m2) tile is the next lesson -> shows the "Next" badge.
    const budgeting = (await screen.findByText('Budgeting')).closest('a')!;
    expect(budgeting).toHaveTextContent('Next');
    // Stocks (m1) is only the recommendation -> must NOT be highlighted.
    const stocks = screen.getByText('Stocks').closest('a')!;
    expect(stocks).not.toHaveTextContent('Next');
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- Home.test`
Expected: FAIL — currently `recommendedModuleId` comes from recommendations (`m1`), so "Stocks" carries the "Next" badge and the assertion that "Budgeting" has it fails.

- [ ] **Step 3: Change the highlight source in `pages/child/Home.tsx`**

Add the hook import near the other imports:
```tsx
import { useNextLesson } from '@/hooks/useNextLesson';
```
In the component body, add the call (alongside the other hooks):
```tsx
  const next = useNextLesson();
```
Replace the recommendations-derived highlight:
```tsx
  const recommendedModuleId =
    recs?.continue_learning?.[0]?.module_id ??
    recs?.something_new?.[0]?.module_id ??
    null;
```
with:
```tsx
  const recommendedModuleId = next.moduleId;
```
Leave `const { data: recs } = useRecommendations();` in place — it still feeds the `ReviewBanner` (`recs.review_summary.due_count`). Do not remove that import.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- Home.test`
Expected: PASS.

- [ ] **Step 5: Typecheck + lint**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint`
Expected: clean (modulo the known `button.tsx` warning). If `recs` is now flagged unused anywhere, confirm it's still referenced by the `ReviewBanner` block — it should be; do not delete it.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Home.tsx invest-ed/frontend/src/pages/child/__tests__/Home.test.tsx
git commit -m "fix(home): align module grid highlight to the next-lesson resolver

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Progress screen (`StrengthsGaps.tsx`) light re-skin

**Files:**
- Modify: `pages/child/StrengthsGaps.tsx`
- Test: `pages/child/__tests__/StrengthsGaps.test.tsx` (new)

- [ ] **Step 1: Write the failing test** — create `pages/child/__tests__/StrengthsGaps.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import StrengthsGaps from '../StrengthsGaps';

vi.mock('@/api/ai', () => ({
  useStrengths: () => ({
    isLoading: false,
    data: {
      overall_mastery: 0.6,
      topics: [
        { topic: 'stocks', status: 'strong', mastery_score: 0.8, weak_count: 1, due_for_review: 0 },
        { topic: 'budgeting', status: 'new', mastery_score: 0, weak_count: 0, due_for_review: 0 },
      ],
    },
  }),
}));

describe('StrengthsGaps (light re-skin)', () => {
  it('renders the progress screen with no dark-slate surfaces', () => {
    const { container } = render(<StrengthsGaps />);
    expect(screen.getByText('My Progress')).toBeInTheDocument();
    // No leftover dark theme classes after the re-skin.
    expect(container.querySelector('[class*="slate-800"]')).toBeNull();
    expect(container.querySelector('[class*="slate-600"]')).toBeNull();
    expect(container.querySelector('[class*="slate-500"]')).toBeNull();
    expect(container.querySelector('[class*="slate-400"]')).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<StrengthsGaps />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- StrengthsGaps`
Expected: FAIL — the dark-slate classes are still present (`slate-800`/`600`/`500`/`400`).

- [ ] **Step 3: Re-skin `pages/child/StrengthsGaps.tsx`**

Apply these exact class/value swaps:

In `STATUS_STYLES`, the `new` entry:
```tsx
  new: { border: 'border-l-brand-200', text: 'text-muted-foreground', label: 'Not started yet', emoji: '🆕' },
```

In `MasteryRing` — the track circle stroke and the centre label:
```tsx
          <circle cx="60" cy="60" r="52" fill="none" stroke="#bae6fd" strokeWidth="10" />
```
```tsx
        <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-900">
```

In `TopicCard` — the card container, topic name, the "—" placeholder, the progress track, and the footer text:
```tsx
    <div className={`rounded-xl border border-brand-100 ${style.border} border-l-4 bg-card p-4 shadow-sm`}>
```
```tsx
          <p className="font-semibold text-gray-900 text-sm">{topic.topic.replace(/_/g, ' ')}</p>
```
```tsx
          <span className="text-xl font-bold text-muted-foreground">—</span>
```
```tsx
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
```
```tsx
      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
```

Leave the `strong` and `needs_practice` status styles (`success-*` / `accent-*`), the ring fill `#a78bfa`, and all structural/aria markup unchanged. These tokens (`text-gray-900`, `text-muted-foreground #475569`, `bg-card #fff`, `brand-100`, `success`/`accent`) are the same AA-passing tokens used across the app, so contrast on the new light surface is maintained.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- StrengthsGaps`
Expected: PASS (both the no-dark-classes test and the axe test). Note: jsdom + axe does not compute pixel colour-contrast, so the axe check guarantees structural a11y; contrast is guaranteed by reusing the app's known-AA tokens above.

- [ ] **Step 5: Typecheck + lint**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint`
Expected: clean (modulo the known `button.tsx` warning).

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/StrengthsGaps.tsx invest-ed/frontend/src/pages/child/__tests__/StrengthsGaps.test.tsx
git commit -m "style(progress): re-skin StrengthsGaps to the light brand tokens

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full regression, iOS sync, push

**Files:** none (verification + sync).

- [ ] **Step 1: Full frontend verification**

Run:
```
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint && npm test && npm run build
```
Expected: tsc clean; lint clean (modulo the one known `button.tsx` warning); all vitest suites pass; production build succeeds.

- [ ] **Step 2: Sync the web build into the iOS app**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx cap sync ios`
Expected: "Sync finished". (No native code changed — this just copies the new web bundle. A device/TestFlight rebuild in Xcode is a USER step; note it in the report.)

- [ ] **Step 3: Commit any Capacitor sync artifacts (if the sync touched tracked files)**

```bash
cd "/Users/leeashmore/Local Repo"
git status --short
# If `npx cap sync ios` modified tracked files (e.g. ios/App/App/public or capacitor.config), add + commit them:
git add -A invest-ed/frontend/ios
git commit -m "chore(ios): cap sync web bundle after flow cleanup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "nothing to commit from cap sync"
```
(If `git status` shows no tracked iOS changes, skip the commit.)

- [ ] **Step 4: Push**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```

- [ ] **Step 5: Report** — summarise the commits; note that Vercel auto-deploys the web frontend on green CI, and that seeing the changes in the iOS app needs a USER Xcode rebuild/TestFlight archive (no native code changed).

---

## Self-Review

**Spec coverage:**
- Part 1 (literal vocabulary, all 10 string sites + 2 test fixtures) → Task 1. ✓
- Part 4 (TopNav monogram IE→IK) → Task 1 Step 5. ✓
- Part 2 (Home highlight from `useNextLesson().moduleId`; keep `useRecommendations` for the banner) → Task 2. ✓
- Part 3 (StrengthsGaps light re-skin to semantic tokens; AA) → Task 3. ✓
- Testing (updated fixtures; Home highlight test; StrengthsGaps axe test; tsc/lint/test/build; cap sync) → Tasks 1–4. ✓

**Placeholder scan:** No TBD/TODO; every code step shows the exact old→new content. The Step 8 grep is a guard with a defined resolution rule, not a placeholder. ✓

**Type consistency:** `useNextLesson()` returns `{ moduleId: string | null, ... }`; `recommendedModuleId = next.moduleId` matches the existing `ModuleTile recommended={m.id === recommendedModuleId}` (string|null compare). Nav `label` strings are plain literals consumed identically by both nav components. StrengthsGaps edits are class-string-only; no signature changes. ✓
