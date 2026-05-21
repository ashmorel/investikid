# Parent Analytics Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add inline learning analytics to each child card on the parent dashboard, showing level, XP, streak, lesson progress, recent lessons, and badges.

**Architecture:** Extend the existing `GET /parent/children` endpoint to include an `analytics` object per child, built from `UserProgress`, `LessonCompletion`, and `UserBadge` data already in the DB. On the frontend, add a `ChildAnalytics` component (expandable section) and a reusable `ProgressBar` to `ChildCard`. No new tables, migrations, pages, or routes.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, React 18, TypeScript, Tailwind CSS, Framer Motion, TanStack Query, Vitest, vitest-axe

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/schemas/parent.py` | Modify | Add `RecentLessonOut`, `BadgeOut`, `ChildAnalyticsOut` Pydantic schemas; add `analytics` field to `ChildOut` |
| `backend/app/services/analytics_service.py` | Create | `build_child_analytics(session, user)` — queries progress, completions, badges, returns `ChildAnalyticsOut` |
| `backend/app/routers/parent.py` | Modify | Call `build_child_analytics` in `list_children` endpoint |
| `backend/tests/test_parent_analytics.py` | Create | Tests for analytics service and endpoint response shape |
| `frontend/src/api/parent.ts` | Modify | Add `ChildAnalytics`, `RecentLesson`, `BadgeInfo` types; update `Child` type |
| `frontend/src/components/ProgressBar.tsx` | Create | Reusable progress bar with ARIA attributes |
| `frontend/src/components/ProgressBar.test.tsx` | Create | Unit tests for ProgressBar |
| `frontend/src/components/ChildAnalytics.tsx` | Create | Expandable analytics section with summary line, progress, lessons, badges |
| `frontend/src/components/ChildAnalytics.test.tsx` | Create | Unit tests for ChildAnalytics |
| `frontend/src/components/ChildCard.tsx` | Modify | Render `<ChildAnalytics>` inside card |
| `frontend/tests/a11y/child-analytics.a11y.test.tsx` | Create | Axe scans of collapsed and expanded states |
| `frontend/tests/a11y/parent.a11y.test.tsx` | Modify | Update mock data to include `analytics` field |

---

### Task 1: Backend Schemas & Analytics Service

**Files:**
- Modify: `backend/app/schemas/parent.py`
- Create: `backend/app/services/analytics_service.py`
- Create: `backend/tests/test_parent_analytics.py`

- [ ] **Step 1: Add Pydantic schemas to `backend/app/schemas/parent.py`**

Add these imports and classes after the existing `PremiumToggleRequest`:

```python
class RecentLessonOut(BaseModel):
    title: str
    type: str
    score: float | None
    completed_at: datetime


class BadgeOut(BaseModel):
    name: str
    icon: str
    earned_at: datetime


class ChildAnalyticsOut(BaseModel):
    level: int
    xp: int
    xp_to_next_level: int
    streak_count: int
    lessons_completed: int
    lessons_total: int
    recent_lessons: list[RecentLessonOut]
    badges: list[BadgeOut]
```

Then add the `analytics` field to the existing `ChildOut` class:

```python
class ChildOut(BaseModel):
    user_id: uuid.UUID
    username: str
    country_code: str
    is_active: bool
    is_premium: bool
    parent_consent_given_at: datetime | None
    consent_declined_at: datetime | None
    deleted_at: datetime | None
    deletion_requested_at: datetime | None
    analytics: ChildAnalyticsOut | None = None
```

- [ ] **Step 2: Create analytics service at `backend/app/services/analytics_service.py`**

```python
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import UserProgress
from app.schemas.parent import BadgeOut, ChildAnalyticsOut, RecentLessonOut
from app.services.content_service import derive_lesson_title

# XP thresholds per level — mirrors content_service._LEVEL_THRESHOLDS
_LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2500, 5000]


def _xp_to_next_level(level: int, xp: int) -> int:
    """XP remaining to reach the next level. 0 if already at max."""
    if level >= len(_LEVEL_THRESHOLDS):
        return 0
    return max(0, _LEVEL_THRESHOLDS[level] - xp)


async def build_child_analytics(
    session: AsyncSession,
    user_id: uuid.UUID,
    country_code: str,
) -> ChildAnalyticsOut:
    # 1. UserProgress
    progress = await session.scalar(
        select(UserProgress).where(UserProgress.user_id == user_id)
    )
    level = progress.level if progress else 1
    xp = progress.xp if progress else 0
    streak_count = progress.streak_count if progress else 0

    # 2. Lesson counts
    # Total lessons accessible to this child's country
    lessons_total = await session.scalar(
        select(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.country_codes.any(country_code)
            | (Module.country_codes == [])
        )
    ) or 0

    lessons_completed = await session.scalar(
        select(func.count(LessonCompletion.id))
        .where(LessonCompletion.user_id == user_id)
    ) or 0

    # 3. Recent lessons (last 5)
    recent_rows = (await session.execute(
        select(LessonCompletion, Lesson)
        .join(Lesson, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user_id)
        .order_by(LessonCompletion.completed_at.desc())
        .limit(5)
    )).all()

    recent_lessons = [
        RecentLessonOut(
            title=derive_lesson_title(lesson.type, lesson.content_json),
            type=lesson.type,
            score=completion.score,
            completed_at=completion.completed_at,
        )
        for completion, lesson in recent_rows
    ]

    # 4. Badges
    badge_rows = (await session.execute(
        select(UserBadge, Badge)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user_id)
        .order_by(UserBadge.earned_at.desc())
    )).all()

    badges = [
        BadgeOut(
            name=badge.name,
            icon=badge.icon_url,
            earned_at=ub.earned_at,
        )
        for ub, badge in badge_rows
    ]

    return ChildAnalyticsOut(
        level=level,
        xp=xp,
        xp_to_next_level=_xp_to_next_level(level, xp),
        streak_count=streak_count,
        lessons_completed=lessons_completed,
        lessons_total=lessons_total,
        recent_lessons=recent_lessons,
        badges=badges,
    )
```

- [ ] **Step 3: Write backend tests at `backend/tests/test_parent_analytics.py`**

```python
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import User, UserProgress
from app.services.analytics_service import _xp_to_next_level, build_child_analytics
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


# ---------- unit: _xp_to_next_level ----------

def test_xp_to_next_level_at_start():
    assert _xp_to_next_level(1, 0) == 100


def test_xp_to_next_level_mid():
    assert _xp_to_next_level(2, 150) == 100  # need 250, have 150


def test_xp_to_next_level_at_max():
    assert _xp_to_next_level(7, 9999) == 0


# ---------- integration: build_child_analytics ----------

async def test_analytics_empty_user(db_session):
    """A user with no progress/completions/badges returns sensible defaults."""
    user = User(
        email="ana-empty@example.com", username="anaempty",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert result.level == 1
    assert result.xp == 0
    assert result.streak_count == 0
    assert result.lessons_completed == 0
    assert result.recent_lessons == []
    assert result.badges == []


async def test_analytics_with_data(db_session):
    """User with progress, completions, and a badge gets populated analytics."""
    user = User(
        email="ana-full@example.com", username="anafull",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    progress = UserProgress(user_id=user.id, xp=480, level=3, streak_count=5)
    db_session.add(progress)

    module = Module(
        topic="stocks", title="Stocks 101",
        country_codes=["GB"], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()

    lessons = []
    for i in range(3):
        lesson = Lesson(
            module_id=module.id, type="card", xp_reward=10, order_index=i,
            content_json={"title": f"Lesson {i}"},
        )
        db_session.add(lesson)
        lessons.append(lesson)
    await db_session.flush()

    # Complete 2 of 3 lessons
    for i, lesson in enumerate(lessons[:2]):
        db_session.add(LessonCompletion(
            user_id=user.id, lesson_id=lesson.id,
            completed_at=datetime.now(UTC) - timedelta(days=i),
            score=0.9 if i == 0 else None,
        ))

    badge = Badge(
        name="First Lesson", description="Complete your first lesson",
        icon_url="trophy", condition_type="lessons_completed", condition_value=1,
    )
    db_session.add(badge)
    await db_session.flush()
    db_session.add(UserBadge(user_id=user.id, badge_id=badge.id))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert result.level == 3
    assert result.xp == 480
    assert result.xp_to_next_level == 20  # threshold[3]=500, 500-480=20
    assert result.streak_count == 5
    assert result.lessons_completed == 2
    assert len(result.recent_lessons) == 2
    assert result.recent_lessons[0].title == "Lesson 0"  # most recent first
    assert result.recent_lessons[0].score == 0.9
    assert len(result.badges) == 1
    assert result.badges[0].name == "First Lesson"


async def test_recent_lessons_limited_to_5(db_session):
    """Only the 5 most recent completions are returned."""
    user = User(
        email="ana-limit@example.com", username="analimit",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting", title="Budget",
        country_codes=["GB"], is_premium=False, order_index=1, icon="💰",
    )
    db_session.add(module)
    await db_session.flush()

    for i in range(8):
        lesson = Lesson(
            module_id=module.id, type="card", xp_reward=10, order_index=i,
            content_json={"title": f"Budget {i}"},
        )
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(
            user_id=user.id, lesson_id=lesson.id,
            completed_at=datetime.now(UTC) - timedelta(hours=i),
        ))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)
    assert len(result.recent_lessons) == 5
    assert result.lessons_completed == 8


# ---------- endpoint: GET /parent/children includes analytics ----------

async def test_children_endpoint_includes_analytics(client, db_session):
    """The list_children endpoint response includes an analytics object."""
    await client.post("/auth/register", json={
        "email": "anakid@example.com", "username": "anakid", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "anaparent@example.com",
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email="anaparent@example.com",
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")

    r = await client.get("/parent/children")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    child = body[0]
    assert "analytics" in child
    ana = child["analytics"]
    assert ana["level"] == 1
    assert ana["xp"] == 0
    assert ana["streak_count"] == 0
    assert ana["lessons_completed"] == 0
    assert ana["recent_lessons"] == []
    assert ana["badges"] == []
    assert "xp_to_next_level" in ana
    assert "lessons_total" in ana
```

- [ ] **Step 4: Run backend tests to verify they fail (service doesn't exist yet in router)**

Run:
```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_analytics.py -v
```
Expected: Unit tests for `_xp_to_next_level` pass. Integration tests pass (service exists). Endpoint test fails because the router doesn't call the service yet.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/parent.py backend/app/services/analytics_service.py backend/tests/test_parent_analytics.py
git commit -m "feat: add analytics schemas and service for parent dashboard"
```

---

### Task 2: Wire Analytics Into Parent Router

**Files:**
- Modify: `backend/app/routers/parent.py`

- [ ] **Step 1: Update the `list_children` endpoint to include analytics**

In `backend/app/routers/parent.py`, add this import at the top:

```python
from app.services.analytics_service import build_child_analytics
```

Then replace the `list_children` function body:

```python
@router.get("/children", response_model=list[ChildOut])
async def list_children(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(User).where(User.parent_email == parent_email)
        .execution_options(include_deleted=True)
        .order_by(User.created_at)
    )).all()

    children = []
    for r in rows:
        analytics = None
        if r.deleted_at is None:
            analytics = await build_child_analytics(session, r.id, r.country_code)
        children.append(
            ChildOut(
                user_id=r.id, username=r.username, country_code=r.country_code,
                is_active=r.is_active, is_premium=r.is_premium,
                parent_consent_given_at=r.parent_consent_given_at,
                consent_declined_at=r.consent_declined_at,
                deleted_at=r.deleted_at,
                deletion_requested_at=r.deletion_requested_at,
                analytics=analytics,
            )
        )
    return children
```

- [ ] **Step 2: Run all backend tests**

Run:
```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_analytics.py tests/test_parent_dashboard.py -v
```
Expected: All tests pass including the new endpoint test.

- [ ] **Step 3: Run full backend suite to check for regressions**

Run:
```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -x -q
```
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/parent.py
git commit -m "feat: wire analytics into GET /parent/children endpoint"
```

---

### Task 3: Frontend Types & ProgressBar Component

**Files:**
- Modify: `frontend/src/api/parent.ts`
- Create: `frontend/src/components/ProgressBar.tsx`
- Create: `frontend/src/components/ProgressBar.test.tsx`

- [ ] **Step 1: Update TypeScript types in `frontend/src/api/parent.ts`**

Add these types before the existing `Child` type:

```ts
export type RecentLesson = {
  title: string;
  type: 'card' | 'quiz' | 'scenario' | 'video';
  score: number | null;
  completed_at: string;
};

export type BadgeInfo = {
  name: string;
  icon: string;
  earned_at: string;
};

export type ChildAnalytics = {
  level: number;
  xp: number;
  xp_to_next_level: number;
  streak_count: number;
  lessons_completed: number;
  lessons_total: number;
  recent_lessons: RecentLesson[];
  badges: BadgeInfo[];
};
```

Then add the `analytics` field to the existing `Child` type:

```ts
export type Child = {
  user_id: string;
  username: string;
  country_code: string;
  is_active: boolean;
  is_premium: boolean;
  parent_consent_given_at: string | null;
  consent_declined_at: string | null;
  deleted_at: string | null;
  deletion_requested_at: string | null;
  analytics: ChildAnalytics | null;
};
```

- [ ] **Step 2: Write ProgressBar tests at `frontend/src/components/ProgressBar.test.tsx`**

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from './ProgressBar';

describe('ProgressBar', () => {
  it('renders label text', () => {
    render(<ProgressBar value={5} max={10} label="5 of 10 lessons" />);
    expect(screen.getByText('5 of 10 lessons')).toBeInTheDocument();
  });

  it('has correct ARIA attributes', () => {
    render(<ProgressBar value={3} max={10} label="3 of 10" />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '3');
    expect(bar).toHaveAttribute('aria-valuemax', '10');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
  });

  it('renders correct fill width', () => {
    const { container } = render(<ProgressBar value={4} max={10} label="4 of 10" />);
    const fill = container.querySelector('[data-testid="progress-fill"]');
    expect(fill).toHaveStyle({ width: '40%' });
  });

  it('handles zero max gracefully', () => {
    render(<ProgressBar value={0} max={0} label="No lessons" />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
  });

  it('clamps fill to 100%', () => {
    const { container } = render(<ProgressBar value={15} max={10} label="15 of 10" />);
    const fill = container.querySelector('[data-testid="progress-fill"]');
    expect(fill).toHaveStyle({ width: '100%' });
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd invest-ed/frontend && npx vitest run src/components/ProgressBar.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 4: Create ProgressBar component at `frontend/src/components/ProgressBar.tsx`**

```tsx
export function ProgressBar({
  value,
  max,
  label,
}: {
  value: number;
  max: number;
  label: string;
}) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;

  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div
          data-testid="progress-fill"
          className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd invest-ed/frontend && npx vitest run src/components/ProgressBar.test.tsx
```
Expected: 5/5 pass.

- [ ] **Step 6: Verify TypeScript compiles**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit
```
Expected: Clean (0 errors).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/parent.ts frontend/src/components/ProgressBar.tsx frontend/src/components/ProgressBar.test.tsx
git commit -m "feat: add frontend analytics types and ProgressBar component"
```

---

### Task 4: ChildAnalytics Component

**Files:**
- Create: `frontend/src/components/ChildAnalytics.tsx`
- Create: `frontend/src/components/ChildAnalytics.test.tsx`

- [ ] **Step 1: Write ChildAnalytics tests at `frontend/src/components/ChildAnalytics.test.tsx`**

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChildAnalytics } from './ChildAnalytics';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

const MOCK_ANALYTICS: ChildAnalyticsType = {
  level: 5,
  xp: 480,
  xp_to_next_level: 20,
  streak_count: 3,
  lessons_completed: 12,
  lessons_total: 30,
  recent_lessons: [
    { title: 'What is a Stock?', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
    { title: 'Supply & Demand', type: 'quiz', score: 0.9, completed_at: '2026-05-19T10:00:00Z' },
    { title: 'Reading Graphs', type: 'quiz', score: 0.6, completed_at: '2026-05-18T10:00:00Z' },
  ],
  badges: [
    { name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' },
    { name: 'Stock Savvy', icon: 'chart', earned_at: '2026-05-18T10:00:00Z' },
  ],
};

const EMPTY_ANALYTICS: ChildAnalyticsType = {
  level: 1,
  xp: 0,
  xp_to_next_level: 100,
  streak_count: 0,
  lessons_completed: 0,
  lessons_total: 30,
  recent_lessons: [],
  badges: [],
};

describe('ChildAnalytics', () => {
  it('renders summary line with level, xp, and streak', () => {
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    expect(screen.getByText(/Lvl 5/)).toBeInTheDocument();
    expect(screen.getByText(/480 XP/)).toBeInTheDocument();
    expect(screen.getByText(/3-day streak/)).toBeInTheDocument();
  });

  it('does not show expanded content by default', () => {
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    expect(screen.queryByText(/12 of 30 lessons/)).not.toBeInTheDocument();
  });

  it('expands on toggle click to show progress and lessons', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText(/12 of 30 lessons/)).toBeInTheDocument();
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    expect(screen.getByText('Supply & Demand')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
  });

  it('shows badges in expanded section', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText(/First Lesson/)).toBeInTheDocument();
    expect(screen.getByText(/Stock Savvy/)).toBeInTheDocument();
  });

  it('collapses on second toggle click', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    await user.click(toggle);
    expect(screen.getByText(/12 of 30 lessons/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /hide progress/i }));
    expect(screen.queryByText(/12 of 30 lessons/)).not.toBeInTheDocument();
  });

  it('shows zero-state message when no activity', () => {
    render(<ChildAnalytics analytics={EMPTY_ANALYTICS} />);
    expect(screen.getByText(/No activity yet/)).toBeInTheDocument();
  });

  it('toggle has aria-expanded attribute', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(screen.getByRole('button', { name: /hide progress/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('shows checkmark for card lessons, percentage for quizzes', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    // Card lesson (no score) shows checkmark
    expect(screen.getByText('✓')).toBeInTheDocument();
    // Quiz lessons show percentage
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd invest-ed/frontend && npx vitest run src/components/ChildAnalytics.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create ChildAnalytics component at `frontend/src/components/ChildAnalytics.tsx`**

```tsx
import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ProgressBar } from './ProgressBar';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

function formatScore(type: string, score: number | null): string {
  if (type === 'card' || type === 'video') return '✓';
  if (score === null) return '—';
  return `${Math.round(score * 100)}%`;
}

function TypeBadge({ type }: { type: string }) {
  const label = type.charAt(0).toUpperCase() + type.slice(1);
  return (
    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
      {label}
    </span>
  );
}

export function ChildAnalytics({ analytics }: { analytics: ChildAnalyticsType }) {
  const [expanded, setExpanded] = useState(false);
  const hasActivity = analytics.lessons_completed > 0 || analytics.badges.length > 0;

  if (!hasActivity) {
    return (
      <p className="mt-2 text-xs text-muted-foreground">No activity yet</p>
    );
  }

  return (
    <div className="mt-2">
      {/* Summary line — always visible */}
      <p className="text-[13px] text-muted-foreground">
        Lvl {analytics.level}
        <span className="mx-1.5">&middot;</span>
        {analytics.xp} XP
        <span className="mx-1.5">&middot;</span>
        {analytics.streak_count}-day streak
        {analytics.streak_count > 0 && ' 🔥'}
      </p>

      {/* Toggle */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="mt-1 text-[13px] font-medium text-amber-600 hover:text-amber-700"
      >
        {expanded ? 'Hide progress' : 'Show progress'}
      </button>

      {/* Expanded section */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="analytics-detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-3 border-t pt-2">
              {/* Progress bar */}
              <ProgressBar
                value={analytics.lessons_completed}
                max={analytics.lessons_total}
                label={`${analytics.lessons_completed} of ${analytics.lessons_total} lessons completed`}
              />

              {/* Recent lessons */}
              {analytics.recent_lessons.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground">Recent:</p>
                  <ul className="mt-1 divide-y divide-muted">
                    {analytics.recent_lessons.map((lesson) => (
                      <li
                        key={`${lesson.title}-${lesson.completed_at}`}
                        className="flex items-center justify-between py-1 text-xs"
                      >
                        <span className="flex items-center gap-1.5">
                          {lesson.title}
                          <TypeBadge type={lesson.type} />
                        </span>
                        <span
                          className={
                            lesson.score !== null && lesson.score < 0.7
                              ? 'font-medium text-amber-500'
                              : 'font-medium text-emerald-600'
                          }
                        >
                          {formatScore(lesson.type, lesson.score)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Badges */}
              {analytics.badges.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Badges:{' '}
                  {analytics.badges.map((b, i) => (
                    <span key={b.name}>
                      {i > 0 && <span className="mx-1">&middot;</span>}
                      {b.name}
                    </span>
                  ))}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd invest-ed/frontend && npx vitest run src/components/ChildAnalytics.test.tsx
```
Expected: 8/8 pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChildAnalytics.tsx frontend/src/components/ChildAnalytics.test.tsx
git commit -m "feat: add ChildAnalytics expandable component"
```

---

### Task 5: Wire ChildAnalytics Into ChildCard

**Files:**
- Modify: `frontend/src/components/ChildCard.tsx`

- [ ] **Step 1: Add ChildAnalytics import and render in ChildCard**

In `frontend/src/components/ChildCard.tsx`, add this import at the top alongside other imports:

```ts
import { ChildAnalytics } from '@/components/ChildAnalytics';
```

Then insert the analytics component inside the `<article>` element, after the header `<div>` (the one with username and status chip) and before the `<div className="mt-4 ...">` that contains the freeze toggle:

```tsx
      {child.analytics && !isDeleted && (
        <ChildAnalytics analytics={child.analytics} />
      )}
```

The full `<article>` structure becomes:
```tsx
    <article className="rounded-lg border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        {/* ... username, country code, status chip ... */}
      </div>

      {child.analytics && !isDeleted && (
        <ChildAnalytics analytics={child.analytics} />
      )}

      <div className="mt-4 flex items-center justify-between">
        {/* ... freeze toggle, premium badge, delete dialog ... */}
      </div>
    </article>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit
```
Expected: Clean (0 errors).

- [ ] **Step 3: Run full Vitest suite for regressions**

Run:
```bash
cd invest-ed/frontend && npx vitest run
```
Expected: All existing tests pass. Some a11y tests that mock `Child` data may need updating (handled in Task 6).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChildCard.tsx
git commit -m "feat: render ChildAnalytics in ChildCard"
```

---

### Task 6: Accessibility Tests & Mock Data Updates

**Files:**
- Create: `frontend/tests/a11y/child-analytics.a11y.test.tsx`
- Modify: `frontend/tests/a11y/parent.a11y.test.tsx`

- [ ] **Step 1: Create a11y tests at `frontend/tests/a11y/child-analytics.a11y.test.tsx`**

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { ChildAnalytics } from '@/components/ChildAnalytics';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

const ANALYTICS: ChildAnalyticsType = {
  level: 5,
  xp: 480,
  xp_to_next_level: 20,
  streak_count: 3,
  lessons_completed: 12,
  lessons_total: 30,
  recent_lessons: [
    { title: 'What is a Stock?', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
    { title: 'Supply & Demand', type: 'quiz', score: 0.9, completed_at: '2026-05-19T10:00:00Z' },
  ],
  badges: [
    { name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' },
  ],
};

describe('a11y: ChildAnalytics', () => {
  it('collapsed state has no axe violations', async () => {
    const { container } = render(<ChildAnalytics analytics={ANALYTICS} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('expanded state has no axe violations', async () => {
    const user = userEvent.setup();
    const { container } = render(<ChildAnalytics analytics={ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(await axe(container)).toHaveNoViolations();
  });

  it('toggle is keyboard accessible', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    toggle.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /hide progress/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('progress bar has correct role and aria attributes', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '12');
    expect(bar).toHaveAttribute('aria-valuemax', '30');
  });
});
```

- [ ] **Step 2: Update mock data in `frontend/tests/a11y/parent.a11y.test.tsx`**

In the test `'ParentDashboard with children has no axe violations'`, update both mock child objects in the `JSON.stringify([ ... ])` array to include the `analytics` field. Update each child object to add:

```ts
analytics: {
  level: 3, xp: 250, xp_to_next_level: 250, streak_count: 2,
  lessons_completed: 5, lessons_total: 20,
  recent_lessons: [
    { title: 'Test Lesson', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
  ],
  badges: [{ name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' }],
},
```

Add this field after `deletion_requested_at: null,` in both child objects.

Also update the empty-state test mock (the first test) — the `[]` response needs no change since there are no children.

- [ ] **Step 3: Run a11y tests**

Run:
```bash
cd invest-ed/frontend && npx vitest run tests/a11y/child-analytics.a11y.test.tsx tests/a11y/parent.a11y.test.tsx
```
Expected: All pass with no axe violations.

- [ ] **Step 4: Run full Vitest suite**

Run:
```bash
cd invest-ed/frontend && npx vitest run
```
Expected: All tests pass (308 + new tests).

- [ ] **Step 5: Verify TypeScript compiles**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit
```
Expected: Clean (0 errors).

- [ ] **Step 6: Commit**

```bash
git add frontend/tests/a11y/child-analytics.a11y.test.tsx frontend/tests/a11y/parent.a11y.test.tsx
git commit -m "test: add a11y tests for ChildAnalytics and update parent mock data"
```

---

### Task 7: Full Regression

**Files:**
- None (verification only)

- [ ] **Step 1: Run TypeScript check**

```bash
cd invest-ed/frontend && npx tsc --noEmit
```
Expected: Clean (0 errors).

- [ ] **Step 2: Run Vitest suite**

```bash
cd invest-ed/frontend && npx vitest run
```
Expected: All tests pass (308 existing + ~17 new = ~325 tests).

- [ ] **Step 3: Run backend tests**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -x -q
```
Expected: All tests pass.

- [ ] **Step 4: Verify Playwright discovers e2e specs (no regressions)**

```bash
cd invest-ed/frontend && npx playwright test --list
```
Expected: Lists all 10 spec files. No compilation errors.

- [ ] **Step 5: Commit (only if fixes were needed)**

Only if Steps 1-4 surfaced issues that required changes. Otherwise, no commit needed — all code was committed in Tasks 1-6.
