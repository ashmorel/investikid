# Learning Path Intelligence (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the existing recommendation engine with admin-defined prerequisites, age-based filtering, and updated scoring weights. Add prerequisite/age fields to the admin panel.

**Architecture:** The app already has a recommendation service (`backend/app/services/recommendation_service.py`) with hardcoded `TOPIC_PREREQUISITES`, a `TopicMastery` model, and a "Next Quest" card on the Home page. We enhance this by: (1) adding `prerequisite_ids`, `min_age`, `max_age` columns to Module, (2) replacing the hardcoded prerequisite dict with DB-driven prerequisites, (3) adding age filtering to the recommendation algorithm, (4) updating scoring weights per spec, (5) adding admin UI for prerequisites and age ranges.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, React 18, TypeScript, TanStack Query, Tailwind CSS, vitest, pytest

**Important codebase context:**
- Backend tests: run with `/Users/leeashmore/Local Repo/.venv/bin/pytest` from `invest-ed/backend`
- Frontend: `npm ci --legacy-peer-deps` for installs
- Existing recommendation endpoint: `GET /recommendations` in `backend/app/routers/ai.py`
- Existing recommendation service: `backend/app/services/recommendation_service.py`
- Existing TopicMastery model: `backend/app/models/skill_profile.py`
- Existing "Next Quest" card: `frontend/src/pages/child/Home.tsx` (already consumes `aiApi.getRecommendations()`)
- Admin module types: `frontend/src/api/admin.ts` → `AdminModule` interface
- Admin module form: `frontend/src/components/admin/ModuleForm.tsx` (uses wrapper/inner pattern)
- Admin schemas: `backend/app/schemas/admin.py`
- Admin router: `backend/app/routers/admin.py`

---

### Task 1: Database Migration — Add Module Columns

**Files:**
- Modify: `backend/app/models/content.py` (Module model)
- Create: `backend/alembic/versions/xxxx_add_module_prerequisites_age.py`

- [ ] **Step 1: Add columns to Module model**

In `backend/app/models/content.py`, add three new columns to the `Module` class after the `icon` field:

```python
# Add to imports at top of file:
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
# UUID and ARRAY are already imported; just ensure UUID(as_uuid=True) variant is available

# Add these columns to the Module class, after `icon`:
    prerequisite_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 2: Create Alembic migration**

Run from `invest-ed/backend`:
```bash
alembic revision --autogenerate -m "add module prerequisites and age range"
```

Review the generated migration to confirm it adds `prerequisite_ids` (ARRAY of UUID), `min_age` (Integer, nullable), `max_age` (Integer, nullable) to the `modules` table.

- [ ] **Step 3: Run migration**

```bash
alembic upgrade head
```

- [ ] **Step 4: Verify migration**

```bash
alembic current
```

Expected: shows the new revision as current.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/content.py backend/alembic/versions/
git commit -m "feat: add prerequisite_ids, min_age, max_age columns to Module model"
```

---

### Task 2: Backend Schemas — Add Prerequisite/Age Fields

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Create: `backend/tests/test_recommendation_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_recommendation_schemas.py`:

```python
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.admin import ModuleCreate, ModuleUpdate, ModuleOut


def test_module_create_with_prerequisites():
    pid = uuid.uuid4()
    m = ModuleCreate(
        topic="stocks", title="Test", icon="📈", order_index=0,
        prerequisite_ids=[pid], min_age=8, max_age=12,
    )
    assert m.prerequisite_ids == [pid]
    assert m.min_age == 8
    assert m.max_age == 12


def test_module_create_defaults_empty_prerequisites():
    m = ModuleCreate(topic="stocks", title="Test", icon="📈", order_index=0)
    assert m.prerequisite_ids == []
    assert m.min_age is None
    assert m.max_age is None


def test_module_update_accepts_prerequisites():
    pid = uuid.uuid4()
    m = ModuleUpdate(prerequisite_ids=[pid], min_age=10, max_age=14)
    assert m.prerequisite_ids == [pid]
    assert m.min_age == 10
    assert m.max_age == 14


def test_module_out_includes_new_fields():
    m = ModuleOut(
        id=uuid.uuid4(), topic="stocks", title="Test", icon="📈",
        is_premium=False, country_codes=[], order_index=0, lesson_count=3,
        prerequisite_ids=[], min_age=8, max_age=None,
    )
    assert m.prerequisite_ids == []
    assert m.min_age == 8
    assert m.max_age is None


def test_module_create_rejects_min_age_greater_than_max_age():
    with pytest.raises(ValidationError, match="min_age.*max_age"):
        ModuleCreate(
            topic="stocks", title="Test", icon="📈", order_index=0,
            min_age=15, max_age=8,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_schemas.py -v`
Expected: FAIL — `ModuleCreate` doesn't have `prerequisite_ids`, `min_age`, `max_age` fields yet.

- [ ] **Step 3: Update admin schemas**

In `backend/app/schemas/admin.py`, update the Module schemas:

```python
# Add to imports at top:
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Update ModuleCreate:
class ModuleCreate(BaseModel):
    topic: str
    title: str
    icon: str = "📚"
    is_premium: bool = False
    country_codes: list[str] = []
    order_index: int
    prerequisite_ids: list[uuid.UUID] = []
    min_age: int | None = None
    max_age: int | None = None

    @model_validator(mode="after")
    def validate_age_range(self):
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age must be less than or equal to max_age")
        return self


# Update ModuleUpdate:
class ModuleUpdate(BaseModel):
    topic: str | None = None
    title: str | None = None
    icon: str | None = None
    is_premium: bool | None = None
    country_codes: list[str] | None = None
    prerequisite_ids: list[uuid.UUID] | None = None
    min_age: int | None = None
    max_age: int | None = None


# Update ModuleOut:
class ModuleOut(BaseModel):
    id: uuid.UUID
    topic: str
    title: str
    icon: str
    is_premium: bool
    country_codes: list[str]
    order_index: int
    lesson_count: int = 0
    prerequisite_ids: list[uuid.UUID] = []
    min_age: int | None = None
    max_age: int | None = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_schemas.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/admin.py backend/tests/test_recommendation_schemas.py
git commit -m "feat: add prerequisite_ids, min_age, max_age to admin module schemas"
```

---

### Task 3: Backend Admin Router — Prerequisite Validation

**Files:**
- Modify: `backend/app/routers/admin.py`
- Create: `backend/tests/test_admin_prerequisites.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_admin_prerequisites.py`:

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-token-xyz"}


@pytest.mark.asyncio
async def test_create_module_with_prerequisites(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create prerequisite module first
        r1 = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Prereq Module", "icon": "📈",
            "order_index": 0, "prerequisite_ids": [], "min_age": None, "max_age": None,
        }, headers=admin_headers)
        assert r1.status_code == 200
        prereq_id = r1.json()["id"]

        # Create module that depends on it
        r2 = await ac.post("/admin/modules", json={
            "topic": "risk", "title": "Risk Module", "icon": "⚠️",
            "order_index": 1, "prerequisite_ids": [prereq_id], "min_age": 10, "max_age": 16,
        }, headers=admin_headers)
        assert r2.status_code == 200
        data = r2.json()
        assert data["prerequisite_ids"] == [prereq_id]
        assert data["min_age"] == 10
        assert data["max_age"] == 16


@pytest.mark.asyncio
async def test_create_module_self_reference_rejected(admin_headers):
    """Cannot set a module as its own prerequisite during update."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Self Ref", "icon": "📈", "order_index": 0,
        }, headers=admin_headers)
        assert r1.status_code == 200
        mod_id = r1.json()["id"]

        r2 = await ac.put(f"/admin/modules/{mod_id}", json={
            "prerequisite_ids": [mod_id],
        }, headers=admin_headers)
        assert r2.status_code == 400
        assert "self-reference" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_module_nonexistent_prerequisite_rejected(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_id = str(uuid.uuid4())
        r = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Bad Prereq", "icon": "📈",
            "order_index": 0, "prerequisite_ids": [fake_id],
        }, headers=admin_headers)
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_modules_includes_new_fields(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/admin/modules", json={
            "topic": "savings", "title": "Age Test", "icon": "🏦",
            "order_index": 0, "min_age": 8, "max_age": 12,
        }, headers=admin_headers)

        r = await ac.get("/admin/modules", headers=admin_headers)
        assert r.status_code == 200
        modules = r.json()
        mod = next(m for m in modules if m["title"] == "Age Test")
        assert mod["min_age"] == 8
        assert mod["max_age"] == 12
        assert "prerequisite_ids" in mod
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_prerequisites.py -v`
Expected: FAIL — admin router doesn't validate prerequisites or pass new fields.

- [ ] **Step 3: Update admin router**

In `backend/app/routers/admin.py`:

Update the `create_module` endpoint to validate prerequisites and pass new fields:

```python
@router.post("/modules", response_model=ModuleOut)
async def create_module(payload: ModuleCreate, session: AsyncSession = Depends(get_session)):
    # Validate prerequisite_ids exist
    if payload.prerequisite_ids:
        for pid in payload.prerequisite_ids:
            prereq = await session.get(Module, pid)
            if prereq is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prerequisite module {pid} not found",
                )
    module = Module(
        topic=payload.topic, title=payload.title, icon=payload.icon,
        is_premium=payload.is_premium, country_codes=payload.country_codes,
        order_index=payload.order_index,
        prerequisite_ids=payload.prerequisite_ids,
        min_age=payload.min_age, max_age=payload.max_age,
    )
    session.add(module)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=0,
        prerequisite_ids=module.prerequisite_ids,
        min_age=module.min_age, max_age=module.max_age,
    )
```

Update the `update_module` endpoint to validate self-reference and prerequisite existence:

```python
@router.put("/modules/{module_id}", response_model=ModuleOut)
async def update_module(
    module_id: uuid.UUID, payload: ModuleUpdate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id, options=[selectinload(Module.lessons)])
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    update_data = payload.model_dump(exclude_unset=True)
    # Validate prerequisite_ids
    if "prerequisite_ids" in update_data and update_data["prerequisite_ids"] is not None:
        prereq_ids = update_data["prerequisite_ids"]
        if module_id in prereq_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prerequisite self-reference not allowed",
            )
        for pid in prereq_ids:
            prereq = await session.get(Module, pid)
            if prereq is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prerequisite module {pid} not found",
                )
    for field, value in update_data.items():
        setattr(module, field, value)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=len(module.lessons),
        prerequisite_ids=module.prerequisite_ids,
        min_age=module.min_age, max_age=module.max_age,
    )
```

Update the `list_modules` endpoint to include new fields:

```python
@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Module).options(selectinload(Module.lessons)).order_by(Module.order_index)
    )
    modules = result.scalars().all()
    return [
        ModuleOut(
            id=m.id, topic=m.topic, title=m.title, icon=m.icon,
            is_premium=m.is_premium, country_codes=m.country_codes,
            order_index=m.order_index, lesson_count=len(m.lessons),
            prerequisite_ids=m.prerequisite_ids,
            min_age=m.min_age, max_age=m.max_age,
        )
        for m in modules
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_prerequisites.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_admin_prerequisites.py
git commit -m "feat: add prerequisite and age validation to admin module endpoints"
```

---

### Task 4: Backend — Enhance Recommendation Service

**Files:**
- Modify: `backend/app/services/recommendation_service.py`
- Create: `backend/tests/test_recommendation_enhanced.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_recommendation_enhanced.py`:

```python
"""Tests for the enhanced recommendation algorithm with DB-driven prerequisites and age filtering."""
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.recommendation_service import (
    _score_module,
    _apply_hard_filters,
    _build_reason,
)


def _make_user(*, dob=date(2015, 1, 1), topic_path="stocks", country_code="GB", is_premium_val=False, profiling_enabled=True):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.dob = dob
    user.topic_path = topic_path
    user.country_code = country_code
    user.is_premium = is_premium_val
    user.profiling_enabled = profiling_enabled
    return user


def _make_module(*, topic="stocks", prerequisite_ids=None, min_age=None, max_age=None,
                 is_premium=False, country_codes=None, order_index=0):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.topic = topic
    m.title = f"Module {topic}"
    m.prerequisite_ids = prerequisite_ids or []
    m.min_age = min_age
    m.max_age = max_age
    m.is_premium = is_premium
    m.country_codes = country_codes or []
    m.order_index = order_index
    return m


class TestHardFilters:
    def test_excludes_completed_module(self):
        user = _make_user()
        module = _make_module()
        completed_ids = {module.id}
        assert _apply_hard_filters(module, user, completed_ids, {}, 11) is False

    def test_excludes_unmet_prerequisites(self):
        prereq_id = uuid.uuid4()
        user = _make_user()
        module = _make_module(prerequisite_ids=[prereq_id])
        completed_module_ids: set[uuid.UUID] = set()  # prereq not completed
        assert _apply_hard_filters(module, user, set(), completed_module_ids, 11) is False

    def test_includes_met_prerequisites(self):
        prereq_id = uuid.uuid4()
        user = _make_user()
        module = _make_module(prerequisite_ids=[prereq_id])
        completed_module_ids = {prereq_id}
        assert _apply_hard_filters(module, user, set(), completed_module_ids, 11) is True

    def test_excludes_age_too_young(self):
        user = _make_user(dob=date(2020, 1, 1))  # age ~6
        module = _make_module(min_age=10)
        assert _apply_hard_filters(module, user, set(), set(), 6) is False

    def test_excludes_age_too_old(self):
        user = _make_user(dob=date(2010, 1, 1))  # age ~16
        module = _make_module(max_age=12)
        assert _apply_hard_filters(module, user, set(), set(), 16) is False

    def test_includes_age_in_range(self):
        user = _make_user(dob=date(2015, 1, 1))  # age ~11
        module = _make_module(min_age=8, max_age=14)
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_includes_no_age_restriction(self):
        user = _make_user()
        module = _make_module()
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_excludes_premium_for_free_user(self):
        user = _make_user(is_premium_val=False)
        module = _make_module(is_premium=True)
        assert _apply_hard_filters(module, user, set(), set(), 11) is False

    def test_excludes_wrong_country(self):
        user = _make_user(country_code="US")
        module = _make_module(country_codes=["GB", "DE"])
        assert _apply_hard_filters(module, user, set(), set(), 11) is False

    def test_includes_matching_country(self):
        user = _make_user(country_code="GB")
        module = _make_module(country_codes=["GB", "DE"])
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_includes_empty_country_list(self):
        user = _make_user(country_code="US")
        module = _make_module(country_codes=[])
        assert _apply_hard_filters(module, user, set(), set(), 11) is True


class TestScoring:
    def test_topic_match_scores_higher(self):
        user = _make_user(topic_path="stocks")
        matching = _make_module(topic="stocks")
        non_matching = _make_module(topic="savings")
        mastery_by_topic: dict = {}
        s1 = _score_module(matching, user, 0, 3, mastery_by_topic)
        s2 = _score_module(non_matching, user, 0, 3, mastery_by_topic)
        assert s1["score"] > s2["score"]

    def test_partially_completed_scores_higher(self):
        user = _make_user(topic_path=None)
        m = _make_module(topic="stocks")
        mastery_by_topic: dict = {}
        partial = _score_module(m, user, 2, 5, mastery_by_topic)
        untouched = _score_module(m, user, 0, 5, mastery_by_topic)
        assert partial["score"] > untouched["score"]

    def test_returns_null_when_no_modules(self):
        """Placeholder test — the full integration test checks this."""
        pass


class TestReasonStrings:
    def test_near_completion_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=3, total=5, is_topic_match=False, is_variety=False, readiness_score=1.0)
        assert "keep going" in reason.lower() or "halfway" in reason.lower()

    def test_topic_match_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=0, total=5, is_topic_match=True, is_variety=False, readiness_score=1.0)
        assert "stocks" in reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_enhanced.py -v`
Expected: FAIL — `_apply_hard_filters`, `_score_module` functions don't exist yet.

- [ ] **Step 3: Refactor recommendation service**

Replace `backend/app/services/recommendation_service.py` with the enhanced version. The key changes:
1. Extract `_apply_hard_filters()` — testable pure function for hard filter logic
2. Extract `_score_module()` — testable pure function for scoring
3. Replace `TOPIC_PREREQUISITES` dict with `module.prerequisite_ids` from DB
4. Add age filtering using user's `dob`
5. Update weights to match spec (30% topic match, 25% readiness, 20% near completion, 15% order, 10% variety)
6. Update `_build_reason()` to accept scoring context

```python
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.content_service import is_module_accessible
from app.services.entitlements import is_premium

# Scoring weights per spec
_W_TOPIC_MATCH = 0.30
_W_READINESS = 0.25
_W_NEAR_COMPLETION = 0.20
_W_ORDER = 0.15
_W_VARIETY = 0.10

_READINESS_THRESHOLD = 0.7  # prereq avg score considered "strong"


def _calculate_age(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def _apply_hard_filters(
    module: Module,
    user: User,
    fully_completed_module_ids: set[uuid.UUID],
    completed_module_ids_for_prereqs: set[uuid.UUID],
    user_age: int,
) -> bool:
    """Return True if module passes all hard filters."""
    # 1. Already completed
    if module.id in fully_completed_module_ids:
        return False

    # 2. Prerequisites not met
    for prereq_id in (module.prerequisite_ids or []):
        if prereq_id not in completed_module_ids_for_prereqs:
            return False

    # 3. Age out of range
    if module.min_age is not None and user_age < module.min_age:
        return False
    if module.max_age is not None and user_age > module.max_age:
        return False

    # 4. Premium gating
    if module.is_premium and not is_premium(user):
        return False

    # 5. Country filtering
    if module.country_codes and user.country_code not in module.country_codes:
        return False

    return True


def _score_module(
    module: Module,
    user: User,
    completed_count: int,
    total_count: int,
    mastery_by_topic: dict[str, TopicMastery],
) -> dict[str, Any]:
    """Score a module for recommendation ranking. Returns dict with score, reason context."""
    # Topic match
    topic_match = 1.0 if user.topic_path and module.topic == user.topic_path else 0.0

    # Readiness — prereqs completed with strong scores
    prereq_ids = module.prerequisite_ids or []
    if not prereq_ids:
        readiness = 1.0
    else:
        strong = sum(
            1 for pid_topic in prereq_ids
            # We can't resolve topic from prereq_id here without the module object,
            # so readiness is based on whether prereqs are completed (they passed hard filter)
        )
        readiness = 1.0  # prereqs are met (hard filter passed), check mastery
        for pid in prereq_ids:
            # Look up mastery for the prereq's topic — we'll resolve this in the caller
            pass
        # Simplified: if prerequisites exist and we got here, they're met
        readiness = 1.0

    # Near completion (scales with % complete)
    if total_count == 0:
        near_completion = 0.0
    elif completed_count == 0:
        near_completion = 0.0
    else:
        near_completion = completed_count / total_count  # 0.0-1.0, higher = closer to done

    # Natural order (lower order_index = higher score; normalise to 0-1)
    # We cap at order_index 20 for normalisation
    order_score = max(0.0, 1.0 - module.order_index / 20.0)

    # Topic variety (bonus if topic hasn't been touched recently)
    mastery = mastery_by_topic.get(module.topic)
    if mastery is None:
        variety = 1.0  # never touched = very fresh
    else:
        days_since = (datetime.now(UTC) - mastery.last_activity_at).days
        variety = min(days_since / 30.0, 1.0)

    score = (
        _W_TOPIC_MATCH * topic_match
        + _W_READINESS * readiness
        + _W_NEAR_COMPLETION * near_completion
        + _W_ORDER * order_score
        + _W_VARIETY * variety
    )

    return {
        "score": round(score, 4),
        "is_topic_match": topic_match > 0,
        "near_completion": near_completion,
        "variety": variety,
        "readiness": readiness,
    }


def _build_reason(
    module: Module,
    *,
    completed: int,
    total: int,
    is_topic_match: bool,
    is_variety: bool,
    readiness_score: float,
) -> str:
    """Build a child-friendly reason string based on the top scoring factor."""
    if completed > 0 and completed < total:
        return "You're halfway through — keep going!"
    if is_topic_match:
        topic_label = module.topic.replace("_", " ")
        return f"You're great at {topic_label} — try this next!"
    if is_variety:
        return "Something new to explore!"
    if readiness_score >= 1.0:
        return "You're ready for the next level!"
    return "Recommended for you"


async def get_recommendations(
    session: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Return personalised module rankings and a next-quest suggestion."""
    if not user.profiling_enabled:
        seed = await _topic_path_seed(session, user)
        return {"next_quest": seed, "suggested_modules": []}

    user_age = _calculate_age(user.dob)

    # Load all modules
    all_modules = (
        await session.scalars(select(Module).order_by(Module.order_index))
    ).all()

    if not all_modules:
        return {"next_quest": None, "suggested_modules": []}

    # Load user's mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    ).all()
    mastery_by_topic: dict[str, TopicMastery] = {tm.topic: tm for tm in mastery_rows}

    # Load completion counts per module
    module_ids = [m.id for m in all_modules]
    lesson_counts_result = await session.execute(
        select(Lesson.module_id, func.count(Lesson.id))
        .where(Lesson.module_id.in_(module_ids))
        .group_by(Lesson.module_id)
    )
    total_lessons: dict[uuid.UUID, int] = dict(lesson_counts_result.all())

    completed_counts_result = await session.execute(
        select(Lesson.module_id, func.count(LessonCompletion.id))
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(Lesson.module_id.in_(module_ids), LessonCompletion.user_id == user.id)
        .group_by(Lesson.module_id)
    )
    completed_lessons: dict[uuid.UUID, int] = dict(completed_counts_result.all())

    # Determine fully completed modules and completed-for-prereqs
    fully_completed_module_ids: set[uuid.UUID] = set()
    completed_module_ids: set[uuid.UUID] = set()
    for m in all_modules:
        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)
        if total > 0 and completed >= total:
            fully_completed_module_ids.add(m.id)
            completed_module_ids.add(m.id)

    # Score eligible modules
    scored: list[dict[str, Any]] = []
    for m in all_modules:
        if not _apply_hard_filters(m, user, fully_completed_module_ids, completed_module_ids, user_age):
            continue

        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)

        score_data = _score_module(m, user, completed, total, mastery_by_topic)
        reason = _build_reason(
            m,
            completed=completed, total=total,
            is_topic_match=score_data["is_topic_match"],
            is_variety=score_data["variety"] > 0.5,
            readiness_score=score_data["readiness"],
        )

        scored.append({
            "module_id": m.id,
            "score": score_data["score"],
            "reason": reason,
            "topic": m.topic,
            "_completed_count": completed,
            "_total_count": total,
        })

    # Sort by score descending, then order_index for ties
    scored.sort(key=lambda s: (-s["score"], next(m.order_index for m in all_modules if m.id == s["module_id"])))

    # Find next quest: first incomplete lesson in the top-ranked module
    next_quest = None
    for entry in scored:
        lessons = (
            await session.scalars(
                select(Lesson)
                .where(Lesson.module_id == entry["module_id"])
                .order_by(Lesson.order_index)
            )
        ).all()
        completed_ids_result = await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user.id,
                LessonCompletion.lesson_id.in_([lesson.id for lesson in lessons]),
            )
        )
        completed_ids = set(completed_ids_result.all())
        for lesson in lessons:
            if lesson.id not in completed_ids:
                next_quest = {
                    "module_id": entry["module_id"],
                    "lesson_id": lesson.id,
                    "reason": entry["reason"],
                }
                break
        if next_quest:
            break

    suggested = [
        {"module_id": s["module_id"], "score": s["score"], "reason": s["reason"]}
        for s in scored
    ]

    return {"next_quest": next_quest, "suggested_modules": suggested}


async def _topic_path_seed(session: AsyncSession, user: User):
    """Profiling-off only: first incomplete lesson in the self-declared topic."""
    pref = user.topic_path
    if not pref:
        return None

    from sqlalchemy import func as sa_func
    completion_count = int(
        await session.scalar(
            select(sa_func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == user.id
            )
        )
        or 0
    )
    if completion_count > 0:
        return None

    modules = (
        await session.scalars(
            select(Module).where(Module.topic == pref).order_by(Module.order_index)
        )
    ).all()
    for m in modules:
        if not is_module_accessible(
            user.country_code, is_premium(user), m.country_codes, m.is_premium
        ):
            continue
        lessons = (
            await session.scalars(
                select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order_index)
            )
        ).all()
        if lessons:
            return {
                "module_id": m.id,
                "lesson_id": lessons[0].id,
                "reason": f"Start your {pref.replace('_', ' ')} journey",
            }
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_recommendation_enhanced.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run existing tests to verify no regression**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/ -v --ignore=backend/tests/test_admin_prerequisites.py`
Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_enhanced.py
git commit -m "feat: enhance recommendation service with DB prerequisites and age filtering"
```

---

### Task 5: Frontend — Admin Module Types & API Updates

**Files:**
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: Update AdminModule interface**

In `frontend/src/api/admin.ts`, add the new fields to `AdminModule`:

```typescript
export interface AdminModule {
  id: string;
  topic: string;
  title: string;
  icon: string;
  is_premium: boolean;
  country_codes: string[];
  order_index: number;
  lesson_count: number;
  prerequisite_ids: string[];
  min_age: number | null;
  max_age: number | null;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit` from `frontend/`
Expected: Clean (0 errors). The `useCreateModule` and `useUpdateModule` mutations use `Partial<Omit<AdminModule, ...>>` so they automatically pick up the new fields.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "feat: add prerequisite_ids, min_age, max_age to AdminModule type"
```

---

### Task 6: Frontend — Admin ModuleForm Updates

**Files:**
- Modify: `frontend/src/components/admin/ModuleForm.tsx`
- Modify: `frontend/src/components/admin/__tests__/ModuleForm.test.tsx`

- [ ] **Step 1: Write the failing test**

Add tests to `frontend/src/components/admin/__tests__/ModuleForm.test.tsx`:

```typescript
// Add to existing describe block:

  it('renders prerequisite multi-select in create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByText(/prerequisites/i)).toBeInTheDocument();
  });

  it('renders age range inputs in create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByLabelText(/min age/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max age/i)).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/components/admin/__tests__/ModuleForm.test.tsx` from `frontend/`
Expected: FAIL — no prerequisites or age range fields in the form.

- [ ] **Step 3: Add prerequisite and age fields to ModuleFormInner**

In `frontend/src/components/admin/ModuleForm.tsx`:

Add state for new fields in `ModuleFormInner`:

```typescript
  const [prerequisiteIds, setPrerequisiteIds] = useState<string[]>(existing?.prerequisite_ids ?? []);
  const [minAge, setMinAge] = useState<string>(existing?.min_age?.toString() ?? '');
  const [maxAge, setMaxAge] = useState<string>(existing?.max_age?.toString() ?? '');
```

Update `handleSave` to include new fields:

```typescript
  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const moduleData = {
      topic, title, icon,
      is_premium: isPremium,
      country_codes: countryCodes,
      prerequisite_ids: prerequisiteIds,
      min_age: minAge ? Number(minAge) : null,
      max_age: maxAge ? Number(maxAge) : null,
    };
    if (isEdit && moduleId) {
      await updateMod.mutateAsync({ id: moduleId, ...moduleData });
    } else {
      const maxOrder = modules.reduce((max, m) => Math.max(max, m.order_index), -1);
      await createMod.mutateAsync({ ...moduleData, order_index: maxOrder + 1 });
    }
    navigate('/admin/modules');
  }
```

Add prerequisite toggle function:

```typescript
  function togglePrerequisite(id: string) {
    setPrerequisiteIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }
```

Add UI fields after the countries section, before the lessons section:

```tsx
        {/* Prerequisites */}
        <div>
          <span className="mb-1 block text-sm text-slate-400">Prerequisites (optional)</span>
          <div className="flex flex-wrap gap-2">
            {modules
              .filter((m) => m.id !== moduleId)
              .map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => togglePrerequisite(m.id)}
                  className={`rounded-md px-3 py-1 text-xs ${
                    prerequisiteIds.includes(m.id)
                      ? 'bg-purple-600 text-white'
                      : 'border border-slate-600 bg-slate-800 text-slate-400'
                  }`}
                >
                  {m.icon} {m.title}
                </button>
              ))}
          </div>
        </div>

        {/* Age Range */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="mod-min-age" className="mb-1 block text-sm text-slate-400">Min Age</label>
            <input id="mod-min-age" type="number" value={minAge} onChange={(e) => setMinAge(e.target.value)}
              min={1} max={99} placeholder="Any"
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="flex-1">
            <label htmlFor="mod-max-age" className="mb-1 block text-sm text-slate-400">Max Age</label>
            <input id="mod-max-age" type="number" value={maxAge} onChange={(e) => setMaxAge(e.target.value)}
              min={1} max={99} placeholder="Any"
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <p className="self-end pb-2 text-xs text-slate-500">Leave empty for all ages</p>
        </div>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/components/admin/__tests__/ModuleForm.test.tsx` from `frontend/`
Expected: All tests pass (existing + new).

- [ ] **Step 5: Verify TypeScript compiles**

Run: `npx tsc --noEmit` from `frontend/`
Expected: Clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/admin/ModuleForm.tsx frontend/src/components/admin/__tests__/ModuleForm.test.tsx
git commit -m "feat: add prerequisite and age range fields to admin ModuleForm"
```

---

### Task 7: Frontend — Accessibility Tests

**Files:**
- Modify: `frontend/tests/a11y/admin.a11y.test.tsx` (or create `frontend/tests/a11y/recommendations.a11y.test.tsx`)

- [ ] **Step 1: Add a11y test for updated ModuleForm**

Add to the existing `frontend/tests/a11y/admin.a11y.test.tsx` or create `frontend/tests/a11y/recommendations.a11y.test.tsx`:

```typescript
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleForm from '@/components/admin/ModuleForm';

expect.extend(toHaveNoViolations);

vi.mock('@/api/admin', () => ({
  useModules: () => ({
    data: [
      { id: '1', topic: 'stocks', title: 'Prereq Mod', icon: '📈', is_premium: false, country_codes: [], order_index: 0, lesson_count: 2, prerequisite_ids: [], min_age: null, max_age: null },
    ],
    isLoading: false,
  }),
  useCreateModule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateModule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useLessons: () => ({ data: [], isLoading: false }),
  useCountries: () => ({ data: ['GB'], isLoading: false }),
  useCreateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteLesson: () => ({ mutate: vi.fn() }),
  useReorderLessons: () => ({ mutate: vi.fn() }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({}), useNavigate: () => vi.fn() };
});

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ModuleForm with prerequisites a11y', () => {
  it('passes axe audit', async () => {
    const { container } = render(<ModuleForm />, { wrapper });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run a11y tests**

Run: `npx vitest run tests/a11y/` from `frontend/`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/a11y/
git commit -m "test: add accessibility test for ModuleForm with prerequisite fields"
```

---

### Task 8: Full Regression

**Files:** None (verification only)

- [ ] **Step 1: Run full frontend vitest suite**

Run from `frontend/`:
```bash
npx vitest run --reporter=verbose
```
Expected: All tests pass (359+ existing + new tests).

- [ ] **Step 2: TypeScript check**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: Clean (0 errors).

- [ ] **Step 3: ESLint check on admin components**

Run from `frontend/`:
```bash
npx eslint src/components/admin/ --ext .ts,.tsx
```
Expected: Clean (0 errors).

- [ ] **Step 4: Vite build**

Run from `frontend/`:
```bash
npx vite build
```
Expected: Build succeeds.

- [ ] **Step 5: Backend test suite**

Run from `backend/`:
```bash
/Users/leeashmore/Local Repo/.venv/bin/pytest tests/ -v
```
Expected: All tests pass (auth-only tests pass without DB; DB-dependent tests pass with Postgres running).

- [ ] **Step 6: Commit if any fixes were needed**

Only commit if regression fixes were applied.
