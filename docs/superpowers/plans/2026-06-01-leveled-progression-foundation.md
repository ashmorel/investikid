# Leveled Progression — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `Level` between Module and Lesson so children progress Level 1 → 2 → beyond within a topic; a level unlocks when the previous is completed and passed; levels can be premium; `video` becomes an authored lesson type.

**Architecture:** New `Level` model (Module → Levels → Lessons). `Lesson` gains `level_id` (keeps `module_id` denormalized). Level unlock/pass state is *derived* from existing `LessonCompletion` rows by a new pure-ish `level_service`. Best-score-wins re-completion enables retry-to-pass. Child + admin APIs gain a level layer; the frontend inserts a levels screen between module and lessons.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, Postgres; React 18 + Vite + TanStack Query + Tailwind + Capacitor.

**Spec:** `invest-ed/docs/superpowers/specs/2026-06-01-leveled-progression-foundation-design.md`

---

## Conventions (read once)

- **Backend tests:** `/Users/leeashmore/Local Repo/.venv/bin/pytest` run from `invest-ed/backend`. Async tests use module-level `pytestmark = pytest.mark.asyncio(loop_scope="session")` and the `client` + `db_session` fixtures from `tests/conftest.py`. **Never** create a raw `AsyncClient(app=app)` (breaks the event-loop/engine — use the `client` fixture).
- **Admin auth header in tests:** `{"Authorization": "Bearer test-admin-token-xyz"}`.
- **Lint:** `ruff check .` from `invest-ed/backend` (must pass; `tests/` and `app/seed/` ignore E501). Frontend `npm run lint` (eslint — run it; tsc alone is not enough).
- **Alembic:** migrations are hand-written, chained via `down_revision`. **Current head is `f6a7b8c9d0e1`** (verify with `/Users/leeashmore/Local Repo/.venv/bin/alembic heads`).
- **Git:** from repo root `/Users/leeashmore/Local Repo`. Commit to `main`. End messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. ⚠️ **Railway deploys only on GREEN CI** — all 5 jobs (frontend, backend, security, a11y, responsive) must pass.
- **Pydantic v2** (`model_config = ConfigDict(from_attributes=True)`). **SQLAlchemy 2.0** (`Mapped`/`mapped_column`).

---

## File Structure

**Backend — create:**
- `app/services/level_service.py` — pure level-state derivation
- `alembic/versions/<rev>_add_levels.py` — migration
- `tests/test_levels.py` — child level endpoints + state
- `tests/test_admin_levels.py` — admin level CRUD
- `tests/test_best_score.py` — best-score-wins

**Backend — modify:**
- `app/models/content.py` — `Level` model + `Lesson.level_id`
- `app/models/__init__.py` — register `Level`
- `app/schemas/content.py` — `LevelOut`, `LevelState`
- `app/schemas/admin.py` — `AdminLevelCreate/Update/Out`; add `"video"` to lesson types
- `app/routers/content.py` — `GET /modules/{id}/levels`, `GET /levels/{id}/lessons`, best-score-wins
- `app/routers/admin.py` — level CRUD, lessons scoped to level
- `app/seed/content.py` — wrap seed lessons in a Level 1 + add video lessons

**Frontend — create:**
- `src/components/child/LevelCard.tsx`
- `src/pages/child/Level.tsx`
- `src/components/admin/LevelList.tsx`, `src/components/admin/LevelForm.tsx`
- tests alongside

**Frontend — modify:**
- `src/api/content.ts`, `src/api/admin.ts` — level types + methods
- `src/pages/child/Module.tsx` — render levels list
- `src/pages/child/Lesson.tsx` — level route param + invalidate levels query
- `src/App.tsx` — level route segment + admin level routes
- `src/components/admin/LessonForm.tsx` — video editor + level scoping
- `src/components/admin/ModuleList.tsx` — link to a module's levels

---

## Task 1: `Level` model + `Lesson.level_id`

**Files:**
- Modify: `backend/app/models/content.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Add the `Level` model and `level_id` to `Lesson`**

In `app/models/content.py`, add the `Level` class after `Module` and before `Lesson`, and add `level_id` to `Lesson`:

```python
class Level(Base):
    __tablename__ = "levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.7")
    content_source: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="authored"
    )
    icon: Mapped[str] = mapped_column(String(10), nullable=False, server_default="📊")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

Then in `Lesson`, add `level_id` right after `module_id` (nullable in DB, app-enforced):

```python
    level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.id", ondelete="CASCADE"), nullable=True, index=True
    )
```

(`Boolean, DateTime, Float, ForeignKey, Integer, String` and `UUID`, `datetime`, `UTC` are already imported in this file.)

- [ ] **Step 2: Register the model**

In `app/models/__init__.py`, update the content import line to include `Level`:

```python
from app.models.content import Lesson, LessonCompletion, Level, Module  # noqa: F401
```

- [ ] **Step 3: Verify import**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.models import Level, Lesson; print(Level.__tablename__, 'level_id' in Lesson.__table__.columns)"`
Expected: `levels True`

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/content.py invest-ed/backend/app/models/__init__.py
git commit -m "feat: add Level model and Lesson.level_id

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Migration — create `levels`, add `lessons.level_id`, backfill Level 1

**Files:**
- Create: `backend/alembic/versions/b1c2d3e4f5a6_add_levels.py`

- [ ] **Step 1: Write the migration**

Create the file (chained from current head `f6a7b8c9d0e1`):

```python
"""add levels and lessons.level_id with Level 1 backfill

Revision ID: b1c2d3e4f5a6
Revises: f6a7b8c9d0e1
Create Date: 2026-06-01 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "levels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pass_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("content_source", sa.String(length=16), nullable=False, server_default="authored"),
        sa.Column("icon", sa.String(length=10), nullable=False, server_default="📊"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_levels_module_id", "levels", ["module_id"])

    op.add_column("lessons", sa.Column("level_id", sa.Uuid(), nullable=True))
    op.create_index("ix_lessons_level_id", "lessons", ["level_id"])
    op.create_foreign_key(
        "fk_lessons_level_id", "lessons", "levels", ["level_id"], ["id"], ondelete="CASCADE"
    )

    # Backfill: one "Level 1" per module, inheriting is_premium; attach its lessons.
    conn = op.get_bind()
    modules = conn.execute(sa.text("SELECT id, is_premium FROM modules")).fetchall()
    for module_id, is_premium in modules:
        level_id = conn.execute(
            sa.text(
                "INSERT INTO levels (id, module_id, title, order_index, is_premium, "
                "pass_threshold, content_source, icon, created_at) "
                "VALUES (gen_random_uuid(), :mid, 'Level 1', 0, :prem, 0.7, 'authored', '📊', now()) "
                "RETURNING id"
            ),
            {"mid": module_id, "prem": is_premium},
        ).scalar_one()
        conn.execute(
            sa.text("UPDATE lessons SET level_id = :lid WHERE module_id = :mid"),
            {"lid": level_id, "mid": module_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_lessons_level_id", "lessons", type_="foreignkey")
    op.drop_index("ix_lessons_level_id", table_name="lessons")
    op.drop_column("lessons", "level_id")
    op.drop_index("ix_levels_module_id", table_name="levels")
    op.drop_table("levels")
```

NOTE: `gen_random_uuid()` requires the `pgcrypto`/`pgcrypto`-provided function. Postgres 13+ exposes `gen_random_uuid()` in core — the project runs Postgres 16 (CI + Railway), so it is available. If `alembic upgrade` errors with "function gen_random_uuid() does not exist", add `op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')` as the first line of `upgrade()` and report it.

- [ ] **Step 2: Verify single head**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/alembic heads`
Expected: `b1c2d3e4f5a6 (head)` — a single head.

- [ ] **Step 3: Apply against the dev DB (if available)**

`/Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head`
Expected: completes; ends at `b1c2d3e4f5a6`. (DB-connection error in a keyless env is acceptable — the migration is exercised by CI's Postgres; report if so.)

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/alembic/versions/b1c2d3e4f5a6_add_levels.py
git commit -m "feat: migration for levels + lessons.level_id with Level 1 backfill

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Best-score-wins re-completion

**Files:**
- Modify: `backend/app/routers/content.py` (`_award_completion`)
- Test: `backend/tests/test_best_score.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_best_score.py`. Use the `client` fixture and register/login a child, then complete the same quiz lesson twice with rising scores. To get a lesson id, read the seeded modules/levels through the API.

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {
    "password": "SecurePass123!", "dob": "2006-01-01",
    "country_code": "GB", "currency_code": "GBP",
}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    r = await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    assert r.status_code == 200


async def _seed_quiz_lesson(db_session):
    """Create a module → level → quiz lesson directly; return the lesson id."""
    from app.models.content import Lesson, Level, Module
    m = Module(topic="stocks", title="BS Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    lesson = Lesson(
        module_id=m.id, level_id=lvl.id, type="quiz", order_index=0, xp_reward=10,
        content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0},
    )
    db_session.add(lesson)
    await db_session.flush()
    return str(lesson.id)


async def test_recompletion_keeps_best_score_and_awards_xp_once(client, db_session):
    await _login(client, "bs@example.com", "bsuser")
    lesson_id = await _seed_quiz_lesson(db_session)

    r1 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.4})
    assert r1.status_code == 200
    assert r1.json()["xp_awarded"] == 10
    assert r1.json()["already_completed"] is False

    r2 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.9})
    assert r2.status_code == 200
    assert r2.json()["xp_awarded"] == 0           # XP only once
    assert r2.json()["already_completed"] is True

    # Lower score must NOT lower the stored best
    r3 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.2})
    assert r3.status_code == 200

    from sqlalchemy import select
    from app.models.content import LessonCompletion
    score = await db_session.scalar(
        select(LessonCompletion.score).where(LessonCompletion.lesson_id == lesson_id)
    )
    assert score == 0.9
```

- [ ] **Step 2: Run it — expect failure**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_best_score.py -q`
Expected: FAIL on the `score == 0.9` assertion (current code no-ops on repeat; stored score stays 0.4).

- [ ] **Step 3: Rewrite `_award_completion` to best-score-wins**

In `app/routers/content.py`, replace the body of `_award_completion` with a select-then-branch (avoids the IntegrityError/rollback path so we can update the existing row):

```python
async def _award_completion(
    session: AsyncSession,
    user_id,
    progress: UserProgress,
    lesson: Lesson,
    score: float | None,
    today_local,
) -> tuple[int, bool]:
    """Insert a LessonCompletion + award XP once. On repeat, keep the best score."""
    existing = await session.scalar(
        select(LessonCompletion).where(
            LessonCompletion.user_id == user_id,
            LessonCompletion.lesson_id == lesson.id,
        )
    )
    if existing is not None:
        # Best-score-wins; XP already awarded on first completion.
        if score is not None and (existing.score is None or score > existing.score):
            existing.score = score
            existing.completed_at = datetime.now(UTC)
        return 0, True

    session.add(LessonCompletion(
        user_id=user_id, lesson_id=lesson.id, score=score,
        completed_at=datetime.now(UTC),
    ))
    await session.flush()

    progress.xp += lesson.xp_reward
    progress.level = compute_level(progress.xp)
    new_streak, new_last = streak_after_activity(
        progress.last_activity_date, progress.streak_count, today_local
    )
    progress.streak_count = new_streak
    progress.last_activity_date = new_last
    return lesson.xp_reward, False
```

(`select` and `LessonCompletion` are already imported in this module.)

- [ ] **Step 4: Run it — expect pass**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_best_score.py -q`
Expected: PASS.

- [ ] **Step 5: Regression on the content/skill suites**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_content.py tests/test_skill_profile.py -q` (run whichever exist; if a path doesn't exist, skip it). Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/content.py invest-ed/backend/tests/test_best_score.py
git commit -m "feat: best-score-wins on lesson re-completion (retry to pass)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Level-state derivation service

**Files:**
- Create: `backend/app/services/level_service.py`
- Test: `backend/tests/test_level_service.py`

A pure function: given ordered levels, the lesson ids per level, the user's completed lesson ids, the per-lesson best scores, and `is_premium(user)`, return each level's state.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_level_service.py`:

```python
import uuid

from app.services.level_service import LevelStateInput, derive_level_states


def _mk(order, *, premium=False, threshold=0.7):
    return LevelStateInput(
        level_id=uuid.uuid4(), order_index=order, is_premium=premium,
        pass_threshold=threshold,
    )


def test_first_level_unlocked_rest_locked_when_nothing_done():
    lvls = [_mk(0), _mk(1)]
    states = derive_level_states(
        lvls, lessons_by_level={lv.level_id: [uuid.uuid4()] for lv in lvls},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    s0, s1 = states[lvls[0].level_id], states[lvls[1].level_id]
    assert s0.state == "in_progress" and s0.locked_reason is None
    assert s1.state == "locked" and s1.locked_reason == "progression"


def test_passing_level1_unlocks_level2():
    l1, l2 = _mk(0, threshold=0.7), _mk(1)
    q = uuid.uuid4()  # one scored lesson in L1
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [q], l2.level_id: [uuid.uuid4()]},
        completed_ids={q}, scores={q: 0.8}, user_is_premium=False,
    )
    assert states[l1.level_id].state == "completed"
    assert states[l1.level_id].passed is True
    assert states[l2.level_id].state == "in_progress"


def test_completed_but_not_passed_keeps_next_locked():
    l1, l2 = _mk(0, threshold=0.7), _mk(1)
    q = uuid.uuid4()
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [q], l2.level_id: [uuid.uuid4()]},
        completed_ids={q}, scores={q: 0.5}, user_is_premium=False,
    )
    assert states[l1.level_id].passed is False
    assert states[l2.level_id].state == "locked"


def test_premium_level_shows_premium_lock_for_free_user():
    l1 = _mk(0, premium=True)
    states = derive_level_states(
        [l1], lessons_by_level={l1.level_id: [uuid.uuid4()]},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    assert states[l1.level_id].locked_reason == "premium"


def test_premium_precedence_over_progression():
    l1, l2 = _mk(0), _mk(1, premium=True)
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [uuid.uuid4()], l2.level_id: [uuid.uuid4()]},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    # L2 is both progression-locked and premium → premium wins
    assert states[l2.level_id].locked_reason == "premium"
```

- [ ] **Step 2: Run it — expect failure**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_level_service.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.level_service`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/level_service.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class LevelStateInput:
    level_id: uuid.UUID
    order_index: int
    is_premium: bool
    pass_threshold: float


@dataclass(frozen=True)
class LevelState:
    state: str            # "in_progress" | "completed" | "locked"
    locked_reason: str | None  # "premium" | "progression" | None
    passed: bool
    lessons_total: int
    lessons_completed: int


def _complete_and_passed(
    lesson_ids: list[uuid.UUID],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    threshold: float,
) -> tuple[bool, bool, int]:
    total = len(lesson_ids)
    done = sum(1 for lid in lesson_ids if lid in completed_ids)
    complete = total > 0 and done == total
    scored = [scores.get(lid) for lid in lesson_ids if scores.get(lid) is not None]
    if not scored:
        passed = complete  # no scored lessons → pass on completion
    else:
        passed = complete and (sum(scored) / len(scored)) >= threshold
    return complete, passed, done


def derive_level_states(
    levels: list[LevelStateInput],
    *,
    lessons_by_level: dict[uuid.UUID, list[uuid.UUID]],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    user_is_premium: bool,
) -> dict[uuid.UUID, LevelState]:
    ordered = sorted(levels, key=lambda lv: lv.order_index)
    out: dict[uuid.UUID, LevelState] = {}
    prev_passed = True  # the first level has no predecessor gate
    for lv in ordered:
        lesson_ids = lessons_by_level.get(lv.level_id, [])
        complete, passed, done = _complete_and_passed(
            lesson_ids, completed_ids, scores, lv.pass_threshold
        )
        progression_locked = not prev_passed
        if lv.is_premium and not user_is_premium:
            state, reason = "locked", "premium"
        elif progression_locked:
            state, reason = "locked", "progression"
        elif complete:
            state, reason = "completed", None
        else:
            state, reason = "in_progress", None
        out[lv.level_id] = LevelState(
            state=state, locked_reason=reason, passed=passed,
            lessons_total=len(lesson_ids), lessons_completed=done,
        )
        prev_passed = passed
    return out
```

- [ ] **Step 4: Run it — expect pass**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_level_service.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/services/level_service.py tests/test_level_service.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/level_service.py invest-ed/backend/tests/test_level_service.py
git commit -m "feat: level-state derivation service

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Content schemas for levels

**Files:**
- Modify: `backend/app/schemas/content.py`

- [ ] **Step 1: Add the schemas**

Append to `app/schemas/content.py`:

```python
class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    order_index: int
    is_premium: bool
    icon: str = "📊"
    state: Literal["in_progress", "completed", "locked"]
    locked_reason: Literal["premium", "progression"] | None = None
    passed: bool = False
    lessons_total: int = 0
    lessons_completed: int = 0
```

(`uuid`, `Literal`, `BaseModel`, `ConfigDict` are already imported.)

- [ ] **Step 2: Verify import**

`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.schemas.content import LevelOut; print('ok')"` (run from `invest-ed/backend`). Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/content.py
git commit -m "feat: LevelOut schema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Child endpoints — list levels & level lessons

**Files:**
- Modify: `backend/app/routers/content.py`
- Test: `backend/tests/test_levels.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_levels.py`:

```python
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _module_two_levels(db_session, *, l2_premium=False):
    m = Module(topic="stocks", title="LV Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    l1 = Level(module_id=m.id, title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)
    l2 = Level(module_id=m.id, title="Level 2", order_index=1, is_premium=l2_premium, pass_threshold=0.7)
    db_session.add_all([l1, l2])
    await db_session.flush()
    q1 = Lesson(module_id=m.id, level_id=l1.id, type="quiz", order_index=0, xp_reward=10,
                content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0})
    q2 = Lesson(module_id=m.id, level_id=l2.id, type="card", order_index=0, xp_reward=10,
                content_json={"title": "t", "body": "b"})
    db_session.add_all([q1, q2])
    await db_session.flush()
    return m, l1, l2, q1, q2


async def test_list_levels_returns_states(client, db_session):
    await _login(client, "lv1@example.com", "lv1user")
    m, l1, l2, q1, q2 = await _module_two_levels(db_session)
    r = await client.get(f"/modules/{m.id}/levels")
    assert r.status_code == 200
    body = sorted(r.json(), key=lambda x: x["order_index"])
    assert body[0]["state"] == "in_progress"
    assert body[1]["state"] == "locked" and body[1]["locked_reason"] == "progression"


async def test_level_lessons_premium_gate(client, db_session):
    await _login(client, "lv2@example.com", "lv2user")
    m, l1, l2, q1, q2 = await _module_two_levels(db_session, l2_premium=True)
    # free user → premium level lessons 403
    r = await client.get(f"/levels/{l2.id}/lessons")
    assert r.status_code == 403
    # non-premium level OK
    r1 = await client.get(f"/levels/{l1.id}/lessons")
    assert r1.status_code == 200
    assert len(r1.json()) == 1
```

- [ ] **Step 2: Run — expect failure**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_levels.py -q`
Expected: FAIL (404 — endpoints don't exist).

- [ ] **Step 3: Add the endpoints**

In `app/routers/content.py`: add the `Level` import (`from app.models.content import Lesson, LessonCompletion, Level, Module`), import the schema and service, and add two endpoints. Add `LevelOut` to the `app.schemas.content` import and:

```python
from app.services.level_service import LevelStateInput, derive_level_states
```

Add an accessible-level helper and the endpoints (place after `list_lessons`):

```python
async def _get_accessible_level(level_id, current_user, session) -> Level:
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    # Reuse module access (country/age/premium-module gate)
    await _get_accessible_module(level.module_id, current_user, session)
    if level.is_premium and not is_premium(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Level requires premium")
    return level


@router.get("/modules/{module_id}/levels", response_model=list[LevelOut])
async def list_levels(
    module_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_accessible_module(module_id, current_user, session)
    levels = list(await session.scalars(
        select(Level).where(Level.module_id == module_id).order_by(Level.order_index)
    ))
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.module_id == module_id)
    ))
    lessons_by_level: dict = {}
    for lsn in lessons:
        if lsn.level_id is not None:
            lessons_by_level.setdefault(lsn.level_id, []).append(lsn.id)

    all_lesson_ids = [lsn.id for lsn in lessons]
    completed_ids: set = set()
    scores: dict = {}
    if all_lesson_ids:
        rows = (await session.execute(
            select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_(all_lesson_ids),
            )
        )).all()
        for lid, score in rows:
            completed_ids.add(lid)
            scores[lid] = score

    states = derive_level_states(
        [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
        lessons_by_level=lessons_by_level,
        completed_ids=completed_ids, scores=scores,
        user_is_premium=is_premium(current_user),
    )
    return [
        LevelOut(
            id=lv.id, module_id=lv.module_id, title=lv.title, order_index=lv.order_index,
            is_premium=lv.is_premium, icon=lv.icon,
            state=states[lv.id].state, locked_reason=states[lv.id].locked_reason,
            passed=states[lv.id].passed, lessons_total=states[lv.id].lessons_total,
            lessons_completed=states[lv.id].lessons_completed,
        )
        for lv in levels
    ]


@router.get("/levels/{level_id}/lessons", response_model=list[LessonSummary])
async def list_level_lessons(
    level_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_accessible_level(level_id, current_user, session)
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.level_id == level_id).order_by(Lesson.order_index)
    ))
    completed_ids: set = set()
    if lessons:
        completed_ids = set(await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_([lsn.id for lsn in lessons]),
            )
        ))
    return [
        LessonSummary(
            id=lsn.id, type=lsn.type,
            title=derive_lesson_title(lsn.type, lsn.content_json or {}),
            xp_reward=lsn.xp_reward, order_index=lsn.order_index,
            completed=lsn.id in completed_ids,
        )
        for lsn in lessons
    ]
```

Add `LevelOut` to the schema import block at the top of the file.

- [ ] **Step 4: Run — expect pass**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_levels.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: App boots + routes exist**

`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.main import app; print(sorted(p for p in (r.path for r in app.routes) if 'level' in p))"`
Expected: includes `/levels/{level_id}/lessons` and `/modules/{module_id}/levels`.

- [ ] **Step 6: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/routers/content.py tests/test_levels.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/content.py invest-ed/backend/tests/test_levels.py
git commit -m "feat: child level endpoints (list levels + level lessons with premium gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Admin level schemas + `video` lesson type

**Files:**
- Modify: `backend/app/schemas/admin.py`

- [ ] **Step 1: Add admin level schemas and allow `video`**

In `app/schemas/admin.py`:

1. Change the lesson type literals on `LessonCreate.type` and `LessonUpdate.type` from `Literal["card", "quiz", "scenario"]` to `Literal["card", "quiz", "scenario", "video"]` (keep `| None` on `LessonUpdate`).
2. In the `content_json` validator for lessons, add a `video` branch requiring a non-empty `youtube_id` (string). Find the validator (around line 63) and add:

```python
        if values.get("type") == "video":
            if not isinstance(v.get("youtube_id"), str) or not v["youtube_id"].strip():
                raise ValueError("video lessons require a non-empty youtube_id")
```
(Match the validator's existing access pattern — it may use `info.data` in Pydantic v2; mirror how the card/quiz branches read the type.)

3. Append admin level schemas:

```python
class AdminLevelCreate(BaseModel):
    title: str
    order_index: int
    is_premium: bool = False
    pass_threshold: float = 0.7
    icon: str = "📊"


class AdminLevelUpdate(BaseModel):
    title: str | None = None
    order_index: int | None = None
    is_premium: bool | None = None
    pass_threshold: float | None = None
    icon: str | None = None


class AdminLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    order_index: int
    is_premium: bool
    pass_threshold: float
    content_source: str
    icon: str
    lesson_count: int = 0
```

(`uuid`, `BaseModel`, `ConfigDict`, `Literal`, `field_validator` are already imported; if `ConfigDict` is not, add it.)

- [ ] **Step 2: Verify import**

`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.schemas.admin import AdminLevelCreate, AdminLevelOut, AdminLevelUpdate; print('ok')"` (from `invest-ed/backend`). Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/admin.py
git commit -m "feat: admin level schemas + video lesson type

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Admin level CRUD + lessons scoped to level

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/test_admin_levels.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_admin_levels.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")
H = {"Authorization": "Bearer test-admin-token-xyz"}


async def _make_module(client):
    r = await client.post("/admin/modules", json={
        "topic": "stocks", "title": "Admin LV Mod", "icon": "📈", "order_index": 0,
    }, headers=H)
    assert r.status_code == 200
    return r.json()["id"]


async def test_level_crud_and_lessons(client):
    module_id = await _make_module(client)

    # create a level
    r = await client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 1", "order_index": 0, "is_premium": False, "pass_threshold": 0.7,
    }, headers=H)
    assert r.status_code == 200
    level_id = r.json()["id"]
    assert r.json()["content_source"] == "authored"

    # list levels
    r = await client.get(f"/admin/modules/{module_id}/levels", headers=H)
    assert r.status_code == 200 and len(r.json()) == 1

    # add a video lesson scoped to the level
    r = await client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10,
        "content_json": {"youtube_id": "abc123", "caption": "Intro"},
    }, headers=H)
    assert r.status_code == 200
    assert r.json()["type"] == "video"

    # update level
    r = await client.put(f"/admin/levels/{level_id}", json={"is_premium": True}, headers=H)
    assert r.status_code == 200 and r.json()["is_premium"] is True

    # delete level
    r = await client.delete(f"/admin/levels/{level_id}", headers=H)
    assert r.status_code == 200


async def test_video_lesson_requires_youtube_id(client):
    module_id = await _make_module(client)
    r = await client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "L1", "order_index": 0,
    }, headers=H)
    level_id = r.json()["id"]
    r = await client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10, "content_json": {"caption": "no id"},
    }, headers=H)
    assert r.status_code == 422
```

- [ ] **Step 2: Run — expect failure**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_admin_levels.py -q`
Expected: FAIL (404).

- [ ] **Step 3: Add admin endpoints**

In `app/routers/admin.py`: import `Level` (`from app.models.content import ... , Level`) and the new schemas (`AdminLevelCreate, AdminLevelUpdate, AdminLevelOut`). Add a helper to count lessons and these endpoints:

```python
def _level_out(level: Level, lesson_count: int) -> AdminLevelOut:
    return AdminLevelOut(
        id=level.id, module_id=level.module_id, title=level.title,
        order_index=level.order_index, is_premium=level.is_premium,
        pass_threshold=level.pass_threshold, content_source=level.content_source,
        icon=level.icon, lesson_count=lesson_count,
    )


@router.get("/modules/{module_id}/levels", response_model=list[AdminLevelOut])
async def admin_list_levels(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    levels = list(await session.scalars(
        select(Level).where(Level.module_id == module_id).order_by(Level.order_index)
    ))
    out = []
    for lv in levels:
        n = await session.scalar(
            select(func.count()).select_from(Lesson).where(Lesson.level_id == lv.id)
        )
        out.append(_level_out(lv, n or 0))
    return out


@router.post("/modules/{module_id}/levels", response_model=AdminLevelOut)
async def admin_create_level(
    module_id: uuid.UUID, payload: AdminLevelCreate, session: AsyncSession = Depends(get_session)
):
    module = await session.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    level = Level(
        module_id=module_id, title=payload.title, order_index=payload.order_index,
        is_premium=payload.is_premium, pass_threshold=payload.pass_threshold,
        content_source="authored", icon=payload.icon,
    )
    session.add(level)
    await session.commit()
    await session.refresh(level)
    return _level_out(level, 0)


@router.put("/levels/{level_id}", response_model=AdminLevelOut)
async def admin_update_level(
    level_id: uuid.UUID, payload: AdminLevelUpdate, session: AsyncSession = Depends(get_session)
):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    data = payload.model_dump(exclude_unset=True)
    for k, val in data.items():
        setattr(level, k, val)
    await session.commit()
    await session.refresh(level)
    n = await session.scalar(select(func.count()).select_from(Lesson).where(Lesson.level_id == level.id))
    return _level_out(level, n or 0)


@router.delete("/levels/{level_id}")
async def admin_delete_level(level_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    await session.delete(level)
    await session.commit()
    return {"status": "deleted"}


@router.get("/levels/{level_id}/lessons", response_model=list[LessonOut])
async def admin_list_level_lessons(level_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.level_id == level_id).order_by(Lesson.order_index)
    ))
    return [LessonOut.model_validate(lsn) for lsn in lessons]


@router.post("/levels/{level_id}/lessons", response_model=LessonOut)
async def admin_create_level_lesson(
    level_id: uuid.UUID, payload: LessonCreate, session: AsyncSession = Depends(get_session)
):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    lesson = Lesson(
        module_id=level.module_id, level_id=level.id, type=payload.type,
        content_json=payload.content_json, xp_reward=payload.xp_reward,
        order_index=payload.order_index,
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return LessonOut.model_validate(lesson)
```

(`func` is already imported in admin.py; `Module`, `Lesson`, `LessonOut`, `LessonCreate` are imported. Confirm `LessonOut` from `app.schemas.admin` includes `level_id` — if not, leave LessonOut as-is; it already has module_id which is set.)

- [ ] **Step 4: Run — expect pass**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_admin_levels.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/routers/admin.py tests/test_admin_levels.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/admin.py invest-ed/backend/tests/test_admin_levels.py
git commit -m "feat: admin level CRUD + level-scoped lesson create

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Seed — Level 1 per module + example videos

**Files:**
- Modify: `backend/app/seed/content.py`

- [ ] **Step 1: Update `seed_modules_and_lessons` to create a Level 1 and attach lessons**

Open `app/seed/content.py`. In the per-module loop (where a `Module` is created and lessons added), after the module is flushed, create one `Level` (idempotent: look up by `module_id` + `order_index=0`) and set `level_id` on each lesson it creates. Concretely, where the code currently does `session.add(Lesson(module_id=module.id, ...))`, first ensure a level:

```python
from app.models.content import Level  # add to imports at top

# inside the loop, after `await session.flush()` for the module and before adding lessons:
level = await session.scalar(
    select(Level).where(Level.module_id == module.id, Level.order_index == 0)
)
if level is None:
    level = Level(
        module_id=module.id, title="Level 1", order_index=0,
        is_premium=module.is_premium, pass_threshold=0.7, content_source="authored",
    )
    session.add(level)
    await session.flush()
```

Then add `level_id=level.id` to every `Lesson(...)` constructed in that loop. (`select` is already imported in the seed file; if not, add `from sqlalchemy import select`.)

- [ ] **Step 2: Add two example video lessons**

In one or two module specs in `_MODULES` (e.g. the "stocks" module), add a video lesson entry to its `lessons` list:

```python
{"type": "video", "xp_reward": 10, "content_json": {
    "youtube_id": "p7HKvqRI_Bo", "caption": "What is a stock? (intro)"}},
```

(Pick real, kid-appropriate finance-education YouTube IDs; if unsure, leave a clearly-labelled placeholder ID and note it for the user to replace — do NOT block on sourcing.)

- [ ] **Step 3: Verify seed runs idempotently**

If a dev DB is available, run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -m app.seed.run && /Users/leeashmore/Local Repo/.venv/bin/python -m app.seed.run`
Expected: completes twice without error (idempotent). If no DB, the existing seed tests in `tests/test_seed.py` cover it — run those.

- [ ] **Step 4: Run seed tests**

`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_seed.py -q` (if it exists). Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/seed/content.py
git commit -m "feat: seed a Level 1 per module + example video lessons

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Frontend API types + methods

**Files:**
- Modify: `frontend/src/api/content.ts`
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: Add level types + methods to content.ts**

In `src/api/content.ts`, add:

```typescript
export type LevelState = 'in_progress' | 'completed' | 'locked';

export type LevelOut = {
  id: string;
  module_id: string;
  title: string;
  order_index: number;
  is_premium: boolean;
  icon: string;
  state: LevelState;
  locked_reason: 'premium' | 'progression' | null;
  passed: boolean;
  lessons_total: number;
  lessons_completed: number;
};
```

And in `contentApi`, add:

```typescript
  listLevels: (moduleId: string) =>
    apiFetch<LevelOut[]>(`/modules/${moduleId}/levels`),
  listLevelLessons: (levelId: string) =>
    apiFetch<LessonSummary[]>(`/levels/${levelId}/lessons`),
```

- [ ] **Step 2: Add admin level types + methods to admin.ts**

In `src/api/admin.ts`, add an `AdminLevel` interface and `useLevels`/create/update/delete/`useLevelLessons` hooks mirroring the existing `useModules`/`useCreateModule` patterns (use `adminFetch`, the same `useQuery`/`useMutation` style):

```typescript
export interface AdminLevel {
  id: string;
  module_id: string;
  title: string;
  order_index: number;
  is_premium: boolean;
  pass_threshold: number;
  content_source: string;
  icon: string;
  lesson_count: number;
}

export function useLevels(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'levels', moduleId],
    queryFn: () => adminFetch<AdminLevel[]>(`/admin/modules/${moduleId}/levels`),
    enabled: !!moduleId,
  });
}

export function useCreateLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminLevel, 'id' | 'module_id' | 'content_source' | 'lesson_count'>) =>
      adminFetch<AdminLevel>(`/admin/modules/${moduleId}/levels`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}

export function useUpdateLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<AdminLevel>) =>
      adminFetch<AdminLevel>(`/admin/levels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}

export function useDeleteLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/levels/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}
```

Also add a level-scoped lesson list/create hook (`useLevelLessons(levelId)` → GET `/admin/levels/${levelId}/lessons`; create → POST `/admin/levels/${levelId}/lessons`), mirroring the existing admin lesson hooks but keyed on `levelId`.

- [ ] **Step 3: Typecheck**

Run from `invest-ed/frontend`: `npx tsc -b`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/content.ts invest-ed/frontend/src/api/admin.ts
git commit -m "feat: frontend level API types + hooks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: `LevelCard` component

**Files:**
- Create: `frontend/src/components/child/LevelCard.tsx`
- Test: `frontend/src/components/child/__tests__/LevelCard.test.tsx`

- [ ] **Step 1: Write the test**

Create `frontend/src/components/child/__tests__/LevelCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LevelCard } from '../LevelCard';
import type { LevelOut } from '@/api/content';

const base: LevelOut = {
  id: 'l1', module_id: 'm1', title: 'Level 1', order_index: 0, is_premium: false,
  icon: '📊', state: 'in_progress', locked_reason: null, passed: false,
  lessons_total: 4, lessons_completed: 1,
};

describe('LevelCard', () => {
  it('unlocked level is clickable', () => {
    const onOpen = vi.fn();
    render(<LevelCard level={base} onOpen={onOpen} onLockedClick={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /Level 1/ }));
    expect(onOpen).toHaveBeenCalled();
  });

  it('premium-locked shows premium and calls onLockedClick', () => {
    const onLockedClick = vi.fn();
    render(<LevelCard level={{ ...base, state: 'locked', locked_reason: 'premium' }}
      onOpen={() => {}} onLockedClick={onLockedClick} />);
    expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(onLockedClick).toHaveBeenCalled();
  });

  it('progression-locked shows unlock hint', () => {
    render(<LevelCard level={{ ...base, state: 'locked', locked_reason: 'progression' }}
      onOpen={() => {}} onLockedClick={() => {}} />);
    expect(screen.getByText(/unlock/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect failure**

`cd invest-ed/frontend && npm test -- LevelCard` → FAIL (no component).

- [ ] **Step 3: Implement `LevelCard`**

Create `frontend/src/components/child/LevelCard.tsx`. Follow `ModuleCard` styling/patterns (decorative emoji `aria-hidden`, a real `<button>`, an `<h2>` title for a11y). Four states: completed (✓), in_progress (tappable, progress hint), locked-progression (🔒 "Finish the previous level to unlock"), locked-premium (✨ "Premium"). Premium takes precedence (already encoded server-side via `locked_reason`).

```tsx
import { Lock } from 'lucide-react';

type Props = {
  level: import('@/api/content').LevelOut;
  onOpen: () => void;
  onLockedClick: () => void;
};

export function LevelCard({ level, onOpen, onLockedClick }: Props) {
  const locked = level.state === 'locked';
  const premium = level.locked_reason === 'premium';
  const handle = locked ? onLockedClick : onOpen;
  return (
    <button
      type="button"
      onClick={handle}
      aria-label={`${level.title}${locked ? (premium ? ' (premium)' : ' (locked)') : ''}`}
      className="flex w-full flex-col items-start gap-1 rounded-2xl border-2 border-amber-200 bg-white p-4 text-left disabled:opacity-60"
    >
      <span className="text-2xl" aria-hidden="true">{level.icon}</span>
      <h2 className="text-sm font-bold text-gray-900">{level.title}</h2>
      {level.state === 'completed' && (
        <span className="text-xs font-medium text-emerald-600">✓ Completed</span>
      )}
      {level.state === 'in_progress' && (
        <span className="text-xs text-gray-500">{level.lessons_completed}/{level.lessons_total} lessons</span>
      )}
      {locked && premium && (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" /> Premium
        </span>
      )}
      {locked && !premium && (
        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" /> Finish the previous level to unlock
        </span>
      )}
    </button>
  );
}
```

- [ ] **Step 4: Run — expect pass**

`npm test -- LevelCard` → PASS (3).

- [ ] **Step 5: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx eslint src/components/child/LevelCard.tsx src/components/child/__tests__/LevelCard.test.tsx
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/LevelCard.tsx invest-ed/frontend/src/components/child/__tests__/LevelCard.test.tsx
git commit -m "feat: LevelCard component with four states

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 12: Module page → levels list; new Level page; routing

**Files:**
- Modify: `frontend/src/pages/child/Module.tsx`
- Create: `frontend/src/pages/child/Level.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Module page renders levels**

Rewrite `src/pages/child/Module.tsx` to fetch `contentApi.listLevels(moduleId)` (TanStack Query, key `['module-levels', moduleId]`) and render a grid of `LevelCard`s. Tapping an unlocked level → `navigate(`/lessons/${moduleId}/${level.id}`)`. Locked → toast ("Premium — ask a grown-up to unlock." for premium; "Finish the previous level first." for progression), reusing the existing `useToast` pattern from the old Module/Lessons page. Keep the page shell/heading consistent with the current Module page.

- [ ] **Step 2: Create the Level page**

Create `src/pages/child/Level.tsx` — reads `:moduleId` and `:levelId` from `useParams`, fetches `contentApi.listLevelLessons(levelId)` (key `['level-lessons', levelId]`), renders the lesson list exactly as the *old* Module page rendered lessons (reuse that JSX/lesson-row component), each linking to `/lessons/${moduleId}/${levelId}/${lesson.id}`. On a 403 (premium), show a friendly "This level is premium" message.

- [ ] **Step 3: Update routes in App.tsx**

In `src/App.tsx`, replace the child lesson routes with the three-segment structure:

```tsx
<Route path="/lessons" element={<Lessons />} />
<Route path="/lessons/:moduleId" element={<Module />} />
<Route path="/lessons/:moduleId/:levelId" element={<Level />} />
<Route path="/lessons/:moduleId/:levelId/:lessonId" element={<Lesson />} />
```

Add `import Level from '@/pages/child/Level';`. Keep a redirect for the old 2-segment lesson deep link: add `<Route path="/lessons/:moduleId/:lessonId" element={<LegacyLessonRedirect />} />` **only if** it doesn't collide — simpler: drop the old 2-seg lesson route (levels are the new entry). If a legacy redirect is wanted, resolve `lesson.level_id` via `contentApi.getLesson` and redirect; otherwise omit (out of MVP scope — note it).

- [ ] **Step 4: Typecheck + tests**

`cd invest-ed/frontend && npx tsc -b && npm test -- Module Level`
Expected: tsc clean; any existing Module tests updated to the new levels behaviour (update them in this task if they assert the old lesson-list-on-module behaviour).

- [ ] **Step 5: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm run lint
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Module.tsx invest-ed/frontend/src/pages/child/Level.tsx invest-ed/frontend/src/App.tsx
git commit -m "feat: module→levels→lessons navigation (child)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 13: Lesson page — level route param + invalidate levels

**Files:**
- Modify: `frontend/src/pages/child/Lesson.tsx`

- [ ] **Step 1: Read `levelId` and fix back-links + invalidation**

In `src/pages/child/Lesson.tsx`:
1. Add `levelId` to `useParams`.
2. Change "back to module" links to point to `/lessons/${moduleId}/${levelId}`.
3. The lessons list used for "next lesson" should come from `contentApi.listLevelLessons(levelId)` (key `['level-lessons', levelId]`) instead of the module lessons.
4. In the completion `onSuccess`, invalidate the level + module-levels queries so the dashboard and level states refresh:

```tsx
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['progress'] });
      qc.invalidateQueries({ queryKey: ['level-lessons', levelId] });
      qc.invalidateQueries({ queryKey: ['module-levels', moduleId] });
    },
```

- [ ] **Step 2: Typecheck + tests**

`cd invest-ed/frontend && npx tsc -b && npm test -- Lesson`
Expected: tsc clean; update any Lesson tests that referenced the 2-segment route to include `levelId`.

- [ ] **Step 3: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm run lint
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Lesson.tsx
git commit -m "feat: lesson page level-scoped nav + invalidate level/progress queries

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 14: Admin — Level list + form, wired into module nav

**Files:**
- Create: `frontend/src/components/admin/LevelList.tsx`, `frontend/src/components/admin/LevelForm.tsx`
- Modify: `frontend/src/components/admin/ModuleList.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: LevelList + LevelForm**

Create `LevelList.tsx` (lists a module's levels via `useLevels(moduleId)`; create/reorder via `OrderArrows`; delete via `ConfirmDialog`; each level row links to its lessons) and `LevelForm.tsx` (fields: title, order_index, is_premium toggle, pass_threshold number, icon; uses `useCreateLevel`/`useUpdateLevel`). Mirror the existing `ModuleList`/`ModuleForm` component structure and styling.

- [ ] **Step 2: Routes + module link**

In `src/App.tsx` admin route block, add:
```tsx
<Route path="modules/:moduleId/levels" element={<LevelList />} />
<Route path="modules/:moduleId/levels/:levelId/lessons" element={<LessonList />} />
```
(Add imports. If a dedicated admin `LessonList` doesn't exist yet, route the level's lessons to the existing lesson-management screen scoped by `levelId`.) In `ModuleList.tsx`, add a "Levels" link/button on each module row → `/admin/modules/${id}/levels`.

- [ ] **Step 3: Typecheck + lint + tests**

`cd invest-ed/frontend && npx tsc -b && npm run lint && npm test -- LevelList LevelForm` (add minimal render tests for the two components, asserting fields render and create calls the hook — mirror existing admin component tests).

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/LevelList.tsx invest-ed/frontend/src/components/admin/LevelForm.tsx invest-ed/frontend/src/components/admin/ModuleList.tsx invest-ed/frontend/src/App.tsx
git commit -m "feat: admin level list + form, linked from modules

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 15: Admin LessonForm — video editor + level scoping

**Files:**
- Modify: `frontend/src/components/admin/LessonForm.tsx`

- [ ] **Step 1: Add video type + editor; scope create to level**

In `LessonForm.tsx`:
1. Add `video` to the type picker.
2. When `type === 'video'`, render inputs for **YouTube URL/ID** and **caption**; on submit build `content_json = { youtube_id, caption }` (extract the 11-char id if a full URL is pasted).
3. When the form is opened in a level context (a `levelId` route param/prop), create via the level-scoped endpoint (`POST /admin/levels/${levelId}/lessons`) instead of the module endpoint.

- [ ] **Step 2: Typecheck + lint + tests**

`cd invest-ed/frontend && npx tsc -b && npm run lint && npm test -- LessonForm`
Expected: clean; update/extend LessonForm tests to cover the video editor (renders youtube/caption inputs; builds correct content_json).

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/LessonForm.tsx
git commit -m "feat: admin video lesson editor + level-scoped lesson create

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 16: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend full suite + lint**

From `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest -q`
Expected: ruff clean; all tests pass (no new failures vs. the green baseline).

- [ ] **Step 2: Frontend full suite + lint + typecheck + build**

From `invest-ed/frontend`:
`npm run lint && npx tsc -b && npm test && npm run build`
Expected: all clean/green.

- [ ] **Step 3: Push and watch CI**

```bash
cd "/Users/leeashmore/Local Repo" && git push origin main
gh run watch "$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```
Expected: all 5 CI jobs green (frontend, backend, security, a11y, responsive). ⚠️ If any job is red, Railway will SKIP the deploy — fix to green before considering done.

- [ ] **Step 4: Verify deploy + smoke**

After CI is green, confirm Railway deployed (health 200) and the new endpoint exists publicly:
`curl -s -o /dev/null -w "%{http_code}\n" https://lee-local-code-repo-production.up.railway.app/health`
Then in the app (web `app.investikid.ai` and/or iOS Simulator after `npm run build && npx cap sync ios`): a module shows **Levels**; completing Level 1's lessons (and passing) unlocks Level 2; a premium level shows the premium lock for a free child; a video lesson plays and completes. (iOS needs a Capacitor rebuild to pick up the new bundle.)

---

## Self-review notes (for the executor)

- **Migration:** the one migration chains from `f6a7b8c9d0e1` and backfills a Level 1 per module — run `alembic heads` to confirm a single head before committing.
- **Best-score-wins** changed `_award_completion` from an IntegrityError/rollback pattern to select-then-branch; this also fixes the prior "rollback the whole txn on duplicate" behaviour.
- **`Lesson.module_id` is intentionally kept** alongside `level_id` (spec decision) — the level endpoints read `module_id` for the module-wide completion set and `level_id` for level scoping.
- **iOS:** all backend changes deploy via CI→Railway; the frontend changes require `npm run build && npx cap sync ios` + an Xcode re-run to reach the Simulator (call this out at hand-off).
- **AI levels / recommendations** are explicitly out of scope (sub-projects #2 and #3); `content_source` exists but is always `"authored"` here.
