# Stats Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a gamification Stats page in the child SPA that surfaces badges, weekly challenges, and a leaderboard — giving kids 12–18 visible progress and motivation.

**Architecture:** One new backend endpoint (`GET /badges`) returning all badge definitions. One new frontend page at `/stats` composed of four sections (XpSummary, BadgeGrid, ChallengeList, LeaderboardTable), each loading data independently via TanStack Query hooks. A new `gamification.ts` API module wraps four endpoints; a small `country.ts` utility converts ISO codes to flag emoji.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 18 + TypeScript + TanStack Query 5 + Tailwind CSS + lucide-react (frontend), Vitest + RTL (unit tests), Playwright (E2E).

---

### Task 1: Backend `GET /badges` endpoint

**Files:**
- Modify: `backend/app/routers/gamification.py` (add endpoint after line 34)
- Modify: `backend/app/schemas/gamification.py` (add `BadgeDefinitionOut` schema)
- Test: `backend/tests/test_gamification.py` (add test)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_gamification.py`:

```python
async def test_all_badges_returns_definitions(client, db_session):
    """GET /badges returns all badge definitions with earned_at=None."""
    await _seed(db_session)
    await _login(client)
    r = await client.get("/badges")
    assert r.status_code == 200
    badges = r.json()
    assert len(badges) == 1  # _seed creates one badge
    b = badges[0]
    assert b["name"] == "First Step"
    assert b["condition_type"] == "lesson_count"
    assert b["condition_value"] == 1
    assert b["earned_at"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_gamification.py::test_all_badges_returns_definitions -v`
Expected: FAIL — 404 because `GET /badges` doesn't exist yet.

- [ ] **Step 3: Add `BadgeDefinitionOut` schema**

In `backend/app/schemas/gamification.py`, add after the `BadgeOut` class:

```python
class BadgeDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    condition_type: str
    condition_value: int
    earned_at: None = None
```

- [ ] **Step 4: Add `GET /badges` endpoint**

In `backend/app/routers/gamification.py`, add the import of `BadgeDefinitionOut` to the existing import line:

```python
from app.schemas.gamification import BadgeDefinitionOut, BadgeOut, ChallengeOut, LeaderboardEntry
```

Add the endpoint after the `list_my_badges` function (before `list_active_challenges`):

```python
@router.get("/badges", response_model=list[BadgeDefinitionOut])
async def list_all_badges(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    badges = (await session.scalars(select(Badge).order_by(Badge.name))).all()
    return badges
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_gamification.py::test_all_badges_returns_definitions -v`
Expected: PASS

- [ ] **Step 6: Run full gamification test suite**

Run: `cd backend && python -m pytest tests/test_gamification.py -v`
Expected: All tests pass (existing + new).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/gamification.py backend/app/routers/gamification.py backend/tests/test_gamification.py
git commit -m "feat(api): add GET /badges endpoint returning all badge definitions"
```

---

### Task 2: Frontend API client — `gamification.ts`

**Files:**
- Create: `frontend/src/api/gamification.ts`
- Test: `frontend/tests/unit/api-gamification.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/api-gamification.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { gamificationApi } from '@/api/gamification';

beforeEach(() => vi.restoreAllMocks());

describe('gamificationApi', () => {
  it('getAllBadges calls GET /badges', async () => {
    const body = [{ id: '1', name: 'First Step', description: 'd', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const result = await gamificationApi.getAllBadges();
    expect(result).toEqual(body);
    expect(fetch).toHaveBeenCalledWith('/badges', expect.objectContaining({ method: 'GET' }));
  });

  it('getEarnedBadges calls GET /users/me/badges', async () => {
    const body = [{ id: '1', name: 'First Step', description: 'd', icon_url: '/x.svg', earned_at: '2026-01-01T00:00:00Z' }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const result = await gamificationApi.getEarnedBadges();
    expect(result).toEqual(body);
    expect(fetch).toHaveBeenCalledWith('/users/me/badges', expect.objectContaining({ method: 'GET' }));
  });

  it('getChallenges calls GET /challenges', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const result = await gamificationApi.getChallenges();
    expect(result).toEqual([]);
    expect(fetch).toHaveBeenCalledWith('/challenges', expect.objectContaining({ method: 'GET' }));
  });

  it('getLeaderboard calls GET /leaderboard', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const result = await gamificationApi.getLeaderboard();
    expect(result).toEqual([]);
    expect(fetch).toHaveBeenCalledWith('/leaderboard', expect.objectContaining({ method: 'GET' }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/api-gamification.test.ts`
Expected: FAIL — module `@/api/gamification` not found.

- [ ] **Step 3: Write the API module**

Create `frontend/src/api/gamification.ts`:

```typescript
import { apiFetch } from './client';

export type BadgeDefinition = {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  condition_type: string;
  condition_value: number;
  earned_at: null;
};

export type EarnedBadge = {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  earned_at: string;
};

export type ChallengeOut = {
  id: string;
  title: string;
  description: string;
  type: string;
  target_value: number;
  xp_reward: number;
  starts_at: string;
  ends_at: string;
  is_premium: boolean;
  progress: number;
  completed_at: string | null;
};

export type LeaderboardEntry = {
  username: string;
  country_code: string;
  xp_this_week: number;
};

export const gamificationApi = {
  getAllBadges: () => apiFetch<BadgeDefinition[]>('/badges'),
  getEarnedBadges: () => apiFetch<EarnedBadge[]>('/users/me/badges'),
  getChallenges: () => apiFetch<ChallengeOut[]>('/challenges'),
  getLeaderboard: () => apiFetch<LeaderboardEntry[]>('/leaderboard'),
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/api-gamification.test.ts`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/gamification.ts frontend/tests/unit/api-gamification.test.ts
git commit -m "feat(frontend): add gamification API client with typed endpoints"
```

---

### Task 3: Country flag utility — `country.ts`

**Files:**
- Create: `frontend/src/lib/country.ts`
- Test: `frontend/tests/unit/country.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/country.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { countryFlag } from '@/lib/country';

describe('countryFlag', () => {
  it('converts GB to flag emoji', () => {
    expect(countryFlag('GB')).toBe('\u{1F1EC}\u{1F1E7}');
  });

  it('converts US to flag emoji', () => {
    expect(countryFlag('US')).toBe('\u{1F1FA}\u{1F1F8}');
  });

  it('handles lowercase input', () => {
    expect(countryFlag('gb')).toBe('\u{1F1EC}\u{1F1E7}');
  });

  it('returns empty string for empty input', () => {
    expect(countryFlag('')).toBe('');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/country.test.ts`
Expected: FAIL — module `@/lib/country` not found.

- [ ] **Step 3: Implement the utility**

Create `frontend/src/lib/country.ts`:

```typescript
/**
 * Convert a 2-letter ISO 3166-1 alpha-2 country code to a flag emoji.
 * Each letter is offset to the Regional Indicator Symbol range.
 */
export function countryFlag(code: string): string {
  if (!code || code.length !== 2) return '';
  const upper = code.toUpperCase();
  const offset = 0x1F1E6 - 0x41; // Regional indicator 'A' minus ASCII 'A'
  return String.fromCodePoint(
    upper.charCodeAt(0) + offset,
    upper.charCodeAt(1) + offset,
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/country.test.ts`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/country.ts frontend/tests/unit/country.test.ts
git commit -m "feat(frontend): add countryFlag utility for ISO code to emoji conversion"
```

---

### Task 4: TanStack Query hooks

**Files:**
- Create: `frontend/src/hooks/useAllBadges.ts`
- Create: `frontend/src/hooks/useBadges.ts`
- Create: `frontend/src/hooks/useChallenges.ts`
- Create: `frontend/src/hooks/useLeaderboard.ts`
- Test: `frontend/tests/unit/hooks-gamification.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/tests/unit/hooks-gamification.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useLeaderboard } from '@/hooks/useLeaderboard';

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useAllBadges', () => {
  it('fetches from GET /badges with staleTime Infinity', async () => {
    const body = [{ id: '1', name: 'X', description: '', icon_url: '', condition_type: 'lesson_count', condition_value: 1, earned_at: null }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useAllBadges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});

describe('useBadges', () => {
  it('fetches from GET /users/me/badges', async () => {
    const body = [{ id: '1', name: 'X', description: '', icon_url: '', earned_at: '2026-01-01T00:00:00Z' }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useBadges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});

describe('useChallenges', () => {
  it('fetches from GET /challenges', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useChallenges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });
});

describe('useLeaderboard', () => {
  it('fetches from GET /leaderboard', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run tests/unit/hooks-gamification.test.tsx`
Expected: FAIL — modules not found.

- [ ] **Step 3: Create `useAllBadges.ts`**

Create `frontend/src/hooks/useAllBadges.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type BadgeDefinition } from '@/api/gamification';

export function useAllBadges() {
  return useQuery<BadgeDefinition[] | null>({
    queryKey: ['badges-all'],
    queryFn: () => gamificationApi.getAllBadges(),
    retry: false,
    staleTime: Infinity,
  });
}
```

- [ ] **Step 4: Create `useBadges.ts`**

Create `frontend/src/hooks/useBadges.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type EarnedBadge } from '@/api/gamification';

export function useBadges() {
  return useQuery<EarnedBadge[] | null>({
    queryKey: ['badges-earned'],
    queryFn: () => gamificationApi.getEarnedBadges(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

- [ ] **Step 5: Create `useChallenges.ts`**

Create `frontend/src/hooks/useChallenges.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type ChallengeOut } from '@/api/gamification';

export function useChallenges() {
  return useQuery<ChallengeOut[] | null>({
    queryKey: ['challenges'],
    queryFn: () => gamificationApi.getChallenges(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

- [ ] **Step 6: Create `useLeaderboard.ts`**

Create `frontend/src/hooks/useLeaderboard.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type LeaderboardEntry } from '@/api/gamification';

export function useLeaderboard() {
  return useQuery<LeaderboardEntry[] | null>({
    queryKey: ['leaderboard'],
    queryFn: () => gamificationApi.getLeaderboard(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && npx vitest run tests/unit/hooks-gamification.test.tsx`
Expected: PASS — all 4 tests.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useAllBadges.ts frontend/src/hooks/useBadges.ts frontend/src/hooks/useChallenges.ts frontend/src/hooks/useLeaderboard.ts frontend/tests/unit/hooks-gamification.test.tsx
git commit -m "feat(frontend): add TanStack Query hooks for gamification endpoints"
```

---

### Task 5: XpSummary component

**Files:**
- Create: `frontend/src/components/child/stats/XpSummary.tsx`
- Test: `frontend/tests/unit/child-XpSummary.test.tsx`

The XpSummary card shows: level with progress bar toward next level, total XP, and streak count with active/inactive state. Data comes from the existing `useProgress()` hook. Level formula: `floor(xp / 100) + 1`. Progress within level: `xp % 100` out of 100.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/child-XpSummary.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { XpSummary } from '@/components/child/stats/XpSummary';

function renderSummary(overrides: Partial<Parameters<typeof XpSummary>[0]> = {}) {
  const defaults = {
    xp: 250,
    streakCount: 5,
    lastActivityDate: '2026-05-08',
    today: new Date('2026-05-08T12:00:00Z'),
  };
  return render(<XpSummary {...defaults} {...overrides} />);
}

describe('XpSummary', () => {
  it('renders correct level from XP (250 XP = Level 3)', () => {
    renderSummary();
    expect(screen.getByText(/Level 3/)).toBeInTheDocument();
  });

  it('renders total XP', () => {
    renderSummary();
    expect(screen.getByText('250')).toBeInTheDocument();
  });

  it('renders progress bar with correct width (250 % 100 = 50%)', () => {
    renderSummary();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('renders streak count', () => {
    renderSummary();
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it('shows active streak state when activity is recent', () => {
    renderSummary({ lastActivityDate: '2026-05-08', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak active/i)).toBeInTheDocument();
  });

  it('shows inactive streak state when activity is old', () => {
    renderSummary({ lastActivityDate: '2026-05-01', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak inactive/i)).toBeInTheDocument();
  });

  it('handles 0 XP (Level 1, 0% progress)', () => {
    renderSummary({ xp: 0 });
    expect(screen.getByText(/Level 1/)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/child-XpSummary.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement XpSummary**

Create `frontend/src/components/child/stats/XpSummary.tsx`:

```tsx
import { Flame, Star, TrendingUp } from 'lucide-react';
import { isStreakActive } from '@/lib/streak';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  streakCount: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function XpSummary({ xp, streakCount, lastActivityDate, today }: Props) {
  const now = today ?? new Date();
  const level = Math.floor(xp / 100) + 1;
  const progress = xp % 100;
  const active = isStreakActive(lastActivityDate, now);

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="grid gap-6 sm:grid-cols-3">
        {/* Level + progress bar */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4" />
            Level
          </div>
          <p className="text-2xl font-bold">Level {level}</p>
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="XP progress to next level"
            className="h-2 w-full rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">{progress}/100 XP to next level</p>
        </div>

        {/* Total XP */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Star className="h-4 w-4" />
            Total XP
          </div>
          <p className="text-2xl font-bold">{xp}</p>
        </div>

        {/* Streak */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Flame className="h-4 w-4" />
            Streak
          </div>
          <p
            className={cn('text-2xl font-bold', !active && 'opacity-50')}
            aria-label={active ? 'streak active' : 'streak inactive'}
          >
            {streakCount}-day
          </p>
          <p className="text-xs text-muted-foreground">
            {active ? 'Keep it going!' : 'Complete a lesson to restart'}
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/child-XpSummary.test.tsx`
Expected: PASS — all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/stats/XpSummary.tsx frontend/tests/unit/child-XpSummary.test.tsx
git commit -m "feat(frontend): add XpSummary card with level, XP, and streak display"
```

---

### Task 6: BadgeGrid component

**Files:**
- Create: `frontend/src/components/child/stats/BadgeGrid.tsx`
- Test: `frontend/tests/unit/child-BadgeGrid.test.tsx`

The BadgeGrid shows earned badges in full colour and locked badges greyed out with a lock icon. Badges are merged from `GET /badges` (all definitions) and `GET /users/me/badges` (earned, with `earned_at`). Icon is a lucide icon based on `condition_type`: `lesson_count` → BookOpen, `streak_days` → Flame, `trade_count` → TrendingUp, `total_xp` → Star. Earned date shown as relative time via `Intl.RelativeTimeFormat` or simple "Earned {date}".

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/child-BadgeGrid.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BadgeGrid } from '@/components/child/stats/BadgeGrid';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

const allBadges: BadgeDefinition[] = [
  { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null },
  { id: '2', name: 'Streak Master', description: 'Maintain a 7-day streak', icon_url: '/x.svg', condition_type: 'streak_days', condition_value: 7, earned_at: null },
  { id: '3', name: 'First Trade', description: 'Execute your first paper trade', icon_url: '/x.svg', condition_type: 'trade_count', condition_value: 1, earned_at: null },
  { id: '4', name: 'Century Club', description: 'Earn 100 XP', icon_url: '/x.svg', condition_type: 'total_xp', condition_value: 100, earned_at: null },
  { id: '5', name: 'Quiz Ace', description: 'Complete 10 lessons', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 10, earned_at: null },
];

const earnedBadges: EarnedBadge[] = [
  { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', earned_at: '2026-05-01T10:00:00Z' },
  { id: '4', name: 'Century Club', description: 'Earn 100 XP', icon_url: '/x.svg', earned_at: '2026-05-03T14:00:00Z' },
];

describe('BadgeGrid', () => {
  it('renders all 5 badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('First Step')).toBeInTheDocument();
    expect(screen.getByText('Streak Master')).toBeInTheDocument();
    expect(screen.getByText('First Trade')).toBeInTheDocument();
    expect(screen.getByText('Century Club')).toBeInTheDocument();
    expect(screen.getByText('Quiz Ace')).toBeInTheDocument();
  });

  it('shows earned badges with "Earned" text', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    const earnedTexts = screen.getAllByText(/^Earned/);
    expect(earnedTexts).toHaveLength(2);
  });

  it('shows lock icon for locked badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    const lockIcons = screen.getAllByLabelText(/locked/i);
    expect(lockIcons).toHaveLength(3);
  });

  it('shows condition text as description for locked badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('Maintain a 7-day streak')).toBeInTheDocument();
    expect(screen.getByText('Execute your first paper trade')).toBeInTheDocument();
  });

  it('renders earned badge description', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('Complete your first lesson')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/child-BadgeGrid.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement BadgeGrid**

Create `frontend/src/components/child/stats/BadgeGrid.tsx`:

```tsx
import { BookOpen, Flame, Lock, Star, TrendingUp } from 'lucide-react';
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

export function BadgeGrid({ allBadges, earnedBadges }: Props) {
  const earnedById = new Map(earnedBadges.map((b) => [b.id, b]));

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {allBadges.map((badge) => {
        const earned = earnedById.get(badge.id);
        const Icon = CONDITION_ICONS[badge.condition_type] ?? Star;

        return (
          <div
            key={badge.id}
            className={cn(
              'relative rounded-lg border p-4',
              earned ? 'bg-card' : 'bg-muted/50 opacity-60',
            )}
          >
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                  earned ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground',
                )}
              >
                <Icon className="h-5 w-5" />
              </div>
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
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/child-BadgeGrid.test.tsx`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/stats/BadgeGrid.tsx frontend/tests/unit/child-BadgeGrid.test.tsx
git commit -m "feat(frontend): add BadgeGrid component with earned/locked badge display"
```

---

### Task 7: ChallengeList component

**Files:**
- Create: `frontend/src/components/child/stats/ChallengeList.tsx`
- Test: `frontend/tests/unit/child-ChallengeList.test.tsx`

Shows active challenges with progress bars, XP reward, and completed state. Empty state: "No active challenges this week."

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/child-ChallengeList.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import type { ChallengeOut } from '@/api/gamification';

const challenges: ChallengeOut[] = [
  {
    id: '1', title: 'Weekly Learner', description: 'Complete 3 lessons this week',
    type: 'lessons_completed', target_value: 3, xp_reward: 50,
    starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
    is_premium: false, progress: 1, completed_at: null,
  },
  {
    id: '2', title: 'Market Explorer', description: 'Make 1 paper trade this week',
    type: 'trades_executed', target_value: 1, xp_reward: 30,
    starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
    is_premium: false, progress: 1, completed_at: '2026-05-06T10:00:00Z',
  },
];

describe('ChallengeList', () => {
  it('renders challenge titles', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Weekly Learner')).toBeInTheDocument();
    expect(screen.getByText('Market Explorer')).toBeInTheDocument();
  });

  it('shows progress bar with correct aria values for in-progress challenge', () => {
    render(<ChallengeList challenges={challenges} />);
    const bars = screen.getAllByRole('progressbar');
    const inProgress = bars[0];
    expect(inProgress).toHaveAttribute('aria-valuenow', '1');
    expect(inProgress).toHaveAttribute('aria-valuemax', '3');
  });

  it('shows percentage text for in-progress challenge', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('33%')).toBeInTheDocument();
  });

  it('shows XP reward', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('+50 XP')).toBeInTheDocument();
    expect(screen.getByText('+30 XP')).toBeInTheDocument();
  });

  it('shows "Completed!" for completed challenges', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Completed!')).toBeInTheDocument();
  });

  it('renders empty state when no challenges', () => {
    render(<ChallengeList challenges={[]} />);
    expect(screen.getByText(/no active challenges this week/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/child-ChallengeList.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement ChallengeList**

Create `frontend/src/components/child/stats/ChallengeList.tsx`:

```tsx
import { CheckCircle2 } from 'lucide-react';
import type { ChallengeOut } from '@/api/gamification';
import { cn } from '@/lib/utils';

type Props = {
  challenges: ChallengeOut[];
};

export function ChallengeList({ challenges }: Props) {
  if (challenges.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        No active challenges this week.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {challenges.map((c) => {
        const completed = c.completed_at !== null;
        const pct = Math.min(Math.round((c.progress / c.target_value) * 100), 100);

        return (
          <div key={c.id} className="rounded-lg border bg-card p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {completed && <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />}
                  <p className="font-medium">{c.title}</p>
                </div>
                <p className="text-sm text-muted-foreground">{c.description}</p>
              </div>
              <span className="shrink-0 text-sm font-medium text-primary">+{c.xp_reward} XP</span>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <div
                role="progressbar"
                aria-valuenow={c.progress}
                aria-valuemin={0}
                aria-valuemax={c.target_value}
                aria-label={`${c.title} progress`}
                className="h-2 flex-1 rounded-full bg-muted"
              >
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    completed ? 'bg-green-600' : 'bg-blue-600',
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs font-medium text-muted-foreground">
                {completed ? 'Completed!' : `${pct}%`}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/child-ChallengeList.test.tsx`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/stats/ChallengeList.tsx frontend/tests/unit/child-ChallengeList.test.tsx
git commit -m "feat(frontend): add ChallengeList component with progress bars and XP display"
```

---

### Task 8: LeaderboardTable component

**Files:**
- Create: `frontend/src/components/child/stats/LeaderboardTable.tsx`
- Test: `frontend/tests/unit/child-LeaderboardTable.test.tsx`

Shows a table with Rank, Username, Country (flag emoji), XP This Week. Current user's row is highlighted. Uses `countryFlag()` from `src/lib/country.ts`. Empty state: "No activity this week yet. Complete a lesson to get on the board!"

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/child-LeaderboardTable.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { LeaderboardTable } from '@/components/child/stats/LeaderboardTable';
import type { LeaderboardEntry } from '@/api/gamification';

const entries: LeaderboardEntry[] = [
  { username: 'alice', country_code: 'US', xp_this_week: 120 },
  { username: 'testuser', country_code: 'GB', xp_this_week: 80 },
  { username: 'bob', country_code: 'FR', xp_this_week: 50 },
];

describe('LeaderboardTable', () => {
  it('renders table with rank numbers', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    const rows = screen.getAllByRole('row');
    // 1 header + 3 data rows
    expect(rows).toHaveLength(4);
    expect(within(rows[1]).getByText('1')).toBeInTheDocument();
    expect(within(rows[2]).getByText('2')).toBeInTheDocument();
    expect(within(rows[3]).getByText('3')).toBeInTheDocument();
  });

  it('renders usernames', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('testuser')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
  });

  it('highlights current user row with "You" badge', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('You')).toBeInTheDocument();
  });

  it('renders country flag with aria-label', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByLabelText('US')).toBeInTheDocument();
    expect(screen.getByLabelText('GB')).toBeInTheDocument();
    expect(screen.getByLabelText('FR')).toBeInTheDocument();
  });

  it('renders XP values', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('80')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('renders empty state when no entries', () => {
    render(<LeaderboardTable entries={[]} currentUsername="testuser" />);
    expect(screen.getByText(/no activity this week/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/child-LeaderboardTable.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement LeaderboardTable**

Create `frontend/src/components/child/stats/LeaderboardTable.tsx`:

```tsx
import type { LeaderboardEntry } from '@/api/gamification';
import { countryFlag } from '@/lib/country';
import { cn } from '@/lib/utils';

type Props = {
  entries: LeaderboardEntry[];
  currentUsername: string;
};

export function LeaderboardTable({ entries, currentUsername }: Props) {
  if (entries.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        No activity this week yet. Complete a lesson to get on the board!
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">#</th>
            <th className="px-4 py-3 text-left font-medium">Username</th>
            <th className="px-4 py-3 text-left font-medium">Country</th>
            <th className="px-4 py-3 text-right font-medium">XP This Week</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => {
            const isCurrentUser = entry.username === currentUsername;
            return (
              <tr
                key={entry.username}
                className={cn(
                  'border-b last:border-b-0',
                  isCurrentUser && 'bg-primary/5 font-medium',
                )}
              >
                <td className="px-4 py-3">{i + 1}</td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    {entry.username}
                    {isCurrentUser && (
                      <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
                        You
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span aria-label={entry.country_code}>
                    {countryFlag(entry.country_code)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{entry.xp_this_week}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/child-LeaderboardTable.test.tsx`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/stats/LeaderboardTable.tsx frontend/tests/unit/child-LeaderboardTable.test.tsx
git commit -m "feat(frontend): add LeaderboardTable with rank, flag emoji, and user highlight"
```

---

### Task 9: Stats page

**Files:**
- Create: `frontend/src/pages/child/Stats.tsx`
- Test: `frontend/tests/unit/child-Stats.test.tsx`

Composes all four sections: XpSummary, BadgeGrid, ChallengeList, LeaderboardTable. Each section loads independently. The page renders loading skeletons while data is being fetched. The existing `useProgress()` hook provides XP/streak data. `useChildSession()` provides the current user's username for leaderboard highlighting.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/child-Stats.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';

// Mock all data hooks
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({
    data: { xp: 150, level: 2, streak_count: 3, last_activity_date: '2026-05-08' },
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useAllBadges', () => ({
  useAllBadges: () => ({
    data: [
      { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useBadges', () => ({
  useBadges: () => ({
    data: [
      { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', earned_at: '2026-05-01T10:00:00Z' },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useChallenges', () => ({
  useChallenges: () => ({
    data: [
      { id: 'c1', title: 'Weekly Learner', description: 'Complete 3 lessons', type: 'lessons_completed', target_value: 3, xp_reward: 50, starts_at: '', ends_at: '', is_premium: false, progress: 1, completed_at: null },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useLeaderboard', () => ({
  useLeaderboard: () => ({
    data: [
      { username: 'testuser', country_code: 'GB', xp_this_week: 100 },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({
    data: { username: 'testuser' },
  }),
}));

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Stats page', () => {
  it('renders page title', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /your stats/i })).toBeInTheDocument();
  });

  it('renders XP summary section', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText(/Level 2/)).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('renders badges section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /badges/i })).toBeInTheDocument();
  });

  it('renders challenges section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /weekly challenges/i })).toBeInTheDocument();
  });

  it('renders leaderboard section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /weekly leaderboard/i })).toBeInTheDocument();
  });

  it('renders challenge data', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText('Weekly Learner')).toBeInTheDocument();
  });

  it('renders leaderboard with current user highlighted', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText('You')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/child-Stats.test.tsx`
Expected: FAIL — module `@/pages/child/Stats` not found.

- [ ] **Step 3: Implement the Stats page**

Create `frontend/src/pages/child/Stats.tsx`:

```tsx
import { useProgress } from '@/hooks/useProgress';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import { useChildSession } from '@/hooks/useChildSession';
import { XpSummary } from '@/components/child/stats/XpSummary';
import { BadgeGrid } from '@/components/child/stats/BadgeGrid';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import { LeaderboardTable } from '@/components/child/stats/LeaderboardTable';

function SectionSkeleton() {
  return <div className="h-32 animate-pulse rounded-lg bg-muted" />;
}

export default function Stats() {
  const progress = useProgress();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const challenges = useChallenges();
  const leaderboard = useLeaderboard();
  const session = useChildSession();

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-6">
      <h1 className="text-2xl font-bold">Your Stats</h1>

      {/* XP Summary */}
      {progress.isLoading ? (
        <SectionSkeleton />
      ) : progress.data ? (
        <XpSummary
          xp={progress.data.xp}
          streakCount={progress.data.streak_count}
          lastActivityDate={progress.data.last_activity_date}
        />
      ) : null}

      {/* Badges */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Badges</h2>
        {allBadges.isLoading || earnedBadges.isLoading ? (
          <SectionSkeleton />
        ) : allBadges.data && earnedBadges.data ? (
          <BadgeGrid allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
        ) : null}
      </section>

      {/* Weekly Challenges */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Weekly Challenges</h2>
        {challenges.isLoading ? (
          <SectionSkeleton />
        ) : challenges.data ? (
          <ChallengeList challenges={challenges.data} />
        ) : null}
      </section>

      {/* Weekly Leaderboard */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Weekly Leaderboard</h2>
        {leaderboard.isLoading ? (
          <SectionSkeleton />
        ) : leaderboard.data ? (
          <LeaderboardTable
            entries={leaderboard.data}
            currentUsername={session.data?.username ?? ''}
          />
        ) : null}
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/child-Stats.test.tsx`
Expected: PASS — all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/Stats.tsx frontend/tests/unit/child-Stats.test.tsx
git commit -m "feat(frontend): add Stats page composing XpSummary, BadgeGrid, ChallengeList, LeaderboardTable"
```

---

### Task 10: Routing, TopNav, and Vite proxy

**Files:**
- Modify: `frontend/src/App.tsx` (add `/stats` route)
- Modify: `frontend/src/components/child/TopNav.tsx` (promote Stats to active NavLink, remove COMING_SOON)
- Modify: `frontend/vite.config.ts` (add `/challenges`, `/leaderboard`, `/badges` proxy entries)

- [ ] **Step 1: Add `/stats` route to App.tsx**

In `frontend/src/App.tsx`, add the import at the top with other page imports:

```typescript
import Stats from '@/pages/child/Stats';
```

Add the route inside the `<Route element={<Shell />}>` block, after the simulator routes:

```tsx
<Route path="/stats" element={<Stats />} />
```

The full Shell block should now look like:

```tsx
{/* Authed child routes inside Shell */}
<Route element={<Shell />}>
  <Route path="/home" element={<Home />} />
  <Route path="/lessons" element={<Lessons />} />
  <Route path="/lessons/:moduleId" element={<Module />} />
  <Route path="/lessons/:moduleId/:lessonId" element={<Lesson />} />
  <Route path="/simulator" element={<Simulator />} />
  <Route path="/simulator/market" element={<Market />} />
  <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
  <Route path="/stats" element={<Stats />} />
</Route>
```

- [ ] **Step 2: Update TopNav to make Stats an active link**

In `frontend/src/components/child/TopNav.tsx`:

1. Remove the `COMING_SOON` array and its imports (`Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger`).
2. Remove the `<TooltipProvider>` wrapper from the entire component.
3. Add a Stats `NavLink` after the Simulator `NavLink` in both desktop and mobile navs.
4. Remove the `COMING_SOON.map(...)` blocks from both desktop and mobile navs.

The updated file:

```tsx
import { Link, NavLink } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

export function TopNav({ username }: { username: string }) {
  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/home" className="text-lg font-semibold">Invest-Ed</Link>

        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Primary">
          <NavLink to="/home"
            className={({ isActive }) => cn(
              'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
              isActive && 'bg-muted font-medium',
            )}>Home</NavLink>
          <NavLink to="/lessons"
            className={({ isActive }) => cn(
              'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
              isActive && 'bg-muted font-medium',
            )}>Lessons</NavLink>
          <NavLink to="/simulator"
            className={({ isActive }) => cn(
              'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
              isActive && 'bg-muted font-medium',
            )}>Simulator</NavLink>
          <NavLink to="/stats"
            className={({ isActive }) => cn(
              'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
              isActive && 'bg-muted font-medium',
            )}>Stats</NavLink>
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
                <NavLink to="/home"
                  className={({ isActive }) => cn(
                    'rounded-md px-3 py-2 text-sm hover:bg-muted',
                    isActive && 'bg-muted font-medium',
                  )}>Home</NavLink>
                <NavLink to="/lessons"
                  className={({ isActive }) => cn(
                    'rounded-md px-3 py-2 text-sm hover:bg-muted',
                    isActive && 'bg-muted font-medium',
                  )}>Lessons</NavLink>
                <NavLink to="/simulator"
                  className={({ isActive }) => cn(
                    'rounded-md px-3 py-2 text-sm hover:bg-muted',
                    isActive && 'bg-muted font-medium',
                  )}>Simulator</NavLink>
                <NavLink to="/stats"
                  className={({ isActive }) => cn(
                    'rounded-md px-3 py-2 text-sm hover:bg-muted',
                    isActive && 'bg-muted font-medium',
                  )}>Stats</NavLink>
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

- [ ] **Step 3: Add proxy entries to vite.config.ts**

In `frontend/vite.config.ts`, add these proxy entries inside the `proxy` object (after the `/portfolio` entry, before `/health`):

```typescript
'/challenges': {
  target: 'http://localhost:8000',
  bypass(req) {
    if (req.headers.accept?.includes('text/html')) return '/index.html';
  },
},
'/leaderboard': {
  target: 'http://localhost:8000',
  bypass(req) {
    if (req.headers.accept?.includes('text/html')) return '/index.html';
  },
},
'/badges': {
  target: 'http://localhost:8000',
  bypass(req) {
    if (req.headers.accept?.includes('text/html')) return '/index.html';
  },
},
```

Note: `/users/me/badges` is already proxied by the existing `/users` entry. `/badges` needs its own entry since it's a top-level path.

- [ ] **Step 4: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: All existing + new tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/child/TopNav.tsx frontend/vite.config.ts
git commit -m "feat(frontend): add /stats route, promote Stats in TopNav, add proxy entries"
```

---

### Task 11: E2E smoke test

**Files:**
- Create: `frontend/tests/e2e/stats-flow.spec.ts`

One smoke test: register + approve consent + log in → navigate to `/stats` → verify XP summary visible (Level 1, 0 XP), all 5 badges visible (all locked for new user), challenges section visible, leaderboard section visible.

- [ ] **Step 1: Write the E2E test**

Create `frontend/tests/e2e/stats-flow.spec.ts`:

```typescript
import { test, expect, type Page } from '@playwright/test';
import { registerMinor, readLatestEmailToken, uniq } from './helpers';

async function loginAsChild(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill('SecurePass123!');
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/home');
}

async function approveConsent(page: Page, parentEmail: string) {
  const token = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${token}`);
  await page.getByRole('button', { name: /approve/i }).click();
  await page.waitForURL(/\/consent\/verify/);
}

test('stats: new user sees XP summary, badges, challenges, leaderboard', async ({ page }) => {
  const id = uniq('stats');
  const childEmail = `${id}@test.example`;
  const parentEmail = `parent-${id}@test.example`;

  // Register + approve
  await registerMinor({ email: childEmail, username: id, parentEmail });
  await approveConsent(page, parentEmail);

  // Log in as child
  await loginAsChild(page, childEmail);

  // Navigate to Stats
  await page.getByRole('link', { name: /stats/i }).click();
  await page.waitForURL('/stats');

  // XP summary — new user: Level 1, 0 XP
  await expect(page.getByText(/Level 1/)).toBeVisible();
  await expect(page.getByText('0')).toBeVisible();

  // Badges section — all 5 should be visible (all locked for new user)
  await expect(page.getByRole('heading', { name: /badges/i })).toBeVisible();
  await expect(page.getByText('First Step')).toBeVisible();
  await expect(page.getByText('Quiz Ace')).toBeVisible();
  await expect(page.getByText('Streak Master')).toBeVisible();
  await expect(page.getByText('First Trade')).toBeVisible();
  await expect(page.getByText('Century Club')).toBeVisible();

  // Challenges section visible
  await expect(page.getByRole('heading', { name: /weekly challenges/i })).toBeVisible();

  // Leaderboard section visible
  await expect(page.getByRole('heading', { name: /weekly leaderboard/i })).toBeVisible();
});
```

- [ ] **Step 2: Run E2E test** (requires backend + frontend running)

Run: `cd frontend && npx playwright test tests/e2e/stats-flow.spec.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/e2e/stats-flow.spec.ts
git commit -m "test(e2e): add stats dashboard smoke test for new user flow"
```
