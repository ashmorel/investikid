# Re-engagement: Streak-Freeze + Local Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Defend streaks with milestone-earned freezes and pull kids back with an opt-in on-device "streak at risk" reminder.

**Architecture:** Backend adds a `streak_freezes` count to `UserProgress` and freeze logic to the pure `streak_after_activity` function (config-driven). Frontend adds `@capacitor/local-notifications` with a pure scheduling-decision helper + a native-guarded wrapper, an opt-in toggle, and a streak-freeze indicator. Every tunable lives in one config module.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres; React 18 + Vite + TS + TanStack Query + Tailwind v4 + Vitest/vitest-axe; Capacitor 8 (`@capacitor/local-notifications`).

**Spec:** `docs/superpowers/specs/2026-06-05-reengagement-streak-defense-design.md`

**Working dirs:** backend `invest-ed/backend`, frontend `invest-ed/frontend`. Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Commands:**
- Backend: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest` · `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .` · `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` (current head `f0a1b2c3d4e5`)
- Frontend (from `invest-ed/frontend`): `npx tsc -b` · `npm run lint` (one pre-existing `button.tsx` + one `Market.tsx` warning are acceptable) · `npm test` · `npm run build`

**Notes:**
- Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures. Local test Postgres can hang after a killed run → rely on CI if a DB test hangs ~90s+.
- There is a pre-existing unstaged `.env.production` change in the working tree (separate CI work) — NEVER stage or touch any `.env*`.
- Some frontend tests live in a parallel `tests/unit/` mirror dir in addition to `src/**/__tests__/`. After changing a component's rendered text, run the FULL `npm test` once to catch mirror-suite breakage.

## File Structure

**Backend**
- Create `app/services/streak_config.py` — the three streak tunables.
- Modify `app/services/content_service.py` — `streak_after_activity` gains freeze logic.
- Modify `app/models/user.py` — `UserProgress.streak_freezes`.
- Create `alembic/versions/a1b2c3d4e5f6_add_streak_freezes.py`.
- Modify `app/routers/content.py` (`_award_completion` + `LessonCompletionResult` construction) and `app/schemas/content.py` (`LessonCompletionResult.streak_freezes`).
- Modify `app/schemas/user.py` (`UserProgressOut.streak_freezes`) and `app/routers/users.py` (both construction sites).

**Frontend**
- Create `src/lib/reminderConfig.ts` — the `REMINDER` config object.
- Create `src/lib/streakReminder.ts` — `decideStreakReminder` (pure), `ymdLocal` (pure), `applyStreakReminder` + `requestReminderPermission` (native wrappers).
- Create `src/hooks/useStreakReminder.ts` — evaluates + applies on progress changes.
- Modify `src/api/content.ts` (`Progress.streak_freezes`, `LessonCompletionResult.streak_freezes`), `src/components/child/StatsBar.tsx` (shield indicator), `src/pages/child/Stats.tsx` (explainer), `src/components/child/ProfileMenu.tsx` (toggle), `src/components/child/Shell.tsx` (mount hook), `frontend/package.json` (plugin).
- Tests: `tests/unit/` or co-located `__tests__/` for the pure helpers, StatsBar, and the toggle.

---

### Task 1: `streak_config.py` + `streak_freezes` column + migration

**Files:**
- Create: `app/services/streak_config.py`, `alembic/versions/a1b2c3d4e5f6_add_streak_freezes.py`
- Modify: `app/models/user.py`
- Test: `tests/test_streak_freeze.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/test_streak_freeze.py`:

```python
import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_streak_config_constants():
    from app.services import streak_config
    assert streak_config.STREAK_MILESTONE == 7
    assert streak_config.STREAK_FREEZE_CAP == 2
    assert streak_config.STREAK_FREEZE_GAP == 2


async def test_user_progress_has_streak_freezes_default_zero(db_session):
    import uuid
    from app.models.user import User, UserProgress

    u = User(
        username="freezekid", password_hash="x",
        dob=__import__("datetime").date(2014, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserProgress(user_id=u.id))
    await db_session.flush()

    p = await db_session.scalar(select(UserProgress).where(UserProgress.user_id == u.id))
    assert p.streak_freezes == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py -v`
Expected: FAIL — `streak_config` module missing / `streak_freezes` attribute missing.

- [ ] **Step 3: Create `app/services/streak_config.py`**

```python
"""Single source of truth for streak / streak-freeze tunables.

Product rules (not secrets) — change here to retune; ships with a backend deploy,
no app release. Promote to env-driven Settings later if per-env tuning is ever needed.
"""

STREAK_MILESTONE = 7    # earn a freeze each time the streak hits a multiple of this
STREAK_FREEZE_CAP = 2   # max freezes a user can hold
STREAK_FREEZE_GAP = 2   # a day-gap of exactly this (= 1 missed day) is freezable
```

- [ ] **Step 4: Add the model column** — in `app/models/user.py`, `UserProgress` (after `virtual_coins`):

```python
    streak_freezes: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
```

- [ ] **Step 5: Write the migration** — `alembic/versions/a1b2c3d4e5f6_add_streak_freezes.py`:

```python
"""add streak_freezes to user_progress

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-06-05 13:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_progress",
        sa.Column("streak_freezes", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_progress", "streak_freezes")
```

- [ ] **Step 6: Verify single head**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: single head `a1b2c3d4e5f6 (head)`. If two heads, fix `down_revision`.

- [ ] **Step 7: Run the test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py -v`
Expected: PASS.

- [ ] **Step 8: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/streak_config.py invest-ed/backend/app/models/user.py invest-ed/backend/alembic/versions/a1b2c3d4e5f6_add_streak_freezes.py invest-ed/backend/tests/test_streak_freeze.py
git commit -m "feat: add streak_freezes column + streak_config tunables

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Freeze logic in `streak_after_activity`

**Files:**
- Modify: `app/services/content_service.py`
- Test: `tests/test_streak_freeze.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_streak_freeze.py`:

```python
from datetime import date, timedelta


def test_streak_after_activity_freeze_matrix():
    from app.services.content_service import streak_after_activity

    d = date(2026, 1, 15)
    f = streak_after_activity
    # (last, current, freezes, today) -> (streak, last, freezes)
    assert f(None, 0, 0, d) == (1, d, 0)                    # first ever
    assert f(d, 5, 1, d) == (5, d, 1)                       # same day, no change
    assert f(d - timedelta(days=1), 5, 0, d) == (6, d, 0)   # consecutive
    assert f(d - timedelta(days=1), 6, 0, d) == (7, d, 1)   # milestone grants a freeze
    assert f(d - timedelta(days=1), 13, 1, d) == (14, d, 2) # 2nd milestone -> cap edge
    assert f(d - timedelta(days=1), 6, 2, d) == (7, d, 2)   # milestone but already at cap
    assert f(d - timedelta(days=2), 5, 1, d) == (6, d, 0)   # 1 missed day, freeze absorbs
    assert f(d - timedelta(days=2), 6, 1, d) == (7, d, 1)   # freeze absorb + milestone (net 0)
    assert f(d - timedelta(days=2), 5, 0, d) == (1, d, 0)   # missed day, no freeze -> reset
    assert f(d - timedelta(days=3), 5, 2, d) == (1, d, 2)   # 2+ days missed -> reset, freezes kept
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py::test_streak_after_activity_freeze_matrix -v`
Expected: FAIL — `streak_after_activity` still has the old 3-arg signature.

- [ ] **Step 3: Rewrite `streak_after_activity`** in `app/services/content_service.py` (replace the existing function; add the import at the top of the file):

```python
from app.services.streak_config import (
    STREAK_FREEZE_CAP,
    STREAK_FREEZE_GAP,
    STREAK_MILESTONE,
)
```

```python
def _grant_milestone(streak: int, freezes: int) -> int:
    """Grant one freeze (capped) when the streak hits a milestone."""
    if streak % STREAK_MILESTONE == 0:
        return min(STREAK_FREEZE_CAP, freezes + 1)
    return freezes


def streak_after_activity(
    last: date | None, current: int, freezes: int, today: date
) -> tuple[int, date, int]:
    """Return (new_streak, new_last_activity_date, new_freezes) after an activity today.

    - First ever activity -> streak = 1.
    - Same day as last activity -> no change.
    - Exactly the next day -> increment; milestone may grant a freeze.
    - Exactly one missed day (gap == STREAK_FREEZE_GAP) with a freeze available ->
      consume one freeze, continue the streak (milestone re-checked on the new value).
    - Any larger gap, or a missed day with no freeze -> reset to 1 (freezes unchanged).
    """
    if last is None:
        return 1, today, freezes
    if last == today:
        return current, today, freezes
    gap = (today - last).days
    if gap == 1:
        new = current + 1
        return new, today, _grant_milestone(new, freezes)
    if gap == STREAK_FREEZE_GAP and freezes > 0:
        new = current + 1
        return new, today, _grant_milestone(new, freezes - 1)
    return 1, today, freezes
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py -v`
Expected: PASS. (Callers still pass 3 args — they're fixed in Task 3; the app may not import-break since this is a pure function, but DO NOT run the full suite yet; the single caller in `content.py` is updated next.)

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/content_service.py invest-ed/backend/tests/test_streak_freeze.py
git commit -m "feat: freeze-aware streak_after_activity (config-driven)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Wire freeze into completion + expose in API

**Files:**
- Modify: `app/routers/content.py`, `app/schemas/content.py`, `app/schemas/user.py`, `app/routers/users.py`
- Test: `tests/test_streak_freeze.py`

- [ ] **Step 1: Write the failing integration test** — append to `tests/test_streak_freeze.py`:

```python
async def test_progress_endpoint_returns_streak_freezes(client, db_session):
    await client.post("/auth/register", json={
        "email": "fz@example.com", "username": "fzkid", "password": "SecurePass123!",
        "dob": "2014-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    r = await client.get("/users/me/progress")
    assert r.status_code == 200
    assert r.json()["streak_freezes"] == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py::test_progress_endpoint_returns_streak_freezes -v`
Expected: FAIL — `KeyError: 'streak_freezes'` (schema doesn't include it yet).

- [ ] **Step 3: Update `_award_completion` in `app/routers/content.py`** — replace the streak block (the `new_streak, new_last = streak_after_activity(...)` lines):

```python
    new_streak, new_last, new_freezes = streak_after_activity(
        progress.last_activity_date, progress.streak_count, progress.streak_freezes, today_local
    )
    progress.streak_count = new_streak
    progress.last_activity_date = new_last
    progress.streak_freezes = new_freezes
    return lesson.xp_reward, False
```

- [ ] **Step 4: Add `streak_freezes` to `LessonCompletionResult`** — in `app/schemas/content.py`:

```python
class LessonCompletionResult(BaseModel):
    xp_awarded: int
    already_completed: bool
    total_xp: int
    level: int
    streak_count: int
    streak_freezes: int = 0
    practice_available: bool = False
```
And in `app/routers/content.py` where `LessonCompletionResult(...)` is constructed, add the field:

```python
    return LessonCompletionResult(
        xp_awarded=xp_awarded, already_completed=already,
        total_xp=progress.xp, level=progress.level, streak_count=progress.streak_count,
        streak_freezes=progress.streak_freezes,
        practice_available=practice_available,
    )
```

- [ ] **Step 5: Add `streak_freezes` to `UserProgressOut`** — in `app/schemas/user.py`:

```python
class UserProgressOut(BaseModel):
    xp: int
    level: int
    streak_count: int
    streak_freezes: int = 0
    last_activity_date: date | None
```
And in `app/routers/users.py` `get_progress`, set it in BOTH branches:

```python
    if progress is None:
        return UserProgressOut(xp=0, level=1, streak_count=0, streak_freezes=0, last_activity_date=None)
    return UserProgressOut(
        xp=progress.xp,
        level=progress.level,
        streak_count=progress.streak_count,
        streak_freezes=progress.streak_freezes,
        last_activity_date=progress.last_activity_date,
    )
```

- [ ] **Step 6: Run the new test + the existing content/progress tests**

Run:
```
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_streak_freeze.py tests/test_content.py tests/test_users.py -v
```
Expected: PASS (the freeze field defaults to 0 everywhere; existing assertions unaffected). If `test_content.py`/`test_users.py` names differ, run `pytest -k "progress or completion or streak"`.

- [ ] **Step 7: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/content.py invest-ed/backend/app/schemas/content.py invest-ed/backend/app/schemas/user.py invest-ed/backend/app/routers/users.py invest-ed/backend/tests/test_streak_freeze.py
git commit -m "feat: persist + expose streak_freezes on completion and progress

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Notification config + scheduling helpers (frontend)

**Files:**
- Create: `src/lib/reminderConfig.ts`, `src/lib/streakReminder.ts`
- Modify: `frontend/package.json` (add `@capacitor/local-notifications`)
- Test: `src/lib/__tests__/streakReminder.test.ts` (new)

- [ ] **Step 1: Install the plugin**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm install @capacitor/local-notifications`
Expected: it installs and appears under `dependencies` in `package.json`. **If this fails because the sandbox has no network**, STOP and report BLOCKED (the package is required for `cap sync ios`; the user can run the install). Do not fake it.

- [ ] **Step 2: Write the failing test** — create `src/lib/__tests__/streakReminder.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { decideStreakReminder, ymdLocal } from '../streakReminder';
import { REMINDER } from '../reminderConfig';

const at = (h: number) => { const d = new Date(2026, 0, 15, h, 0, 0, 0); return d; };

describe('ymdLocal', () => {
  it('formats local YYYY-MM-DD', () => {
    expect(ymdLocal(new Date(2026, 0, 5, 9))).toBe('2026-01-05');
  });
});

describe('decideStreakReminder', () => {
  const base = { enabled: true, practicedToday: false, streakCount: 3 };
  it('cancels when disabled', () => {
    expect(decideStreakReminder({ ...base, enabled: false, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('cancels when no active streak', () => {
    expect(decideStreakReminder({ ...base, streakCount: 0, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('cancels when already practiced today', () => {
    expect(decideStreakReminder({ ...base, practicedToday: true, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('schedules at the primary hour in the morning', () => {
    const d = decideStreakReminder({ ...base, now: at(9) });
    expect(d.action).toBe('schedule');
    if (d.action === 'schedule') expect(d.at.getHours()).toBe(REMINDER.primaryHour);
  });
  it('falls back to the later hour in the evening', () => {
    const d = decideStreakReminder({ ...base, now: at(REMINDER.primaryHour + 1) });
    expect(d.action).toBe('schedule');
    if (d.action === 'schedule') expect(d.at.getHours()).toBe(REMINDER.fallbackHour);
  });
  it('cancels when it is too late at night', () => {
    expect(decideStreakReminder({ ...base, now: at(REMINDER.fallbackHour + 1) })).toEqual({ action: 'cancel' });
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- streakReminder`
Expected: FAIL — modules don't exist.

- [ ] **Step 4: Create `src/lib/reminderConfig.ts`**

```ts
// Single source of truth for the streak-reminder local notification.
// Changing these needs an app release (native bundle); structured so a future
// server-config endpoint could hydrate it without touching callers.
export const REMINDER = {
  notificationId: 1001,
  primaryHour: 18, // first-choice fire time (local 24h)
  fallbackHour: 20, // used if it's already past primaryHour
  storageKey: 'notif_streak_reminder',
  title: (streak: number) => `🔥 Keep your ${streak}-day streak alive!`,
  body: 'A quick lesson before bed keeps your streak going.',
} as const;
```

- [ ] **Step 5: Create `src/lib/streakReminder.ts`**

```ts
import { LocalNotifications } from '@capacitor/local-notifications';
import { isNativeApp } from './platform';
import { REMINDER } from './reminderConfig';

export type ReminderDecision = { action: 'cancel' } | { action: 'schedule'; at: Date };

/** Local YYYY-MM-DD (matches the backend's local-date streak handling). */
export function ymdLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function decideStreakReminder(args: {
  enabled: boolean;
  practicedToday: boolean;
  streakCount: number;
  now: Date;
}): ReminderDecision {
  const { enabled, practicedToday, streakCount, now } = args;
  if (!enabled || streakCount <= 0 || practicedToday) return { action: 'cancel' };
  const hour = now.getHours();
  let targetHour: number;
  if (hour < REMINDER.primaryHour) targetHour = REMINDER.primaryHour;
  else if (hour < REMINDER.fallbackHour) targetHour = REMINDER.fallbackHour;
  else return { action: 'cancel' };
  const at = new Date(now);
  at.setHours(targetHour, 0, 0, 0);
  return { action: 'schedule', at };
}

/** Ask for notification permission. Returns true if granted. Native only. */
export async function requestReminderPermission(): Promise<boolean> {
  if (!isNativeApp()) return false;
  const res = await LocalNotifications.requestPermissions();
  return res.display === 'granted';
}

/** Apply a decision via the OS scheduler. No-op on web. */
export async function applyStreakReminder(
  decision: ReminderDecision,
  streakCount: number,
): Promise<void> {
  if (!isNativeApp()) return;
  // Always clear the existing one first so we never stack duplicates.
  await LocalNotifications.cancel({ notifications: [{ id: REMINDER.notificationId }] });
  if (decision.action === 'cancel') return;
  await LocalNotifications.schedule({
    notifications: [
      {
        id: REMINDER.notificationId,
        title: REMINDER.title(streakCount),
        body: REMINDER.body,
        schedule: { at: decision.at },
      },
    ],
  });
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- streakReminder`
Expected: PASS. (The pure functions don't touch the plugin; `vitest` resolves the import but never calls the native methods.)

- [ ] **Step 7: Typecheck + commit**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b`
Expected: clean.

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/package.json invest-ed/frontend/package-lock.json invest-ed/frontend/src/lib/reminderConfig.ts invest-ed/frontend/src/lib/streakReminder.ts invest-ed/frontend/src/lib/__tests__/streakReminder.test.ts
git commit -m "feat(fe): local-notification config + streak-reminder helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Frontend types + StatsBar freeze indicator + Stats explainer

**Files:**
- Modify: `src/api/content.ts`, `src/components/child/StatsBar.tsx`, `src/pages/child/Stats.tsx`
- Test: `src/components/child/__tests__/StatsBar.test.tsx` (new or existing)

- [ ] **Step 1: Add the FE types** — in `src/api/content.ts`, add `streak_freezes` to both shapes:

In the `LessonCompletionResult` type (the object with `xp_awarded`/`already_completed`/...):
```ts
  streak_count: number;
  streak_freezes: number;
  practice_available: boolean;
```
In `Progress`:
```ts
export type Progress = {
  xp: number;
  level: number;
  streak_count: number;
  streak_freezes: number;
  last_activity_date: string | null; // YYYY-MM-DD
};
```

- [ ] **Step 2: Write the failing StatsBar test** — create `src/components/child/__tests__/StatsBar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { StatsBar } from '../StatsBar';

describe('StatsBar freeze indicator', () => {
  it('shows the shield with count when freezes > 0', () => {
    render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={2} lastActivityDate={null} />);
    expect(screen.getByLabelText(/2 streak freeze/i)).toBeInTheDocument();
  });
  it('hides the shield when freezes is 0', () => {
    render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={0} lastActivityDate={null} />);
    expect(screen.queryByLabelText(/streak freeze/i)).toBeNull();
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={1} lastActivityDate={null} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- StatsBar`
Expected: FAIL — `StatsBar` has no `streakFreezes` prop.

- [ ] **Step 4: Add the indicator to `StatsBar.tsx`** — add `streakFreezes` to `Props` and render a shield chip:

```tsx
type Props = {
  xp: number;
  level: number;
  streakCount: number;
  streakFreezes: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function StatsBar({ xp, level, streakCount, streakFreezes, lastActivityDate, today }: Props) {
```
Then, immediately after the streak `<span>`, add:
```tsx
      {streakFreezes > 0 && (
        <span
          className="rounded-full bg-brand-100 px-4 py-1.5 text-sm font-bold text-brand-800"
          aria-label={`${streakFreezes} streak freeze${streakFreezes === 1 ? '' : 's'} — saves your streak if you miss a day`}
        >
          <span aria-hidden="true">🛡️ ×{streakFreezes}</span>
        </span>
      )}
```

- [ ] **Step 5: Pass the prop where StatsBar is used** — in `src/pages/child/Home.tsx`, the `<StatsBar ... />` call: add `streakFreezes={progress?.streak_freezes ?? 0}`. Grep for any other `StatsBar` usage and pass it there too:

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && grep -rn "<StatsBar" src`
For each call site, add `streakFreezes={progress?.streak_freezes ?? 0}` (use the local progress object available there).

- [ ] **Step 6: Add the Stats-page explainer** — in `src/pages/child/Stats.tsx`, near where streak/freezes are shown, add one line (only meaningful when the user has the data; keep it static and brief):

```tsx
        <p className="text-xs text-muted-foreground">🛡️ A streak freeze saves your streak if you miss a day. Earn one every 7-day streak (up to 2).</p>
```
(Place it inside the existing stats container; match surrounding markup. If `Stats.tsx` doesn't currently show the streak, add the sentence under the StatsBar/streak area.)

- [ ] **Step 7: Run tests + typecheck**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- StatsBar && npx tsc -b && npm run lint`
Expected: StatsBar tests pass; tsc clean; lint clean (known warnings only). If other tests render `StatsBar` and now error on the required prop, update those call sites/mocks to pass `streakFreezes={0}` — run the FULL `npm test` to catch them.

- [ ] **Step 8: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src
git commit -m "feat(fe): streak-freeze indicator in StatsBar + Stats explainer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `useStreakReminder` hook + Shell mount + ProfileMenu toggle

**Files:**
- Create: `src/hooks/useStreakReminder.ts`
- Modify: `src/components/child/Shell.tsx`, `src/components/child/ProfileMenu.tsx`
- Test: `src/components/child/__tests__/ProfileMenu.reminder.test.tsx` (new)

- [ ] **Step 1: Create the hook** — `src/hooks/useStreakReminder.ts`:

```ts
import { useEffect } from 'react';
import { useProgress } from './useProgress';
import { isNativeApp } from '@/lib/platform';
import { REMINDER } from '@/lib/reminderConfig';
import { applyStreakReminder, decideStreakReminder, ymdLocal } from '@/lib/streakReminder';

/** Re-evaluates the streak reminder whenever progress changes. Native only; web no-op. */
export function useStreakReminder(): void {
  const { data: progress } = useProgress();
  const lastActivity = progress?.last_activity_date ?? null;
  const streakCount = progress?.streak_count ?? 0;

  useEffect(() => {
    if (!isNativeApp()) return;
    const enabled = localStorage.getItem(REMINDER.storageKey) === '1';
    const now = new Date();
    const practicedToday = lastActivity === ymdLocal(now);
    const decision = decideStreakReminder({ enabled, practicedToday, streakCount, now });
    void applyStreakReminder(decision, streakCount);
  }, [lastActivity, streakCount]);
}
```

- [ ] **Step 2: Mount it in `Shell.tsx`** — inside the `Shell` component body (after the existing hooks, before the early returns), add:

```tsx
  useStreakReminder();
```
and the import:
```tsx
import { useStreakReminder } from '@/hooks/useStreakReminder';
```

- [ ] **Step 3: Write the failing toggle test** — create `src/components/child/__tests__/ProfileMenu.reminder.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/lib/platform', () => ({ isNativeApp: () => true }));
vi.mock('@/lib/streakReminder', () => ({
  requestReminderPermission: vi.fn(async () => true),
  applyStreakReminder: vi.fn(async () => {}),
  decideStreakReminder: () => ({ action: 'cancel' }),
  ymdLocal: () => '2026-01-15',
}));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false } }) }));

import { ProfileMenu } from '../ProfileMenu';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

beforeEach(() => localStorage.clear());

describe('ProfileMenu daily reminder toggle (native)', () => {
  it('renders the reminder toggle on native', () => {
    render(wrap(<ProfileMenu username="Sam" />));
    // The menu opens its content; the toggle is labelled "Daily streak reminder".
    expect(screen.getByText(/daily streak reminder/i)).toBeInTheDocument();
  });
});
```
> Note: if `ProfileMenu` renders its settings inside a closed dropdown/bottomsheet, the test must open it first (click the trigger) OR the toggle must live in the always-rendered editor content. Read `ProfileMenu.tsx` and mirror however existing ProfileMenu tests (e.g. `ProfileMenu.test.tsx`) reveal the content; reuse their open-the-menu pattern. Keep the assertion (toggle present) intact.

- [ ] **Step 4: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- ProfileMenu.reminder`
Expected: FAIL — no reminder toggle yet.

- [ ] **Step 5: Add the toggle to `ProfileMenu.tsx`** — read the file first. In the `editorContent` "Preferences" section (or a new "Reminders" sub-block), add a native-only toggle. Use the existing imports plus:

```tsx
import { isNativeApp } from '@/lib/platform';
import { REMINDER } from '@/lib/reminderConfig';
import { requestReminderPermission, applyStreakReminder } from '@/lib/streakReminder';
```
Add component state near the other `useState`s:
```tsx
  const [reminderOn, setReminderOn] = useState(() => localStorage.getItem(REMINDER.storageKey) === '1');
  const [reminderDenied, setReminderDenied] = useState(false);
```
Add a handler:
```tsx
  async function toggleReminder(next: boolean) {
    if (next) {
      const granted = await requestReminderPermission();
      if (!granted) { setReminderDenied(true); setReminderOn(false); return; }
      localStorage.setItem(REMINDER.storageKey, '1');
      setReminderDenied(false);
      setReminderOn(true);
      // Scheduling is handled by useStreakReminder on next progress read; nothing to do here.
    } else {
      localStorage.removeItem(REMINDER.storageKey);
      setReminderOn(false);
      void applyStreakReminder({ action: 'cancel' }, 0);
    }
  }
```
Render inside the Preferences section, native only:
```tsx
        {isNativeApp() && (
          <div className="space-y-1.5 border-t border-line pt-3">
            <label className="flex items-center justify-between gap-3 text-sm font-medium">
              <span>Daily streak reminder</span>
              <input
                type="checkbox"
                checked={reminderOn}
                onChange={(e) => void toggleReminder(e.target.checked)}
                className="h-5 w-5"
                aria-describedby="reminder-help"
              />
            </label>
            <p id="reminder-help" className="text-xs text-muted-foreground">
              A friendly evening nudge if your streak is about to end. Off by default.
            </p>
            {reminderDenied && (
              <p className="text-xs text-accent-700">
                Turn on notifications for InvestiKid in your device Settings to use reminders.
              </p>
            )}
          </div>
        )}
```

- [ ] **Step 6: Run the toggle test + full frontend suite**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- ProfileMenu && npx tsc -b && npm run lint`
Expected: toggle test passes; existing ProfileMenu tests still pass; tsc + lint clean.

- [ ] **Step 7: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src
git commit -m "feat(fe): opt-in daily streak reminder toggle + scheduling hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full regression, iOS sync, push

**Files:** none (verification + sync).

- [ ] **Step 1: Backend regression**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: all pass; ruff clean; single head `a1b2c3d4e5f6`. (DB hang ~90s+ = environmental; rely on CI.)

- [ ] **Step 2: Frontend regression**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean (known warnings only); all vitest suites pass; build succeeds.

- [ ] **Step 3: iOS sync**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx cap sync ios`
Expected: "Sync finished", and the plugin is listed (`@capacitor/local-notifications`). If `git status` shows tracked `invest-ed/frontend/ios` changes, commit them:
```bash
cd "/Users/leeashmore/Local Repo"
git add -A invest-ed/frontend/ios && git commit -m "chore(ios): cap sync local-notifications plugin

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "nothing to commit from cap sync"
```

- [ ] **Step 4: Push**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```

- [ ] **Step 5: Report** — summarise commits; note: Railway deploys the backend + Vercel the frontend on green CI; the streak-reminder + freeze indicator need a **USER Xcode rebuild/TestFlight** to verify on device (the iOS notification permission prompt + a scheduled reminder); freezes themselves work immediately on web/backend.

---

## Self-Review

**Spec coverage:**
- Streak-freeze data + migration → Task 1. ✓
- `streak_after_activity` freeze logic (milestone/cap/absorb/reset, config-driven) → Task 2. ✓
- Wire into completion + expose on completion result & progress endpoint → Task 3. ✓
- `@capacitor/local-notifications`, `reminderConfig`, `decideStreakReminder` + `ymdLocal` + `applyStreakReminder` + `requestReminderPermission` → Task 4. ✓
- FE types + StatsBar shield + Stats explainer → Task 5. ✓
- `useStreakReminder` + Shell mount + opt-in ProfileMenu toggle (native-only, off by default, permission flow, denied note) → Task 6. ✓
- Configurability (`streak_config.py` + `reminderConfig.ts`, no inline literals, tests reference constants) → Tasks 1, 2, 4. ✓
- iOS sync + USER rebuild note → Task 7. ✓

**Placeholder scan:** No TBD/TODO; every code step shows the content. The `<StatsBar` grep (Task 5 Step 5) and the ProfileMenu open-pattern note (Task 6 Step 3) have explicit resolution rules, not placeholders. ✓

**Type consistency:** `streak_after_activity(last, current, freezes, today) -> (int, date, int)` is defined in Task 2 and called with exactly those 4 args in Task 3. `streak_freezes` is added consistently to the model (Task 1), both schemas (Task 3), both FE types (Task 5), and the `StatsBar` `streakFreezes` prop (Task 5) consumed by `useProgress().streak_freezes`. `decideStreakReminder`/`applyStreakReminder`/`ymdLocal`/`requestReminderPermission` signatures match between Task 4 (definition) and Task 6 (usage). `REMINDER` keys (`notificationId`, `primaryHour`, `fallbackHour`, `storageKey`, `title`, `body`) are used identically across Tasks 4 and 6. ✓
