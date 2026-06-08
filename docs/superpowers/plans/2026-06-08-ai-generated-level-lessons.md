# AI-Generated Level Lessons + Admin Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin AI-generate a batch of draft lessons for a level, review/edit them, and approve the safe ones into live lessons — moderation enforced, drafts invisible to children.

**Architecture:** A separate `lesson_drafts` table holds AI output outside the live `Lesson` path. A generation service mirrors the proven `generate_practice_quiz` pipeline (premium LLM → validate per-type schema → `moderate_output` → persist draft, flagged if unsafe). Admin-only, rate-limited endpoints generate/list/edit/approve/regenerate/reject; approve materialises a real `Lesson`. New admin React UI for the generate form + draft review.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + pydantic v2 (backend); React 18 + Vite + TS + TanStack Query + vitest/vitest-axe (frontend).

**Conventions (MANDATORY):**
- Branch `testing`. Explicit `git add <paths>` only — never `git add -A`. Leave the unrelated modified `.gitignore` untouched.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Backend tools (from `backend/`): pytest `/Users/leeashmore/Local Repo/.venv/bin/pytest`, ruff `/Users/leeashmore/Local Repo/.venv/bin/ruff`, alembic `/Users/leeashmore/Local Repo/.venv/bin/alembic`.
- Async DB tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `db_session`/`client` fixtures.
- LLM/moderation tests mock with `unittest.mock.AsyncMock` + `patch("app.services.<module>.get_llm_client", return_value=mock_client)` (see `tests/test_ai_content_service.py`).

---

### Task 1: Extract `validate_lesson_content_json` helper (DRY)

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Test: `backend/tests/test_lesson_content_validation.py`

The current per-type validation lives inline in `LessonCreate.validate_content`. Extract it to a pure module-level function and have the validator delegate, so the generation service can reuse the exact same rules.

- [ ] **Step 1: Write the failing test** `backend/tests/test_lesson_content_validation.py`

```python
import pytest

from app.schemas.admin import validate_lesson_content_json


def test_valid_card():
    validate_lesson_content_json("card", {"title": "T", "body": "B"})


def test_card_missing_body_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("card", {"title": "T"})


def test_valid_quiz():
    validate_lesson_content_json("quiz", {
        "question": "Q", "choices": ["a", "b"], "answer_index": 1, "explanation": "E",
    })


def test_quiz_answer_index_out_of_range_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("quiz", {
            "question": "Q", "choices": ["a", "b"], "answer_index": 5, "explanation": "E",
        })


def test_valid_scenario():
    validate_lesson_content_json("scenario", {
        "prompt": "P",
        "choices": [{"label": "a", "outcome": "o1"}, {"label": "b", "outcome": "o2"}],
        "correct_index": 0,
    })


def test_scenario_choice_missing_outcome_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("scenario", {
            "prompt": "P", "choices": [{"label": "a"}], "correct_index": 0,
        })
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_lesson_content_validation.py -v`
Expected: FAIL (`ImportError: cannot import name 'validate_lesson_content_json'`).

- [ ] **Step 3: Add the helper + delegate** in `backend/app/schemas/admin.py`. Add this module-level function (near the `LessonCreate` class):

```python
def validate_lesson_content_json(lesson_type: str, v: dict) -> None:
    """Per-type content_json rules. Raises ValueError on invalid. Shared by the
    admin LessonCreate validator AND the AI generation service."""
    if lesson_type == "card":
        if "title" not in v or "body" not in v:
            raise ValueError("Card requires title and body")
    elif lesson_type == "quiz":
        for key in ("question", "choices", "answer_index", "explanation"):
            if key not in v:
                raise ValueError(f"Quiz requires {key}")
        if not isinstance(v["choices"], list) or len(v["choices"]) < 2:
            raise ValueError("Quiz requires at least 2 choices")
        if not (0 <= v["answer_index"] < len(v["choices"])):
            raise ValueError("Invalid answer_index — must be within choices range")
    elif lesson_type == "scenario":
        for key in ("prompt", "choices", "correct_index"):
            if key not in v:
                raise ValueError(f"Scenario requires {key}")
        if not isinstance(v["choices"], list) or len(v["choices"]) < 2:
            raise ValueError("Scenario requires at least 2 choices")
        for c in v["choices"]:
            if not isinstance(c, dict) or "label" not in c or "outcome" not in c:
                raise ValueError("Each scenario choice requires label and outcome")
        if not (0 <= v["correct_index"] < len(v["choices"])):
            raise ValueError("Invalid correct_index — must be within choices range")
    elif lesson_type == "video":
        source = v.get("video_source", "youtube")
        if source == "hosted":
            if not isinstance(v.get("video_url"), str) or not v["video_url"]:
                raise ValueError("hosted video lessons require a non-empty video_url")
        else:
            if not isinstance(v.get("youtube_id"), str) or not v["youtube_id"]:
                raise ValueError("video lessons require a non-empty youtube_id")
```

Then replace the body of `LessonCreate.validate_content` to delegate (keep the validator + return):

```python
    @field_validator("content_json")
    @classmethod
    def validate_content(cls, v: dict, info) -> dict:
        validate_lesson_content_json(info.data.get("type"), v)
        return v
```

- [ ] **Step 4: Run new test + the existing admin schema/lesson tests** (no regression)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_lesson_content_validation.py -v` → PASS (6).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/ -k "admin or lesson" -q` → PASS (existing lesson-create validation still enforced).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/schemas/admin.py tests/test_lesson_content_validation.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/admin.py backend/tests/test_lesson_content_validation.py
git commit -m "refactor(content): extract reusable validate_lesson_content_json

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `LessonDraft` model + migration

**Files:**
- Create: `backend/app/models/lesson_draft.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/b6c7d8e9f0a1_add_lesson_drafts.py`
- Test: `backend/tests/models/test_lesson_draft.py`

- [ ] **Step 1: Confirm the head**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → note the single head (expected `a5b6c7d8e9f0`; if different, use that as `down_revision`).

- [ ] **Step 2: Write the failing test** `backend/tests/models/test_lesson_draft.py`

```python
import pytest

from app.models.lesson_draft import LessonDraft

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_lesson_draft_persists(db_session):
    from app.models.content import Module, Level

    module = Module(topic="saving", title="Saving Basics", country_codes=[], is_premium=True, order_index=0)
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Level 2", order_index=1, is_premium=True, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()

    draft = LessonDraft(
        level_id=level.id, type="card",
        content_json={"title": "T", "body": "B"},
        concept="compound interest", model_used="test-model",
        moderation_safe=True, moderation_category=None,
    )
    db_session.add(draft)
    await db_session.flush()
    fetched = await db_session.get(LessonDraft, draft.id)
    assert fetched is not None
    assert fetched.moderation_safe is True
    assert fetched.content_json["title"] == "T"
```

(Adjust `Module`/`Level` constructor kwargs to the real columns — open `app/models/content.py` first.)

- [ ] **Step 3: Run it, expect FAIL** — `ModuleNotFoundError: app.models.lesson_draft`.

- [ ] **Step 4: Create `backend/app/models/lesson_draft.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LessonDraft(Base):
    __tablename__ = "lesson_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    moderation_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    moderation_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
```

(Match the JSON column type to how `Lesson.content_json` is declared in `app/models/content.py` — if it uses `JSONB`/a custom type, mirror it. `JSON` is the safe portable default.)

- [ ] **Step 5: Register** in `backend/app/models/__init__.py`: add `from app.models.lesson_draft import LessonDraft  # noqa: F401`.

- [ ] **Step 6: Create the migration** `backend/alembic/versions/b6c7d8e9f0a1_add_lesson_drafts.py`

```python
"""add lesson_drafts

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-06-08

"""
import sqlalchemy as sa
from alembic import op

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("level_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("concept", sa.String(length=200), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column("moderation_safe", sa.Boolean(), nullable=False),
        sa.Column("moderation_category", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lesson_drafts_level_id"), "lesson_drafts", ["level_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_drafts_level_id"), table_name="lesson_drafts")
    op.drop_table("lesson_drafts")
```

(Match `sa.Uuid()` to how other migrations declare UUID PKs/FKs in this repo — check a recent migration; if they use `postgresql.UUID(as_uuid=True)`, mirror that.)

- [ ] **Step 7: Verify single head + test + ruff**

`/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → single head `b6c7d8e9f0a1`.
`/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_lesson_draft.py -v` → PASS.
`/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/models/lesson_draft.py alembic/versions/b6c7d8e9f0a1_add_lesson_drafts.py tests/models/test_lesson_draft.py` → clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/lesson_draft.py backend/app/models/__init__.py backend/alembic/versions/b6c7d8e9f0a1_add_lesson_drafts.py backend/tests/models/test_lesson_draft.py
git commit -m "feat(content): LessonDraft model + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Generation service

**Files:**
- Create: `backend/app/services/admin_content_generation_service.py`
- Test: `backend/tests/test_admin_content_generation.py`

Read `backend/app/services/ai_content_service.py::generate_practice_quiz` first and mirror its LLM+moderation flow.

- [ ] **Step 1: Write the failing tests** `backend/tests/test_admin_content_generation.py`

```python
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.admin_content_generation_service import generate_level_lessons
from app.services.moderation import ModerationResult
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")

CARD = json.dumps({"title": "Compound Interest", "body": "Money grows on money."})


async def _seed_level(db_session):
    module = Module(topic="saving", title="Saving", country_codes=[], is_premium=True,
                    order_index=0, min_age=10, max_age=14)
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Level 2", order_index=1, is_premium=True, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return level


async def test_generates_n_safe_drafts(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_level_lessons(db_session, level, concept="compound interest",
                                              count=2, types=["card"])
    assert len(result.created) == 2
    assert result.skipped == 0
    drafts = (await db_session.scalars(select(LessonDraft).where(LessonDraft.level_id == level.id))).all()
    assert len(drafts) == 2
    assert all(d.moderation_safe for d in drafts)


async def test_unsafe_output_flagged_and_audited(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=False, category="violence", text="x"))):
        result = await generate_level_lessons(db_session, level, concept="x", count=1, types=["card"])
    assert len(result.created) == 1
    assert result.created[0].moderation_safe is False
    assert result.created[0].moderation_category == "violence"


async def test_bad_json_retried_then_skipped(db_session):
    level = await _seed_level(db_session)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not json")  # always bad -> retry once -> skip
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_level_lessons(db_session, level, concept="x", count=1, types=["card"])
    assert result.created == []
    assert result.skipped == 1
    assert mock_client.complete.await_count == 2  # initial + one retry
```

- [ ] **Step 2: Run, expect FAIL** (`ImportError`).

- [ ] **Step 3: Implement `backend/app/services/admin_content_generation_service.py`**

```python
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.content import Level, Module
from app.models.lesson_draft import LessonDraft
from app.schemas.admin import validate_lesson_content_json
from app.services.llm_client import get_llm_client, get_model_name
from app.services.moderation import moderate_output

logger = logging.getLogger(__name__)

_SCHEMA_HINT = {
    "card": '{"title": str, "body": str}',
    "quiz": '{"question": str, "choices": [str, str, ...(2-5)], "answer_index": int, "explanation": str}',
    "scenario": '{"prompt": str, "choices": [{"label": str, "outcome": str}, ...(>=2)], "correct_index": int}',
}


@dataclass
class GenerationResult:
    created: list[LessonDraft] = field(default_factory=list)
    skipped: int = 0


def _system_prompt(lesson_type: str, module: Module, level: Level) -> str:
    age = f"ages {module.min_age}-{module.max_age}" if module.min_age else "children 8-16"
    return (
        f"You write a single financial-education {lesson_type} lesson for {age} on the topic "
        f"'{module.topic}' (module '{module.title}', '{level.title}'). Keep it simple, encouraging, "
        f"factual, and age-appropriate. Never give personalised financial advice. "
        f"Respond with ONLY a JSON object matching exactly: {_SCHEMA_HINT[lesson_type]}"
    )


def _concat_text(parsed: dict) -> str:
    parts: list[str] = []
    for key in ("title", "body", "question", "explanation", "prompt"):
        if isinstance(parsed.get(key), str):
            parts.append(parsed[key])
    for ch in parsed.get("choices", []) or []:
        if isinstance(ch, str):
            parts.append(ch)
        elif isinstance(ch, dict):
            parts.extend(str(ch.get(k, "")) for k in ("label", "outcome"))
    return "\n".join(parts)


async def _generate_one(session: AsyncSession, *, level, module, concept: str, lesson_type: str) -> LessonDraft | None:
    client = get_llm_client("premium")
    system = _system_prompt(lesson_type, module, level)
    user = f"Create a {lesson_type} lesson teaching: {concept}."
    for attempt in range(2):
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.4, max_tokens=700, response_format="json",
        )
        try:
            parsed = json.loads(raw)
            validate_lesson_content_json(lesson_type, parsed)
            break
        except (json.JSONDecodeError, ValueError, TypeError):
            if attempt == 1:
                return None
    mod = await moderate_output(_concat_text(parsed), surface="lesson")
    draft = LessonDraft(
        level_id=level.id, type=lesson_type, content_json=parsed, concept=concept,
        model_used=get_model_name("premium"),
        moderation_safe=mod.safe, moderation_category=mod.category,
    )
    session.add(draft)
    if not mod.safe:
        session.add(AuditLog(event_type="moderation_block",
                             detail=f"lesson-gen:{lesson_type}:{mod.category}"))
    await session.flush()
    return draft


async def generate_level_lessons(session: AsyncSession, level, *, concept: str, count: int,
                                 types: list[str]) -> GenerationResult:
    module = await session.get(Module, level.module_id)
    result = GenerationResult()
    for i in range(count):
        lesson_type = types[i % len(types)]
        draft = await _generate_one(session, level=level, module=module, concept=concept,
                                    lesson_type=lesson_type)
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result
```

(Verify `AuditLog`'s real columns — match `event_type`/`detail` to the actual model; the quiz pipeline at `ai_content_service.py:121` shows the real constructor — copy its field names.)

- [ ] **Step 4: Run tests + ruff**

`/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_content_generation.py -v` → PASS (3).
`/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/admin_content_generation_service.py tests/test_admin_content_generation.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/admin_content_generation_service.py backend/tests/test_admin_content_generation.py
git commit -m "feat(content): AI level-lesson generation service (moderated, fail-closed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Draft schemas

**Files:**
- Modify: `backend/app/schemas/admin.py`

- [ ] **Step 1: Add the schemas** (near the other admin schemas; `Field`, `Literal`, `uuid`, `datetime`, `ConfigDict`, `BaseModel` are already imported — add any missing):

```python
class GenerateLessonsRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=200)
    count: int = Field(ge=1, le=8)
    types: list[Literal["card", "quiz", "scenario"]] = Field(min_length=1)


class LessonDraftOut(BaseModel):
    id: uuid.UUID
    level_id: uuid.UUID
    type: str
    content_json: dict
    concept: str
    moderation_safe: bool
    moderation_category: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateLessonsResponse(BaseModel):
    created: list[LessonDraftOut]
    skipped: int


class LessonDraftUpdate(BaseModel):
    content_json: dict
```

- [ ] **Step 2: Sanity check imports compile**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/python -c "import app.schemas.admin"` → no error.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/schemas/admin.py` → clean.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/admin.py
git commit -m "feat(content): lesson-draft request/response schemas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `POST /admin/levels/{level_id}/generate`

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/test_lesson_draft_endpoints.py`

Read an existing admin level endpoint + a rate-limited endpoint in `app/routers/ai.py` (for the `request: Request` + `@limiter.limit` pattern) and the existing admin tests for the admin-auth fixture.

- [ ] **Step 1: Write the failing tests** (start the shared test file) `backend/tests/test_lesson_draft_endpoints.py`

```python
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

CARD = json.dumps({"title": "T", "body": "B"})

# _admin_client + _make_level(...) helpers: copy the admin-auth + level-creation
# pattern from the existing admin tests (grep tests/ for get_current_admin / admin level create).


async def test_generate_requires_admin(client):
    resp = await client.post("/admin/levels/00000000-0000-0000-0000-000000000000/generate",
                             json={"concept": "x", "count": 1, "types": ["card"]})
    assert resp.status_code in (401, 403)


async def test_generate_happy_path(admin_client, db_session):
    level_id = await _make_level(admin_client, db_session)
    mock_client = AsyncMock(); mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.post(f"/admin/levels/{level_id}/generate",
                                       json={"concept": "compound interest", "count": 2, "types": ["card"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["created"]) == 2 and body["skipped"] == 0


async def test_generate_unknown_level_404(admin_client):
    resp = await admin_client.post("/admin/levels/00000000-0000-0000-0000-000000000000/generate",
                                   json={"concept": "x", "count": 1, "types": ["card"]})
    assert resp.status_code == 404
```

Replace `admin_client`/`_make_level` with the real admin-auth client + level-creation the existing admin tests use (read them; reuse verbatim).

- [ ] **Step 2: Run, expect FAIL** (404 route missing).

- [ ] **Step 3: Add the endpoint** in `backend/app/routers/admin.py`. Imports (add to existing groups): `from fastapi import Request`; `from app.core.rate_limit import limiter`; `from app.schemas.admin import GenerateLessonsRequest, GenerateLessonsResponse, LessonDraftOut`; `from app.services.admin_content_generation_service import generate_level_lessons`; `from app.models.content import Level`; `from app.models.lesson_draft import LessonDraft`.

```python
@router.post("/levels/{level_id}/generate", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    result = await generate_level_lessons(
        session, level, concept=payload.concept, count=payload.count, types=payload.types,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )
```

(Confirm `uuid`, `Depends`, `get_current_admin`, `get_session`, `AsyncSession`, `HTTPException`, `status`, `User`, `router` are already imported in admin.py — they are.)

- [ ] **Step 4: Run tests + ruff** → PASS; clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_lesson_draft_endpoints.py
git commit -m "feat(admin): POST levels/{id}/generate (rate-limited, admin-only)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `GET /admin/levels/{level_id}/drafts`

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/test_lesson_draft_endpoints.py` (extend)

- [ ] **Step 1: Add the failing test**

```python
async def test_list_drafts(admin_client, db_session):
    level_id = await _make_level(admin_client, db_session)
    mock_client = AsyncMock(); mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        await admin_client.post(f"/admin/levels/{level_id}/generate",
                                json={"concept": "x", "count": 1, "types": ["card"]})
    resp = await admin_client.get(f"/admin/levels/{level_id}/drafts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Add the endpoint**

```python
@router.get("/levels/{level_id}/drafts", response_model=list[LessonDraftOut])
async def list_lesson_drafts(
    level_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level_id).order_by(LessonDraft.created_at)
    )).all()
    return [LessonDraftOut.model_validate(d) for d in rows]
```

(`select` is already imported in admin.py.)

- [ ] **Step 4: Run + ruff** → PASS; clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_lesson_draft_endpoints.py
git commit -m "feat(admin): GET levels/{id}/drafts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `PUT /admin/lesson-drafts/{draft_id}` (edit + re-moderate)

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/test_lesson_draft_endpoints.py` (extend)

- [ ] **Step 1: Add failing tests** — valid edit re-moderates + persists; invalid content → 422. (Create a draft directly via `db_session.add(LessonDraft(...))` for these, to avoid LLM mocking.)

```python
async def test_edit_draft_revalidates_and_remoderates(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft); await db_session.flush()
    with patch("app.routers.admin.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.put(f"/admin/lesson-drafts/{draft.id}",
                                      json={"content_json": {"title": "New", "body": "Body"}})
    assert resp.status_code == 200
    assert resp.json()["content_json"]["title"] == "New"


async def test_edit_draft_invalid_content_422(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft); await db_session.flush()
    resp = await admin_client.put(f"/admin/lesson-drafts/{draft.id}", json={"content_json": {"title": "only"}})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Add the endpoint** (import `moderate_output` + `validate_lesson_content_json` at top of admin.py):

```python
@router.put("/lesson-drafts/{draft_id}", response_model=LessonDraftOut)
async def update_lesson_draft(
    draft_id: uuid.UUID,
    payload: LessonDraftUpdate,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    try:
        validate_lesson_content_json(draft.type, payload.content_json)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    from app.services.admin_content_generation_service import _concat_text
    mod = await moderate_output(_concat_text(payload.content_json), surface="lesson")
    draft.content_json = payload.content_json
    draft.moderation_safe = mod.safe
    draft.moderation_category = mod.category
    await session.commit()
    return LessonDraftOut.model_validate(draft)
```

(Add `from app.schemas.admin import LessonDraftUpdate` to imports.)

- [ ] **Step 4: Run + ruff** → PASS; clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_lesson_draft_endpoints.py
git commit -m "feat(admin): PUT lesson-drafts/{id} edit + re-moderate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `POST /admin/lesson-drafts/{draft_id}/approve`

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `backend/tests/test_lesson_draft_endpoints.py` (extend)

- [ ] **Step 1: Add failing tests** — flagged draft → 409 and no Lesson; safe draft → materialises a Lesson (correct `module_id`/`level_id`/`type`/`content_json`, `order_index` appended) and the draft is deleted.

```python
async def test_approve_flagged_draft_409(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=False, moderation_category="violence")
    db_session.add(draft); await db_session.flush()
    resp = await admin_client.post(f"/admin/lesson-drafts/{draft.id}/approve")
    assert resp.status_code == 409


async def test_approve_safe_draft_materialises_lesson(admin_client, db_session):
    from app.models.content import Lesson, Level
    from app.models.lesson_draft import LessonDraft
    from sqlalchemy import select
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft); await db_session.flush()
    resp = await admin_client.post(f"/admin/lesson-drafts/{draft.id}/approve")
    assert resp.status_code == 200
    lessons = (await db_session.scalars(select(Lesson).where(Lesson.level_id == level_id))).all()
    assert any(le.type == "card" and le.content_json["title"] == "A" for le in lessons)
    assert await db_session.get(LessonDraft, draft.id) is None
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Add the endpoint**

```python
@router.post("/lesson-drafts/{draft_id}/approve", response_model=LessonOut)
async def approve_lesson_draft(
    draft_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if not draft.moderation_safe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Draft failed moderation")
    level = await session.get(Level, draft.level_id)
    max_order = await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == draft.level_id)
    )
    lesson = Lesson(
        module_id=level.module_id, level_id=draft.level_id, type=draft.type,
        content_json=draft.content_json, xp_reward=10, order_index=(max_order or 0) + 1,
    )
    session.add(lesson)
    await session.delete(draft)
    await session.commit()
    return LessonOut.model_validate(lesson)
```

(Add `from sqlalchemy import func` if not present; `Lesson`, `LessonOut` imported.)

- [ ] **Step 4: Run + ruff** → PASS; clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_lesson_draft_endpoints.py
git commit -m "feat(admin): approve draft -> materialise Lesson (409 if flagged)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Regenerate + reject endpoints

**Files:**
- Modify: `backend/app/routers/admin.py`, `backend/app/services/admin_content_generation_service.py`
- Test: `backend/tests/test_lesson_draft_endpoints.py` (extend)

- [ ] **Step 1: Add a single-draft regenerate helper** to the service:

```python
async def regenerate_draft(session: AsyncSession, draft: LessonDraft) -> LessonDraft | None:
    level = await session.get(Level, draft.level_id)
    module = await session.get(Module, level.module_id)
    fresh = await _generate_one(session, level=level, module=module, concept=draft.concept,
                                lesson_type=draft.type)
    if fresh is None:
        return None
    draft.content_json = fresh.content_json
    draft.moderation_safe = fresh.moderation_safe
    draft.moderation_category = fresh.moderation_category
    draft.model_used = fresh.model_used
    await session.delete(fresh)
    await session.commit()
    return draft
```

- [ ] **Step 2: Add failing tests** — regenerate replaces content + returns 200; reject deletes (204) and a second reject → 404.

```python
async def test_reject_deletes_draft(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft); await db_session.flush()
    resp = await admin_client.delete(f"/admin/lesson-drafts/{draft.id}")
    assert resp.status_code == 204
    assert await db_session.get(LessonDraft, draft.id) is None


async def test_regenerate_replaces_content(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client, db_session)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "old", "body": "old"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft); await db_session.flush()
    NEW = json.dumps({"title": "new", "body": "new"})
    mock_client = AsyncMock(); mock_client.complete = AsyncMock(return_value=NEW)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.post(f"/admin/lesson-drafts/{draft.id}/regenerate")
    assert resp.status_code == 200
    assert resp.json()["content_json"]["title"] == "new"
```

- [ ] **Step 3: Add the endpoints**

```python
@router.post("/lesson-drafts/{draft_id}/regenerate", response_model=LessonDraftOut)
@limiter.limit("5/minute")
async def regenerate_lesson_draft(
    request: Request,
    draft_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    from app.services.admin_content_generation_service import regenerate_draft
    updated = await regenerate_draft(session, draft)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Generation failed")
    return LessonDraftOut.model_validate(updated)


@router.delete("/lesson-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reject_lesson_draft(
    draft_id: uuid.UUID,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    await session.delete(draft)
    await session.commit()
```

- [ ] **Step 4: Run full draft-endpoint suite + ruff** → PASS; clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/app/services/admin_content_generation_service.py backend/tests/test_lesson_draft_endpoints.py
git commit -m "feat(admin): regenerate + reject lesson drafts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Frontend API client (types + hooks)

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Test: none (covered via component tests in Task 11)

- [ ] **Step 1: Add types + hooks.** Match the existing hook style in `admin.ts` (TanStack Query `useQuery`/`useMutation`, `adminFetch`/`apiFetch`, `useQueryClient` invalidation). Add:

```typescript
export type LessonDraft = {
  id: string;
  level_id: string;
  type: 'card' | 'quiz' | 'scenario';
  content_json: Record<string, unknown>;
  concept: string;
  moderation_safe: boolean;
  moderation_category: string | null;
  created_at: string;
};
export type GenerateLessonsBody = { concept: string; count: number; types: ('card' | 'quiz' | 'scenario')[] };
export type GenerateLessonsResult = { created: LessonDraft[]; skipped: number };
```

Hooks (mirror `useCreateLevelLesson`/`useLevelLessons` exactly — same `adminFetch` path style, same `onSuccess` invalidation):
- `useLevelDrafts(levelId)` → `GET /admin/levels/{levelId}/drafts`, key `['level-drafts', levelId]`.
- `useGenerateLevelLessons(levelId)` → `POST /admin/levels/{levelId}/generate`; invalidate `['level-drafts', levelId]`.
- `useUpdateDraft(levelId)` → `PUT /admin/lesson-drafts/{id}`; invalidate `['level-drafts', levelId]`.
- `useApproveDraft(levelId)` → `POST /admin/lesson-drafts/{id}/approve`; invalidate `['level-drafts', levelId]` AND `['level-lessons', levelId]`.
- `useRegenerateDraft(levelId)` → `POST /admin/lesson-drafts/{id}/regenerate`; invalidate `['level-drafts', levelId]`.
- `useRejectDraft(levelId)` → `DELETE /admin/lesson-drafts/{id}`; invalidate `['level-drafts', levelId]`.

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc -b` → clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "feat(admin-fe): lesson-draft API client + hooks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Admin generate form + draft review UI

**Files:**
- Create: `frontend/src/components/admin/LessonDraftReview.tsx`
- Modify: the level lesson screen (`frontend/src/components/admin/LevelLessonList.tsx`) to mount the generate form + review list
- Test: `frontend/src/components/admin/__tests__/LessonDraftReview.test.tsx`

- [ ] **Step 1: Read** `LevelLessonList.tsx`, `LessonForm.tsx` (per-type editors), and `ConfirmDialog.tsx` to reuse their patterns + props.

- [ ] **Step 2: Write the failing test** `frontend/src/components/admin/__tests__/LessonDraftReview.test.tsx` (copy the admin test render-with-providers helper; mock `@/api/admin` hooks). Assertions:
  - A **flagged** draft (`moderation_safe:false`, `moderation_category:'violence'`) shows a "Flagged" badge with the category and the **Approve** button is **disabled**.
  - A **safe** draft's **Approve** click calls the approve mutation.
  - **Edit** opens the editor and Save calls the update mutation.
  - **Reject** → confirm → calls the reject mutation; **Regenerate** calls the regenerate mutation.
  - `axe(container)` has no violations.

```typescript
// mock @/api/admin: useLevelDrafts -> {data:[safeDraft, flaggedDraft]}, and
// useApproveDraft/useUpdateDraft/useRejectDraft/useRegenerateDraft/useGenerateLevelLessons -> { mutate: vi.fn(), ... }
// Render <LessonDraftReview levelId="L1" /> inside QueryClientProvider.
// Then assert per the bullets above (getByRole('button', {name:/approve/i}) disabled for the flagged card, etc.)
```

- [ ] **Step 3: Run, expect FAIL.**

- [ ] **Step 4: Implement `LessonDraftReview.tsx`.** A component taking `{ levelId: string }`:
  - A **"Generate lessons"** form: `concept` text input, `count` number input (min 1 max 8), and three checkboxes (card/quiz/scenario); a submit button calls `useGenerateLevelLessons(levelId)`; show a spinner while pending and a "skipped N" note if the result has `skipped > 0`.
  - The **draft list** from `useLevelDrafts(levelId)`: each draft card shows a type badge, a per-type **preview** (title/body; question + choices; prompt + choices — a simple structured read-only render), and a **moderation badge**: safe → `bg-success-… text-…` "Safe ✓"; flagged → `bg-danger-… text-danger-…` "⚠ Flagged: {category}". Actions: **Approve** (`disabled={!draft.moderation_safe}`, with `title`/`aria-disabled` explaining why), **Edit** (toggles an inline editor reusing the `LessonForm` per-type editor; Save → `useUpdateDraft`), **Regenerate** (`useRegenerateDraft`), **Reject** (opens `ConfirmDialog` → `useRejectDraft`).
  - Accessibility: labelled inputs/buttons, ≥44px targets, keyboard, semantic tokens (Penny/sky). Admin desktop.
  - Mount `<LessonDraftReview levelId={levelId} />` in `LevelLessonList.tsx` below the existing manual lesson list.

- [ ] **Step 5: Run tests + typecheck + lint**

Run: `cd frontend && npm run test -- LessonDraftReview` → PASS.
Run: `npx tsc -b && npm run lint` → clean (fix only touched-file issues).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/admin/LessonDraftReview.tsx frontend/src/components/admin/LevelLessonList.tsx frontend/src/components/admin/__tests__/LessonDraftReview.test.tsx
git commit -m "feat(admin-fe): AI lesson generate form + draft review UI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend lint + full suite**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: clean + green (incl. all new draft/generation tests). If the local Postgres hangs ~90s+, note it as environmental — the new non-DB unit tests must pass; rely on CI for DB-backed ones.

- [ ] **Step 2: Frontend full checks**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green.

- [ ] **Step 3: Push + confirm CI**

```bash
git push origin testing
```
Confirm CI green (frontend, backend, security, a11y, responsive). No `cap sync` (admin web surface, no native change).

---

## Self-review notes
- Spec coverage: validate helper (T1), LessonDraft model+migration (T2), generation service moderated/fail-closed (T3), schemas (T4), generate endpoint rate-limited (T5), list (T6), edit+re-moderate (T7), approve→Lesson/409-if-flagged (T8), regenerate+reject (T9), FE client (T10), FE generate+review UI with flagged-disables-approve+axe (T11), regression (T12). All spec sections covered.
- Type consistency: `LessonDraft`, `GenerationResult(created, skipped)`, `generate_level_lessons(session, level, *, concept, count, types)`, `validate_lesson_content_json(type, content_json)`, `_concat_text`, schema names `GenerateLessonsRequest/Response`, `LessonDraftOut`, `LessonDraftUpdate`, and FE hook names are consistent across tasks.
- Implementer notes: (a) match `AuditLog` constructor fields to the real model (copy from `ai_content_service.py:121`); (b) match `sa.Uuid()`/JSON column types to the repo's existing migrations + `Lesson.content_json`; (c) reuse the existing admin-auth test client + level-creation helper verbatim for the endpoint tests; (d) reuse `LessonForm` per-type editors + `ConfirmDialog` real props for the review UI.
