# Level-Aware Recommendations + Parent Per-Level Analytics (15.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make recommendations point at the first lesson in the first *unlocked* level (never a locked one) and carry level context, and give parents a per-module → per-level progress breakdown — deterministically, with no LLM and no DB migration.

**Architecture:** Reuse the existing `level_service.derive_level_states`. Extract one pure helper (`first_actionable_lesson`) and call it from `recommendation_service` (pointer) and `analytics_service` (per-level rows). Backend changes are additive; frontend adds an optional eyebrow on the recommendation card and a "Progress by module" disclosure in the parent `ChildAnalytics` view.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + pydantic v2 (backend, venv `/Users/leeashmore/Local Repo/.venv`); React 18 + Vite + TS + TanStack Query + Tailwind v4 + vitest/vitest-axe (frontend). Working dir `/Users/leeashmore/investikid`, branch `testing`.

**Conventions (every task):** TDD bite-sized steps. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated working-tree `.gitignore` change alone. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Backend verify: `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` + `/Users/leeashmore/Local Repo/.venv/bin/pytest`. Frontend verify (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. WCAG 2.2 AA; touch targets / inputs ≥16px. No `cap sync` (web/parent surfaces only).

**Reused facts (verified in code):**
- `derive_level_states(levels, *, lessons_by_level, completed_ids, scores, user_is_premium) -> dict[level_id, LevelState]`; `LevelState(state, locked_reason, passed, lessons_total, lessons_completed)`; `state ∈ {"in_progress","completed","locked"}`; `locked_reason ∈ {"premium","progression",None}`. `LevelStateInput(level_id, order_index, is_premium, pass_threshold)`. All in `app/services/level_service.py`.
- `Level(id, module_id, title, order_index, is_premium, pass_threshold, content_source, icon)`; `Lesson(... module_id, level_id, type, content_json, order_index)`; `Module(... topic, title, icon, country_codes, is_premium, order_index, min_age, max_age, prerequisite_ids)` in `app/models/content.py`.
- `is_module_accessible(user_country, is_premium_user, module_country_codes, module_is_premium) -> bool` and `content_region_for(user)` in `app/services/content_service.py`.
- `is_premium(user) -> bool` (reads `user.is_premium`) in `app/services/entitlements.py`.
- `build_child_analytics(session, user_id, country_code) -> ChildAnalyticsOut` in `app/services/analytics_service.py`; called by `app/routers/parent.py` as `build_child_analytics(session, r.id, content_region_for(r))`.
- FE recommendation render unit is `frontend/src/components/child/RecommendationCard.tsx` (reads `item: RecommendationCategoryItem`). The `Disclosure` primitive is `frontend/src/components/a11y/Disclosure.tsx` (`label: string`, `defaultOpen?`, `children`). `ProgressBar` is `frontend/src/components/ProgressBar.tsx` (`value`, `max`, `label`).

---

## Section 1 — Level-aware recommendations

### Task 1: Pure helper `first_actionable_lesson` (level_service.py)

**Files:**
- Modify: `backend/app/services/level_service.py`
- Test: `backend/tests/test_first_actionable_lesson.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_first_actionable_lesson.py`:

```python
"""Pure unit tests for first_actionable_lesson (no async, no db)."""
import uuid

from app.services.level_service import LevelStateInput, first_actionable_lesson


def _lvl(order, *, premium=False, threshold=0.7):
    return LevelStateInput(uuid.uuid4(), order, premium, threshold)


def test_first_in_progress_level_first_incomplete_lesson():
    l1, l2 = _lvl(0), _lvl(1)
    a1, a2 = uuid.uuid4(), uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1, a2], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=False,
    )
    assert result == (l1.level_id, a2)


def test_skips_to_second_level_when_first_complete_and_passed():
    l1, l2 = _lvl(0), _lvl(1)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},  # passes threshold -> level 1 completed+passed
        user_is_premium=False,
    )
    assert result == (l2.level_id, b1)


def test_never_points_into_premium_locked_level():
    l1, l2 = _lvl(0), _lvl(1, premium=True)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    # level 1 fully complete+passed, level 2 premium-locked for a free user
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=False,
    )
    assert result is None


def test_progression_locked_when_prev_not_passed():
    l1, l2 = _lvl(0), _lvl(1)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    # level 1 complete but FAILED (score below threshold) -> level 2 progression-locked,
    # and level 1 is "completed" (not in_progress) -> nothing actionable
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.1},
        user_is_premium=False,
    )
    assert result is None


def test_premium_user_can_enter_premium_level():
    l1, l2 = _lvl(0), _lvl(1, premium=True)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=True,
    )
    assert result == (l2.level_id, b1)


def test_returns_none_when_no_lessons():
    l1 = _lvl(0)
    result = first_actionable_lesson(
        [l1],
        lessons_by_level_ordered={l1.level_id: []},
        completed_ids=set(),
        scores={},
        user_is_premium=False,
    )
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_first_actionable_lesson.py -q`
Expected: FAIL — `ImportError: cannot import name 'first_actionable_lesson'`.

- [ ] **Step 3: Implement the helper**

Append to `backend/app/services/level_service.py` (after `derive_level_states`):

```python
def first_actionable_lesson(
    levels: list[LevelStateInput],
    *,
    lessons_by_level_ordered: dict[uuid.UUID, list[uuid.UUID]],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    user_is_premium: bool,
) -> tuple[uuid.UUID, uuid.UUID] | None:
    """(level_id, lesson_id) of the first incomplete lesson in the first
    ``in_progress`` level, walking levels by order_index. None when no level is
    actionable (all complete, or the next is locked). ``lessons_by_level_ordered``
    must list lesson ids per level in display order. Pure — reuses derive_level_states
    so locking matches the level screens exactly."""
    states = derive_level_states(
        levels,
        lessons_by_level=lessons_by_level_ordered,
        completed_ids=completed_ids,
        scores=scores,
        user_is_premium=user_is_premium,
    )
    for lv in sorted(levels, key=lambda x: x.order_index):
        if states[lv.level_id].state != "in_progress":
            continue
        for lid in lessons_by_level_ordered.get(lv.level_id, []):
            if lid not in completed_ids:
                return (lv.level_id, lid)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_first_actionable_lesson.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/level_service.py backend/tests/test_first_actionable_lesson.py
git commit -m "$(cat <<'EOF'
feat(15.3): first_actionable_lesson level-walking helper

Pure helper returning the first incomplete lesson in the first in_progress
level, reusing derive_level_states so locking matches the level screens.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Schema fields on `RecommendationCategoryItem` (ai.py)

**Files:**
- Modify: `backend/app/schemas/ai.py:68-74`
- Test: `backend/tests/test_recommendation_schemas.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_recommendation_schemas.py`:

```python
def test_recommendation_item_accepts_level_context():
    import uuid as _uuid

    from app.schemas.ai import RecommendationCategoryItem

    lvl = _uuid.uuid4()
    item = RecommendationCategoryItem(
        module_id=_uuid.uuid4(),
        lesson_id=_uuid.uuid4(),
        level_id=lvl,
        level_title="Level 2",
        score=0.5,
        reason="Keep going!",
    )
    assert item.level_id == lvl
    assert item.level_title == "Level 2"


def test_recommendation_item_level_context_defaults_none():
    import uuid as _uuid

    from app.schemas.ai import RecommendationCategoryItem

    item = RecommendationCategoryItem(module_id=_uuid.uuid4(), score=0.0, reason="x")
    assert item.level_id is None
    assert item.level_title is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_schemas.py -q`
Expected: FAIL — `TypeError`/validation error on unexpected `level_id`/`level_title`.

- [ ] **Step 3: Add the fields**

In `backend/app/schemas/ai.py`, change `RecommendationCategoryItem`:

```python
class RecommendationCategoryItem(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    level_title: str | None = None
    score: float
    reason: str
    review_prompt: str | None = None
    weak_concepts: list[str] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_schemas.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/schemas/ai.py backend/tests/test_recommendation_schemas.py
git commit -m "$(cat <<'EOF'
feat(15.3): add optional level_id/level_title to RecommendationCategoryItem

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Level-aware pointer in `recommendation_service` (+ seed)

**Files:**
- Modify: `backend/app/services/recommendation_service.py` (imports; `_categorise_scored_modules` item dict ~160-167; pointer block ~320-340; scored.append ~342-353; profiling-off seed item ~217-224; `_topic_path_seed` ~379-418)
- Test: `backend/tests/test_recommendation_levels.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_recommendation_levels.py`:

```python
"""Level-aware recommendation pointer (DB-backed)."""
from datetime import date

import pytest

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User
from app.services.recommendation_service import get_recommendations

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, *, premium=False):
    u = User(
        email=f"rl-{date.today()}-{premium}@example.com",
        username=f"rl{int(premium)}",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
        is_premium=premium, profiling_enabled=True, topic_path="stocks",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _module_two_levels(db_session, *, second_premium=False):
    m = Module(topic="stocks", title="Stocks 101", country_codes=["GB"],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    l1 = Level(module_id=m.id, title="Level 1", order_index=0,
               is_premium=False, pass_threshold=0.7, icon="1️⃣")
    l2 = Level(module_id=m.id, title="Level 2", order_index=1,
               is_premium=second_premium, pass_threshold=0.7, icon="2️⃣")
    db_session.add_all([l1, l2])
    await db_session.flush()
    lessons = []
    for lv in (l1, l2):
        for i in range(2):
            lsn = Lesson(module_id=m.id, level_id=lv.id, type="card",
                         xp_reward=10, order_index=i, content_json={"title": f"{lv.title}-{i}"})
            db_session.add(lsn)
            lessons.append((lv, lsn))
    await db_session.flush()
    return m, l1, l2, lessons


def _find(recs, module_id):
    for cat in ("continue_learning", "practise_again", "something_new"):
        for item in recs[cat]:
            if item["module_id"] == module_id:
                return item
    return None


async def test_pointer_targets_first_level_not_locked_second(db_session):
    u = await _user(db_session)
    m, l1, l2, lessons = await _module_two_levels(db_session, second_premium=True)
    # complete the first lesson of level 1 -> module is partially complete
    first = [lsn for lv, lsn in lessons if lv.id == l1.id][0]
    db_session.add(LessonCompletion(user_id=u.id, lesson_id=first.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    # points at the SECOND lesson of level 1, with level context
    second_l1 = [lsn for lv, lsn in lessons if lv.id == l1.id][1]
    assert item["lesson_id"] == second_l1.id
    assert item["level_id"] == l1.id
    assert item["level_title"] == "Level 1"


async def test_pointer_advances_to_second_level_when_first_passed(db_session):
    u = await _user(db_session)
    m, l1, l2, lessons = await _module_two_levels(db_session)
    for lv, lsn in lessons:
        if lv.id == l1.id:
            db_session.add(LessonCompletion(user_id=u.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    assert item["level_id"] == l2.id
    assert item["level_title"] == "Level 2"


async def test_pointer_none_when_remaining_level_locked(db_session):
    u = await _user(db_session)  # free user
    m, l1, l2, lessons = await _module_two_levels(db_session, second_premium=True)
    for lv, lsn in lessons:
        if lv.id == l1.id:
            db_session.add(LessonCompletion(user_id=u.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None  # module still surfaced
    assert item["lesson_id"] is None
    assert item["level_id"] is None


async def test_unlevelled_module_keeps_first_incomplete_lesson(db_session):
    u = await _user(db_session)
    m = Module(topic="stocks", title="Legacy", country_codes=["GB"],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lessons = []
    for i in range(3):
        lsn = Lesson(module_id=m.id, level_id=None, type="card", xp_reward=10,
                     order_index=i, content_json={"title": f"L{i}"})
        db_session.add(lsn)
        lessons.append(lsn)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=u.id, lesson_id=lessons[0].id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    assert item["lesson_id"] == lessons[1].id
    assert item["level_id"] is None
    assert item["level_title"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_levels.py -q`
Expected: FAIL — items have no `level_id`/`level_title` keys (KeyError) and the pointer ignores level locks.

- [ ] **Step 3: Update imports**

In `backend/app/services/recommendation_service.py`, change the model import and add the helper import:

```python
from app.models.content import Lesson, LessonCompletion, Level, Module
```

and below the existing `from app.services.entitlements import is_premium` line add:

```python
from app.services.level_service import LevelStateInput, first_actionable_lesson
```

- [ ] **Step 4: Pass level context through `_categorise_scored_modules`**

In `_categorise_scored_modules`, extend the `item` dict (the block beginning `item: dict[str, Any] = {`):

```python
        item: dict[str, Any] = {
            "module_id": entry["module_id"],
            "lesson_id": entry.get("_lesson_id"),
            "level_id": entry.get("_level_id"),
            "level_title": entry.get("_level_title"),
            "score": entry["score"],
            "reason": entry["reason"],
            "review_prompt": None,
            "weak_concepts": [],
        }
```

- [ ] **Step 5: Make the pointer block level-aware**

In `get_recommendations`, replace the entire `# Find first incomplete lesson` block (from `lesson_id = None` through the `for lesson in lessons: ... break` loop) with:

```python
        # Find the next actionable lesson (level-aware when the module has levels)
        lesson_id = None
        level_id = None
        level_title = None
        if not is_fully_completed:
            lessons = (
                await session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == m.id)
                    .order_by(Lesson.order_index)
                )
            ).all()
            lesson_ids = [lsn.id for lsn in lessons]
            comp_rows = (
                await session.execute(
                    select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                        LessonCompletion.user_id == user.id,
                        LessonCompletion.lesson_id.in_(lesson_ids),
                    )
                )
            ).all()
            completed_ids = {lid for lid, _ in comp_rows}
            scores = {lid: score for lid, score in comp_rows}

            levels = (
                await session.scalars(
                    select(Level)
                    .where(Level.module_id == m.id)
                    .order_by(Level.order_index)
                )
            ).all()

            if levels:
                lessons_by_level_ordered: dict[uuid.UUID, list[uuid.UUID]] = {}
                for lsn in lessons:  # already ordered by order_index
                    if lsn.level_id is not None:
                        lessons_by_level_ordered.setdefault(lsn.level_id, []).append(lsn.id)
                pointer = first_actionable_lesson(
                    [
                        LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold)
                        for lv in levels
                    ],
                    lessons_by_level_ordered=lessons_by_level_ordered,
                    completed_ids=completed_ids,
                    scores=scores,
                    user_is_premium=is_premium(user),
                )
                if pointer is not None:
                    level_id, lesson_id = pointer
                    level_title = {lv.id: lv.title for lv in levels}.get(level_id)
            else:
                # Unlevelled module — first incomplete lesson (legacy behaviour)
                for lesson in lessons:
                    if lesson.id not in completed_ids:
                        lesson_id = lesson.id
                        break
```

- [ ] **Step 6: Carry level context in the scored entry**

In the same loop, extend the `scored.append({...})` dict with two keys (add after `"_lesson_id": lesson_id,`):

```python
            "_level_id": level_id,
            "_level_title": level_title,
```

- [ ] **Step 7: Add level context to the profiling-off seed item**

In `get_recommendations`, in the `if not user.profiling_enabled:` branch, extend the `something_new` seed dict:

```python
                "something_new": [{
                    "module_id": seed["module_id"],
                    "lesson_id": seed["lesson_id"],
                    "level_id": seed.get("level_id"),
                    "level_title": seed.get("level_title"),
                    "score": 0.0,
                    "reason": seed["reason"],
                    "review_prompt": None,
                    "weak_concepts": [],
                }],
```

- [ ] **Step 8: Make `_topic_path_seed` level-aware**

Replace the body of the `for m in modules:` loop in `_topic_path_seed` with:

```python
    for m in modules:
        # Basic accessibility check: premium and country
        if m.is_premium and not is_premium(user):
            continue
        if m.country_codes and content_region_for(user) not in m.country_codes:
            continue
        lessons = (
            await session.scalars(
                select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order_index)
            )
        ).all()
        if not lessons:
            continue
        levels = (
            await session.scalars(
                select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
            )
        ).all()
        lesson_id = lessons[0].id
        level_id = None
        level_title = None
        if levels:
            lessons_by_level_ordered: dict = {}
            for lsn in lessons:
                if lsn.level_id is not None:
                    lessons_by_level_ordered.setdefault(lsn.level_id, []).append(lsn.id)
            pointer = first_actionable_lesson(
                [
                    LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold)
                    for lv in levels
                ],
                lessons_by_level_ordered=lessons_by_level_ordered,
                completed_ids=set(),
                scores={},
                user_is_premium=is_premium(user),
            )
            if pointer is not None:
                level_id, lesson_id = pointer
                level_title = {lv.id: lv.title for lv in levels}.get(level_id)
        return {
            "module_id": m.id,
            "lesson_id": lesson_id,
            "level_id": level_id,
            "level_title": level_title,
            "reason": f"Start your {pref.replace('_', ' ')} journey",
        }
    return None
```

- [ ] **Step 9: Run the new + existing recommendation tests**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_levels.py backend/tests/test_recommendation_service.py backend/tests/test_recommendation_categorised.py backend/tests/test_recommendation_enhanced.py backend/tests/test_recommendation_topic_seed.py -q`
Expected: PASS (new level tests pass; all existing recommendation tests still pass).

- [ ] **Step 10: Lint**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .`
Expected: no errors (fix import ordering with `ruff check --fix .` if I001 appears).

- [ ] **Step 11: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_levels.py
git commit -m "$(cat <<'EOF'
feat(15.3): level-aware recommendation pointer + seed

The continue-learning pointer (and profiling-off seed) now target the first
incomplete lesson in the first in_progress level via first_actionable_lesson,
never a locked level, and carry level_id/level_title. Unlevelled modules keep
the first-incomplete-lesson behaviour. Hard filters unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Frontend — level eyebrow on `RecommendationCard`

**Files:**
- Modify: `frontend/src/api/ai.ts:26-33` (type)
- Modify: `frontend/src/components/child/RecommendationCard.tsx`
- Test: `frontend/src/components/child/__tests__/RecommendationCard.test.tsx`

- [ ] **Step 1: Write the failing tests**

Append to `RecommendationCard.test.tsx` (inside the `describe('RecommendationCard', ...)` block):

```jsx
  it('renders the level eyebrow when level_title is present', () => {
    renderCard({ item: { ...BASE_ITEM, level_id: 'lvl-2', level_title: 'Level 2' } });
    expect(screen.getByText(/Level 2/)).toBeInTheDocument();
  });

  it('omits the level eyebrow when level_title is absent', () => {
    renderCard();
    expect(screen.queryByText(/Level \d/)).not.toBeInTheDocument();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- RecommendationCard`
Expected: FAIL — no element with "Level 2"; and TS may flag unknown `level_title` on the item type.

- [ ] **Step 3: Extend the type**

In `frontend/src/api/ai.ts`, update `RecommendationCategoryItem`:

```ts
export type RecommendationCategoryItem = {
  module_id: string;
  lesson_id: string | null;
  level_id?: string | null;
  level_title?: string | null;
  score: number;
  reason: string;
  review_prompt: string | null;
  weak_concepts: string[];
};
```

- [ ] **Step 4: Render the eyebrow**

In `frontend/src/components/child/RecommendationCard.tsx`, add the eyebrow directly above the module title `<p>`:

```jsx
      {item.level_title && (
        <p className={`${colors.text} text-[11px] font-semibold uppercase tracking-wide`}>
          {item.level_title}
        </p>
      )}
      <p className="font-semibold text-white text-sm">{moduleTitle}</p>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm run test -- RecommendationCard`
Expected: PASS (all RecommendationCard tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/api/ai.ts frontend/src/components/child/RecommendationCard.tsx frontend/src/components/child/__tests__/RecommendationCard.test.tsx
git commit -m "$(cat <<'EOF'
feat(15.3): show level eyebrow on RecommendationCard when present

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Section 2 — Parent per-level analytics

### Task 5: Backend schemas — `LevelProgressOut` + `ModuleProgressOut`

**Files:**
- Modify: `backend/app/schemas/parent.py` (add classes; add `modules_progress` to `ChildAnalyticsOut`)
- Test: `backend/tests/test_parent_analytics.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_parent_analytics.py` (a pure schema test, no db):

```python
def test_child_analytics_out_has_modules_progress_default():
    from app.schemas.parent import ChildAnalyticsOut

    out = ChildAnalyticsOut(
        level=1, xp=0, xp_to_next_level=100, streak_count=0,
        lessons_completed=0, lessons_total=0, recent_lessons=[], badges=[],
    )
    assert out.modules_progress == []


def test_module_progress_out_nests_levels():
    import uuid as _uuid

    from app.schemas.parent import LevelProgressOut, ModuleProgressOut

    mod = ModuleProgressOut(
        module_id=_uuid.uuid4(), title="Stocks", icon="📈",
        lessons_completed=2, lessons_total=4,
        levels=[LevelProgressOut(
            level_id=_uuid.uuid4(), title="Level 1", state="in_progress",
            locked_reason=None, passed=False, lessons_completed=2, lessons_total=2,
        )],
    )
    assert mod.levels[0].state == "in_progress"
    assert mod.levels[0].locked_reason is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_parent_analytics.py -q -k "modules_progress or module_progress"`
Expected: FAIL — `ImportError`/unexpected field.

- [ ] **Step 3: Add the schemas**

In `backend/app/schemas/parent.py`, add above `class ChildAnalyticsOut`:

```python
class LevelProgressOut(BaseModel):
    level_id: uuid.UUID
    title: str
    state: str  # "in_progress" | "completed" | "locked"
    locked_reason: str | None  # "premium" | "progression" | None
    passed: bool
    lessons_completed: int
    lessons_total: int


class ModuleProgressOut(BaseModel):
    module_id: uuid.UUID
    title: str
    icon: str
    lessons_completed: int
    lessons_total: int
    levels: list[LevelProgressOut]
```

And add the field to `ChildAnalyticsOut` (after `badges`):

```python
    badges: list[BadgeOut]
    modules_progress: list[ModuleProgressOut] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_parent_analytics.py -q -k "modules_progress or module_progress"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/schemas/parent.py backend/tests/test_parent_analytics.py
git commit -m "$(cat <<'EOF'
feat(15.3): add ModuleProgressOut/LevelProgressOut + modules_progress field

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Backend — compute `modules_progress` in `build_child_analytics`

**Files:**
- Modify: `backend/app/services/analytics_service.py` (imports; build + return)
- Test: `backend/tests/test_parent_analytics.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_parent_analytics.py`:

```python
@asyncio_pytest_mark
async def test_analytics_modules_progress_per_level(db_session):
    from app.models.content import Level

    user = User(
        email="ana-levels@example.com", username="analevels",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()

    module = Module(topic="stocks", title="Stocks 101", country_codes=["GB"],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    l1 = Level(module_id=module.id, title="Level 1", order_index=0,
               is_premium=False, pass_threshold=0.7, icon="1️⃣")
    l2 = Level(module_id=module.id, title="Level 2", order_index=1,
               is_premium=True, pass_threshold=0.7, icon="2️⃣")
    db_session.add_all([l1, l2])
    await db_session.flush()

    lessons = {}
    for lv in (l1, l2):
        lessons[lv.id] = []
        for i in range(2):
            lsn = Lesson(module_id=module.id, level_id=lv.id, type="card",
                         xp_reward=10, order_index=i, content_json={"title": f"{lv.title}-{i}"})
            db_session.add(lsn)
            lessons[lv.id].append(lsn)
    await db_session.flush()
    # pass all of level 1
    for lsn in lessons[l1.id]:
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert len(result.modules_progress) == 1
    mp = result.modules_progress[0]
    assert mp.title == "Stocks 101"
    assert mp.lessons_completed == 2
    assert mp.lessons_total == 4
    assert [lv.title for lv in mp.levels] == ["Level 1", "Level 2"]
    assert mp.levels[0].state == "completed"
    assert mp.levels[0].passed is True
    # free child -> premium level 2 is locked
    assert mp.levels[1].state == "locked"
    assert mp.levels[1].locked_reason == "premium"


@asyncio_pytest_mark
async def test_analytics_modules_progress_skips_unlevelled(db_session):
    user = User(
        email="ana-nolvl@example.com", username="ananolvl",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()
    module = Module(topic="stocks", title="Legacy", country_codes=["GB"],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    db_session.add(Lesson(module_id=module.id, level_id=None, type="card",
                          xp_reward=10, order_index=0, content_json={"title": "x"}))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)
    assert result.modules_progress == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_parent_analytics.py -q -k "modules_progress_per_level or skips_unlevelled"`
Expected: FAIL — `modules_progress` is empty (not yet computed).

- [ ] **Step 3: Update imports**

In `backend/app/services/analytics_service.py`, replace the content/schema imports with:

```python
from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import User, UserProgress
from app.schemas.parent import (
    BadgeOut,
    ChildAnalyticsOut,
    LevelProgressOut,
    ModuleProgressOut,
    RecentLessonOut,
)
from app.services.content_service import derive_lesson_title, is_module_accessible
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, derive_level_states
```

- [ ] **Step 4: Compute the breakdown**

In `build_child_analytics`, immediately before the final `return ChildAnalyticsOut(`, insert:

```python
    # 5. Per-module / per-level progress (modules with levels only)
    child = await session.scalar(select(User).where(User.id == user_id))
    child_premium = is_premium(child) if child else False

    all_completions = (await session.execute(
        select(LessonCompletion.lesson_id, LessonCompletion.score)
        .where(LessonCompletion.user_id == user_id)
    )).all()
    completed_ids = {lid for lid, _ in all_completions}
    completion_scores = {lid: s for lid, s in all_completions}

    modules = list(await session.scalars(
        select(Module).order_by(Module.order_index)
    ))
    modules_progress: list[ModuleProgressOut] = []
    for m in modules:
        if not is_module_accessible(country_code, child_premium, m.country_codes, m.is_premium):
            continue
        levels = list(await session.scalars(
            select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
        ))
        if not levels:
            continue
        module_lessons = list(await session.scalars(
            select(Lesson).where(Lesson.module_id == m.id)
        ))
        lessons_by_level: dict[uuid.UUID, list[uuid.UUID]] = {}
        for lsn in module_lessons:
            if lsn.level_id is not None:
                lessons_by_level.setdefault(lsn.level_id, []).append(lsn.id)
        states = derive_level_states(
            [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
            lessons_by_level=lessons_by_level,
            completed_ids=completed_ids,
            scores=completion_scores,
            user_is_premium=child_premium,
        )
        level_outs: list[LevelProgressOut] = []
        m_completed = 0
        m_total = 0
        for lv in sorted(levels, key=lambda x: x.order_index):
            st = states[lv.id]
            m_completed += st.lessons_completed
            m_total += st.lessons_total
            level_outs.append(LevelProgressOut(
                level_id=lv.id, title=lv.title, state=st.state,
                locked_reason=st.locked_reason, passed=st.passed,
                lessons_completed=st.lessons_completed, lessons_total=st.lessons_total,
            ))
        modules_progress.append(ModuleProgressOut(
            module_id=m.id, title=m.title, icon=m.icon,
            lessons_completed=m_completed, lessons_total=m_total,
            levels=level_outs,
        ))
```

Then add `modules_progress=modules_progress,` to the `ChildAnalyticsOut(...)` return.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_parent_analytics.py -q`
Expected: PASS (all analytics tests, new + existing).

- [ ] **Step 6: Lint**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .`
Expected: no errors (`ruff check --fix .` if I001 import-order appears).

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/analytics_service.py backend/tests/test_parent_analytics.py
git commit -m "$(cat <<'EOF'
feat(15.3): per-module/per-level progress in build_child_analytics

modules_progress lists each accessible levelled module with per-level
state/locked_reason/passed/counts from derive_level_states. Unlevelled
modules are skipped. Premium/region gating reused via is_module_accessible.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Frontend — "Progress by module" disclosure in `ChildAnalytics`

**Files:**
- Modify: `frontend/src/api/parent.ts` (types)
- Modify: `frontend/src/components/ChildAnalytics.tsx`
- Test: `frontend/src/components/ChildAnalytics.test.tsx`

- [ ] **Step 1: Add the FE types**

In `frontend/src/api/parent.ts`, add above `export type ChildAnalytics = {`:

```ts
export type LevelProgress = {
  level_id: string;
  title: string;
  state: 'in_progress' | 'completed' | 'locked';
  locked_reason: 'premium' | 'progression' | null;
  passed: boolean;
  lessons_completed: number;
  lessons_total: number;
};

export type ModuleProgress = {
  module_id: string;
  title: string;
  icon: string;
  lessons_completed: number;
  lessons_total: number;
  levels: LevelProgress[];
};
```

And add to the `ChildAnalytics` type (after `badges`):

```ts
  badges: BadgeInfo[];
  modules_progress: ModuleProgress[];
```

- [ ] **Step 2: Write the failing tests**

In `frontend/src/components/ChildAnalytics.test.tsx`, add `modules_progress` to **both** existing mocks so they stay valid:

```ts
// add to MOCK_ANALYTICS:
  modules_progress: [
    {
      module_id: 'mod-1',
      title: 'Stocks 101',
      icon: '📈',
      lessons_completed: 2,
      lessons_total: 4,
      levels: [
        { level_id: 'l1', title: 'Level 1', state: 'completed', locked_reason: null, passed: true, lessons_completed: 2, lessons_total: 2 },
        { level_id: 'l2', title: 'Level 2', state: 'locked', locked_reason: 'premium', passed: false, lessons_completed: 0, lessons_total: 2 },
      ],
    },
  ],
// add to EMPTY_ANALYTICS:
  modules_progress: [],
```

Add the import at the top and new tests at the end of the `describe` block:

```ts
import { axe } from 'vitest-axe';
```

```jsx
  it('shows the module progress disclosure when expanded', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText(/Progress by module/i)).toBeInTheDocument();
    const moduleToggle = screen.getByRole('button', { name: /Stocks 101/i });
    await user.click(moduleToggle);
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    expect(screen.getByText('Level 2')).toBeInTheDocument();
    expect(screen.getByText(/Completed/i)).toBeInTheDocument();
    expect(screen.getByText(/Locked/i)).toBeInTheDocument();
  });

  it('has no axe violations when fully expanded', async () => {
    const user = userEvent.setup();
    const { container } = render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    await user.click(screen.getByRole('button', { name: /Stocks 101/i }));
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npm run test -- ChildAnalytics`
Expected: FAIL — no "Progress by module" text / no module toggle button.

- [ ] **Step 4: Render the disclosure**

In `frontend/src/components/ChildAnalytics.tsx`, add the imports at the top:

```jsx
import { Disclosure } from './a11y/Disclosure';
import type { ChildAnalytics as ChildAnalyticsType, ModuleProgress, LevelProgress } from '@/api/parent';
```

(Replace the existing single `import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';` line with the combined import above.)

Add a small state badge + module block helper above the `ChildAnalytics` component:

```jsx
function LevelStateBadge({ level }: { level: LevelProgress }) {
  if (level.state === 'completed') {
    return (
      <span className="rounded-full bg-success-100 px-2 py-0.5 text-[11px] font-medium text-success-700">
        Completed{level.passed ? ' ✓' : ''}
      </span>
    );
  }
  if (level.state === 'locked') {
    return (
      <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
        🔒 Locked
      </span>
    );
  }
  return (
    <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-medium text-brand-700">
      In progress
    </span>
  );
}

function ModuleProgressBlock({ module }: { module: ModuleProgress }) {
  return (
    <Disclosure label={`${module.icon} ${module.title} — ${module.lessons_completed}/${module.lessons_total}`}>
      <ul className="space-y-1.5">
        {module.levels.map((level) => (
          <li key={level.level_id} className="flex items-center justify-between gap-2 text-xs">
            <span className="text-gray-700">{level.title}</span>
            <span className="flex items-center gap-2">
              <LevelStateBadge level={level} />
              <span className="text-muted-foreground">
                {level.lessons_completed}/{level.lessons_total}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </Disclosure>
  );
}
```

Then, inside the expanded `<div className="mt-2 space-y-3 border-t pt-2">`, add the new section after the badges block (still inside that div):

```jsx
              {analytics.modules_progress.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Progress by module</p>
                  <div className="mt-1 space-y-2">
                    {analytics.modules_progress.map((m) => (
                      <ModuleProgressBlock key={m.module_id} module={m} />
                    ))}
                  </div>
                </div>
              )}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm run test -- ChildAnalytics`
Expected: PASS (all ChildAnalytics tests including axe).

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/api/parent.ts frontend/src/components/ChildAnalytics.tsx frontend/src/components/ChildAnalytics.test.tsx
git commit -m "$(cat <<'EOF'
feat(15.3): parent ChildAnalytics "Progress by module" per-level disclosure

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend lint + full test suite**

Run: `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest -q`
Expected: ruff clean; all tests pass (note the CLAUDE.md gotcha: if a DB-backed test *hangs* ~90s+ it's the local Postgres, not the code — rely on CI).

- [ ] **Step 2: Frontend typecheck + lint + tests + build**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green.

- [ ] **Step 3: Push**

```bash
cd /Users/leeashmore/investikid
git push origin testing
```

- [ ] **Step 4: Report CI status**

Watch the 5 CI jobs (frontend, backend, security, a11y, responsive). Report green/red. No `cap sync` (no native change). Do **not** promote to staging/main — promotion is a separate, gated step.

---

## Self-Review

**1. Spec coverage**
- §1a level-aware pointer → Tasks 1+3. §1b schema fields → Task 2. §1c FE eyebrow → Task 4. §1d backend tests → Task 1 (helper) + Task 3 (4 DB scenarios incl. locked + unlevelled); FE card test → Task 4. ✓
- §2a `modules_progress` service → Task 6. §2b schemas → Task 5. §2c FE disclosure → Task 7. §2d tests → Task 6 (per-level + skip-unlevelled) + Task 7 (render + axe + mock update). ✓
- "Optional: also use helper in next_lesson_service" — deliberately **not** done (spec says leave it untouched if not clean; `next_lesson_service` already works and isn't in scope). ✓
- "no DB migration / no LLM / parent-only / `_apply_hard_filters` unchanged" — honoured (no migration steps; gating block untouched; no child analytics view). ✓

**2. Placeholder scan** — every code step has full code; no TBD/TODO/"handle edge cases". ✓

**3. Type consistency** — `first_actionable_lesson(levels, *, lessons_by_level_ordered, completed_ids, scores, user_is_premium)` identical across Tasks 1, 3. `LevelStateInput(id, order_index, is_premium, pass_threshold)` positional args match the dataclass. Scored-dict keys `_level_id`/`_level_title` written in Task 3 Step 6 and read in Task 3 Step 4. Schema field names (`level_id`, `level_title`, `modules_progress`, `LevelProgressOut`, `ModuleProgressOut`) consistent across BE schema (Tasks 2, 5), BE services (Tasks 3, 6) and FE types (Tasks 4, 7). FE `ModuleProgress`/`LevelProgress` field names match the BE JSON. ✓
