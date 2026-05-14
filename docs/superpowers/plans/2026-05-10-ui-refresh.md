# UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the plain UI into a warm, gamified, kid-friendly experience with colour, illustrations, emoji module icons, and "quest" framing.

**Architecture:** Backend adds an `icon` column to modules (migration + seed update + schema). Frontend updates CSS variables for the warm sunset palette, restyles all child-facing components, adds SVG illustration components, and renames "lesson" to "quest" in UI copy. No new dependencies.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy, Alembic, PostgreSQL

---

### Task 1: Backend — Add `icon` column to Module

**Files:**
- Modify: `backend/app/models/content.py`
- Modify: `backend/app/schemas/content.py`
- Modify: `backend/app/routers/content.py`
- Modify: `backend/app/seed/content.py`
- Create: `backend/alembic/versions/xxxx_add_module_icon.py` (via autogenerate)

- [ ] **Step 1: Add `icon` field to Module model**

In `backend/app/models/content.py`, add the `icon` column after `order_index` (line 21):

Replace:
```python
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="module")
```

With:
```python
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    icon: Mapped[str] = mapped_column(String(10), nullable=False, server_default="📚")

    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="module")
```

- [ ] **Step 2: Update ModuleTopic and ModuleOut schema**

In `backend/app/schemas/content.py`, update the `ModuleTopic` literal to include all topics and add `icon` to `ModuleOut`:

Replace:
```python
ModuleTopic = Literal["stocks", "savings", "real_estate"]


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: ModuleTopic
    title: str
    country_codes: list[str]
    is_premium: bool
    order_index: int
    locked: bool = False
```

With:
```python
ModuleTopic = Literal[
    "stocks", "savings", "real_estate", "budgeting", "risk",
    "crypto", "taxes", "debt", "entrepreneurship",
]


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: ModuleTopic
    title: str
    country_codes: list[str]
    is_premium: bool
    order_index: int
    icon: str = "📚"
    locked: bool = False
```

- [ ] **Step 3: Update router to include `icon` in ModuleOut**

In `backend/app/routers/content.py`, update the `list_modules` endpoint to pass `icon` when constructing `ModuleOut` (around line 68):

Replace:
```python
        out.append(ModuleOut(
            id=m.id, topic=m.topic, title=m.title,
            country_codes=m.country_codes, is_premium=m.is_premium,
            order_index=m.order_index, locked=not accessible,
        ))
```

With:
```python
        out.append(ModuleOut(
            id=m.id, topic=m.topic, title=m.title,
            country_codes=m.country_codes, is_premium=m.is_premium,
            order_index=m.order_index, icon=m.icon, locked=not accessible,
        ))
```

- [ ] **Step 4: Add `icon` to all modules in seed data**

In `backend/app/seed/content.py`, add `"icon"` to each module dict. Update the first three modules at the top:

For the first module (around line 8), add `"icon": "📈"` after `"order_index": 0`:
```python
    {
        "topic": "stocks", "title": "What is a Stock?",
        "country_codes": [], "is_premium": False, "order_index": 0, "icon": "📈",
```

For the second module, add `"icon": "🏦"`:
```python
    {
        "topic": "savings", "title": "Compound Interest Basics",
        "country_codes": [], "is_premium": False, "order_index": 1, "icon": "🏦",
```

For the third module, add `"icon": "🏠"`:
```python
    {
        "topic": "real_estate", "title": "What is a REIT?",
        "country_codes": [], "is_premium": False, "order_index": 2, "icon": "🏠",
```

For the remaining 9 modules added in the curriculum expansion, add these icons:
- Module 4 (Budgeting Basics): `"icon": "💰"`
- Module 5 (Needs vs Wants): `"icon": "🛒"`
- Module 6 (Risk & Diversification): `"icon": "🎲"`
- Module 7 (What is Crypto?): `"icon": "₿"`
- Module 8 (How Taxes Work): `"icon": "🧾"`
- Module 9 (Debt & Credit Explained): `"icon": "💳"`
- Module 10 (Starting a Side Hustle): `"icon": "🚀"`
- Module 11 (Revenue, Costs & Profit): `"icon": "📊"`
- Module 12 (Your First Paycheque): `"icon": "💷"`

Also update `seed_modules_and_lessons()` to set `icon` when creating or updating modules. Find the line that creates modules (it should be assigning `topic`, `title`, etc.) and add `icon=mod_data.get("icon", "📚")`.

- [ ] **Step 5: Generate the Alembic migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add module icon column"
```

Expected: Creates a new migration file. Verify it contains `add_column('modules', sa.Column('icon', ...))`.

- [ ] **Step 6: Apply the migration**

Run:
```bash
cd backend && alembic upgrade head
```

Expected: Migration applies successfully.

- [ ] **Step 7: Re-run seed to populate icons**

Run:
```bash
cd backend && python -m app.seed.run
```

Expected: Modules now have `icon` values. Verify:
```bash
cd backend && python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, text
async def check():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(text('SELECT title, icon FROM modules ORDER BY order_index'))
        for r in rows:
            print(r)
asyncio.run(check())
"
```

- [ ] **Step 8: Run the full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass (the seed test may need the `icon` field — if it fails, update the assertion).

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/content.py backend/app/schemas/content.py backend/app/routers/content.py backend/app/seed/content.py backend/alembic/versions/
git commit -m "feat: add icon column to modules with emoji per topic"
```

---

### Task 2: Frontend — Warm sunset colour palette

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/api/content.ts`

- [ ] **Step 1: Update CSS variables for warm sunset palette**

In `frontend/src/index.css`, replace the `:root` variables block:

Replace:
```css
  :root {
    --background: 0 0% 100%;
    --foreground: 222 47% 11%;
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    --primary: 221 83% 53%;
    --primary-foreground: 0 0% 100%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --accent: 210 40% 96%;
    --accent-foreground: 222 47% 11%;
    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 221 83% 53%;
    --radius: 0.5rem;
  }
```

With:
```css
  :root {
    --background: 48 100% 96%;
    --foreground: 220 9% 12%;
    --card: 0 0% 100%;
    --card-foreground: 220 9% 12%;
    --primary: 38 92% 50%;
    --primary-foreground: 0 0% 100%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --muted: 48 100% 93%;
    --muted-foreground: 220 9% 46%;
    --accent: 48 100% 93%;
    --accent-foreground: 220 9% 12%;
    --border: 48 97% 77%;
    --input: 48 97% 77%;
    --ring: 38 92% 50%;
    --radius: 0.75rem;
  }
```

- [ ] **Step 2: Update ModuleTopic type to include all topics**

In `frontend/src/api/content.ts`, update the `ModuleTopic` type and add `icon` to `ModuleOut`:

Replace:
```typescript
export type ModuleTopic = 'stocks' | 'savings' | 'real_estate';
```

With:
```typescript
export type ModuleTopic = 'stocks' | 'savings' | 'real_estate' | 'budgeting' | 'risk' | 'crypto' | 'taxes' | 'debt' | 'entrepreneurship';
```

Replace:
```typescript
export type ModuleOut = {
  id: string;
  topic: ModuleTopic;
  title: string;
  country_codes: string[];
  is_premium: boolean;
  order_index: number;
  locked: boolean;
};
```

With:
```typescript
export type ModuleOut = {
  id: string;
  topic: ModuleTopic;
  title: string;
  country_codes: string[];
  is_premium: boolean;
  order_index: number;
  icon: string;
  locked: boolean;
};
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds (may show warnings about unused vars but no errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css frontend/src/api/content.ts
git commit -m "style: update colour palette to warm sunset theme and add icon to ModuleOut type"
```

---

### Task 3: Frontend — Restyle TopNav and Shell

**Files:**
- Modify: `frontend/src/components/child/TopNav.tsx`
- Modify: `frontend/src/components/child/Shell.tsx`

- [ ] **Step 1: Restyle TopNav with warm colours**

Replace the entire content of `frontend/src/components/child/TopNav.tsx`:

```tsx
import { Link, NavLink } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
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
          <span className="flex h-8 w-8 items-center justify-content rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-center text-sm font-extrabold text-white">IE</span>
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

        <div className="ml-auto flex items-center gap-2">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left">
              <nav className="mt-6 flex flex-col gap-1" aria-label="Primary mobile">
                {NAV_LINKS.map(({ to, label }) => (
                  <NavLink key={to} to={to}
                    className={({ isActive }) => cn(
                      'rounded-lg px-3 py-2 text-sm font-semibold',
                      isActive ? 'bg-amber-50 text-amber-600' : 'text-gray-600 hover:bg-amber-50',
                    )}>{label}</NavLink>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
          <ProfileMenu username={username} />
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Update Shell with warm background**

In `frontend/src/components/child/Shell.tsx`, update the wrapper div to use a warm gradient background:

Replace:
```tsx
  return (
    <div className="min-h-screen">
      <TopNav username={session.data.username} />
      <main>
        <Outlet />
      </main>
    </div>
  );
```

With:
```tsx
  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      <TopNav username={session.data.username} />
      <main>
        <Outlet />
      </main>
    </div>
  );
```

Also update the loading state div to match:

Replace:
```tsx
      <div className="min-h-screen">
        <header className="h-14 border-b" aria-busy="true" />
```

With:
```tsx
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
        <header className="h-14 border-b border-amber-200" aria-busy="true" />
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/child/TopNav.tsx frontend/src/components/child/Shell.tsx
git commit -m "style: restyle TopNav and Shell with warm sunset colours"
```

---

### Task 4: Frontend — Restyle ModuleCard with emoji icons

**Files:**
- Modify: `frontend/src/components/child/ModuleCard.tsx`
- Modify: `frontend/src/components/child/StatsBar.tsx`

- [ ] **Step 1: Restyle ModuleCard with emoji icon and warm styling**

Replace the entire content of `frontend/src/components/child/ModuleCard.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import type { ModuleOut } from '@/api/content';
import { cn } from '@/lib/utils';

type Props = {
  module: ModuleOut;
  completedCount: number;
  totalCount: number;
  onLockedClick: () => void;
};

export function ModuleCard({ module, completedCount, totalCount, onLockedClick }: Props) {
  const pct = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);
  const isDone = pct === 100;

  if (module.locked) {
    return (
      <button
        type="button"
        onClick={onLockedClick}
        aria-label={`${module.title} (locked)`}
        className="flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center opacity-60 cursor-not-allowed"
      >
        <span className="text-3xl">{module.icon}</span>
        <h3 className="font-bold text-sm text-gray-900">{module.title}</h3>
        <span className="inline-flex items-center gap-1 text-xs text-gray-500">
          <Lock className="h-3.5 w-3.5" /> Premium
        </span>
      </button>
    );
  }

  return (
    <Link
      to={`/lessons/${module.id}`}
      className="flex flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center transition hover:border-amber-400 hover:shadow-md"
    >
      <span className="text-4xl">{module.icon}</span>
      <h3 className="font-bold text-sm text-gray-900">{module.title}</h3>
      <p className="text-xs text-gray-500">{completedCount} / {totalCount} quests</p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-amber-100">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            isDone ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gradient-to-r from-amber-400 to-orange-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isDone && (
        <span className="text-xs font-semibold text-green-600">✓ Complete</span>
      )}
    </Link>
  );
}
```

- [ ] **Step 2: Restyle StatsBar with gradient chips**

Replace the entire content of `frontend/src/components/child/StatsBar.tsx`:

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

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/child/ModuleCard.tsx frontend/src/components/child/StatsBar.tsx
git commit -m "style: restyle ModuleCard with emoji icons and StatsBar with gradient chips"
```

---

### Task 5: Frontend — Restyle Home page

**Files:**
- Modify: `frontend/src/pages/child/Home.tsx`

- [ ] **Step 1: Restyle Home page with friendly greeting, XP bar, and quest card**

Replace the entire content of `frontend/src/pages/child/Home.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { StatsBar } from '@/components/child/StatsBar';
import { Button } from '@/components/ui/button';

type NextUp = {
  module: ModuleOut;
  lesson: LessonSummary;
  hasAnyCompletion: boolean;
} | null;

export default function Home() {
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const accessibleModules = (modulesQ.data ?? []).filter((m) => !m.locked);

  const lessonQueries = useQueries({
    queries: accessibleModules.map((m) => ({
      queryKey: ['module', m.id, 'lessons'],
      queryFn: () => contentApi.listLessons(m.id),
      retry: false,
      staleTime: 60_000,
    })),
  });

  const nextUp: NextUp = (() => {
    if (lessonQueries.some((q) => !q.isSuccess)) return null;
    let anyCompletion = false;
    for (let i = 0; i < accessibleModules.length; i++) {
      const lessons = (lessonQueries[i].data ?? []) as LessonSummary[];
      anyCompletion = anyCompletion || lessons.some((l) => l.completed);
      const next = lessons.find((l) => !l.completed);
      if (next) return { module: accessibleModules[i], lesson: next, hasAnyCompletion: anyCompletion };
    }
    return null;
  })();

  const allDone = lessonQueries.length > 0
    && lessonQueries.every((q) => q.isSuccess)
    && nextUp === null;

  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;
  const xpInLevel = xp % 100;
  const xpForNext = 100;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-extrabold text-gray-900">
        Hey {me?.username ?? '…'}! 👋
      </h1>
      <p className="mt-1 text-sm text-gray-500">Ready to level up your money skills?</p>

      <div className="mt-4">
        <StatsBar
          xp={xp}
          level={level}
          streakCount={progress?.streak_count ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
        />
      </div>

      {/* XP Progress to next level */}
      <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Level {level}</span>
          <span>{xpInLevel} / {xpForNext} XP</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-amber-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500 transition-all"
            style={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
          />
        </div>
      </div>

      {/* Next Quest card */}
      <section className="mt-5 rounded-2xl border-2 border-amber-200 bg-white p-4">
        {nextUp ? (
          <QuestCard nextUp={nextUp} />
        ) : allDone ? (
          <p className="text-sm text-center">🎉 You've completed all available quests — more coming soon!</p>
        ) : (
          <p className="text-sm text-gray-500">Loading quests…</p>
        )}
      </section>

      <div className="mt-5">
        <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}

function QuestCard({ nextUp }: { nextUp: NonNullable<NextUp> }) {
  const { module, lesson, hasAnyCompletion } = nextUp;
  const cta = hasAnyCompletion ? 'Resume' : 'Start';
  return (
    <>
      <p className="text-xs font-bold text-amber-700 mb-2">🎯 YOUR NEXT QUEST</p>
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 text-2xl">
          {module.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-gray-900 truncate">{lesson.title}</p>
          <p className="text-xs text-gray-500">{module.title} · {lesson.xp_reward} XP</p>
        </div>
        <Link
          to={`/lessons/${module.id}/${lesson.id}`}
          className="shrink-0 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-2 text-sm font-bold text-white hover:from-amber-500 hover:to-orange-600 transition-colors"
        >
          {cta} →
        </Link>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/child/Home.tsx
git commit -m "style: restyle Home page with friendly greeting, XP bar, and quest card"
```

---

### Task 6: Frontend — Restyle Lessons grid and Module page

**Files:**
- Modify: `frontend/src/pages/child/Lessons.tsx`
- Modify: `frontend/src/pages/child/Module.tsx`
- Modify: `frontend/src/components/child/LessonRow.tsx`

- [ ] **Step 1: Update Lessons page heading and copy**

In `frontend/src/pages/child/Lessons.tsx`, update the heading section:

Replace:
```tsx
      <h1 className="text-2xl font-semibold">Lessons</h1>
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
```

With:
```tsx
      <h1 className="text-2xl font-extrabold text-gray-900">Lessons</h1>
      <p className="mt-1 text-sm text-gray-500">{modules.length} modules · {modules.reduce((acc, m) => acc + (lessonsByModuleId.get(m.id)?.length ?? 0), 0)} quests</p>
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
```

- [ ] **Step 2: Restyle Module page with banner**

Replace the entire content of `frontend/src/pages/child/Module.tsx`:

```tsx
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { LessonRow } from '@/components/child/LessonRow';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
  });

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['module', moduleId, 'lessons'],
    queryFn: () => contentApi.listLessons(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  if (modulesQ.isLoading || lessonsQ.isLoading) {
    return <div className="mx-auto max-w-3xl p-6 text-sm text-gray-500">Loading…</div>;
  }

  if (modulesQ.isError || lessonsQ.isError) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p>Module not found or locked.</p>
        <Link to="/lessons" className="text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);
  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const completed = lessons.filter((l) => l.completed).length;

  return (
    <div className="mx-auto max-w-3xl">
      {/* Banner */}
      <div className="bg-gradient-to-br from-amber-100 to-amber-200 px-6 py-8 text-center">
        <span className="text-5xl">{module?.icon ?? '📚'}</span>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-900">{module?.title ?? 'Module'}</h1>
        <p className="mt-1 text-sm text-gray-600">
          {completed} / {lessons.length} quests complete
        </p>
      </div>

      {/* Quest list */}
      <div className="px-6 py-4">
        <div className="rounded-2xl border-2 border-amber-200 bg-white overflow-hidden">
          {lessons.map((lesson, i) => {
            const nextIndex = lessons.findIndex((l) => !l.completed);
            return (
              <LessonRow
                key={lesson.id}
                moduleId={moduleId!}
                lesson={lesson}
                status={lesson.completed ? 'done' : i === nextIndex ? 'next' : 'later'}
              />
            );
          })}
        </div>
        <Link to="/lessons" className="mt-4 inline-block text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Restyle LessonRow with warm accents**

Replace the entire content of `frontend/src/components/child/LessonRow.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { Check, Play, Circle } from 'lucide-react';
import type { LessonSummary } from '@/api/content';

type Status = 'done' | 'next' | 'later';

export function LessonRow({ moduleId, lesson, status }: { moduleId: string; lesson: LessonSummary; status: Status }) {
  return (
    <Link
      to={`/lessons/${moduleId}/${lesson.id}`}
      className="flex items-center gap-3 border-b border-amber-100 px-4 py-3.5 last:border-b-0 hover:bg-amber-50 transition-colors"
    >
      <StatusIcon status={status} />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-900 truncate">{lesson.order_index + 1}. {lesson.title}</p>
      </div>
      <div className="flex items-center gap-2 text-xs shrink-0">
        <span className="rounded-lg bg-amber-100 px-2 py-0.5 font-semibold text-amber-800 capitalize">{lesson.type}</span>
        <span className="text-gray-500">{lesson.xp_reward} XP</span>
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'done') return <Check aria-label="completed" className="h-5 w-5 text-green-500" />;
  if (status === 'next') return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500">
      <Play aria-label="next up" className="h-3.5 w-3.5 text-white" fill="white" />
    </span>
  );
  return <Circle aria-label="not started" className="h-5 w-5 text-gray-300" />;
}
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/Lessons.tsx frontend/src/pages/child/Module.tsx frontend/src/components/child/LessonRow.tsx
git commit -m "style: restyle Lessons grid, Module page with banner, and LessonRow"
```

---

### Task 7: Frontend — SVG illustration components

**Files:**
- Create: `frontend/src/components/child/lesson/illustrations/FallbackIllustration.tsx`
- Create: `frontend/src/components/child/lesson/illustrations/BudgetPieChart.tsx`
- Create: `frontend/src/components/child/lesson/illustrations/EggsInBaskets.tsx`
- Create: `frontend/src/components/child/lesson/illustrations/CryptoChart.tsx`
- Create: `frontend/src/components/child/lesson/illustrations/Trophy.tsx`
- Create: `frontend/src/components/child/lesson/LessonIllustration.tsx`

- [ ] **Step 1: Create illustrations directory**

Run: `mkdir -p frontend/src/components/child/lesson/illustrations`

- [ ] **Step 2: Create FallbackIllustration**

Create `frontend/src/components/child/lesson/illustrations/FallbackIllustration.tsx`:

```tsx
const TOPIC_EMOJI: Record<string, string> = {
  stocks: '📈',
  savings: '🏦',
  real_estate: '🏠',
  budgeting: '💰',
  risk: '🎲',
  crypto: '₿',
  taxes: '🧾',
  debt: '💳',
  entrepreneurship: '🚀',
};

export function FallbackIllustration({ topic }: { topic: string }) {
  const emoji = TOPIC_EMOJI[topic] ?? '📚';
  return (
    <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 py-8">
      <span className="text-6xl">{emoji}</span>
    </div>
  );
}
```

- [ ] **Step 3: Create BudgetPieChart illustration**

Create `frontend/src/components/child/lesson/illustrations/BudgetPieChart.tsx`:

```tsx
export function BudgetPieChart() {
  return (
    <div className="flex items-center justify-center gap-6 rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 p-6">
      <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
        <circle cx="70" cy="70" r="60" fill="#dbeafe" />
        <path d="M70,70 L70,10 A60,60 0 0,1 122,100 Z" fill="#3b82f6" />
        <path d="M70,70 L122,100 A60,60 0 0,1 18,100 Z" fill="#f59e0b" />
        <path d="M70,70 L18,100 A60,60 0 0,1 70,10 Z" fill="#10b981" />
        <circle cx="70" cy="70" r="28" fill="white" />
        <text x="70" y="74" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1f2937">Budget</text>
      </svg>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-blue-500" />
          <span className="text-sm font-bold text-blue-800">50% Needs</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-amber-500" />
          <span className="text-sm font-bold text-amber-800">30% Wants</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-green-500" />
          <span className="text-sm font-bold text-green-800">20% Savings</span>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create EggsInBaskets illustration**

Create `frontend/src/components/child/lesson/illustrations/EggsInBaskets.tsx`:

```tsx
export function EggsInBaskets() {
  return (
    <div className="flex items-end justify-center gap-8 rounded-xl bg-gradient-to-br from-blue-100 to-purple-100 p-6">
      <div className="text-center">
        <svg width="70" height="80" viewBox="0 0 70 80" aria-hidden="true">
          <ellipse cx="35" cy="65" rx="30" ry="12" fill="#d97706" />
          <rect x="5" y="40" width="60" height="25" rx="4" fill="#f59e0b" />
          <line x1="5" y1="45" x2="65" y2="45" stroke="#d97706" strokeWidth="1.5" />
          <line x1="5" y1="52" x2="65" y2="52" stroke="#d97706" strokeWidth="1.5" />
          <ellipse cx="22" cy="36" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <ellipse cx="38" cy="34" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <ellipse cx="50" cy="36" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <line x1="20" y1="10" x2="50" y2="30" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
          <line x1="50" y1="10" x2="20" y2="30" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <p className="text-xs font-bold text-red-600 mt-1">All in one ✗</p>
      </div>
      <div className="text-center">
        <div className="flex gap-1.5">
          <svg width="50" height="65" viewBox="0 0 50 65" aria-hidden="true">
            <ellipse cx="25" cy="52" rx="22" ry="10" fill="#d97706" />
            <rect x="3" y="32" width="44" height="20" rx="3" fill="#f59e0b" />
            <line x1="3" y1="37" x2="47" y2="37" stroke="#d97706" strokeWidth="1" />
            <line x1="3" y1="43" x2="47" y2="43" stroke="#d97706" strokeWidth="1" />
            <ellipse cx="17" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
            <ellipse cx="33" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          </svg>
          <svg width="50" height="65" viewBox="0 0 50 65" aria-hidden="true">
            <ellipse cx="25" cy="52" rx="22" ry="10" fill="#d97706" />
            <rect x="3" y="32" width="44" height="20" rx="3" fill="#f59e0b" />
            <line x1="3" y1="37" x2="47" y2="37" stroke="#d97706" strokeWidth="1" />
            <line x1="3" y1="43" x2="47" y2="43" stroke="#d97706" strokeWidth="1" />
            <ellipse cx="25" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          </svg>
        </div>
        <p className="text-xs font-bold text-green-600 mt-1">Spread out ✓</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create CryptoChart illustration**

Create `frontend/src/components/child/lesson/illustrations/CryptoChart.tsx`:

```tsx
export function CryptoChart() {
  return (
    <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-orange-100 p-6">
      <svg width="280" height="120" viewBox="0 0 280 120" aria-hidden="true">
        <line x1="30" y1="20" x2="30" y2="100" stroke="#fde68a" strokeWidth="1" />
        <line x1="30" y1="100" x2="270" y2="100" stroke="#fde68a" strokeWidth="1" />
        <line x1="30" y1="60" x2="270" y2="60" stroke="#fde68a" strokeWidth="0.5" strokeDasharray="4" />
        <polyline points="30,80 60,50 90,70 120,20 150,90 180,40 210,75 240,30 270,85" fill="none" stroke="#ea580c" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="248" cy="30" r="16" fill="#f59e0b" />
        <text x="248" y="36" textAnchor="middle" fontSize="18" fontWeight="800" fill="#fff">₿</text>
        <text x="150" y="115" textAnchor="middle" fontSize="10" fill="#92400e" fontWeight="600">↑ This is NOT "guaranteed money" ↑</text>
      </svg>
    </div>
  );
}
```

- [ ] **Step 6: Create Trophy illustration**

Create `frontend/src/components/child/lesson/illustrations/Trophy.tsx`:

```tsx
export function Trophy() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true" className="mx-auto">
      <circle cx="20" cy="25" r="3" fill="#fbbf24" opacity="0.7" />
      <circle cx="100" cy="20" r="2" fill="#f59e0b" opacity="0.6" />
      <circle cx="15" cy="60" r="2" fill="#fde68a" opacity="0.8" />
      <circle cx="105" cy="55" r="3" fill="#fde68a" opacity="0.7" />
      <text x="10" y="45" fontSize="14" fill="#fbbf24">✦</text>
      <text x="100" y="40" fontSize="10" fill="#f59e0b">✦</text>
      <text x="25" y="85" fontSize="8" fill="#fde68a">✦</text>
      <text x="95" y="80" fontSize="12" fill="#fbbf24">✦</text>
      <rect x="45" y="85" width="30" height="8" rx="2" fill="#d97706" />
      <rect x="50" y="75" width="20" height="12" rx="1" fill="#f59e0b" />
      <path d="M35,30 Q35,70 50,75 L70,75 Q85,70 85,30 Z" fill="#fbbf24" />
      <path d="M40,35 Q40,65 52,70 L68,70 Q80,65 80,35 Z" fill="#f59e0b" />
      <text x="60" y="58" textAnchor="middle" fontSize="24" fill="#fff">⭐</text>
      <path d="M35,35 Q20,35 20,50 Q20,65 35,65" fill="none" stroke="#fbbf24" strokeWidth="4" strokeLinecap="round" />
      <path d="M85,35 Q100,35 100,50 Q100,65 85,65" fill="none" stroke="#fbbf24" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}
```

- [ ] **Step 7: Create LessonIllustration resolver component**

Create `frontend/src/components/child/lesson/LessonIllustration.tsx`:

```tsx
import type { ComponentType } from 'react';
import { BudgetPieChart } from './illustrations/BudgetPieChart';
import { EggsInBaskets } from './illustrations/EggsInBaskets';
import { CryptoChart } from './illustrations/CryptoChart';
import { FallbackIllustration } from './illustrations/FallbackIllustration';

const ILLUSTRATION_MAP: Record<string, ComponentType> = {
  'The 50/30/20 rule': BudgetPieChart,
  'Which portfolio is more diversified?': EggsInBaskets,
  "Your friend's hot stock tip": EggsInBaskets,
  'Build a simple portfolio': EggsInBaskets,
  'True or false about crypto': CryptoChart,
  'Classmate says crypto is guaranteed money': CryptoChart,
  'Crypto vs stocks vs savings': CryptoChart,
};

type Props = {
  lessonTitle: string;
  topic: string;
};

export function LessonIllustration({ lessonTitle, topic }: Props) {
  const Illustration = ILLUSTRATION_MAP[lessonTitle];
  if (Illustration) return <Illustration />;
  return <FallbackIllustration topic={topic} />;
}
```

- [ ] **Step 8: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/child/lesson/illustrations/ frontend/src/components/child/lesson/LessonIllustration.tsx
git commit -m "feat: add SVG illustration components for lessons"
```

---

### Task 8: Frontend — Restyle lesson pages with illustrations and quest copy

**Files:**
- Modify: `frontend/src/components/child/lesson/CardLesson.tsx`
- Modify: `frontend/src/components/child/lesson/QuizLesson.tsx`
- Modify: `frontend/src/components/child/lesson/ScenarioLesson.tsx`
- Modify: `frontend/src/components/child/lesson/CompletionPanel.tsx`
- Modify: `frontend/src/pages/child/Lesson.tsx`

- [ ] **Step 1: Restyle CardLesson with illustration slot**

Replace the entire content of `frontend/src/components/child/lesson/CardLesson.tsx`:

```tsx
import { Button } from '@/components/ui/button';

type Props = {
  contentJson: { title?: string; body?: string };
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
};

export function CardLesson({ contentJson, onComplete, illustration }: Props) {
  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <h2 className="text-xl font-extrabold text-gray-900">{contentJson.title ?? ''}</h2>
      <p className="leading-relaxed text-gray-700">{contentJson.body ?? ''}</p>
      <div className="flex justify-end">
        <Button
          onClick={() => onComplete(null)}
          className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
        >Got it →</Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Restyle QuizLesson with illustration slot**

Replace the entire content of `frontend/src/components/child/lesson/QuizLesson.tsx`:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type QuizContent = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
};

type Props = {
  contentJson: QuizContent;
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
};

export function QuizLesson({ contentJson, onComplete, illustration }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.answer_index;

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <p className="text-lg font-bold text-gray-900">{contentJson.question}</p>
      <ul className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.answer_index;
          const showWrongPick = submitted && i === selected && !isCorrect;
          return (
            <li key={i}>
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-colors',
                  !submitted && selected === i && 'border-amber-400 bg-amber-50',
                  !submitted && selected !== i && 'border-gray-200',
                  showCorrect && 'border-green-500 bg-green-50',
                  showWrongPick && 'border-red-500 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <div className={cn(
                  'h-5 w-5 shrink-0 rounded-full border-2',
                  !submitted && selected === i && 'bg-gradient-to-br from-amber-400 to-orange-500 border-amber-400',
                  !submitted && selected !== i && 'border-gray-300',
                  showCorrect && 'bg-green-500 border-green-500',
                  showWrongPick && 'bg-red-500 border-red-500',
                )} />
                <input
                  type="radio"
                  name="quiz"
                  aria-label={choice}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                  className="sr-only"
                />
                <span className={cn('text-sm', submitted && (showCorrect || (i === selected)) && 'font-semibold')}>{choice}</span>
              </label>
            </li>
          );
        })}
      </ul>
      {submitted ? (
        <>
          <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-4 text-sm">
            <p className="font-bold text-gray-900">{isCorrect ? '✅ Correct!' : '❌ Not quite.'}</p>
            <p className="mt-1 text-gray-600">{contentJson.explanation}</p>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}
              className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
            >Continue →</Button>
          </div>
        </>
      ) : (
        <div className="flex justify-end">
          <Button
            disabled={selected === null}
            onClick={() => setSubmitted(true)}
            className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl disabled:opacity-50"
          >Submit</Button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Restyle ScenarioLesson with illustration slot**

Replace the entire content of `frontend/src/components/child/lesson/ScenarioLesson.tsx`:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type ScenarioContent = {
  prompt: string;
  choices: { label: string; outcome: string }[];
  correct_index: number;
};

type Props = {
  contentJson: ScenarioContent;
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
};

export function ScenarioLesson({ contentJson, onComplete, illustration }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.correct_index;

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <p className="text-base italic text-gray-500 leading-relaxed">{contentJson.prompt}</p>
      <ul className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.correct_index;
          const showPickedWrong = submitted && i === selected && !isCorrect;
          return (
            <li key={i} className="space-y-1">
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-colors',
                  !submitted && selected === i && 'border-amber-400 bg-amber-50',
                  !submitted && selected !== i && 'border-gray-200',
                  showCorrect && 'border-green-500 bg-green-50',
                  showPickedWrong && 'border-red-500 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <div className={cn(
                  'h-5 w-5 shrink-0 rounded-full border-2',
                  !submitted && selected === i && 'bg-gradient-to-br from-amber-400 to-orange-500 border-amber-400',
                  !submitted && selected !== i && 'border-gray-300',
                  showCorrect && 'bg-green-500 border-green-500',
                  showPickedWrong && 'bg-red-500 border-red-500',
                )} />
                <input
                  type="radio"
                  name="scenario"
                  aria-label={choice.label}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                  className="sr-only"
                />
                <span className={cn('text-sm', submitted && (showCorrect || (i === selected)) && 'font-semibold')}>{choice.label}</span>
              </label>
              {submitted && (showCorrect || showPickedWrong) && (
                <p className="ml-9 text-sm text-gray-500">{choice.outcome}</p>
              )}
            </li>
          );
        })}
      </ul>
      {submitted ? (
        <div className="flex justify-end">
          <Button
            onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}
            className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
          >Continue →</Button>
        </div>
      ) : (
        <div className="flex justify-end">
          <Button
            disabled={selected === null}
            onClick={() => setSubmitted(true)}
            className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl disabled:opacity-50"
          >Submit</Button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Restyle CompletionPanel with Trophy**

Replace the entire content of `frontend/src/components/child/lesson/CompletionPanel.tsx`:

```tsx
import { Link } from 'react-router-dom';
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
  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-4">
      <Trophy />
      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>
      {!result.already_completed && (
        <p className="text-3xl font-extrabold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          +{result.xp_awarded} XP
        </p>
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
          <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500" style={{ width: `${xpInLevel}%` }} />
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

- [ ] **Step 5: Update Lesson page to pass illustrations and use quest copy**

In `frontend/src/pages/child/Lesson.tsx`, add the illustration import and update the component.

Add this import near the top (after the existing imports):

```typescript
import { LessonIllustration } from '@/components/child/lesson/LessonIllustration';
```

Then find the module query (around line 22) and add a modules query to get the topic for illustrations. Replace the entire `return` block at the bottom of the component (from `return (` to the closing `);` of the main return around line 98). Replace:

```tsx
  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>{positionLabel}</span>
        <span className="rounded bg-muted px-2 py-0.5">{lesson.xp_reward} XP</span>
      </header>
      {lesson.type === 'card' && <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} />}
      {lesson.type === 'quiz' && <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} />}
      {lesson.type === 'scenario' && <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} />}
      {lesson.type === 'video' && <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string }} onComplete={onComplete} />}
    </div>
  );
```

With:

```tsx
  const modulesQ2 = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
  });
  const currentModule = (modulesQ2.data ?? []).find((m) => m.id === moduleId);
  const topic = currentModule?.topic ?? 'stocks';
  const lessonTitle = lesson.type === 'card'
    ? (lesson.content_json as { title?: string }).title ?? ''
    : lesson.type === 'quiz'
    ? (lesson.content_json as { question?: string }).question ?? ''
    : lesson.type === 'scenario'
    ? (lesson.content_json as { prompt?: string }).prompt ?? ''
    : '';
  const illustration = <LessonIllustration lessonTitle={lessonTitle} topic={topic} />;

  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-4 flex items-center justify-between text-sm text-gray-500">
        <span>Quest {lesson.order_index + 1} of {total || '…'}</span>
        <span className="rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">🏆 {lesson.xp_reward} XP</span>
      </header>
      {lesson.type === 'card' && <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} illustration={illustration} />}
      {lesson.type === 'quiz' && <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} illustration={illustration} />}
      {lesson.type === 'scenario' && <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} illustration={illustration} />}
      {lesson.type === 'video' && <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string }} onComplete={onComplete} />}
    </div>
  );
```

Also update the `positionLabel` variable. Replace:
```tsx
  const positionLabel = total > 0
    ? `Lesson ${lesson.order_index + 1} of ${total}`
    : `Lesson ${lesson.order_index + 1}`;
```

With:
```tsx
  const positionLabel = total > 0
    ? `Quest ${lesson.order_index + 1} of ${total}`
    : `Quest ${lesson.order_index + 1}`;
```

Also add the `ModuleOut` import if not already imported. The existing import should already have it:
```typescript
import { contentApi, type LessonOut, type LessonSummary, type LessonCompletionResult } from '@/api/content';
```

Add `type ModuleOut` to this import:
```typescript
import { contentApi, type LessonOut, type LessonSummary, type LessonCompletionResult, type ModuleOut } from '@/api/content';
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/child/lesson/CardLesson.tsx frontend/src/components/child/lesson/QuizLesson.tsx frontend/src/components/child/lesson/ScenarioLesson.tsx frontend/src/components/child/lesson/CompletionPanel.tsx frontend/src/pages/child/Lesson.tsx
git commit -m "feat: restyle lesson components with illustrations, warm theme, and quest copy"
```

---

### Task 9: Verify end-to-end and final cleanup

**Files:**
- No new files — verification only

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Visual smoke test**

Start the app:
```bash
cd backend && uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
```

Open `http://localhost:5173` and verify:
- Login page loads
- Home page: warm colours, friendly greeting, XP bar, quest card with module emoji
- Lessons page: module grid with emoji icons, warm card styling, quest counts
- Module page: banner with emoji, quest list with warm styling
- Lesson page: illustration above content, warm card styling
- Quiz: rounded options, amber highlight on selection
- Completion: trophy, gradient XP text, level progress bar
- Nav: amber accent, gradient logo icon

- [ ] **Step 4: Stop servers and commit any cleanup**

Stop the dev servers. If any small fixes were needed, commit them:

```bash
git add -A
git commit -m "fix: final UI refresh adjustments"
```
