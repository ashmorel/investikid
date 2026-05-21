# Premium Content & AI Engagement Implementation Plan (Sub-project 4b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AI quiz content difficulty-adaptive and non-repetitive, turn the dead `topic_path` field into a self-declared starting-interest signal, and deepen the premium tier — without new per-child data and without weakening AADC profiling-off defaults.

**Architecture:** A new `content_variety_service.resolve_variant()` is the single decision point for which quiz variant a child gets (rung × ordinal × tier pool). `GeneratedContent` gains a `variant_key` column so the cache stores multiple variants per `(lesson, concept, model)`. `ai_content_service.generate_practice_quiz()` resolves a variant before its cache lookup; all downstream behaviour (LLM call, 4a `moderate_output`, deterministic `_fallback`) is unchanged. `topic_path` becomes constrained to the `ModuleTopic` set and drives module-list ordering plus a profiling-off first-quest seed.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, pytest (`asyncio_mode=auto`), React + TS + Vite + @tanstack/react-query.

**Spec:** `docs/superpowers/specs/2026-05-19-premium-content-ai-engagement-design.md`

**Baseline invariant:** the full backend suite (currently 302) must stay green after every task. Frontend build/lint must stay green.

---

## File Structure

**Backend create:**
- `backend/app/services/content_variety_service.py` — `VariantSpec` dataclass + `resolve_variant()`; the only place rung/ordinal/pool logic lives.
- `backend/alembic/versions/<rev1>_add_generated_content_variant_key.py` — variant_key column + reworked unique constraint + backfill.
- `backend/alembic/versions/<rev2>_premium_paycheque_module.py` — flip one seeded module to premium for existing DBs.
- `backend/tests/test_content_variety_service.py` — rung matrix, ordinal, pool, AADC no-query.
- `backend/tests/test_topic_path_validation.py` — schema validation parity across signup + preferences.

**Backend modify:**
- `backend/app/schemas/content.py` — export `TOPIC_PATH_VALUES` derived from `ModuleTopic`.
- `backend/app/schemas/user.py` — `topic_path` validator → membership in `TOPIC_PATH_VALUES`.
- `backend/app/schemas/auth.py` — same validator (parity).
- `backend/app/schemas/ai.py` — `PracticeResponse.variant_rung: str | None = None`.
- `backend/app/models/generated_content.py` — add `variant_key` column + new unique constraint.
- `backend/app/services/ai_content_service.py` — `generate_practice_quiz` gains `user: User`, routes through `resolve_variant`, variant-aware cache + fallback chain, sets `variant_rung`.
- `backend/app/routers/ai.py` — pass `user=current_user` into `generate_practice_quiz`.
- `backend/app/routers/content.py` — `list_modules` stable reorder by `topic_path`.
- `backend/app/services/recommendation_service.py` — profiling-off first-quest seed.
- `backend/app/seed/content.py` — refresh `is_premium` on existing modules; mark "Your First Paycheque" premium.
- `backend/tests/test_ai_content_service.py` — pass the new `user` arg; add variant/fallback cases.

**Frontend modify:**
- `frontend/src/pages/child/Signup.tsx` — `TOPIC_PATHS` → 9 `ModuleTopic` values + "No preference" (empty → null).
- `frontend/src/api/ai.ts` — `PracticeQuiz` type gains optional `variant_rung`.
- `frontend/src/api/auth.ts` — `updatePreferences` call (if absent) for the interest editor.
- `frontend/src/components/child/ProfileMenu.tsx` — small interest editor dialog → `PATCH /users/me`.
- `frontend/src/components/child/lesson/PracticeQuiz.tsx` — optional rung badge when `variant_rung` not `core`.

---

## Task 1: Constrain `topic_path` to the ModuleTopic set

**Files:**
- Modify: `backend/app/schemas/content.py`
- Modify: `backend/app/schemas/user.py`
- Modify: `backend/app/schemas/auth.py:84-90`
- Test: `backend/tests/test_topic_path_validation.py` (create)

**Context:** `topic_path` is currently validated by regex `_TOPIC_RE = ^[a-z0-9_/-]+$` (max 200) in BOTH `schemas/user.py` (`UpdatePreferencesRequest`) and `schemas/auth.py` (`RegisterRequest`). The spec requires it to be one of the 9 `ModuleTopic` literals or null. Empty string means "no preference" and must normalise to `None`. The DB column is `String(20)`; longest topic `entrepreneurship` (16) fits.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_topic_path_validation.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.user import UpdatePreferencesRequest
from app.schemas.auth import RegisterRequest
from app.schemas.content import TOPIC_PATH_VALUES


def test_topic_path_values_are_the_nine_module_topics():
    assert TOPIC_PATH_VALUES == frozenset({
        "stocks", "savings", "real_estate", "budgeting", "risk",
        "crypto", "taxes", "debt", "entrepreneurship",
    })


def test_preferences_accepts_valid_topic():
    assert UpdatePreferencesRequest(topic_path="crypto").topic_path == "crypto"


def test_preferences_empty_string_normalises_to_none():
    assert UpdatePreferencesRequest(topic_path="").topic_path is None


def test_preferences_none_stays_none():
    assert UpdatePreferencesRequest(topic_path=None).topic_path is None


def test_preferences_rejects_legacy_value():
    with pytest.raises(ValidationError):
        UpdatePreferencesRequest(topic_path="investing-101")


def test_register_rejects_invalid_topic_and_accepts_valid():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="a@b.com", username="kiddo", password="Abcd1234!",
            dob="2014-01-01", country_code="GB", currency_code="GBP",
            topic_path="not-a-topic", policy_version_accepted="v1",
        )
    ok = RegisterRequest(
        email="a@b.com", username="kiddo", password="Abcd1234!",
        dob="2014-01-01", country_code="GB", currency_code="GBP",
        topic_path="savings", policy_version_accepted="v1",
    )
    assert ok.topic_path == "savings"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_topic_path_validation.py -q`
Expected: FAIL — `ImportError: cannot import name 'TOPIC_PATH_VALUES'`.

- [ ] **Step 3: Add the shared constant**

In `backend/app/schemas/content.py`, directly after the `ModuleTopic` definition, add:

```python
from typing import get_args

TOPIC_PATH_VALUES: frozenset[str] = frozenset(get_args(ModuleTopic))
```

- [ ] **Step 4: Replace the validator in `schemas/user.py`**

In `backend/app/schemas/user.py`: remove the `_TOPIC_RE` regex constant and replace the `validate_topic` validator on `UpdatePreferencesRequest` with a normalise-and-membership check. Add the import `from app.schemas.content import TOPIC_PATH_VALUES` at the top. Replace the existing `topic_path` field + `validate_topic` method with:

```python
    topic_path: str | None = Field(default=None, max_length=20)

    @field_validator("topic_path", mode="before")
    @classmethod
    def normalise_topic(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("topic_path")
    @classmethod
    def validate_topic(cls, v):
        if v is None:
            return v
        if v not in TOPIC_PATH_VALUES:
            raise ValueError("topic_path must be one of the known learning topics")
        return v
```

Delete the now-unused `_TOPIC_RE = re.compile(...)` line. If `re` is no longer referenced anywhere else in the file, remove the `import re`.

- [ ] **Step 5: Apply the identical validator in `schemas/auth.py`**

In `backend/app/schemas/auth.py`, add `from app.schemas.content import TOPIC_PATH_VALUES` to the imports. Change the `topic_path` field on `RegisterRequest` to `Field(default=None, max_length=20)` and replace its `validate_topic` validator (around lines 84-90) with the same two validators (`normalise_topic` mode="before" + `validate_topic`) shown in Step 4. Remove the auth-local topic regex if present and its now-unused `import re` only if `re` is unreferenced.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_topic_path_validation.py -q`
Expected: PASS (6 tests).

- [ ] **Step 7: Run the auth + users regression**

Run: `cd backend && python -m pytest tests/test_auth.py tests/test_users.py -q`
Expected: PASS (no regressions; if a fixture used a legacy `topic_path` like `"core"`, update that fixture to `"savings"`).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/content.py backend/app/schemas/user.py backend/app/schemas/auth.py backend/tests/test_topic_path_validation.py
git commit -m "feat(4b): constrain topic_path to the ModuleTopic set"
```

---

## Task 2: Add `variant_key` to GeneratedContent (model + migration)

**Files:**
- Modify: `backend/app/models/generated_content.py`
- Create: `backend/alembic/versions/<rev1>_add_generated_content_variant_key.py`
- Test: `backend/tests/test_generated_content_variant_key.py` (create)

**Context:** `GeneratedContent` currently has unique `(lesson_id, concept, model_used)` named `uq_generated_content_lesson_concept_model`. We add `variant_key String(16) NOT NULL` and change the unique constraint to include it. Existing rows backfill to `"core:0"` so already-cached quizzes keep serving unchanged. Current alembic head is `c9bdf248d9b3` (verified via `python -m alembic heads`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_generated_content_variant_key.py`:

```python
import pytest

from app.models.generated_content import GeneratedContent

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_model_has_variant_key_column():
    cols = GeneratedContent.__table__.columns
    assert "variant_key" in cols
    assert cols["variant_key"].nullable is False


def test_unique_constraint_includes_variant_key():
    uniques = [
        c for c in GeneratedContent.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    ]
    cols = {tuple(sorted(col.name for col in u.columns)) for u in uniques}
    assert ("concept", "lesson_id", "model_used", "variant_key") in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_generated_content_variant_key.py -q`
Expected: FAIL — `assert "variant_key" in cols` fails.

- [ ] **Step 3: Update the model**

In `backend/app/models/generated_content.py`, change `__table_args__` and add the column:

```python
    __table_args__ = (
        UniqueConstraint(
            "lesson_id", "concept", "model_used", "variant_key",
            name="uq_generated_content_lesson_concept_model_variant",
        ),
    )
```

Add this column after `model_used`:

```python
    variant_key: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="core:0"
    )
```

- [ ] **Step 4: Create the migration**

First get the current head:

Run: `cd backend && python -m alembic heads`
Expected: `c9bdf248d9b3 (head)`

Create `backend/alembic/versions/a1b2c3d4e5f6_add_generated_content_variant_key.py`:

```python
"""add variant_key to generated_content (4b content variety)

Revision ID: a1b2c3d4e5f6
Revises: c9bdf248d9b3
Create Date: 2026-05-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c9bdf248d9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_UQ = "uq_generated_content_lesson_concept_model"
_NEW_UQ = "uq_generated_content_lesson_concept_model_variant"


def upgrade() -> None:
    op.add_column(
        "generated_content",
        sa.Column("variant_key", sa.String(length=16),
                  nullable=False, server_default="core:0"),
    )
    op.drop_constraint(_OLD_UQ, "generated_content", type_="unique")
    op.create_unique_constraint(
        _NEW_UQ, "generated_content",
        ["lesson_id", "concept", "model_used", "variant_key"],
    )


def downgrade() -> None:
    op.drop_constraint(_NEW_UQ, "generated_content", type_="unique")
    op.create_unique_constraint(
        _OLD_UQ, "generated_content",
        ["lesson_id", "concept", "model_used"],
    )
    op.drop_column("generated_content", "variant_key")
```

If `python -m alembic heads` returned something other than `c9bdf248d9b3`, set `down_revision` to that value instead.

- [ ] **Step 5: Apply the migration against the test DB and verify**

Run: `cd backend && python -m alembic upgrade head`
Expected: completes with no error; `INFO ... Running upgrade c9bdf248d9b3 -> a1b2c3d4e5f6`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_generated_content_variant_key.py -q`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/generated_content.py backend/alembic/versions/a1b2c3d4e5f6_add_generated_content_variant_key.py backend/tests/test_generated_content_variant_key.py
git commit -m "feat(4b): add variant_key to generated_content cache"
```

---

## Task 3: `content_variety_service.resolve_variant`

**Files:**
- Create: `backend/app/services/content_variety_service.py`
- Test: `backend/tests/test_content_variety_service.py` (create)

**Context:** The single decision point. Signature: `resolve_variant(session, user, lesson, concept) -> VariantSpec`. Rules from the spec:

- `premium = is_premium(user)`; `pool_size = 3 if premium else 1`.
- **Rung:** if not premium → `"core"`. Else if `not user.profiling_enabled` → `"core"` (and the score/mastery queries MUST NOT run — AADC). Else derive from the child's single `LessonCompletion.score` for this lesson and `TopicMastery` for the lesson's topic:
  - no completion row → `"core"`
  - `score < 0.5` → `"easier"`
  - `score >= 0.8` AND `TopicMastery.mastery_score >= 0.5` → `"harder"`
  - otherwise → `"core"`
- **Ordinal:** `attempt_count = count(LessonCompletion for this user+lesson)` (0 or 1, since `(user_id, lesson_id)` is unique); `ordinal = attempt_count % pool_size`. Free pool=1 ⇒ ordinal always 0. This is the intended data-minimised semantics: a child sees one variant before completing a lesson and (premium only) a different one after; cross-session "seen" tracking is deliberately out of scope.
- `lesson`'s topic is read via `session.get(Module, lesson.module_id)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_content_variety_service.py`:

```python
import uuid
import pytest

from app.models.content import Module, Lesson, LessonCompletion
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.content_variety_service import resolve_variant, VariantSpec

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk_lesson(db_session) -> Lesson:
    m = Module(topic="savings", title="T", country_codes=[], is_premium=False, order_index=0, icon="🏦")
    db_session.add(m)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, type="quiz", content_json={"question": "q"}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _mk_user(db_session, *, premium: bool, profiling: bool) -> User:
    u = User(
        username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
        dob=__import__("datetime").date(2014, 1, 1), country_code="GB",
        currency_code="GBP", is_premium=premium, profiling_enabled=profiling,
        email=f"{uuid.uuid4().hex[:8]}@e.com",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_free_user_always_core_pool_one(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=False, profiling=True)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec == VariantSpec(rung="core", ordinal=0, pool_size=1)


async def test_premium_profiling_off_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=False)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"
    assert spec.pool_size == 3


async def test_premium_profiling_on_no_completion_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"
    assert spec.ordinal == 0


async def test_premium_low_score_is_easier_and_ordinal_rotates(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.2))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "easier"
    assert spec.ordinal == 1  # 1 completion % pool 3


async def test_premium_high_score_with_mastery_is_harder(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.9))
    db_session.add(TopicMastery(user_id=user.id, topic="savings", mastery_score=0.7))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "harder"


async def test_premium_high_score_without_mastery_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.9))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"


async def test_profiling_off_does_not_query_score(db_session, monkeypatch):
    """AADC: profiling-off path must not read completion score / mastery."""
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=False)
    import app.services.content_variety_service as cvs
    calls = {"n": 0}
    real = cvs._latest_completion_score

    async def spy(*a, **k):
        calls["n"] += 1
        return await real(*a, **k)

    monkeypatch.setattr(cvs, "_latest_completion_score", spy)
    await resolve_variant(db_session, user, lesson, "concept")
    assert calls["n"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_content_variety_service.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.content_variety_service`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/content_variety_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.entitlements import is_premium

PREMIUM_POOL_SIZE = 3
FREE_POOL_SIZE = 1
_LOW_SCORE = 0.5
_HIGH_SCORE = 0.8
_MASTERY_THRESHOLD = 0.5

_RUNGS = ("easier", "core", "harder")


@dataclass(frozen=True)
class VariantSpec:
    rung: str
    ordinal: int
    pool_size: int

    @property
    def variant_key(self) -> str:
        return f"{self.rung}:{self.ordinal}"


async def _attempt_count(session: AsyncSession, user_id, lesson_id) -> int:
    return int(
        await session.scalar(
            select(func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.lesson_id == lesson_id,
            )
        )
        or 0
    )


async def _latest_completion_score(session: AsyncSession, user_id, lesson_id):
    return await session.scalar(
        select(LessonCompletion.score)
        .where(
            LessonCompletion.user_id == user_id,
            LessonCompletion.lesson_id == lesson_id,
        )
        .order_by(LessonCompletion.completed_at.desc())
        .limit(1)
    )


async def _topic_mastery(session: AsyncSession, user_id, topic) -> float:
    score = await session.scalar(
        select(TopicMastery.mastery_score).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic == topic,
        )
    )
    return float(score) if score is not None else 0.0


async def resolve_variant(
    session: AsyncSession,
    user: User,
    lesson: Lesson,
    concept: str,
) -> VariantSpec:
    """Decide which quiz variant this child gets. DB reads only; never mutates."""
    premium = is_premium(user)
    pool_size = PREMIUM_POOL_SIZE if premium else FREE_POOL_SIZE

    attempt_count = await _attempt_count(session, user.id, lesson.id)
    ordinal = attempt_count % pool_size

    # Free tier: laddering disabled, single core variant.
    if not premium:
        return VariantSpec(rung="core", ordinal=ordinal, pool_size=pool_size)

    # AADC: no behavioural inference unless profiling is explicitly enabled.
    if not user.profiling_enabled:
        return VariantSpec(rung="core", ordinal=ordinal, pool_size=pool_size)

    score = await _latest_completion_score(session, user.id, lesson.id)
    if score is None:
        rung = "core"
    elif score < _LOW_SCORE:
        rung = "easier"
    elif score >= _HIGH_SCORE:
        module = await session.get(Module, lesson.module_id)
        topic = module.topic if module else ""
        mastery = await _topic_mastery(session, user.id, topic)
        rung = "harder" if mastery >= _MASTERY_THRESHOLD else "core"
    else:
        rung = "core"

    return VariantSpec(rung=rung, ordinal=ordinal, pool_size=pool_size)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_content_variety_service.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/content_variety_service.py backend/tests/test_content_variety_service.py
git commit -m "feat(4b): content_variety_service.resolve_variant"
```

---

## Task 4: Wire `generate_practice_quiz` to the variant seam

**Files:**
- Modify: `backend/app/services/ai_content_service.py`
- Modify: `backend/app/routers/ai.py:50-58`
- Modify: `backend/app/schemas/ai.py`
- Modify: `backend/tests/test_ai_content_service.py`
- Test: `backend/tests/test_ai_content_variant.py` (create)

**Context:** `generate_practice_quiz(session, lesson, *, topic, concept, premium, wrong_answer_index=None)` must (a) take `user: User`, (b) call `resolve_variant`, (c) key the cache lookup AND the stored row on `variant_key`, (d) on cache miss generate (LLM + existing 4a `moderate_output` unchanged), (e) on generation/moderation failure OR pool exhaustion fall back to a random already-cached *safe* variant for that `(lesson, concept, model)`, then finally the existing deterministic `_fallback(content)`, (f) attach `variant_rung` to the returned dict on every path. Only caller is `routers/ai.py::practice_quiz` (has `current_user`). `tests/test_ai_content_service.py` already calls this function and must be updated for the new arg.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ai_content_variant.py`:

```python
import uuid
import datetime
import pytest

from app.models.content import Module, Lesson, LessonCompletion
from app.models.generated_content import GeneratedContent
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services import ai_content_service
from app.services.ai_content_service import generate_practice_quiz

pytestmark = pytest.mark.asyncio(loop_scope="session")

_QUIZ = {"question": "What is saving?", "choices": ["A", "B", "C"],
         "answer_index": 0, "explanation": "Because."}


async def _setup(db_session, *, premium, profiling):
    m = Module(topic="savings", title="S", country_codes=[], is_premium=False, order_index=0, icon="🏦")
    db_session.add(m); await db_session.flush()
    lesson = Lesson(module_id=m.id, type="quiz",
                    content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0},
                    xp_reward=10, order_index=0)
    db_session.add(lesson)
    u = User(username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
             dob=datetime.date(2014, 1, 1), country_code="GB", currency_code="GBP",
             is_premium=premium, profiling_enabled=profiling,
             email=f"{uuid.uuid4().hex[:8]}@e.com")
    db_session.add(u); await db_session.flush()
    return lesson, u


async def test_returns_variant_rung_and_caches_under_variant_key(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)

    async def fake_complete(**kwargs):
        import json
        return json.dumps(_QUIZ)

    class FakeClient:
        async def complete(self, **kwargs):
            return await fake_complete(**kwargs)

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: FakeClient())

    async def safe_mod(*a, **k):
        from app.services.moderation import ModerationResult
        return ModerationResult(safe=True, category=None)

    monkeypatch.setattr(ai_content_service, "moderate_output", safe_mod)

    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    assert out["variant_rung"] == "core"
    row = await db_session.scalar(
        GeneratedContent.__table__.select().where(
            GeneratedContent.lesson_id == lesson.id
        )
    )
    assert row is not None


async def test_cache_hit_is_variant_scoped(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)
    from app.services.llm_client import get_model_name
    model = get_model_name("premium")
    db_session.add(GeneratedContent(
        lesson_id=lesson.id, concept="saving", model_used=model,
        variant_key="core:0", content_json=_QUIZ,
    ))
    await db_session.flush()

    calls = {"n": 0}

    class BoomClient:
        async def complete(self, **kwargs):
            calls["n"] += 1
            raise AssertionError("should not call LLM on cache hit")

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: BoomClient())
    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    assert out["question"] == _QUIZ["question"]
    assert out["variant_rung"] == "core"
    assert calls["n"] == 0


async def test_llm_failure_falls_back_to_random_cached_safe_variant(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)
    from app.services.llm_client import get_model_name
    model = get_model_name("premium")
    # A safe cached variant under a DIFFERENT variant_key.
    db_session.add(GeneratedContent(
        lesson_id=lesson.id, concept="saving", model_used=model,
        variant_key="easier:0", content_json=_QUIZ,
    ))
    await db_session.flush()

    class FailClient:
        async def complete(self, **kwargs):
            from app.services.llm_client import LLMError
            raise LLMError("down")

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: FailClient())
    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    # Served the cached safe variant rather than _fallback's shuffled stub.
    assert out["question"] == _QUIZ["question"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ai_content_variant.py -q`
Expected: FAIL — `TypeError: generate_practice_quiz() got an unexpected keyword argument 'user'`.

- [ ] **Step 3: Add `variant_rung` to the response schema**

In `backend/app/schemas/ai.py`, change `PracticeResponse`:

```python
class PracticeResponse(BaseModel):
    question: str
    choices: list[str]
    answer_index: int
    explanation: str
    variant_rung: str | None = None
```

- [ ] **Step 4: Rewrite `generate_practice_quiz`**

In `backend/app/services/ai_content_service.py`, add imports near the top:

```python
from app.models.user import User
from app.services.content_variety_service import resolve_variant
```

Replace the function signature and body. The signature becomes:

```python
async def generate_practice_quiz(
    session: AsyncSession,
    lesson: Lesson,
    *,
    user: User,
    topic: str,
    concept: str,
    premium: bool,
    wrong_answer_index: int | None = None,
) -> dict[str, Any]:
    """Generate or serve a cached practice quiz variant for a lesson concept."""
    model_name = get_model_name("premium" if premium else "standard")
    spec = await resolve_variant(session, user, lesson, concept)
    variant_key = spec.variant_key

    def _with_rung(d: dict[str, Any]) -> dict[str, Any]:
        out = dict(d)
        out["variant_rung"] = spec.rung
        return out

    # Variant-scoped cache check
    cached = await session.scalar(
        select(GeneratedContent).where(
            GeneratedContent.lesson_id == lesson.id,
            GeneratedContent.concept == concept,
            GeneratedContent.model_used == model_name,
            GeneratedContent.variant_key == variant_key,
        )
    )
    if cached:
        return _with_rung(cached.content_json)

    content = lesson.content_json or {}
    user_message = f"Lesson topic: {topic}\nLesson content: {json.dumps(content)}"
    if wrong_answer_index is not None and "choices" in content:
        choices = content.get("choices", [])
        if 0 <= wrong_answer_index < len(choices):
            user_message += f"\nThe student chose: {choices[wrong_answer_index]} (wrong)"
    if spec.rung == "easier":
        user_message += "\nMake this question slightly easier and more encouraging."
    elif spec.rung == "harder":
        user_message += "\nMake this question slightly more challenging (still kid-friendly)."

    client = get_llm_client(tier="premium" if premium else "standard")

    for attempt in range(2):
        try:
            raw = await client.complete(
                system_prompt=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
                max_tokens=400,
                response_format="json",
            )
            parsed = json.loads(raw)
            validated = PracticeQuizSchema(**parsed)
            if validated.answer_index >= len(validated.choices):
                raise ValueError("answer_index out of range")
            result = validated.model_dump()

            _mod = await moderate_output(
                " ".join([result["question"], *result["choices"], result["explanation"]]),
                surface="quiz",
            )
            if not _mod.safe:
                session.add(AuditLog(
                    user_id=None,
                    event_type="moderation_block",
                    metadata_json={"surface": "quiz", "category": _mod.category},
                ))
                if attempt == 0:
                    continue
                return _with_rung(await _safe_cached_or_fallback(
                    session, lesson.id, concept, model_name, content
                ))

            session.add(GeneratedContent(
                lesson_id=lesson.id,
                concept=concept,
                content_json=result,
                model_used=model_name,
                variant_key=variant_key,
            ))
            await session.flush()
            return _with_rung(result)

        except (json.JSONDecodeError, ValueError, LLMError):
            if attempt == 0:
                continue
            return _with_rung(await _safe_cached_or_fallback(
                session, lesson.id, concept, model_name, content
            ))

    return _with_rung(await _safe_cached_or_fallback(
        session, lesson.id, concept, model_name, content
    ))
```

Add this helper directly above `_fallback`:

```python
async def _safe_cached_or_fallback(
    session: AsyncSession,
    lesson_id,
    concept: str,
    model_name: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    """Prefer any already-cached (therefore moderation-passed) variant; else deterministic fallback."""
    rows = (
        await session.scalars(
            select(GeneratedContent).where(
                GeneratedContent.lesson_id == lesson_id,
                GeneratedContent.concept == concept,
                GeneratedContent.model_used == model_name,
            )
        )
    ).all()
    if rows:
        return random.choice(rows).content_json
    return _fallback(content)
```

(`random` is already imported at the top of the file.)

- [ ] **Step 5: Update the only caller**

In `backend/app/routers/ai.py`, the `practice_quiz` endpoint call becomes:

```python
    result = await generate_practice_quiz(
        session,
        lesson,
        user=current_user,
        topic=module.topic,
        concept=concept,
        premium=is_premium(current_user),
        wrong_answer_index=payload.wrong_answer_index,
    )
    return result
```

- [ ] **Step 6: Update existing tests for the new arg**

In `backend/tests/test_ai_content_service.py`, every `generate_practice_quiz(...)` call must pass `user=<a User>`. Where a test lacks a user, construct one inline:

```python
import datetime, uuid
from app.models.user import User

def _mk_user():
    return User(
        username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
        dob=datetime.date(2014, 1, 1), country_code="GB",
        currency_code="GBP", is_premium=False, profiling_enabled=False,
        email=f"{uuid.uuid4().hex[:8]}@e.com",
    )
```

If the user must exist for the variant queries, `db_session.add(u); await db_session.flush()` before the call. Add `user=u` (or `user=_mk_user()` when the test only exercises the no-completion path) to each call. Keep all existing assertions; if a test asserted exact dict equality on the returned quiz, update it to ignore/expect the extra `variant_rung` key (e.g. compare `{k: v for k, v in out.items() if k != "variant_rung"}`).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ai_content_variant.py tests/test_ai_content_service.py -q`
Expected: PASS (new file + existing file all green).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ai_content_service.py backend/app/routers/ai.py backend/app/schemas/ai.py backend/tests/test_ai_content_variant.py backend/tests/test_ai_content_service.py
git commit -m "feat(4b): route practice quiz through variant seam with safe fallback"
```

---

## Task 5: `topic_path` module-list ordering

**Files:**
- Modify: `backend/app/routers/content.py:55-77` (`list_modules`)
- Test: `backend/tests/test_modules_topic_path_order.py` (create)

**Context:** `list_modules` currently emits modules in `Module.order_index` order. When `current_user.topic_path` is a known topic, stably move modules whose `topic == topic_path` to the front, preserving relative `order_index` order within both groups. Locked/premium/country logic is untouched. `topic_path` may hold a legacy/unknown value for old accounts — unknown ⇒ no reorder (treated as "no preference").

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_modules_topic_path_order.py`:

```python
import uuid
import datetime
import pytest

from app.models.content import Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _client_for(db_session, app_client, topic_path):
    # Helper assumes the suite's existing authenticated-client fixture pattern.
    ...


async def test_preferred_topic_sorts_first_stable(db_session, auth_client_factory):
    # Seed three modules: savings(0), crypto(1)[premium False for test], taxes(2)
    for t, oi in [("savings", 0), ("crypto", 1), ("taxes", 2)]:
        db_session.add(Module(topic=t, title=f"{t}-mod", country_codes=[],
                              is_premium=False, order_index=oi, icon="📚"))
    await db_session.flush()
    client = await auth_client_factory(topic_path="taxes")
    resp = await client.get("/modules")
    assert resp.status_code == 200
    topics = [m["topic"] for m in resp.json()]
    assert topics[0] == "taxes"
    # remaining preserve order_index order
    assert topics[1:] == ["savings", "crypto"]


async def test_no_topic_path_preserves_order_index(db_session, auth_client_factory):
    for t, oi in [("savings", 0), ("crypto", 1), ("taxes", 2)]:
        db_session.add(Module(topic=t, title=f"{t}-mod", country_codes=[],
                              is_premium=False, order_index=oi, icon="📚"))
    await db_session.flush()
    client = await auth_client_factory(topic_path=None)
    resp = await client.get("/modules")
    topics = [m["topic"] for m in resp.json()]
    assert topics == ["savings", "crypto", "taxes"]
```

**Note:** Match the suite's real authenticated-client fixture. Inspect `backend/tests/conftest.py` and an existing router test (e.g. `tests/test_content.py`) for the established pattern (a fixture that creates a user + auth cookie). Replace `auth_client_factory` usage with that pattern, setting `user.topic_path` accordingly. Do NOT invent a new fixture if one exists.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_modules_topic_path_order.py -q`
Expected: FAIL — preferred topic not first.

- [ ] **Step 3: Implement the stable reorder**

In `backend/app/routers/content.py`, at the end of `list_modules`, after the `out` list is built and before `return out`, add:

```python
    pref = current_user.topic_path
    if pref and pref in {m.topic for m in modules}:
        out.sort(key=lambda mo: (0 if mo.topic == pref else 1))
    return out
```

`list.sort` is stable, so within each group the original `order_index` order (from the DB query) is preserved. Remove the bare `return out` that this replaces.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_modules_topic_path_order.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the content router regression**

Run: `cd backend && python -m pytest tests/test_content.py -q`
Expected: PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/content.py backend/tests/test_modules_topic_path_order.py
git commit -m "feat(4b): order module list by self-declared topic_path"
```

---

## Task 6: Profiling-off first-quest seed

**Files:**
- Modify: `backend/app/services/recommendation_service.py:38-41`
- Test: `backend/tests/test_recommendation_topic_seed.py` (create)

**Context:** `get_recommendations` returns `{"next_quest": None, "suggested_modules": []}` immediately when `not user.profiling_enabled`. New behaviour: when profiling is off AND `user.topic_path` is a known topic AND the user has zero `LessonCompletion` rows, return a `next_quest` pointing at the first incomplete lesson of the first accessible module in that topic (by `order_index`); `suggested_modules` stays `[]`. Any completion, profiling on, or no/unknown `topic_path` ⇒ unchanged behaviour. The profiling-on code path is not modified.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_recommendation_topic_seed.py`:

```python
import uuid
import datetime
import pytest

from app.models.content import Module, Lesson, LessonCompletion
from app.models.user import User
from app.services.recommendation_service import get_recommendations

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, **kw):
    u = User(username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
             dob=datetime.date(2014, 1, 1), country_code="GB", currency_code="GBP",
             email=f"{uuid.uuid4().hex[:8]}@e.com", **kw)
    db_session.add(u); await db_session.flush()
    return u


async def _module_with_lesson(db_session, topic, oi):
    m = Module(topic=topic, title=f"{topic}-m", country_codes=[], is_premium=False,
               order_index=oi, icon="📚")
    db_session.add(m); await db_session.flush()
    lesson = Lesson(module_id=m.id, type="card", content_json={"title": "x"},
                    xp_reward=10, order_index=0)
    db_session.add(lesson); await db_session.flush()
    return m, lesson


async def test_profiling_off_with_topic_path_seeds_next_quest(db_session):
    _, lesson = await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path="savings")
    rec = await get_recommendations(db_session, user)
    assert rec["next_quest"]["lesson_id"] == lesson.id
    assert rec["suggested_modules"] == []


async def test_profiling_off_no_topic_path_returns_none(db_session):
    await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path=None)
    rec = await get_recommendations(db_session, user)
    assert rec["next_quest"] is None


async def test_profiling_off_with_completion_returns_none(db_session):
    _, lesson = await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path="savings")
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=1.0))
    await db_session.flush()
    rec = await get_recommendations(db_session, user)
    assert rec["next_quest"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recommendation_topic_seed.py -q`
Expected: FAIL — `next_quest` is `None` in the seed case.

- [ ] **Step 3: Implement the seed**

In `backend/app/services/recommendation_service.py`, add imports if missing (`func` and `select` are already imported; `is_module_accessible` and `is_premium` are already imported). Replace the early-return block:

```python
    if not user.profiling_enabled:
        return {"next_quest": None, "suggested_modules": []}
```

with:

```python
    if not user.profiling_enabled:
        seed = await _topic_path_seed(session, user)
        return {"next_quest": seed, "suggested_modules": []}
```

Add this helper at the end of the module:

```python
async def _topic_path_seed(session: AsyncSession, user: User):
    """Profiling-off only: first incomplete lesson in the self-declared topic, for a brand-new learner."""
    pref = user.topic_path
    if not pref or pref not in TOPIC_PREREQUISITES:
        return None

    completion_count = int(
        await session.scalar(
            select(func.count(LessonCompletion.id)).where(
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

`TOPIC_PREREQUISITES` keys are exactly the 9 `ModuleTopic` values, so membership doubles as the known-topic check. (Brand-new learner ⇒ zero completions ⇒ lesson 0 of the first module is the entry point.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_recommendation_topic_seed.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the recommendation regression**

Run: `cd backend && python -m pytest tests/test_recommendation_service.py -q`
Expected: PASS (profiling-on path unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_topic_seed.py
git commit -m "feat(4b): profiling-off first-quest seed from topic_path"
```

---

## Task 7: Premium tier breadth (one extra premium module)

**Files:**
- Modify: `backend/app/seed/content.py:438-455`
- Create: `backend/alembic/versions/<rev2>_premium_paycheque_module.py`
- Test: `backend/tests/test_premium_module_breadth.py` (create)

**Context:** Spec allows marking a small set of existing seeded modules `is_premium=True` for breadth. Decision: mark exactly one — `topic="taxes", title="Your First Paycheque"` (order_index 11, an applied/advanced module). Combined with the existing premium `crypto` (order 6) and `entrepreneurship`/"Revenue, Costs & Profit" (order 10) ⇒ 3 premium modules. The seed upsert currently only refreshes `icon` on existing rows; it must also refresh `is_premium` so the seed is the source of truth, and a data migration flips the row on already-migrated DBs.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_premium_module_breadth.py`:

```python
import pytest

from app.seed.content import _MODULES

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_your_first_paycheque_is_premium_in_seed():
    spec = next(m for m in _MODULES if m["title"] == "Your First Paycheque")
    assert spec["is_premium"] is True


def test_premium_seed_count_is_three():
    assert sum(1 for m in _MODULES if m["is_premium"]) == 3


async def test_seed_refreshes_is_premium_on_existing_module(db_session):
    from app.models.content import Module
    from app.seed.content import seed_modules_and_lessons
    db_session.add(Module(topic="taxes", title="Your First Paycheque",
                          country_codes=[], is_premium=False, order_index=11, icon="💷"))
    await db_session.flush()
    await seed_modules_and_lessons(db_session)
    refreshed = await db_session.scalar(
        Module.__table__.select().where(Module.title == "Your First Paycheque")
    )
    assert refreshed.is_premium is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_premium_module_breadth.py -q`
Expected: FAIL — seed value is `False`; seed does not refresh `is_premium`.

- [ ] **Step 3: Update the seed data + upsert**

In `backend/app/seed/content.py`, change the `"Your First Paycheque"` module spec line from `"is_premium": False` to `"is_premium": True`. Then in `seed_modules_and_lessons`, change the existing-row branch so it also refreshes the premium flag:

```python
        if existing:
            existing.icon = spec.get("icon", "📚")
            existing.is_premium = spec["is_premium"]
            continue
```

- [ ] **Step 4: Create the data migration**

Get the head (it should now be the Task 2 revision):

Run: `cd backend && python -m alembic heads`
Expected: `a1b2c3d4e5f6 (head)`

Create `backend/alembic/versions/b2c3d4e5f6a7_premium_paycheque_module.py`:

```python
"""mark 'Your First Paycheque' module premium (4b breadth)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE modules SET is_premium = true "
        "WHERE topic = 'taxes' AND title = 'Your First Paycheque'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE modules SET is_premium = false "
        "WHERE topic = 'taxes' AND title = 'Your First Paycheque'"
    )
```

If `python -m alembic heads` returned a different value, set `down_revision` to it.

- [ ] **Step 5: Apply and verify**

Run: `cd backend && python -m alembic upgrade head`
Expected: `INFO ... Running upgrade a1b2c3d4e5f6 -> b2c3d4e5f6a7`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_premium_module_breadth.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/seed/content.py backend/alembic/versions/b2c3d4e5f6a7_premium_paycheque_module.py backend/tests/test_premium_module_breadth.py
git commit -m "feat(4b): mark 'Your First Paycheque' a premium module"
```

---

## Task 8: Frontend — interest picker alignment, profile editor, rung badge

**Files:**
- Modify: `frontend/src/pages/child/Signup.tsx:23` and the topic `<select>` (~line 195-200)
- Modify: `frontend/src/api/ai.ts` (`PracticeQuiz` type)
- Modify: `frontend/src/api/auth.ts` (add `updatePreferences` if missing)
- Modify: `frontend/src/components/child/ProfileMenu.tsx`
- Modify: `frontend/src/components/child/lesson/PracticeQuiz.tsx`

**Context:** Signup already has an "Interest area" `<select>` but `TOPIC_PATHS = ['core', 'investing-101', 'crypto-basics']` — these are NOT valid `ModuleTopic` values and the backend (Task 1) now rejects them. They must become the 9 topics plus a "No preference" option that submits `null`. There is no profile page; `ProfileMenu` has a disabled "Profile" item — replace it with a minimal interest editor dialog calling `PATCH /users/me`. `PracticeQuiz` should show a small badge when `variant_rung` is `easier`/`harder`.

- [ ] **Step 1: Align the signup topic options**

In `frontend/src/pages/child/Signup.tsx` replace line 23:

```ts
const TOPIC_OPTIONS = [
  { value: '', label: 'No preference' },
  { value: 'stocks', label: 'Stocks' },
  { value: 'savings', label: 'Savings' },
  { value: 'real_estate', label: 'Real estate' },
  { value: 'budgeting', label: 'Budgeting' },
  { value: 'risk', label: 'Risk' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'taxes', label: 'Taxes' },
  { value: 'debt', label: 'Debt' },
  { value: 'entrepreneurship', label: 'Entrepreneurship' },
] as const;
```

Change the state init `const [topic, setTopic] = useState<string>(TOPIC_PATHS[0]);` to `const [topic, setTopic] = useState<string>('');`. Update the `<select>` options block (the `{TOPIC_PATHS.map(...)}`) to:

```tsx
{TOPIC_OPTIONS.map((t) => (
  <option key={t.value} value={t.value}>{t.label}</option>
))}
```

In the submit handler, send `topic_path: topic === '' ? null : topic` (replace the existing `topic_path: topic,`).

- [ ] **Step 2: Add `variant_rung` to the PracticeQuiz type**

In `frontend/src/api/ai.ts`, change the `PracticeQuiz` type:

```ts
export type PracticeQuiz = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
  variant_rung?: string | null;
};
```

- [ ] **Step 3: Ensure an `updatePreferences` API exists**

In `frontend/src/api/auth.ts`, if there is no `updatePreferences`, add to the exported `authApi` object:

```ts
  updatePreferences: (body: { topic_path: string | null }) =>
    apiFetch<Me>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
```

(`Me` already includes `topic_path`.)

- [ ] **Step 4: Replace the disabled Profile item with an interest editor**

In `frontend/src/components/child/ProfileMenu.tsx`, replace the `<DropdownMenuItem disabled>Profile</DropdownMenuItem>` with a dialog trigger. Use the existing `@/components/ui/dialog` primitives. The dialog contains a `<select>` of the same 9 topics + "No preference", initialised from `authApi.me()` (already cached under `['me']`), and a Save button that calls a mutation:

```tsx
const save = useMutation({
  mutationFn: (topic_path: string | null) => authApi.updatePreferences({ topic_path }),
  onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
});
```

Keep the component small and focused; reuse the topic option list (extract a shared `TOPIC_OPTIONS` into `frontend/src/api/content.ts` and import it in both Signup and ProfileMenu to stay DRY). Submit `''` as `null`.

- [ ] **Step 5: Show a rung badge in PracticeQuiz**

In `frontend/src/components/child/lesson/PracticeQuiz.tsx`, after the existing "Practice — no XP" badge span, add a conditional badge:

```tsx
{practiceQ.data.variant_rung && practiceQ.data.variant_rung !== 'core' && (
  <span className="rounded-lg bg-purple-100 px-2.5 py-1 text-xs font-semibold text-purple-800">
    {practiceQ.data.variant_rung === 'harder' ? 'Challenge' : 'Warm-up'}
  </span>
)}
```

(Place it inside the existing flex row beside the practice badge.)

- [ ] **Step 6: Typecheck, lint, build**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint passes; `vite build` succeeds with no type errors.

- [ ] **Step 7: Run the affected frontend unit tests**

Run: `cd frontend && npm test -- --run`
Expected: green (222+ baseline). If a Signup test asserted the old `TOPIC_PATHS` values, update it to the new options + "No preference".

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/child/Signup.tsx frontend/src/api/ai.ts frontend/src/api/auth.ts frontend/src/api/content.ts frontend/src/components/child/ProfileMenu.tsx frontend/src/components/child/lesson/PracticeQuiz.tsx
git commit -m "feat(4b): align interest picker to topics, add profile editor + rung badge"
```

---

## Task 9: Full regression + spec-alignment verification + close-out

**Files:**
- Modify: `docs/superpowers/specs/2026-05-19-premium-content-ai-engagement-design.md` (mark Delivered)
- Verify only: whole backend + frontend suites

**Context:** Final gate. Confirm the baseline invariant (backend suite stays green, count ≥ 302 + the new tests; frontend ≥ 222) and that every spec section maps to delivered code.

- [ ] **Step 1: Full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS, 0 failures. Count = previous 302 + new tests from Tasks 1-7. Record the number.

- [ ] **Step 2: Migration round-trip sanity**

Run: `cd backend && python -m alembic downgrade -2 && python -m alembic upgrade head`
Expected: both succeed (downgrade removes the premium flip + variant_key, upgrade re-applies cleanly).

- [ ] **Step 3: Full frontend suite + build**

Run: `cd frontend && npm test -- --run && npm run build`
Expected: tests green, build succeeds.

- [ ] **Step 4: Spec-alignment checklist (manual, write findings into the commit message)**

Verify each spec section has delivered code:
- §1 architecture/migration → `content_variety_service.py`, variant_key migration ✔
- §2 rung/ordinal/AADC/fallback → `resolve_variant` + `_safe_cached_or_fallback` ✔
- §3 topic_path validation + reorder + profiling-off seed → Tasks 1, 5, 6 ✔
- §4 API/frontend/error/testing → Tasks 4, 8 + all test files ✔
- 4a moderation still applied to every generated variant → confirm `moderate_output` call still in `generate_practice_quiz` generation path ✔

List any gap; if found, fix before close-out.

- [ ] **Step 5: Mark the spec delivered**

In the spec file, change `**Status:** Approved (brainstorming) — 2026-05-19` to `**Status:** Delivered — 2026-05-19 (sub-project 4b)`.

- [ ] **Step 6: Final commit**

```bash
git add docs/superpowers/specs/2026-05-19-premium-content-ai-engagement-design.md
git commit -m "chore(4b): mark premium content & AI engagement delivered; full suite green"
```

- [ ] **Step 7: Finish the development branch**

Use **superpowers:finishing-a-development-branch** to integrate the work (the established delivery convention: commit to `main`, then `git branch -f claude/lucid-cray-03eff5 main && git push origin claude/lucid-cray-03eff5`; PR #7 accumulates the programme — do not open a new PR unless asked).

---

## Self-Review

**Spec coverage:** §1 (architecture/data model) → Tasks 2, 3, 4. §2 (rung/ordinal/AADC/fallback) → Tasks 3, 4. §3 (topic_path validate/reorder/seed) → Tasks 1, 5, 6. §4 (API/frontend/error/testing) → Tasks 4, 8, 9. Premium breadth → Task 7. 4a integration → asserted in Task 4 + Task 9 §4. No gaps.

**Placeholder scan:** No TBD/“handle edge cases”. Migration `down_revision` values are concrete (`c9bdf248d9b3` verified via `alembic heads`) with an explicit fallback instruction if heads differ at execution time. Task 5's test references the suite's real auth fixture with an explicit instruction to match `conftest.py` rather than invent one (justified — fixture name varies and must not be guessed).

**Type/name consistency:** `VariantSpec(rung, ordinal, pool_size)` + `.variant_key` used identically in Tasks 3 and 4. `resolve_variant(session, user, lesson, concept)` signature consistent across service, tests, and `generate_practice_quiz`. `TOPIC_PATH_VALUES` (backend constant) vs `TOPIC_OPTIONS` (frontend list) are intentionally distinct names for distinct artifacts. `variant_rung` field name consistent across schema, service return, frontend type, and badge. Premium module identified consistently as `taxes` / "Your First Paycheque" in seed, migration, and test.
