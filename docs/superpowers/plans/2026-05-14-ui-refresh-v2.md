# UI Refresh v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mobile bottom-tab navigation, playful reward animations, Simulator visual polish with a portfolio value chart, and copy fixes.

**Architecture:** Three frontend workstreams (mobile nav, animations, Simulator refresh) plus one small backend endpoint (portfolio history). Framer Motion drives page transitions and spring animations. Recharts renders the portfolio chart. canvas-confetti fires on quest completion.

**Tech Stack:** React 18, Framer Motion, Recharts, canvas-confetti, Tailwind CSS, FastAPI, SQLAlchemy, PostgreSQL

---

### Task 1: Install Dependencies & Copy Fix

**Files:**
- Modify: `invest-ed/frontend/package.json`
- Modify: `invest-ed/frontend/src/pages/child/Lessons.tsx:41`

- [ ] **Step 1: Install framer-motion, canvas-confetti, and recharts**

```bash
cd invest-ed/frontend && npm install framer-motion canvas-confetti recharts && npm install -D @types/canvas-confetti
```

- [ ] **Step 2: Verify installation**

Run: `cd invest-ed/frontend && node -e "require('framer-motion'); require('canvas-confetti'); require('recharts'); console.log('OK')"`
Expected: `OK`

- [ ] **Step 3: Fix "Lessons" → "Quests" heading**

In `invest-ed/frontend/src/pages/child/Lessons.tsx`, change line 41 from:

```tsx
<h1 className="text-2xl font-extrabold text-gray-900">Lessons</h1>
```

to:

```tsx
<h1 className="text-2xl font-extrabold text-gray-900">Quests</h1>
```

- [ ] **Step 4: Run lint and type check**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npx eslint src/pages/child/Lessons.tsx`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
cd invest-ed/frontend && git add package.json package-lock.json src/pages/child/Lessons.tsx && git commit -m "chore: install framer-motion, canvas-confetti, recharts; fix Lessons→Quests heading"
```

---

### Task 2: Bottom Tab Bar Component

**Files:**
- Create: `invest-ed/frontend/src/components/child/BottomTabBar.tsx`
- Test: `invest-ed/frontend/tests/unit/child-BottomTabBar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `invest-ed/frontend/tests/unit/child-BottomTabBar.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomTabBar } from '@/components/child/BottomTabBar';

describe('BottomTabBar', () => {
  it('renders four nav links', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(4);
  });

  it('highlights the active tab', () => {
    render(
      <MemoryRouter initialEntries={['/lessons']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    const questsLink = screen.getByRole('link', { name: /quests/i });
    expect(questsLink.className).toContain('text-amber-600');
  });

  it('shows correct labels for all tabs', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Quests')).toBeInTheDocument();
    expect(screen.getByText('Simulator')).toBeInTheDocument();
    expect(screen.getByText('Stats')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-BottomTabBar.test.tsx`
Expected: FAIL — module `@/components/child/BottomTabBar` not found

- [ ] **Step 3: Write the BottomTabBar component**

Create `invest-ed/frontend/src/components/child/BottomTabBar.tsx`:

```tsx
import { NavLink } from 'react-router-dom';
import { Home, BookOpen, TrendingUp, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = [
  { to: '/home', label: 'Home', Icon: Home },
  { to: '/lessons', label: 'Quests', Icon: BookOpen },
  { to: '/simulator', label: 'Simulator', Icon: TrendingUp },
  { to: '/stats', label: 'Stats', Icon: BarChart3 },
] as const;

export function BottomTabBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-amber-200 bg-white/95 backdrop-blur md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label="Primary mobile"
    >
      <div className="flex h-16 items-center justify-around">
        {TABS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 px-3 py-1 text-xs font-medium transition-colors',
                isActive ? 'text-amber-600' : 'text-gray-400',
              )
            }
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-BottomTabBar.test.tsx`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/BottomTabBar.tsx tests/unit/child-BottomTabBar.test.tsx && git commit -m "feat: add BottomTabBar mobile navigation component"
```

---

### Task 3: Integrate Bottom Tab Bar into Shell & Simplify TopNav

**Files:**
- Modify: `invest-ed/frontend/src/components/child/Shell.tsx`
- Modify: `invest-ed/frontend/src/components/child/TopNav.tsx`
- Test: `invest-ed/frontend/tests/unit/child-TopNav.test.tsx` (update existing)

- [ ] **Step 1: Update Shell.tsx to add BottomTabBar and mobile padding**

Replace the entire contents of `invest-ed/frontend/src/components/child/Shell.tsx` with:

```tsx
import { Outlet } from 'react-router-dom';
import { useChildSession } from '@/hooks/useChildSession';
import { useChildAuthGuard } from '@/hooks/useChildAuthGuard';
import { TopNav } from './TopNav';
import { BottomTabBar } from './BottomTabBar';

export function Shell() {
  const session = useChildSession();
  useChildAuthGuard(session.error);

  if (session.isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
        <header className="h-14 border-b border-amber-200" aria-busy="true" />
        <p className="mx-auto mt-6 max-w-2xl px-4 text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!session.data) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      <TopNav username={session.data.username} />
      <main className="pb-20 md:pb-0">
        <Outlet />
      </main>
      <BottomTabBar />
    </div>
  );
}
```

Key changes: import `BottomTabBar`, add `pb-20 md:pb-0` to `<main>` so content doesn't get hidden behind the bottom bar on mobile, render `<BottomTabBar />` after main.

- [ ] **Step 2: Simplify TopNav — remove hamburger Sheet**

Replace the entire contents of `invest-ed/frontend/src/components/child/TopNav.tsx` with:

```tsx
import { Link, NavLink } from 'react-router-dom';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

const NAV_LINKS = [
  { to: '/home', label: 'Home' },
  { to: '/lessons', label: 'Quests' },
  { to: '/simulator', label: 'Simulator' },
  { to: '/stats', label: 'Stats' },
] as const;

export function TopNav({ username }: { username: string }) {
  return (
    <header className="sticky top-0 z-10 border-b border-amber-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/home" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-center text-sm font-extrabold text-white">IE</span>
          <span className="text-lg font-extrabold text-gray-900">Invest-Ed</span>
        </Link>

        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors',
                isActive
                  ? 'text-amber-600 bg-amber-50 border-b-2 border-amber-400'
                  : 'text-gray-600 hover:text-amber-600 hover:bg-amber-50',
              )}>{label}</NavLink>
          ))}
        </nav>

        <div className="ml-auto">
          <ProfileMenu username={username} />
        </div>
      </div>
    </header>
  );
}
```

Key changes: removed `Menu` icon, `Button`, `Sheet`/`SheetContent`/`SheetTrigger` imports and the entire hamburger menu block. The desktop nav (`hidden md:flex`) stays. On mobile, only logo + profile avatar show in the top nav — the `BottomTabBar` handles navigation.

- [ ] **Step 3: Update TopNav test**

Read the existing `invest-ed/frontend/tests/unit/child-TopNav.test.tsx` and update it. The test currently checks for "Quests" in the nav links — that should still pass. If it checks for the hamburger menu button, remove that assertion. Replace any assertion about "Open menu" button with an assertion that the hamburger is NOT present:

```tsx
it('does not render a hamburger menu button', () => {
  render(
    <MemoryRouter initialEntries={['/home']}>
      <TopNav username="testuser" />
    </MemoryRouter>,
  );
  expect(screen.queryByLabelText('Open menu')).not.toBeInTheDocument();
});
```

- [ ] **Step 4: Run all frontend tests**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/Shell.tsx src/components/child/TopNav.tsx tests/unit/child-TopNav.test.tsx && git commit -m "feat: integrate BottomTabBar, remove hamburger menu from TopNav"
```

---

### Task 4: Page Transitions with Framer Motion

**Files:**
- Modify: `invest-ed/frontend/src/components/child/Shell.tsx`

- [ ] **Step 1: Add AnimatePresence page transitions to Shell**

Replace the entire contents of `invest-ed/frontend/src/components/child/Shell.tsx` with:

```tsx
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useChildSession } from '@/hooks/useChildSession';
import { useChildAuthGuard } from '@/hooks/useChildAuthGuard';
import { TopNav } from './TopNav';
import { BottomTabBar } from './BottomTabBar';

export function Shell() {
  const session = useChildSession();
  useChildAuthGuard(session.error);
  const location = useLocation();

  if (session.isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
        <header className="h-14 border-b border-amber-200" aria-busy="true" />
        <p className="mx-auto mt-6 max-w-2xl px-4 text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!session.data) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      <TopNav username={session.data.username} />
      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname}
          className="pb-20 md:pb-0"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
        >
          <Outlet />
        </motion.main>
      </AnimatePresence>
      <BottomTabBar />
    </div>
  );
}
```

Key changes: import `useLocation` from react-router-dom, import `AnimatePresence` and `motion` from framer-motion. Wrap `<main>` in `<AnimatePresence mode="wait">` and replace `<main>` with `<motion.main>` with fade + Y-slide animation keyed on `location.pathname`.

- [ ] **Step 2: Run type check and lint**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npx eslint src/components/child/Shell.tsx`
Expected: No errors

- [ ] **Step 3: Run all frontend tests**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/Shell.tsx && git commit -m "feat: add page transitions with Framer Motion AnimatePresence"
```

---

### Task 5: CompletionPanel Animations (Confetti, XP Counter, Trophy Bounce)

**Files:**
- Modify: `invest-ed/frontend/src/components/child/lesson/CompletionPanel.tsx`
- Modify: `invest-ed/frontend/tests/unit/child-CompletionPanel.test.tsx`

- [ ] **Step 1: Update the CompletionPanel test to expect animated content**

Read `invest-ed/frontend/tests/unit/child-CompletionPanel.test.tsx`. The existing test checks for `+25 XP` text. With the animated counter, the XP will animate from 0 to 25 via Framer Motion. In tests (JSDOM), Framer Motion springs resolve immediately, so `+25 XP` should still appear. However, canvas-confetti requires a real canvas, so we need to mock it.

Update the test file. Add a mock for `canvas-confetti` at the top:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';

vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

const baseResult = { xp_awarded: 25, already_completed: false, total_xp: 320, level: 4, streak_count: 5, practice_available: false };

describe('CompletionPanel', () => {
  it('shows xp awarded, totals, and Next Quest link when next exists', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId="L2" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Quest Complete!/)).toBeInTheDocument();
    expect(screen.getByText(/Total: 320 XP/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Next Quest/ })).toHaveAttribute('href', '/lessons/m/L2');
  });

  it('omits Next Quest link and shows Back to module when no next', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: /Next Quest/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to module/ })).toHaveAttribute('href', '/lessons/m');
  });

  it('already-completed variant skips XP line and changes heading', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/already done this one/i)).toBeInTheDocument();
  });

  it('fires confetti when quest is freshly completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(confetti).toHaveBeenCalled();
  });

  it('does not fire confetti when already completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    (confetti as ReturnType<typeof vi.fn>).mockClear();
    render(
      <MemoryRouter>
        <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(confetti).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify existing tests still conceptually match**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-CompletionPanel.test.tsx`
Expected: FAIL (confetti tests fail because CompletionPanel doesn't import confetti yet)

- [ ] **Step 3: Update CompletionPanel with animations**

Replace the entire contents of `invest-ed/frontend/src/components/child/lesson/CompletionPanel.tsx` with:

```tsx
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import confetti from 'canvas-confetti';
import type { LessonCompletionResult } from '@/api/content';
import { Button } from '@/components/ui/button';
import { Trophy } from './illustrations/Trophy';

type Props = {
  result: LessonCompletionResult;
  moduleId: string;
  nextLessonId: string | null;
};

export function CompletionPanel({ result, moduleId, nextLessonId }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Quest Complete!';
  const xpInLevel = result.total_xp % 100;

  const xpCount = useMotionValue(0);
  const xpDisplay = useTransform(xpCount, (v) => `+${Math.round(v)} XP`);

  useEffect(() => {
    if (!result.already_completed) {
      confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
      animate(xpCount, result.xp_awarded, { duration: 0.6 });
    }
  }, [result.already_completed, result.xp_awarded, xpCount]);

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-4">
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
      >
        <Trophy />
      </motion.div>
      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>
      {!result.already_completed && (
        <motion.p className="text-3xl font-extrabold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          {xpDisplay}
        </motion.p>
      )}
      <div className="flex justify-center gap-3 text-sm text-gray-500">
        <span>Total: {result.total_xp} XP</span>
        <span>·</span>
        <span>Level {result.level}</span>
        <span>·</span>
        <span>🔥 {result.streak_count}-day streak</span>
      </div>
      <div className="mx-auto max-w-[240px]">
        <div className="h-2 w-full overflow-hidden rounded-full bg-amber-100">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
            initial={{ width: 0 }}
            animate={{ width: `${xpInLevel}%` }}
            transition={{ duration: 0.8, delay: 0.3 }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">{xpInLevel} / 100 XP to Level {result.level + 1}</p>
      </div>
      <div className="flex justify-center gap-2 pt-2">
        {nextLessonId ? (
          <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
            <Link to={`/lessons/${moduleId}/${nextLessonId}`}>Next Quest →</Link>
          </Button>
        ) : (
          <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
            <Link to={`/lessons/${moduleId}`}>Back to module</Link>
          </Button>
        )}
      </div>
    </div>
  );
}
```

Key changes: import `useEffect`, import `motion`, `useMotionValue`, `useTransform`, `animate` from framer-motion, import `confetti` from canvas-confetti. Added confetti burst on mount, animated XP counter using `useMotionValue` + `animate`, trophy bounce-in using `motion.div` with spring, and smooth progress bar fill using `motion.div` with initial width 0.

- [ ] **Step 4: Run CompletionPanel tests**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-CompletionPanel.test.tsx`
Expected: All 5 tests pass

- [ ] **Step 5: Run full frontend test suite**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/lesson/CompletionPanel.tsx tests/unit/child-CompletionPanel.test.tsx && git commit -m "feat: add confetti, animated XP counter, trophy bounce to CompletionPanel"
```

---

### Task 6: Home Page & StatsBar Animations

**Files:**
- Modify: `invest-ed/frontend/src/components/child/StatsBar.tsx`
- Modify: `invest-ed/frontend/src/pages/child/Home.tsx`
- Modify: `invest-ed/frontend/src/components/child/ModuleCard.tsx`

- [ ] **Step 1: Add streak pulse animation to StatsBar**

Replace the entire contents of `invest-ed/frontend/src/components/child/StatsBar.tsx` with:

```tsx
import { isStreakActive } from '@/lib/streak';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function StatsBar({ xp, level, streakCount, lastActivityDate, today }: Props) {
  const now = today ?? new Date();
  const active = isStreakActive(lastActivityDate, now);
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Your progress">
      <span className="rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-1.5 text-sm font-bold text-white">
        ⭐ Level {level}
      </span>
      <span className="rounded-full bg-blue-100 px-4 py-1.5 text-sm font-bold text-blue-800">
        {xp} XP
      </span>
      <span
        className={cn(
          'rounded-full bg-amber-100 px-4 py-1.5 text-sm font-bold text-amber-800',
          active && 'animate-pulse',
          !active && 'opacity-50',
        )}
        aria-label={active ? 'streak active' : 'streak inactive'}
      >
        🔥 {streakCount}-day streak
      </span>
    </div>
  );
}
```

Key change: added `animate-pulse` class (from tailwindcss-animate) to the streak chip when active.

- [ ] **Step 2: Add smooth XP progress bar animation to Home page**

In `invest-ed/frontend/src/pages/child/Home.tsx`, add Framer Motion import and replace the static progress bar with an animated one.

Add to imports at the top:

```tsx
import { motion } from 'framer-motion';
```

Then find the progress bar div (the `<div>` inside the XP progress card with `className="h-2.5 w-full overflow-hidden rounded-full bg-amber-100"`). Replace the inner div:

```tsx
<div
  className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500 transition-all"
  style={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
/>
```

with:

```tsx
<motion.div
  className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
  initial={{ width: 0 }}
  animate={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
  transition={{ duration: 0.8, delay: 0.2 }}
/>
```

- [ ] **Step 3: Add hover lift animation to ModuleCard**

In `invest-ed/frontend/src/components/child/ModuleCard.tsx`, the unlocked card `<Link>` already has `hover:border-amber-400 hover:shadow-md`. Enhance it by adding `hover:-translate-y-1` to the className:

Find:
```tsx
className="flex flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center transition hover:border-amber-400 hover:shadow-md"
```

Replace with:
```tsx
className="flex flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center transition-all duration-200 hover:-translate-y-1 hover:border-amber-400 hover:shadow-md"
```

- [ ] **Step 4: Add tap feedback to quiz/scenario choice buttons**

In `invest-ed/frontend/src/components/child/lesson/QuizLesson.tsx`, find the label className (around line 37):

```tsx
'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-colors',
```

Replace with:
```tsx
'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-all active:scale-[0.98]',
```

In `invest-ed/frontend/src/components/child/lesson/ScenarioLesson.tsx`, find the choice/option labels and add the same `active:scale-[0.98]` class. Look for any `<label>` or `<button>` elements that wrap answer choices and add `transition-all active:scale-[0.98]` to their className.

- [ ] **Step 5: Run all frontend tests**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/StatsBar.tsx src/pages/child/Home.tsx src/components/child/ModuleCard.tsx src/components/child/lesson/QuizLesson.tsx src/components/child/lesson/ScenarioLesson.tsx && git commit -m "feat: add streak pulse, XP progress animation, module card hover lift, tap feedback"
```

---

### Task 7: Badge Grid Staggered Entrance Animation

**Files:**
- Modify: `invest-ed/frontend/src/components/child/stats/BadgeGrid.tsx`

- [ ] **Step 1: Add staggered entrance to BadgeGrid**

Replace the entire contents of `invest-ed/frontend/src/components/child/stats/BadgeGrid.tsx` with:

```tsx
import { BookOpen, Flame, Lock, Star, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';
import { cn } from '@/lib/utils';

type Props = {
  allBadges: BadgeDefinition[];
  earnedBadges: EarnedBadge[];
};

const CONDITION_ICONS: Record<string, React.ElementType> = {
  lesson_count: BookOpen,
  streak_days: Flame,
  trade_count: TrendingUp,
  total_xp: Star,
};

function formatEarnedDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffDays === 0) return 'Earned today';
  if (diffDays === 1) return 'Earned yesterday';
  if (diffDays < 30) return `Earned ${diffDays} days ago`;
  return `Earned ${date.toLocaleDateString()}`;
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1 },
};

export function BadgeGrid({ allBadges, earnedBadges }: Props) {
  const earnedById = new Map(earnedBadges.map((b) => [b.id, b]));

  return (
    <motion.div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {allBadges.map((badge) => {
        const earned = earnedById.get(badge.id);
        const Icon = CONDITION_ICONS[badge.condition_type] ?? Star;
        const isNewlyEarned = earned && formatEarnedDate(earned.earned_at) === 'Earned today';

        return (
          <motion.div
            key={badge.id}
            variants={item}
            className={cn(
              'relative rounded-lg border p-4',
              earned ? 'bg-card' : 'bg-muted/50 opacity-60',
            )}
          >
            <div className="flex items-start gap-3">
              <motion.div
                className={cn(
                  'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                  earned ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground',
                )}
                {...(isNewlyEarned
                  ? {
                      initial: { scale: 0, rotate: -180 },
                      animate: { scale: 1, rotate: 0 },
                      transition: { type: 'spring', stiffness: 200, damping: 12 },
                    }
                  : {})}
              >
                <Icon className="h-5 w-5" />
              </motion.div>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{badge.name}</p>
                <p className="text-sm text-muted-foreground">{badge.description}</p>
                {earned ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatEarnedDate(earned.earned_at)}
                  </p>
                ) : (
                  <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground" aria-label="locked">
                    <Lock className="h-3 w-3" />
                    Locked
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
```

Key changes: import `motion` from framer-motion. Replaced outer `<div>` with `<motion.div>` using `staggerChildren` variants. Each badge card is now `<motion.div>` with fade+scale entrance. Badges earned today get an extra spin-in animation on their icon.

- [ ] **Step 2: Run BadgeGrid tests**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/child-BadgeGrid.test.tsx`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
cd invest-ed/frontend && git add src/components/child/stats/BadgeGrid.tsx && git commit -m "feat: add staggered entrance and badge unlock animation to BadgeGrid"
```

---

### Task 8: Backend Portfolio History Endpoint

**Files:**
- Modify: `invest-ed/backend/app/schemas/simulator.py`
- Modify: `invest-ed/backend/app/routers/simulator.py`
- Modify: `invest-ed/backend/tests/test_simulator.py`

- [ ] **Step 1: Write the failing test**

Append the following tests to the end of `invest-ed/backend/tests/test_simulator.py`:

```python


async def test_portfolio_history_empty_when_no_trades(client):
    await _login(client, email="hist@example.com", username="histuser")
    r = await client.get("/portfolio/history")
    assert r.status_code == 200
    assert r.json() == []


async def test_portfolio_history_returns_snapshots_after_trades(client):
    await _login(client, email="hist2@example.com", username="hist2user")
    # Make two trades
    await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"})
    await client.post("/portfolio/trades", json={"ticker": "BP", "exchange": "LSE", "type": "buy", "shares": "5"})

    r = await client.get("/portfolio/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) >= 1
    # Each entry has date and value
    for entry in history:
        assert "date" in entry
        assert "value" in entry
        assert isinstance(entry["value"], (int, float))
    # The last entry's value should match current portfolio total_value
    pf = (await client.get("/portfolio")).json()
    assert abs(history[-1]["value"] - float(pf["total_value"])) < 0.02
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/backend && python -m pytest tests/test_simulator.py::test_portfolio_history_empty_when_no_trades -v`
Expected: FAIL with 404 (endpoint doesn't exist)

- [ ] **Step 3: Add PortfolioSnapshot schema**

In `invest-ed/backend/app/schemas/simulator.py`, add the following class at the end of the file:

```python


class PortfolioSnapshot(BaseModel):
    date: str
    value: float
```

- [ ] **Step 4: Add the portfolio history endpoint**

In `invest-ed/backend/app/routers/simulator.py`, add the new import and endpoint.

Add `PortfolioSnapshot` to the imports from `app.schemas.simulator`:

Change the import line:
```python
from app.schemas.simulator import (
    HoldingOut,
    PortfolioOut,
    QuoteOut,
    TradeOut,
    TradeRequest,
)
```

to:
```python
from app.schemas.simulator import (
    HoldingOut,
    PortfolioOut,
    PortfolioSnapshot,
    QuoteOut,
    TradeOut,
    TradeRequest,
)
```

Then add the following import at the top alongside existing imports:

```python
from collections import defaultdict
from decimal import Decimal
```

(`Decimal` is already imported — just add `defaultdict`.)

Then add the endpoint before the closing of the file (after the `list_trades` function):

```python


@router.get("/portfolio/history", response_model=list[PortfolioSnapshot])
async def portfolio_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    if not portfolio:
        return []

    trades = (
        await session.scalars(
            select(Trade)
            .where(Trade.portfolio_id == portfolio.id)
            .order_by(Trade.executed_at.asc())
        )
    ).all()

    if not trades:
        return []

    # Build daily snapshots from trade history
    holdings: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    cash = portfolio.virtual_cash
    # Reconstruct starting cash: reverse all trades
    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash += cost
        else:
            cash -= cost

    snapshots: list[PortfolioSnapshot] = []
    seen_dates: set[str] = set()

    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash -= cost
            holdings[f"{t.exchange}:{t.ticker}"] += t.shares
        else:
            cash += cost
            holdings[f"{t.exchange}:{t.ticker}"] -= t.shares

        date_str = t.executed_at.date().isoformat()
        # Compute portfolio value at this point using trade prices as proxy
        holding_value = Decimal("0")
        for key, shares in holdings.items():
            if shares <= 0:
                continue
            exchange, ticker = key.split(":", 1)
            try:
                q = provider.get_quote(ticker, exchange)
                holding_value += q.price * shares
            except Exception:
                holding_value += t.price * shares

        if date_str in seen_dates:
            # Update the last snapshot for this date
            snapshots[-1] = PortfolioSnapshot(
                date=date_str, value=float((cash + holding_value).quantize(Decimal("0.01")))
            )
        else:
            seen_dates.add(date_str)
            snapshots.append(
                PortfolioSnapshot(
                    date=date_str, value=float((cash + holding_value).quantize(Decimal("0.01")))
                )
            )

    return snapshots
```

- [ ] **Step 5: Run the tests**

Run: `cd invest-ed/backend && python -m pytest tests/test_simulator.py -v`
Expected: All tests pass, including the two new ones

- [ ] **Step 6: Run full backend test suite**

Run: `cd invest-ed/backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
cd invest-ed/backend && git add app/schemas/simulator.py app/routers/simulator.py tests/test_simulator.py && git commit -m "feat: add GET /portfolio/history endpoint for portfolio value chart"
```

---

### Task 9: Frontend Portfolio Chart Component & Hook

**Files:**
- Create: `invest-ed/frontend/src/hooks/usePortfolioHistory.ts`
- Create: `invest-ed/frontend/src/components/child/simulator/PortfolioChart.tsx`
- Modify: `invest-ed/frontend/src/api/simulator.ts`

- [ ] **Step 1: Add the API method to simulator.ts**

In `invest-ed/frontend/src/api/simulator.ts`, add the type and API method.

Add this type after the existing `TradeOut` type:

```tsx
export type PortfolioSnapshot = {
  date: string;
  value: number;
};
```

Add this method inside the `simulatorApi` object (after `placeTrade`):

```tsx
  getPortfolioHistory: () => apiFetch<PortfolioSnapshot[]>('/portfolio/history'),
```

- [ ] **Step 2: Create the usePortfolioHistory hook**

Create `invest-ed/frontend/src/hooks/usePortfolioHistory.ts`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type PortfolioSnapshot } from '@/api/simulator';

export function usePortfolioHistory() {
  return useQuery<PortfolioSnapshot[] | null>({
    queryKey: ['portfolio-history'],
    queryFn: () => simulatorApi.getPortfolioHistory(),
    retry: false,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 3: Create the PortfolioChart component**

Create `invest-ed/frontend/src/components/child/simulator/PortfolioChart.tsx`:

```tsx
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import type { PortfolioSnapshot } from '@/api/simulator';

type Props = {
  history: PortfolioSnapshot[];
};

export function PortfolioChart({ history }: Props) {
  if (history.length < 2) return null;

  return (
    <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Portfolio Value</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={history}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #fde68a',
              fontSize: '13px',
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#portfolioGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Run type check**

Run: `cd invest-ed/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
cd invest-ed/frontend && git add src/api/simulator.ts src/hooks/usePortfolioHistory.ts src/components/child/simulator/PortfolioChart.tsx && git commit -m "feat: add PortfolioChart component with Recharts and usePortfolioHistory hook"
```

---

### Task 10: Simulator Page Visual Refresh

**Files:**
- Modify: `invest-ed/frontend/src/pages/child/Simulator.tsx`
- Modify: `invest-ed/frontend/src/components/child/simulator/HoldingsTable.tsx`

- [ ] **Step 1: Update HoldingsTable empty state**

In `invest-ed/frontend/src/components/child/simulator/HoldingsTable.tsx`, find the empty state block (the `if (holdings.length === 0)` return). Replace it:

Find:
```tsx
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
```

Replace with:
```tsx
  if (holdings.length === 0) {
    return (
      <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-3">
        <span className="text-5xl">📈</span>
        <p className="font-bold text-gray-900">No stocks yet!</p>
        <p className="text-sm text-gray-500">Start by browsing the market and making your first trade.</p>
        <Link
          to="/simulator/market"
          className="inline-block rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-5 py-2 text-sm font-bold text-white hover:from-amber-500 hover:to-orange-600 transition-colors"
        >
          Browse Market →
        </Link>
      </div>
    );
  }
```

- [ ] **Step 2: Rewrite Simulator page with warm header, styled tabs, and chart**

Replace the entire contents of `invest-ed/frontend/src/pages/child/Simulator.tsx` with:

```tsx
import { useState } from 'react';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useTrades } from '@/hooks/useTrades';
import { usePortfolioHistory } from '@/hooks/usePortfolioHistory';
import { CashCard } from '@/components/child/simulator/CashCard';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';
import { PortfolioChart } from '@/components/child/simulator/PortfolioChart';
import { cn } from '@/lib/utils';

type Tab = 'holdings' | 'history';

export default function Simulator() {
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: trades } = useTrades();
  const { data: history } = usePortfolioHistory();
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
      <div className="rounded-2xl border-2 border-amber-200 bg-gradient-to-b from-amber-100 to-amber-50 p-6 text-center">
        <span className="text-4xl">📊</span>
        <h1 className="mt-2 text-xl font-extrabold text-gray-900">Your Portfolio</h1>
        <p className="text-sm text-gray-500">Practice Mode — no real money</p>
      </div>

      <div className="mt-4">
        <CashCard
          virtualCash={portfolio.virtual_cash}
          totalValue={portfolio.total_value}
          currencyCode={portfolio.currency_code}
          hasMultiCurrency={hasMultiCurrency}
          showTotalValue={holdings.length > 0}
        />
      </div>

      {history && <PortfolioChart history={history} />}

      <div className="mt-6">
        <div role="tablist" className="mb-3 flex gap-1 rounded-lg bg-amber-50 p-1">
          <button
            role="tab"
            aria-selected={activeTab === 'holdings'}
            onClick={() => setActiveTab('holdings')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              activeTab === 'holdings' ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
          >
            Holdings
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              activeTab === 'history' ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
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

Key changes: added warm gradient header with emoji, imported and used `usePortfolioHistory` and `PortfolioChart`, replaced plain border-b tabs with pill-style tabs using `bg-amber-50` background and `bg-white` active state, imported `cn` utility.

- [ ] **Step 3: Run type check and lint**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npx eslint src/pages/child/Simulator.tsx src/components/child/simulator/HoldingsTable.tsx`
Expected: No errors

- [ ] **Step 4: Run all frontend tests**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd invest-ed/frontend && git add src/pages/child/Simulator.tsx src/components/child/simulator/HoldingsTable.tsx && git commit -m "feat: Simulator visual refresh — warm header, pill tabs, chart, illustrated empty state"
```

---

### Task 11: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `cd invest-ed/backend && python -m pytest -v`
Expected: All tests pass (including new portfolio history tests)

- [ ] **Step 2: Run full frontend test suite**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 3: Run frontend lint and type check**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npx eslint .`
Expected: No errors

- [ ] **Step 4: Run frontend build**

Run: `cd invest-ed/frontend && npm run build`
Expected: Build succeeds without errors

- [ ] **Step 5: Run backend lint**

Run: `cd invest-ed/backend && ruff check`
Expected: No errors

- [ ] **Step 6: Visual verification in browser**

Start dev servers if not running:
```bash
cd invest-ed/backend && source ../.venv/bin/activate && uvicorn app.main:app --port 8000 &
cd invest-ed/frontend && npm run dev &
```

Test the following in Chrome DevTools at 375px width (mobile) and 1280px width (desktop):

1. **Bottom tab bar**: Visible on mobile only, all 4 tabs work, active tab highlighted amber
2. **TopNav**: On mobile shows only logo + avatar, no hamburger. On desktop shows full nav links.
3. **Page transitions**: Navigate between tabs — should see subtle fade + slide
4. **Home page**: Streak chip pulses when active, XP progress bar animates on load
5. **Quests page**: Heading says "Quests" (not "Lessons"), module cards lift on hover (desktop)
6. **Simulator**: Warm header, pill-style tabs, illustrated empty state when no holdings
7. **Complete a quest**: Navigate to a lesson, answer it, verify confetti fires, XP counter animates up, trophy bounces in, progress bar fills
8. **Stats page**: Badge grid staggers in, newly-earned badge spins
