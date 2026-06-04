# Child Core Screen Layouts (SP-B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the child core screens' layout up to the "Yasmin's Choice" look — a gamified Home (Level card + achievements), a richer learning path (Quests/Module/Level), a card-styled Stats, and light Progress/Coach polish — reusing all existing data/routes/components and SP-A tokens.

**Architecture:** Two new presentational components (`LevelProgressCard`, `AchievementsStrip`) + targeted restyles of existing screens and components (`Home`, `Lessons`, `Module`, `Level`, `Stats`, `StrengthsGaps`, `Coach`, and the existing `LevelCard`/`LessonRow`/`ModuleCard`). Pure presentation fed by existing hooks. **No routes/data/IA/behaviour change.**

**Tech Stack:** React 18 + Vite + TS + Tailwind v4 + shadcn/ui; SP-A semantic tokens (`brand-*`, `accent-*`, `success-*`, `danger-*`, `muted`, `ink`, `line`, `bg-brand-gradient`).

**Spec:** `docs/superpowers/specs/2026-06-04-child-core-layouts-design.md`

**Conventions:** Frontend commands from `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` fast-refresh warning is the baseline), `npm test` (vitest + vitest-axe), `npm run build`. Backend untouched. Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs). iOS rebuild deferred to programme end. **Restyle only: never change a route, query, prop contract, handler, or test behaviour — only layout/markup/classes (and the two new components).**

**Verified existing APIs (reuse, do not change):** `useProgress()`→`{xp,level,streak_count,last_activity_date}`; `useAllBadges()`/`useBadges()` → `BadgeDefinition[]`/`EarnedBadge[]`; `gamificationApi`; `badgeIcon(badge)` in `src/api/admin.ts` (takes `{icon_url,condition_type}`); `LevelOut {id,module_id,title,order_index,is_premium,icon,state,locked_reason,passed,lessons_total,lessons_completed}`; `LessonSummary {id,type,title,xp_reward,order_index,completed}`. Existing components: `LevelCard {level,onOpen,onLockedClick}`, `LessonRow {moduleId,levelId,lesson,status}`, `ModuleCard {module,completedCount,totalCount,onLockedClick}`, `ModuleTile`, `HeroCard`, `StatChip`, `ReviewBanner`, `Penny`, `BadgeGrid`, `XpSummary`, `ChallengeList`, `LeaderboardTable`.

## Screenshot harness (reused by screen tasks)

When a task says "capture", create `invest-ed/frontend/tmp-shot.mjs` if absent with the SP-A mocked-API capturer (already used in SP-0/SP-A — port 5188, mocks `/users/me`, `/users/me/progress`, `/users/me/badges`, `/modules`, `/recommendations`, `/badges`, `/challenges`, `/leaderboard`, `/modules/m1/levels`, `/levels/l1/lessons`, `/lessons/ls2`). Add routes for the screen under test as needed. It is **untracked** — never commit it; it is removed in the final task. Run pattern:
```bash
(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; \
  for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/spb/<tag> node tmp-shot.mjs ; pkill -f "port 5188"
```
If `tmp-shot.mjs` is committed-ignored: it is already in `eslint.config.js`? No — SP-A removed that ignore. If lint flags it, that's fine (it's untracked, not in CI); do not add an ignore.

---

### Task 1: `LevelProgressCard` component (new) + tests

**Files:**
- Create: `src/components/child/LevelProgressCard.tsx`
- Create: `src/components/child/__tests__/LevelProgressCard.test.tsx`

- [ ] **Step 1: Write the failing test**

`src/components/child/__tests__/LevelProgressCard.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { LevelProgressCard } from '../LevelProgressCard';

describe('LevelProgressCard', () => {
  it('shows the level and XP-in-level fraction', () => {
    render(<LevelProgressCard level={4} xp={340} />);
    expect(screen.getByText('Level 4 Investor')).toBeInTheDocument();
    expect(screen.getByText('40 / 100 XP')).toBeInTheDocument();
    expect(screen.getByText(/60 XP to level 5/)).toBeInTheDocument();
  });

  it('exposes an accessible progressbar with the XP-in-level value', () => {
    render(<LevelProgressCard level={4} xp={340} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '40');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('has no axe violations', async () => {
    const { container } = render(<LevelProgressCard level={1} xp={0} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run it, verify it fails**

Run: `npm test -- src/components/child/__tests__/LevelProgressCard.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement the component**

`src/components/child/LevelProgressCard.tsx`:
```tsx
import { cn } from '@/lib/utils';

export function LevelProgressCard({
  level,
  xp,
  className,
}: {
  level: number;
  xp: number;
  className?: string;
}) {
  const xpForNext = 100;
  const xpInLevel = xp % xpForNext;
  const pct = Math.min(100, Math.round((xpInLevel / xpForNext) * 100));
  const toGo = xpForNext - xpInLevel;
  return (
    <div className={cn('rounded-2xl border border-brand-100 bg-card p-4 shadow-sm', className)}>
      <div className="flex items-center gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-white shadow"
          aria-hidden="true"
        >
          <span className="text-sm font-extrabold">L{level}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <span className="text-sm font-extrabold text-ink">Level {level} Investor</span>
            <span className="text-xs font-bold text-brand-600">{xpInLevel} / {xpForNext} XP</span>
          </div>
          <div
            className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
            role="progressbar"
            aria-valuenow={xpInLevel}
            aria-valuemin={0}
            aria-valuemax={xpForNext}
            aria-label={`Level ${level} progress`}
          >
            <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
      <p className="mt-2 text-right text-[11px] font-semibold text-muted-foreground">
        {toGo} XP to level {level + 1}
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `npm test -- src/components/child/__tests__/LevelProgressCard.test.tsx`
Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/LevelProgressCard.tsx invest-ed/frontend/src/components/child/__tests__/LevelProgressCard.test.tsx
git commit -m "feat(home): add LevelProgressCard (level/XP investor card)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `AchievementsStrip` component (new) + tests

**Files:**
- Create: `src/components/child/AchievementsStrip.tsx`
- Create: `src/components/child/__tests__/AchievementsStrip.test.tsx`

- [ ] **Step 1: Write the failing test**

`src/components/child/__tests__/AchievementsStrip.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { AchievementsStrip } from '../AchievementsStrip';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

const all: BadgeDefinition[] = [
  { id: 'b1', name: 'First Steps', description: '', icon_url: '👣', condition_type: 'lessons_completed', condition_value: 1, earned_at: null },
  { id: 'b2', name: 'On Fire', description: '', icon_url: '🔥', condition_type: 'streak', condition_value: 5, earned_at: null },
];
const earned: EarnedBadge[] = [{ id: 'b1', name: 'First Steps', description: '', icon_url: '👣', earned_at: '2026-01-01' }];

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('AchievementsStrip', () => {
  it('renders all badge names and a See all link to /stats', () => {
    wrap(<AchievementsStrip allBadges={all} earnedBadges={earned} />);
    expect(screen.getByText('First Steps')).toBeInTheDocument();
    expect(screen.getByText('On Fire')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /see all/i })).toHaveAttribute('href', '/stats');
  });

  it('renders nothing when there are no badges', () => {
    const { container } = wrap(<AchievementsStrip allBadges={[]} earnedBadges={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<AchievementsStrip allBadges={all} earnedBadges={earned} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run it, verify it fails**

Run: `npm test -- src/components/child/__tests__/AchievementsStrip.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement the component**

`src/components/child/AchievementsStrip.tsx`:
```tsx
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { badgeIcon } from '@/api/admin';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

export function AchievementsStrip({
  allBadges,
  earnedBadges,
}: {
  allBadges: BadgeDefinition[];
  earnedBadges: EarnedBadge[];
}) {
  if (!allBadges.length) return null;
  const earnedIds = new Set(earnedBadges.map((b) => b.id));
  return (
    <section aria-label="Achievements">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-extrabold uppercase tracking-wider text-gray-700">Achievements</h2>
        <Link to="/stats" className="text-xs font-bold text-brand-700 hover:underline">
          See all <span aria-hidden="true">→</span>
        </Link>
      </div>
      <ul className="flex gap-3 overflow-x-auto pb-1">
        {allBadges.map((b) => {
          const earned = earnedIds.has(b.id);
          return (
            <li key={b.id} className="flex w-16 shrink-0 flex-col items-center gap-1 text-center">
              <span
                className={cn(
                  'flex h-12 w-12 items-center justify-center rounded-2xl text-2xl',
                  earned ? 'bg-brand-gradient shadow' : 'bg-muted',
                )}
                aria-hidden="true"
              >
                {earned ? badgeIcon(b) : <Lock className="h-5 w-5 text-gray-400" />}
              </span>
              <span className={cn('text-[10px] font-semibold leading-tight', earned ? 'text-gray-700' : 'text-gray-400')}>
                {b.name}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `npm test -- src/components/child/__tests__/AchievementsStrip.test.tsx`
Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/AchievementsStrip.tsx invest-ed/frontend/src/components/child/__tests__/AchievementsStrip.test.tsx
git commit -m "feat(home): add AchievementsStrip (badges teaser)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Wire Home to LevelProgressCard + AchievementsStrip

**Files:**
- Modify: `src/pages/child/Home.tsx`
- Modify: `src/pages/child/__tests__/child-Home.test.tsx` (if present — update only changed copy/markup)

- [ ] **Step 1: Replace the inline XP bar with `LevelProgressCard`**

In `Home.tsx`: remove the existing "XP Progress to next level" `<div className="mt-4 rounded-2xl border-2 border-amber-200…">…</div>` block (the one with the `motion.div` width bar) and render `<LevelProgressCard level={level} xp={xp} />` in its place (keep the `mt-4` wrapper spacing). Add `import { LevelProgressCard } from '@/components/child/LevelProgressCard';`. `level`/`xp` already exist as locals.

- [ ] **Step 2: Add `AchievementsStrip` below the ReviewBanner**

Add hooks at top: `import { useAllBadges } from '@/hooks/useAllBadges'; import { useBadges } from '@/hooks/useBadges'; import { AchievementsStrip } from '@/components/child/AchievementsStrip';` Then in the component: `const allBadges = useAllBadges(); const earnedBadges = useBadges();` After the `ReviewBanner` block and before the "Your quests" `<section>`, render:
```tsx
{allBadges.data && earnedBadges.data && (
  <div className="mt-5">
    <AchievementsStrip allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
  </div>
)}
```

- [ ] **Step 3: Verify + update Home test**

Run: `npx tsc -b && npm run lint && npm test && npm run build`
If `child-Home.test.tsx` asserted the old XP-bar markup, update those assertions to the new `LevelProgressCard` copy ("Level N Investor"); keep behavioural assertions. Expected: green (button.tsx warning only).

- [ ] **Step 4: Capture + eyeball**

Capture to `/tmp/spb/home` (harness above; the mock already returns progress + badges + modules). VIEW `01-home.png`: confirm the Level investor card sits under the hero, the achievements strip shows earned (gradient) + locked (grey) badges with "See all →", and the quest grid still renders. No layout bleed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Home.tsx invest-ed/frontend/src/pages/child/__tests__
git commit -m "feat(home): gamified layout — Level card + achievements strip

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Quests (`Lessons.tsx`) — progress header + ModuleCard restyle

**Files:**
- Modify: `src/pages/child/Lessons.tsx`
- Modify: `src/components/child/ModuleCard.tsx`
- Test: existing Lessons/ModuleCard tests (update changed markup only)

- [ ] **Step 1: Add an overall-progress header band to `Lessons.tsx`**

Below the `<h1>Quests</h1>` + count `<p>`, before the grid, add a header band computing module progress from the data already loaded (`lessonsByModuleId`): a started-count = modules where `(completed>0 || any lessons)` — concretely, count modules with ≥1 completed lesson as "started", total = `modules.length`. Render:
```tsx
{modules.length > 0 && (() => {
  const started = modules.filter((m) => (lessonsByModuleId.get(m.id) ?? []).some((l) => l.completed)).length;
  const pct = Math.round((started / modules.length) * 100);
  return (
    <div className="mt-4 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
        <span>Your journey</span>
        <span>{started} / {modules.length} modules started</span>
      </div>
      <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100" role="progressbar" aria-valuenow={started} aria-valuemin={0} aria-valuemax={modules.length} aria-label="Modules started">
        <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
})()}
```

- [ ] **Step 2: Restyle `ModuleCard` toward the prototype**

In `ModuleCard.tsx`, keep the props/links/locked logic and the progress bar. Polish the card surface to match the new system: change `border-2 border-brand-200` → `border border-brand-100`, add `shadow-sm`, keep the hover lift on the unlocked variant. Left-align content into a row (emoji tile + title/progress) like the prototype's holdings/quest rows if it reads better — but a centred card is acceptable; the required change is the lighter border + shadow + ensuring the progress bar and "X / Y quests" remain. Keep `data-testid="module-locked"`.

- [ ] **Step 3: Verify + tests**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Update any ModuleCard/Lessons test asserting the old `border-2 border-brand-200` class. Expected: green.

- [ ] **Step 4: Capture + eyeball**

Capture to `/tmp/spb/quests` (add a `/quests`-equivalent: the harness loads `/modules`; navigate `page.goto(BASE + '/lessons')`). VIEW: progress band on top, module cards with progress bars, locked module shown. Confirm no regression.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Lessons.tsx invest-ed/frontend/src/components/child/ModuleCard.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(quests): module-journey progress header + ModuleCard restyle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Module (`Module.tsx`) — LevelCard progress + module header

**Files:**
- Modify: `src/components/child/LevelCard.tsx`
- Modify: `src/pages/child/Module.tsx`
- Test: existing LevelCard test (update markup only)

- [ ] **Step 1: Add a progress bar to `LevelCard`**

In `LevelCard.tsx`, keep the `{level,onOpen,onLockedClick}` API and all states. For `state==='in_progress'`, below the existing `{lessons_completed}/{lessons_total} lessons` text, add a slim progress bar:
```tsx
<div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-brand-100" role="progressbar" aria-valuenow={level.lessons_completed} aria-valuemin={0} aria-valuemax={level.lessons_total} aria-label={`${level.title} progress`}>
  <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${level.lessons_total ? Math.round((level.lessons_completed / level.lessons_total) * 100) : 0}%` }} />
</div>
```
Also soften the card border `border-2 border-brand-200` → `border border-brand-100 shadow-sm`.

- [ ] **Step 2: Add a module progress header to `Module.tsx`**

In the banner area (after the level count `<p>`), add an overall module progress bar computed from `levels`: `completedLevels = levels.filter(l => l.state==='completed').length`. Render a centered progressbar (same pattern, `aria-valuemax={levels.length}`) under the subtitle. Keep the banner gradient + icon.

- [ ] **Step 3: Verify + tests**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Update the LevelCard test if it asserts the old border class. Expected: green.

- [ ] **Step 4: Capture + eyeball**

Capture to `/tmp/spb/module` (`page.goto(BASE + '/lessons/m1')`; harness loads `/modules/m1/levels`). VIEW: module banner with progress, level cards each with a progress bar, locked/premium states intact.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/LevelCard.tsx invest-ed/frontend/src/pages/child/Module.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(module): level progress bars + module progress header

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Level (`Level.tsx`) — LessonRow polish + level progress header

**Files:**
- Modify: `src/components/child/LessonRow.tsx`
- Modify: `src/pages/child/Level.tsx`
- Test: existing LessonRow/Level tests (markup only)

- [ ] **Step 1: Add a level progress header to `Level.tsx`**

Replace the plain `{completed} / {lessons.length} quests complete` `<p>` with a header card containing that text + a progressbar (`aria-valuenow={completed} aria-valuemax={lessons.length}`, `bg-brand-gradient` fill). Keep the `<Link>` back and the bordered list wrapper.

- [ ] **Step 2: Polish `LessonRow`**

In `LessonRow.tsx`, keep the `{moduleId,levelId,lesson,status}` API, the `to` logic, and the StatusIcon. Tighten styling: type chip → `bg-brand-100 text-brand-800` (already), ensure the row has a clear hover (`hover:bg-brand-50` already). Add a subtle XP accent: wrap `{lesson.xp_reward} XP` in `text-accent-700 font-semibold`. No structural change.

- [ ] **Step 3: Verify + tests**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Update Level/LessonRow tests for any changed markup. Expected: green.

- [ ] **Step 4: Capture + eyeball**

Capture to `/tmp/spb/level` (`page.goto(BASE + '/lessons/m1/l1')`; harness loads `/levels/l1/lessons`). VIEW: level progress header + lesson rows with status icons, type chips, XP.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/LessonRow.tsx invest-ed/frontend/src/pages/child/Level.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(level): level progress header + LessonRow polish

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Stats (`Stats.tsx`) — card aesthetic

**Files:**
- Modify: `src/pages/child/Stats.tsx`

- [ ] **Step 1: Wrap each section in a card**

Keep all hooks/children/data. Wrap the Badges, Weekly Challenges, and Weekly Leaderboard `<section>`s each in `className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm"`, and restyle the `<h2>` headers to `text-sm font-extrabold uppercase tracking-wider text-gray-700 mb-3`. Keep `XpSummary` as-is (it's already a card) or wrap consistently. Update `SectionSkeleton` to `rounded-2xl`. Do not change the child components or data.

- [ ] **Step 2: Verify**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Expected: green (update a Stats test only if it asserts old section markup).

- [ ] **Step 3: Capture + eyeball**

Capture to `/tmp/spb/stats` (`page.goto(BASE + '/stats')`; harness loads `/badges`, `/challenges`, `/leaderboard`, `/users/me/badges`, `/users/me/progress`). VIEW: sectioned cards (XP, badges grid, challenges, leaderboard) in the new aesthetic.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Stats.tsx invest-ed/frontend/src/pages/child/__tests__
git commit -m "feat(stats): card-styled sections

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Progress (`StrengthsGaps.tsx`) — light polish

**Files:**
- Modify: `src/pages/child/StrengthsGaps.tsx` (+ its TopicCard/MasteryRing if inline)

- [ ] **Step 1: Resolve the leftover slate tones + align cards**

Read the file. The `slate-600`/`slate-400` tones are used on what look like dark topic cards. Decision: if a topic card has a dark/coloured background, keep slate-on-dark (AA) as intentional; if `slate-400` is used as **text on white**, bump to `text-muted-foreground` (slate-600) for AA. Align any card surface to `rounded-2xl border border-brand-100 bg-card shadow-sm` where it currently uses ad-hoc borders. Keep the MasteryRing and TopicCard structure unchanged.

- [ ] **Step 2: Verify**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Expected: green.

- [ ] **Step 3: Capture + eyeball**

Capture to `/tmp/spb/progress` (`page.goto(BASE + '/progress')`; harness loads `/profile/strengths` + `/profile/mastery` — extend the mock if those return richer shapes). VIEW: mastery ring + topic cards read cleanly, text contrast AA.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/StrengthsGaps.tsx
git commit -m "feat(progress): card-style alignment + contrast polish

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Coach (`Coach.tsx`) — Penny avatar header + spacing polish

**Files:**
- Modify: `src/pages/child/Coach.tsx`

- [ ] **Step 1: Replace the 💡 with a Penny avatar in the header**

Add `import { Penny } from '@/components/child/ui/Penny';`. Replace `<span className="text-xl">💡</span>` with:
```tsx
<span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
  <Penny size={28} mood="happy" />
</span>
```
Keep "Coach Penny" + the messages-left counter. No behaviour/payload change. Optionally tidy chip spacing (`gap-2` → `gap-2.5`) — purely visual.

- [ ] **Step 2: Verify**

Run: `npx tsc -b && npm run lint && npm test && npm run build`. Expected: green (update a Coach test only if it asserted the 💡).

- [ ] **Step 3: Capture + eyeball**

Capture to `/tmp/spb/coach` (`page.goto(BASE + '/coach')`; harness loads the greeting). VIEW: Penny avatar in the header, branded chat, suggestion chips.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Coach.tsx invest-ed/frontend/src/pages/child/__tests__
git commit -m "feat(coach): Penny avatar in header + spacing polish

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Final a11y + full regression + push

**Files:** any a11y fix; remove `tmp-shot.mjs`.

- [ ] **Step 1: Contrast/a11y sweep of new + changed UI**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rnE "text-(brand|info)-(300|400)" src/components/child src/pages/child
```
Bump any that are text-on-white to `-600/700` (leave labels on dark/gradient). Confirm every new progressbar has `role="progressbar"` + aria-value*, decorative glyphs are `aria-hidden`, and the achievements strip badge names are real text.

- [ ] **Step 2: Full regression**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: tsc clean; lint = only the button.tsx warning; vitest green (incl. the 6 new component tests); build OK. Backend untouched (no run needed, but a final `pytest -q` is harmless if quick).

- [ ] **Step 3: Cleanup + push**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && rm -f tmp-shot.mjs
cd "/Users/leeashmore/Local Repo"
git status --porcelain   # only intended files; tmp-shot.mjs gone
git add -A invest-ed/frontend/src
git commit -m "a11y(child-core): contrast pass for SP-B layouts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "no a11y fixes needed"
git push origin main
```

- [ ] **Step 4: Confirm green CI**

Watch the run for `main`: all 5 jobs green (the a11y job — jsx-a11y + vitest-axe + playwright-axe — guards the new components/progressbars). Fix any failure before declaring SP-B done.

- [ ] **Step 5: Report SP-B complete**

Confirm: gamified Home, richer learning path, card Stats, polished Progress/Coach; CI green. iOS rebuild still deferred to programme end. Next: SP-C (simulator suite).

---

## Self-Review

**1. Spec coverage:** LevelProgressCard → Task 1; AchievementsStrip → Task 2; Home gamified → Task 3; Quests header + ModuleCard → Task 4; Module/LevelCard progress → Task 5; Level/LessonRow → Task 6; Stats cards → Task 7; Progress polish → Task 8; Coach Penny header → Task 9; a11y + regression → Task 10. All spec sections covered. ✓

**2. Placeholder scan:** New components carry full code + tests. Screen restyles give exact files, the specific class/markup changes, and a screenshot+build+test gate — not "restyle appropriately." The one judgement call (Progress slate tones) has explicit keep/bump criteria. ✓

**3. Type consistency:** `LevelProgressCard {level,xp,className}` used identically in Tasks 1 & 3. `AchievementsStrip {allBadges,earnedBadges}` (matching `useAllBadges`/`useBadges` data) in Tasks 2 & 3. Existing component APIs (`LevelCard`/`LessonRow`/`ModuleCard`) are preserved — only internal markup changes (Tasks 4–6). `badgeIcon(badge)` signature matches `src/api/admin.ts`. Progressbar aria pattern consistent across Tasks 1/4/5/6. ✓
