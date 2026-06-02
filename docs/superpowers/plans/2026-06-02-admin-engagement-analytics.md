# Admin Engagement Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give admins per-module engagement insight — per-lesson completion, drop-off, and average score, plus a module summary — surfaced on the admin module page, backed by a new lightweight lesson-view event.

**Architecture:** Add a de-duplicated `lesson_views` table + an idempotent `POST /content/lessons/{id}/view` the child app fires on lesson open. A pure aggregation module (`engagement_service.py`) computes metrics from views + completions; a thin async loader fetches rows and calls it. `GET /admin/modules/{id}/engagement` exposes it; an admin React panel renders it on the module page. Metrics are computed live (no caching). Progress is unaffected — it is already computed live elsewhere.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic (hand-written, chained). Pydantic v2. React 18 + TanStack Query + Tailwind. Pytest (async, `loop_scope="session"`). Vitest + vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-02-admin-engagement-analytics-design.md`

**Conventions:**
- Backend cmds from `invest-ed/backend`: tests `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`, lint `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`, migrate `/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head`. Current alembic head: `d4e5f6a7b8c9`.
- Frontend cmds from `invest-ed/frontend`: `npx tsc -b`, `npm run lint`, `npm test`, `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend ONLY on green CI (5 jobs). If the local test Postgres hangs, that's environmental — rely on CI.
- Tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` and the `client` / `admin_client` / `db_session` fixtures in `tests/conftest.py`. Never instantiate a raw `AsyncClient` on the app engine.

## File Structure

- Create `app/models/__init__.py` import + `LessonView` in `app/models/content.py` — view event row.
- Create `alembic/versions/e5f6a7b8c9d0_add_lesson_views.py` — table migration.
- Create `app/services/engagement_service.py` — pure aggregation + async loader.
- Modify `app/schemas/admin.py` — `LessonEngagementOut`, `ModuleEngagementOut`.
- Modify `app/routers/content.py` — `POST /lessons/{id}/view`.
- Modify `app/routers/admin.py` — `GET /modules/{id}/engagement`.
- Create `tests/test_engagement_service.py`, `tests/test_lesson_view.py`, `tests/test_admin_engagement.py`.
- Modify `frontend/src/api/content.ts` — `recordLessonView`.
- Modify `frontend/src/pages/child/Lesson.tsx` — fire view on mount.
- Modify `frontend/src/api/admin.ts` — engagement types + `useModuleEngagement`.
- Create `frontend/src/components/admin/ModuleEngagement.tsx` — panel.
- Modify `frontend/src/components/admin/ModuleForm.tsx` — embed panel (edit mode).
- Create `frontend/src/components/admin/__tests__/ModuleEngagement.test.tsx`.

---

### Task 1: `LessonView` model + migration

**Files:**
- Modify: `app/models/content.py` (append after `LessonCompletion`)
- Create: `alembic/versions/e5f6a7b8c9d0_add_lesson_views.py`

- [ ] **Step 1: Add the model**

In `app/models/content.py`, append (the file already imports `UniqueConstraint`, `ForeignKey`, `DateTime`, `UTC`, `datetime`, `uuid`, `Mapped`, `mapped_column` — reuse them; mirror `LessonCompletion`):

```python
class LessonView(Base):
    __tablename__ = "lesson_views"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_view_user_lesson"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

If `app/models/__init__.py` explicitly imports content models, add `LessonView` to that import line (check with `grep -n "LessonCompletion" app/models/__init__.py`; if present, add `LessonView` alongside it).

- [ ] **Step 2: Write the migration**

Create `alembic/versions/e5f6a7b8c9d0_add_lesson_views.py`:

```python
"""add lesson_views table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-02 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_views",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", UUID(as_uuid=True), nullable=False),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_view_user_lesson"),
    )
    op.create_index("ix_lesson_views_user_id", "lesson_views", ["user_id"])
    op.create_index("ix_lesson_views_lesson_id", "lesson_views", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_views_lesson_id", table_name="lesson_views")
    op.drop_index("ix_lesson_views_user_id", table_name="lesson_views")
    op.drop_table("lesson_views")
```

- [ ] **Step 3: Apply + verify the migration**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head`
Expected: ends at `e5f6a7b8c9d0`. Then `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` shows `e5f6a7b8c9d0 (head)`.

- [ ] **Step 4: Lint**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/models/content.py alembic/versions/e5f6a7b8c9d0_add_lesson_views.py`
Expected: All checks passed.

- [ ] **Step 5: Commit**

```bash
git add invest-ed/backend/app/models/content.py invest-ed/backend/app/models/__init__.py invest-ed/backend/alembic/versions/e5f6a7b8c9d0_add_lesson_views.py
git commit -m "feat(engagement): add lesson_views table + model

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Engagement aggregation — pure functions + tests

**Files:**
- Create: `app/services/engagement_service.py`
- Create: `tests/test_engagement_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engagement_service.py`:

```python
import uuid

from app.services.engagement_service import (
    LessonInput,
    compute_module_engagement,
)


def _lesson(t, **cj):
    return LessonInput(lesson_id=uuid.uuid4(), type=t, content_json=cj)


def test_per_lesson_counts_rate_score_and_completion_implies_view():
    mid = uuid.uuid4()
    q = _lesson("quiz", question="Q1")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [q],
        viewers_by_lesson={q.lesson_id: {u1, u2}},
        completers_by_lesson={q.lesson_id: {u2, u3}},  # u3 completed without a view row
        scores_by_lesson={q.lesson_id: [0.5, 1.0]},
    )
    le = result.lessons[0]
    assert le.views == 3            # u1,u2 viewed + u3 implied by completion
    assert le.completions == 2
    assert le.completion_rate == 2 / 3
    assert le.average_score == 0.75
    assert le.label == "Q1"
    assert le.order == 0


def test_drop_off_uses_previous_lesson_completers():
    mid = uuid.uuid4()
    a, b = _lesson("card", title="A"), _lesson("quiz", question="B")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [a, b],
        viewers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1}},
        completers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1}},
        scores_by_lesson={},
    )
    assert result.lessons[0].drop_off == 0          # first lesson
    assert result.lessons[1].drop_off == 2          # 3 completed A, 1 completed B


def test_module_summary_started_completed_and_rate():
    mid = uuid.uuid4()
    a, b = _lesson("card", title="A"), _lesson("quiz", question="B")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [a, b],
        viewers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1, u2}},
        completers_by_lesson={a.lesson_id: {u1, u2}, b.lesson_id: {u1}},
        scores_by_lesson={},
    )
    assert result.learners_started == 3             # u1,u2,u3 viewed something
    assert result.learners_completed == 1           # only u1 completed every lesson
    assert result.completion_rate == 1 / 3


def test_zero_views_lesson_has_none_rate_no_divide_by_zero():
    mid = uuid.uuid4()
    a = _lesson("video", youtube_id="x", caption="Intro")
    result = compute_module_engagement(
        mid, [a],
        viewers_by_lesson={}, completers_by_lesson={}, scores_by_lesson={},
    )
    le = result.lessons[0]
    assert le.views == 0
    assert le.completion_rate is None
    assert le.average_score is None
    assert le.label == "Intro"


def test_empty_module_is_all_zeros_none():
    mid = uuid.uuid4()
    result = compute_module_engagement(mid, [], {}, {}, {})
    assert result.lessons == []
    assert result.learners_started == 0
    assert result.learners_completed == 0
    assert result.completion_rate is None
    assert result.average_score is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_engagement_service.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.engagement_service'`.

- [ ] **Step 3: Implement the pure functions**

Create `app/services/engagement_service.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.services.content_service import derive_lesson_title


@dataclass(frozen=True)
class LessonInput:
    lesson_id: uuid.UUID
    type: str
    content_json: dict


@dataclass(frozen=True)
class LessonEngagement:
    lesson_id: uuid.UUID
    type: str
    label: str
    order: int
    views: int
    completions: int
    completion_rate: float | None
    average_score: float | None
    drop_off: int


@dataclass(frozen=True)
class ModuleEngagement:
    module_id: uuid.UUID
    learners_started: int
    learners_completed: int
    completion_rate: float | None
    average_score: float | None
    lessons: list[LessonEngagement]


def compute_module_engagement(
    module_id: uuid.UUID,
    lessons: list[LessonInput],
    viewers_by_lesson: dict[uuid.UUID, set[uuid.UUID]],
    completers_by_lesson: dict[uuid.UUID, set[uuid.UUID]],
    scores_by_lesson: dict[uuid.UUID, list[float]],
) -> ModuleEngagement:
    """Pure: compute per-lesson and module engagement from already-fetched sets.

    Completing a lesson implies having viewed it, so completers are unioned into
    viewers. drop_off is completers(prev) - completers(this), clamped at >= 0.
    A learner has 'completed the module' iff they completed every lesson.
    """
    lesson_out: list[LessonEngagement] = []
    started: set[uuid.UUID] = set()
    module_scores: list[float] = []
    completed_all: set[uuid.UUID] | None = None
    prev_completions: int | None = None

    for i, lsn in enumerate(lessons):
        completers = completers_by_lesson.get(lsn.lesson_id, set())
        viewers = viewers_by_lesson.get(lsn.lesson_id, set()) | completers
        scores = scores_by_lesson.get(lsn.lesson_id, [])
        views = len(viewers)
        completions = len(completers)
        rate = (completions / views) if views else None
        avg = (sum(scores) / len(scores)) if scores else None
        drop = 0 if prev_completions is None else max(0, prev_completions - completions)

        lesson_out.append(LessonEngagement(
            lesson_id=lsn.lesson_id, type=lsn.type,
            label=derive_lesson_title(lsn.type, lsn.content_json), order=i,
            views=views, completions=completions,
            completion_rate=rate, average_score=avg, drop_off=drop,
        ))

        started |= viewers
        module_scores.extend(scores)
        completed_all = completers if completed_all is None else (completed_all & completers)
        prev_completions = completions

    learners_started = len(started)
    learners_completed = len(completed_all) if completed_all is not None else 0
    completion_rate = (learners_completed / learners_started) if learners_started else None
    average_score = (sum(module_scores) / len(module_scores)) if module_scores else None

    return ModuleEngagement(
        module_id=module_id,
        learners_started=learners_started,
        learners_completed=learners_completed,
        completion_rate=completion_rate,
        average_score=average_score,
        lessons=lesson_out,
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_engagement_service.py -q`
Expected: 5 passed.

- [ ] **Step 5: Lint + commit**

```bash
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/engagement_service.py tests/test_engagement_service.py
git add invest-ed/backend/app/services/engagement_service.py invest-ed/backend/tests/test_engagement_service.py
git commit -m "feat(engagement): pure module-engagement aggregation + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Async loader for engagement

**Files:**
- Modify: `app/services/engagement_service.py`

- [ ] **Step 1: Add the loader**

Append to `app/services/engagement_service.py` (add imports at top: `from collections import defaultdict`; `from sqlalchemy import select`; `from sqlalchemy.ext.asyncio import AsyncSession`; `from app.models.content import Lesson, LessonCompletion, LessonView, Level, Module`):

```python
async def get_module_engagement(
    session: AsyncSession, module_id: uuid.UUID
) -> ModuleEngagement | None:
    """Load views/completions for a module's lessons and aggregate them.
    Returns None if the module does not exist."""
    module = await session.get(Module, module_id)
    if module is None:
        return None

    rows = (await session.execute(
        select(Lesson)
        .outerjoin(Level, Lesson.level_id == Level.id)
        .where(Lesson.module_id == module_id)
        .order_by(Level.order_index.nulls_first(), Lesson.order_index)
    )).scalars().all()

    lessons = [LessonInput(lesson_id=r.id, type=r.type, content_json=r.content_json or {}) for r in rows]
    lesson_ids = [r.id for r in rows]

    viewers_by: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    completers_by: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    scores_by: dict[uuid.UUID, list[float]] = defaultdict(list)

    if lesson_ids:
        for lid, uid in (await session.execute(
            select(LessonView.lesson_id, LessonView.user_id).where(LessonView.lesson_id.in_(lesson_ids))
        )).all():
            viewers_by[lid].add(uid)
        for lid, uid, score in (await session.execute(
            select(LessonCompletion.lesson_id, LessonCompletion.user_id, LessonCompletion.score)
            .where(LessonCompletion.lesson_id.in_(lesson_ids))
        )).all():
            completers_by[lid].add(uid)
            if score is not None:
                scores_by[lid].append(score)

    return compute_module_engagement(module_id, lessons, viewers_by, completers_by, scores_by)
```

- [ ] **Step 2: Lint (loader is covered by the endpoint test in Task 6)**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/engagement_service.py`
Expected: All checks passed.

- [ ] **Step 3: Commit**

```bash
git add invest-ed/backend/app/services/engagement_service.py
git commit -m "feat(engagement): async loader fetching views/completions per module

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Admin engagement schemas

**Files:**
- Modify: `app/schemas/admin.py`

- [ ] **Step 1: Add the schemas**

Append to `app/schemas/admin.py` (file already imports `uuid`, `BaseModel`, `ConfigDict` from pydantic — verify with `grep -n "ConfigDict\|^import uuid\|from pydantic" app/schemas/admin.py`; add any missing import):

```python
class LessonEngagementOut(BaseModel):
    lesson_id: uuid.UUID
    type: str
    label: str
    order: int
    views: int
    completions: int
    completion_rate: float | None
    average_score: float | None
    drop_off: int

    model_config = ConfigDict(from_attributes=True)


class ModuleEngagementOut(BaseModel):
    module_id: uuid.UUID
    learners_started: int
    learners_completed: int
    completion_rate: float | None
    average_score: float | None
    lessons: list[LessonEngagementOut]

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Lint + commit**

```bash
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/schemas/admin.py
git add invest-ed/backend/app/schemas/admin.py
git commit -m "feat(engagement): admin engagement response schemas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `POST /content/lessons/{id}/view` endpoint + tests

**Files:**
- Modify: `app/routers/content.py`
- Create: `tests/test_lesson_view.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lesson_view.py`. Mirror the auth setup used in `tests/test_content.py` for the `complete` endpoint (it logs a user in via the `client` fixture). Open `tests/test_content.py`, copy its imports, `pytestmark`, and the helper/fixture it uses to obtain an authenticated `client` and a seeded lesson, then:

```python
# (top of file — mirror tests/test_content.py auth + seeding helpers)
import pytest
from sqlalchemy import func, select

from app.models.content import LessonView

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_record_view_inserts_then_is_idempotent(authed_client, seeded_lesson, db_session):
    # authed_client: logged-in child; seeded_lesson: a Lesson row (see test_content.py)
    r1 = await authed_client.post(f"/lessons/{seeded_lesson.id}/view")
    assert r1.status_code == 204
    r2 = await authed_client.post(f"/lessons/{seeded_lesson.id}/view")
    assert r2.status_code == 204
    count = await db_session.scalar(
        select(func.count()).select_from(LessonView).where(LessonView.lesson_id == seeded_lesson.id)
    )
    assert count == 1  # idempotent — one row per (user, lesson)


async def test_record_view_404_for_unknown_lesson(authed_client):
    import uuid
    r = await authed_client.post(f"/lessons/{uuid.uuid4()}/view")
    assert r.status_code == 404
```

> Naming note: use whatever the authenticated-client and lesson fixtures are actually called in `tests/test_content.py` (e.g. it may be the `client` fixture after a login helper, and `user_with_module`/a seeded lesson). Adjust the two fixture names above to match; do not invent new fixtures.

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_lesson_view.py -q`
Expected: FAIL (404 on every POST — route not defined yet).

- [ ] **Step 3: Implement the endpoint**

In `app/routers/content.py`, add `LessonView` to the existing `from app.models.content import ...` line, and add this route (near the `complete_lesson` handler):

```python
@router.post("/lessons/{lesson_id}/view", status_code=204)
async def record_lesson_view(
    lesson_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    existing = await session.scalar(
        select(LessonView).where(
            LessonView.user_id == current_user.id,
            LessonView.lesson_id == lesson_id,
        )
    )
    if existing is None:
        session.add(LessonView(user_id=current_user.id, lesson_id=lesson_id))
        await session.commit()
    return None
```

(`select`, `status`, `HTTPException`, `Depends`, `get_current_user`, `get_session`, `Lesson`, `User`, `AsyncSession` are already imported in this router — verify and add only what's missing.)

- [ ] **Step 4: Run to verify pass**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_lesson_view.py -q`
Expected: 2 passed.

- [ ] **Step 5: Lint + commit**

```bash
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/routers/content.py tests/test_lesson_view.py
git add invest-ed/backend/app/routers/content.py invest-ed/backend/tests/test_lesson_view.py
git commit -m "feat(engagement): idempotent lesson-view record endpoint + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `GET /admin/modules/{id}/engagement` endpoint + tests

**Files:**
- Modify: `app/routers/admin.py`
- Create: `tests/test_admin_engagement.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_admin_engagement.py`. Use the `admin_client` fixture (in `conftest.py`) for authed admin calls and `client` for the unauthorised check. Mirror module/lesson seeding from `tests/test_admin_modules.py`:

```python
import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_engagement_requires_admin(client):
    r = await client.get(f"/admin/modules/{uuid.uuid4()}/engagement")
    assert r.status_code in (401, 403)


async def test_engagement_404_for_unknown_module(admin_client):
    r = await admin_client.get(f"/admin/modules/{uuid.uuid4()}/engagement")
    assert r.status_code == 404


async def test_engagement_shape_for_seeded_module(admin_client, seeded_module_with_lessons):
    # seeded_module_with_lessons: a Module with >=1 Lesson (mirror test_admin_modules.py)
    mod = seeded_module_with_lessons
    r = await admin_client.get(f"/admin/modules/{mod.id}/engagement")
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == str(mod.id)
    assert set(body) >= {"learners_started", "learners_completed", "completion_rate", "average_score", "lessons"}
    assert isinstance(body["lessons"], list)
    if body["lessons"]:
        le = body["lessons"][0]
        assert set(le) >= {"lesson_id", "type", "label", "order", "views", "completions", "completion_rate", "average_score", "drop_off"}
        assert le["order"] == 0
```

> Use the actual module-with-lessons fixture/helper name from `tests/test_admin_modules.py`; adjust `seeded_module_with_lessons` to match. Do not invent a fixture.

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_engagement.py -q`
Expected: FAIL (404/route missing on the shape test).

- [ ] **Step 3: Implement the endpoint**

In `app/routers/admin.py`: add to the schema import (`from app.schemas.admin import ... ModuleEngagementOut`) and add `from app.services.engagement_service import get_module_engagement`, then add the route (place after the existing `GET /modules/{module_id}/lessons`):

```python
@router.get("/modules/{module_id}/engagement", response_model=ModuleEngagementOut)
async def module_engagement(
    module_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await get_module_engagement(session, module_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return result
```

(The admin router is already `dependencies=[Depends(get_current_admin)]`, so auth is enforced automatically. `uuid`, `status`, `HTTPException`, `Depends`, `get_session`, `AsyncSession` are already imported.)

- [ ] **Step 4: Run to verify pass**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_engagement.py -q`
Expected: 3 passed.

- [ ] **Step 5: Lint + commit**

```bash
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/routers/admin.py tests/test_admin_engagement.py
git add invest-ed/backend/app/routers/admin.py invest-ed/backend/tests/test_admin_engagement.py
git commit -m "feat(engagement): admin module-engagement endpoint + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Frontend — record view on lesson open

**Files:**
- Modify: `frontend/src/api/content.ts`
- Modify: `frontend/src/pages/child/Lesson.tsx`

- [ ] **Step 1: Add the API call**

In `frontend/src/api/content.ts`, inside the `contentApi` object (after `completeLesson`), add:

```ts
  recordLessonView: (lessonId: string) =>
    apiFetch<null>(`/lessons/${lessonId}/view`, { method: 'POST' }),
```

- [ ] **Step 2: Fire it on mount**

In `frontend/src/pages/child/Lesson.tsx`, after the existing query declarations, add an effect (fire-and-forget; a failed ping must never disrupt the lesson):

```tsx
  useEffect(() => {
    if (!lessonId) return;
    contentApi.recordLessonView(lessonId).catch(() => { /* analytics ping — ignore */ });
  }, [lessonId]);
```

(`useEffect` and `contentApi` are already imported in this file.)

- [ ] **Step 3: Typecheck + lint + build**

Run from `invest-ed/frontend`: `npx tsc -b && npm run lint`
Expected: tsc clean; lint shows only the pre-existing `button.tsx` fast-refresh warning (0 errors).

- [ ] **Step 4: Commit**

```bash
git add invest-ed/frontend/src/api/content.ts invest-ed/frontend/src/pages/child/Lesson.tsx
git commit -m "feat(engagement): record a lesson view when the lesson opens

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Frontend — engagement types + query hook

**Files:**
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: Add types + hook**

In `frontend/src/api/admin.ts` (which already imports `useQuery` and defines `adminFetch`), add near the other interfaces/hooks:

```ts
export interface LessonEngagement {
  lesson_id: string;
  type: string;
  label: string;
  order: number;
  views: number;
  completions: number;
  completion_rate: number | null;
  average_score: number | null;
  drop_off: number;
}

export interface ModuleEngagement {
  module_id: string;
  learners_started: number;
  learners_completed: number;
  completion_rate: number | null;
  average_score: number | null;
  lessons: LessonEngagement[];
}

export function useModuleEngagement(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'module-engagement', moduleId],
    queryFn: () => adminFetch<ModuleEngagement>(`/admin/modules/${moduleId}/engagement`),
    enabled: !!moduleId,
  });
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd invest-ed/frontend && npx tsc -b
git add invest-ed/frontend/src/api/admin.ts
git commit -m "feat(engagement): admin engagement types + useModuleEngagement hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Frontend — `ModuleEngagement` panel + tests

**Files:**
- Create: `frontend/src/components/admin/ModuleEngagement.tsx`
- Create: `frontend/src/components/admin/__tests__/ModuleEngagement.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/admin/__tests__/ModuleEngagement.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import ModuleEngagement from '../ModuleEngagement';

const base = {
  module_id: 'm1', learners_started: 10, learners_completed: 4,
  completion_rate: 0.4, average_score: 0.82,
  lessons: [
    { lesson_id: 'l1', type: 'card', label: 'Intro', order: 0, views: 10, completions: 9, completion_rate: 0.9, average_score: null, drop_off: 0 },
    { lesson_id: 'l2', type: 'quiz', label: 'What is a stock?', order: 1, views: 9, completions: 4, completion_rate: 0.44, average_score: 0.6, drop_off: 5 },
  ],
};

vi.mock('@/api/admin', () => ({
  useModuleEngagement: () => ({ data: base, isLoading: false, isError: false }),
}));

describe('ModuleEngagement', () => {
  it('renders the summary and per-lesson rows', () => {
    render(<ModuleEngagement moduleId="m1" />);
    expect(screen.getByText(/learners started/i)).toBeInTheDocument();
    expect(screen.getByText('Intro')).toBeInTheDocument();
    expect(screen.getByText('What is a stock?')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ModuleEngagement moduleId="m1" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

Then add an empty-state test by re-mocking in a second file-level `describe` is not possible with a single module mock; instead add this test using a separate mock module value — implement the empty state in the component (Step 3) and assert it manually during dev. (Keep this test file to the two tests above.)

- [ ] **Step 2: Run to verify it fails**

Run from `invest-ed/frontend`: `npx vitest run src/components/admin/__tests__/ModuleEngagement.test.tsx`
Expected: FAIL — cannot resolve `../ModuleEngagement`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/admin/ModuleEngagement.tsx`:

```tsx
import { useModuleEngagement } from '@/api/admin';
import type { LessonEngagement } from '@/api/admin';

function pct(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}
function score(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}

export default function ModuleEngagement({ moduleId }: { moduleId: string }) {
  const { data, isLoading, isError } = useModuleEngagement(moduleId);

  if (isLoading) return <p className="text-slate-400">Loading engagement…</p>;
  if (isError || !data) return <p className="text-slate-400">Engagement data unavailable.</p>;
  if (data.learners_started === 0) {
    return <p className="text-slate-400">No engagement data yet — no learners have started this module.</p>;
  }

  // Highlight the lesson with the lowest completion rate (the sticking point).
  const worst = data.lessons
    .filter((l) => l.completion_rate != null)
    .reduce<LessonEngagement | null>(
      (acc, l) => (acc == null || l.completion_rate! < acc.completion_rate! ? l : acc),
      null,
    )?.lesson_id ?? null;

  return (
    <section aria-labelledby="engagement-heading" className="mt-6">
      <h3 id="engagement-heading" className="mb-3 text-lg font-semibold text-slate-50">Engagement</h3>

      <dl className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Learners started</dt>
          <dd className="text-xl font-semibold text-slate-50">{data.learners_started}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Completed module</dt>
          <dd className="text-xl font-semibold text-slate-50">{pct(data.completion_rate)}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Avg score</dt>
          <dd className="text-xl font-semibold text-slate-50">{score(data.average_score)}</dd>
        </div>
      </dl>

      <table className="w-full text-left text-sm">
        <caption className="sr-only">Per-lesson engagement for this module</caption>
        <thead className="text-xs text-slate-400">
          <tr>
            <th scope="col" className="py-1 pr-2">Lesson</th>
            <th scope="col" className="py-1 pr-2">Views</th>
            <th scope="col" className="py-1 pr-2">Completed</th>
            <th scope="col" className="py-1 pr-2">Rate</th>
            <th scope="col" className="py-1 pr-2">Avg score</th>
            <th scope="col" className="py-1 pr-2">Drop-off</th>
          </tr>
        </thead>
        <tbody>
          {data.lessons.map((l) => (
            <tr key={l.lesson_id} className={l.lesson_id === worst ? 'bg-amber-500/10' : ''}>
              <td className="py-1 pr-2 text-slate-50">{l.label}</td>
              <td className="py-1 pr-2 text-slate-300">{l.views}</td>
              <td className="py-1 pr-2 text-slate-300">{l.completions}</td>
              <td className="py-1 pr-2 text-slate-300">{pct(l.completion_rate)}</td>
              <td className="py-1 pr-2 text-slate-300">{l.type === 'quiz' || l.type === 'scenario' ? score(l.average_score) : '—'}</td>
              <td className="py-1 pr-2 text-slate-300">{l.drop_off > 0 ? `−${l.drop_off}` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run src/components/admin/__tests__/ModuleEngagement.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd invest-ed/frontend && npx tsc -b && npm run lint
git add invest-ed/frontend/src/components/admin/ModuleEngagement.tsx invest-ed/frontend/src/components/admin/__tests__/ModuleEngagement.test.tsx
git commit -m "feat(engagement): admin ModuleEngagement panel + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Wire the panel into the module page (edit mode)

**Files:**
- Modify: `frontend/src/components/admin/ModuleForm.tsx`

- [ ] **Step 1: Render the panel for existing modules**

In `frontend/src/components/admin/ModuleForm.tsx`: import the component near the top —
```tsx
import ModuleEngagement from './ModuleEngagement';
```
Then, in edit mode only (where `moduleId` from `useParams` is present and a module is being edited — the same condition that gates the existing lessons list), render `<ModuleEngagement moduleId={moduleId} />` below the lessons list. Use the exact id variable the file already uses for the current module (check `useParams`/`existing` in the file; the lessons list nearby already references it). Do not render it for the "new module" route (no id yet).

- [ ] **Step 2: Typecheck + lint + the existing ModuleForm test still passes**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npx vitest run src/components/admin/__tests__/ModuleForm.test.tsx`
Expected: tsc clean; lint only the pre-existing warning; ModuleForm tests pass. If the ModuleForm test renders edit mode and now pulls in `useModuleEngagement`, add `useModuleEngagement: () => ({ data: undefined, isLoading: true, isError: false })` to that test's existing `@/api/admin` mock so the component shows its loading state.

- [ ] **Step 3: Commit**

```bash
git add invest-ed/frontend/src/components/admin/ModuleForm.tsx invest-ed/frontend/src/components/admin/__tests__/ModuleForm.test.tsx
git commit -m "feat(engagement): show engagement panel on the admin module page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend suite**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: ruff clean; all tests pass. (If the local Postgres wedges, note it and rely on CI.)

- [ ] **Step 2: Frontend suite**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint only the pre-existing `button.tsx` warning; all vitest tests pass; build succeeds.

- [ ] **Step 3: iOS asset sync (the view-ping ships in the web bundle)**

Run: `cd invest-ed/frontend && npx cap sync ios`
Expected: sync OK. (Call out to the user that the child app needs a rebuild to start firing view events.)

- [ ] **Step 4: Push + confirm CI green**

```bash
git push origin main
```
Then confirm all 5 CI jobs pass (frontend, backend, security, a11y, responsive) before considering the feature deployed (Railway deploys backend only on green CI; Vercel auto-deploys the frontend).

- [ ] **Step 5: Final review**

Dispatch a final code review across the whole feature branch range; address any blocking findings.

---

## Notes for the implementer

- **Forward-only data:** `lesson_views` starts empty; engagement numbers accumulate after deploy. Completions/scores have history; views/started do not backfill. This is expected (per spec).
- **No learner-facing behaviour change:** the only new write is the view ping; progress/level state is still computed live elsewhere.
- **Privacy:** the endpoint returns aggregates only — never per-child rows.
- **Fixture names:** Tasks 5 and 6 reference authenticated-client / seeded-module fixtures by descriptive names; use the real fixture names from `tests/test_content.py` and `tests/test_admin_modules.py` rather than inventing new ones.
