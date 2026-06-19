# Content Localization Pipeline Implementation Plan (Sub-project E1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve InvestiKid's authored content in a user's language from stored translations (curated + Gemini auto, validated/moderated/labelled), with per-entity English fallback, an admin generation pipeline, and a content-language kill-switch — no on-the-fly translation at serve time.

**Architecture:** A `content_translations` table (one row per entity×language holding a translated-fields bundle); a single extraction module defining what's translatable; a translation service (idempotent via source_hash, curated overrides, structural + moderation gate); admin generate/curated/coverage endpoints; a `localize` serving helper gated by an admin-flippable enabled-content-languages setting; and a machine-translated badge on the frontend.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres (backend); React 18 + Vite + TS + react-i18next (frontend). LLM via `get_llm_client("standard")` (Gemini); safety via `moderate_output`.

**Spec:** `docs/superpowers/specs/2026-06-19-content-localization-pipeline-design.md`
**Branch:** `testing`. Carries a prod DB migration → ask the snapshot question before prod.

---

## File Structure

- Create `backend/app/models/content_translation.py` — the `ContentTranslation` model.
- Create `backend/alembic/versions/<rev>_content_translations.py` — additive table.
- Create `backend/app/services/content_i18n.py` — `extract`/`source_hash`/`apply` (single source of truth for translatable fields) + structural validation.
- Create `backend/app/services/translation_service.py` — `translate_entity` + batch helper.
- Modify `backend/app/services/app_settings.py` — enabled-content-languages getter/setter.
- Modify `backend/app/routers/admin.py` + `backend/app/schemas/admin.py` — generate/curated/coverage endpoints + content-languages setting field.
- Create `backend/app/services/content_localize.py` — the `localize` serving helper + per-request translation loader.
- Modify `backend/app/routers/content.py` + `backend/app/schemas/content.py` — wire `localize`, add `machine_translated`.
- Modify `backend/app/services/next_lesson_service.py`, `backend/app/services/revise_service.py` — localize served content text.
- Frontend: `frontend/src/api/content.ts` (+ revise/next types), a `MachineTranslatedBadge` component + mounts, `frontend/src/api/admin.ts` + admin settings/translations UI, `frontend/src/locales/en/*` keys.
- Tests under `backend/tests/` and `frontend/src/**/__tests__/`.

---

### Task 1: `ContentTranslation` model + migration

**Files:**
- Create: `backend/app/models/content_translation.py`, `backend/alembic/versions/c2e5f8a9b0c1_content_translations.py`
- Modify: `backend/app/models/__init__.py` (export, if the repo registers models there)
- Test: `backend/tests/test_content_translation_model.py`

- [ ] **Step 1: Model**

Create `backend/app/models/content_translation.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentTranslation(Base):
    """A stored translation of one content entity's translatable fields into one
    language. One row per (entity_type, entity_id, language)."""

    __tablename__ = "content_translations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(10), nullable=False)  # module|level|lesson
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default="auto")  # curated|auto
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")  # active|failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "language", name="uq_content_translation"),
        Index("ix_content_translation_type_lang", "entity_type", "language"),
    )
```

If `backend/app/models/__init__.py` imports models for metadata registration, add `from app.models.content_translation import ContentTranslation`.

- [ ] **Step 2: Failing test**

Create `backend/tests/test_content_translation_model.py`:

```python
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.content_translation import ContentTranslation

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unique_per_entity_language(db_session):
    eid = uuid.uuid4()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=eid, language="fr",
        translated_json={"title": "Bonjour"}, source="auto", source_hash="abc", status="active",
    ))
    await db_session.flush()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=eid, language="fr",
        translated_json={"title": "Salut"}, source="auto", source_hash="def", status="active",
    ))
    with pytest.raises(IntegrityError):
        await db_session.flush()
```

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_translation_model.py -v` → expect FAIL (no table).

- [ ] **Step 3: Migration**

Confirm head: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → expect `b1d4e5f6a7c8`. Pick a free id: `grep -rl "c2e5f8a9b0c1" backend/alembic/versions/ || echo FREE`. Create `backend/alembic/versions/c2e5f8a9b0c1_content_translations.py`:

```python
"""content_translations table

Revision ID: c2e5f8a9b0c1
Revises: b1d4e5f6a7c8
Create Date: 2026-06-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c2e5f8a9b0c1"
down_revision = "b1d4e5f6a7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("translated_json", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False, server_default="auto"),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("entity_type", "entity_id", "language", name="uq_content_translation"),
    )
    op.create_index("ix_content_translation_type_lang", "content_translations", ["entity_type", "language"])


def downgrade() -> None:
    op.drop_index("ix_content_translation_type_lang", table_name="content_translations")
    op.drop_table("content_translations")
```

- [ ] **Step 4: Apply + test**

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head` then `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_translation_model.py -v` → PASS. Ruff the touched files. (If the local DB hangs >90s, defer the apply to CI.)

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/models/content_translation.py backend/app/models/__init__.py backend/alembic/versions/c2e5f8a9b0c1_content_translations.py backend/tests/test_content_translation_model.py && git commit -m "feat(i18n): content_translations model + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Translatable-field extraction (`content_i18n.py`)

**Files:**
- Create: `backend/app/services/content_i18n.py`
- Test: `backend/tests/test_content_i18n.py`

The translatable fields (verified against `seed/content.py`):
- **module**: `title`, `conversation_prompt` (omit if None).
- **level**: `title`, `learning_objectives` (list[str], omit if None/empty).
- **lesson** by `type`: `card` → `{title, body}`; `quiz` → `{question, choices: [...], explanation}`; `scenario` → `{prompt, choices: [{label, outcome}]}`; `video` → `{caption}`. **Excluded**: `answer_index`, `correct_index`, `youtube_id`, `transcript`, `captions_available`, ids, xp.

- [ ] **Step 1: Failing test**

Create `backend/tests/test_content_i18n.py`:

```python
from app.services.content_i18n import apply_bundle, extract_bundle, source_hash


class FakeModule:
    title = "What is a Stock?"
    conversation_prompt = "Ask them what they own."


class FakeLesson:
    type = "quiz"
    content_json = {
        "question": "Q?", "choices": ["a", "b"], "answer_index": 1, "explanation": "because",
    }


def test_extract_module():
    b = extract_bundle("module", FakeModule())
    assert b == {"title": "What is a Stock?", "conversation_prompt": "Ask them what they own."}


def test_extract_lesson_quiz_excludes_answer_index():
    b = extract_bundle("lesson", FakeLesson())
    assert b == {"question": "Q?", "choices": ["a", "b"], "explanation": "because"}
    assert "answer_index" not in b


def test_source_hash_stable_and_sensitive():
    h1 = source_hash({"a": "x", "b": ["y"]})
    h2 = source_hash({"b": ["y"], "a": "x"})  # key order irrelevant
    assert h1 == h2
    assert source_hash({"a": "x"}) != source_hash({"a": "z"})


def test_apply_overlays_translation_keeping_excluded_fields():
    fields = {"question": "Q?", "choices": ["a", "b"], "answer_index": 1, "explanation": "because"}
    bundle = {"question": "Q-fr", "choices": ["a-fr", "b-fr"], "explanation": "parce que"}
    out = apply_bundle("lesson", fields, bundle)
    assert out["question"] == "Q-fr"
    assert out["choices"] == ["a-fr", "b-fr"]
    assert out["answer_index"] == 1  # untouched
```

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_i18n.py -v` → FAIL.

- [ ] **Step 2: Implement**

Create `backend/app/services/content_i18n.py`:

```python
from __future__ import annotations

import hashlib
import json
from typing import Any

# Translatable lesson content_json keys per lesson type. Scalars + list[str]
# unless noted. Anything not listed (ids, indices, youtube_id, transcript) is
# NEVER translated and is preserved verbatim on serve.
_LESSON_FIELDS: dict[str, list[str]] = {
    "card": ["title", "body"],
    "quiz": ["question", "choices", "explanation"],
    "scenario": ["prompt"],   # scenario.choices handled specially (list of {label, outcome})
    "video": ["caption"],
}


def extract_bundle(entity_type: str, entity: Any) -> dict:
    """The English bundle of translatable strings for an entity. Omits None/empty."""
    if entity_type == "module":
        out: dict[str, Any] = {"title": entity.title}
        if getattr(entity, "conversation_prompt", None):
            out["conversation_prompt"] = entity.conversation_prompt
        return out
    if entity_type == "level":
        out = {"title": entity.title}
        objs = getattr(entity, "learning_objectives", None)
        if objs:
            out["learning_objectives"] = list(objs)
        return out
    if entity_type == "lesson":
        cj = entity.content_json or {}
        keys = _LESSON_FIELDS.get(entity.type, [])
        out = {k: cj[k] for k in keys if k in cj and cj[k] not in (None, "")}
        # scenario choices: list of {label, outcome}
        if entity.type == "scenario" and isinstance(cj.get("choices"), list):
            out["choices"] = [
                {"label": c.get("label", ""), "outcome": c.get("outcome", "")}
                for c in cj["choices"]
            ]
        return out
    raise ValueError(f"unknown entity_type {entity_type!r}")


def source_hash(bundle: dict) -> str:
    return hashlib.sha256(
        json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def apply_bundle(entity_type: str, fields: dict, bundle: dict) -> dict:
    """Overlay a translation bundle onto an entity's served fields. For lesson,
    `fields` is the content_json; only translatable keys are overridden."""
    out = dict(fields)
    if entity_type in ("module", "level"):
        for k, v in bundle.items():
            out[k] = v
        return out
    # lesson: override content_json text keys; scenario choices merge by index
    for k, v in bundle.items():
        if k == "choices" and isinstance(v, list) and isinstance(out.get("choices"), list):
            merged = []
            for orig, tr in zip(out["choices"], v):
                if isinstance(orig, dict):  # scenario {label, outcome, ...}
                    m = dict(orig)
                    m["label"] = tr.get("label", orig.get("label"))
                    m["outcome"] = tr.get("outcome", orig.get("outcome"))
                    merged.append(m)
                else:  # quiz choices: plain strings
                    merged.append(tr)
            # keep any extra original choices if lengths differ (defensive)
            merged += out["choices"][len(v):]
            out["choices"] = merged
        else:
            out[k] = v
    return out


def validate_bundle(entity_type: str, source: dict, translated: dict) -> bool:
    """Structural validation: same keys; same option counts; non-empty strings."""
    if set(source.keys()) != set(translated.keys()):
        return False
    for k, sv in source.items():
        tv = translated.get(k)
        if isinstance(sv, str):
            if not isinstance(tv, str) or not tv.strip():
                return False
        elif isinstance(sv, list):
            if not isinstance(tv, list) or len(tv) != len(sv):
                return False
            for s_item, t_item in zip(sv, tv):
                if isinstance(s_item, dict):  # scenario choice
                    if not isinstance(t_item, dict):
                        return False
                    if not str(t_item.get("label", "")).strip() or not str(t_item.get("outcome", "")).strip():
                        return False
                elif not isinstance(t_item, str) or not t_item.strip():
                    return False
        else:
            return False
    return True
```

Run the test → PASS. Ruff.

- [ ] **Step 3: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/content_i18n.py backend/tests/test_content_i18n.py && git commit -m "feat(i18n): content translatable-field extraction + structural validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Translation service (`translation_service.py`)

**Files:**
- Create: `backend/app/services/translation_service.py`
- Test: `backend/tests/test_translation_service.py`

- [ ] **Step 1: Failing test** (mock the LLM client + moderation)

Create `backend/tests/test_translation_service.py`:

```python
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content_translation import ContentTranslation
from app.services.translation_service import translate_entity

pytestmark = pytest.mark.asyncio(loop_scope="session")


class FakeLesson:
    def __init__(self):
        self.id = uuid.uuid4()
        self.type = "card"
        self.content_json = {"title": "Hello", "body": "World"}


def _llm_returning(payload: dict):
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps(payload))
    return client


async def test_generates_auto_translation_and_stores(db_session):
    lesson = FakeLesson()
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour", "body": "Monde"})), \
         patch("app.services.translation_service.moderate_output",
               new=AsyncMock(return_value=type("R", (), {"allowed": True})())):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    assert action == "generated"
    assert row is not None and row.status == "active" and row.source == "auto"
    assert row.translated_json == {"title": "Bonjour", "body": "Monde"}


async def test_idempotent_skips_fresh(db_session):
    lesson = FakeLesson()
    mod = AsyncMock(return_value=type("R", (), {"allowed": True})())
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour", "body": "Monde"})), \
         patch("app.services.translation_service.moderate_output", new=mod):
        await translate_entity(db_session, "lesson", lesson, "fr")
        client2 = _llm_returning({"title": "X", "body": "Y"})
        with patch("app.services.translation_service.get_llm_client", return_value=client2):
            row, action = await translate_entity(db_session, "lesson", lesson, "fr")
            assert action == "skipped"
            client2.complete.assert_not_called()  # fresh → no second LLM call


async def test_structural_failure_marks_failed(db_session):
    lesson = FakeLesson()
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour"})), \
         patch("app.services.translation_service.moderate_output",
               new=AsyncMock(return_value=type("R", (), {"allowed": True})())):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    assert action == "failed"
    assert row is not None and row.status == "failed"


async def test_curated_not_overwritten(db_session):
    lesson = FakeLesson()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=lesson.id, language="fr",
        translated_json={"title": "Cur", "body": "Ated"}, source="curated",
        source_hash="whatever", status="active",
    ))
    await db_session.flush()
    client = _llm_returning({"title": "Auto", "body": "Gen"})
    with patch("app.services.translation_service.get_llm_client", return_value=client):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    client.complete.assert_not_called()
    assert action == "skipped" and row.source == "curated"
```

> The `moderate_output` mock returns an object with `.allowed`; if the real `ModerationResult`'s first field has a different name (it's a NamedTuple `(allowed, category, text)` — confirm by reading `backend/app/services/moderation.py`), make the service read the correct attribute and update the mock to match. The structural-failure case relies on `validate_bundle` rejecting a missing `body` key.

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_translation_service.py -v` → FAIL.

- [ ] **Step 2: Implement**

Create `backend/app/services/translation_service.py`:

```python
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.languages import is_supported_language
from app.models.content_translation import ContentTranslation
from app.services.content_i18n import (
    apply_bundle,  # noqa: F401  (kept for symmetry / future use)
    extract_bundle,
    source_hash,
    validate_bundle,
)
from app.services.llm_client import get_llm_client
from app.services.moderation import moderate_output

# Map BCP-47 code → human language name for the prompt.
from app.core.languages import SUPPORTED_LANGUAGES

_LANG_NAME = {str(x["code"]): str(x["prompt_name"]) for x in SUPPORTED_LANGUAGES}


def _prompt(language: str) -> str:
    name = _LANG_NAME.get(language, language)
    return (
        f"You are a professional translator localizing a children's financial-"
        f"education app into {name}. Translate ONLY the string values of the JSON "
        f"the user sends into {name}. Return a JSON object with the SAME keys and "
        f"the SAME array lengths. Keep numbers, currency symbols, proper nouns, "
        f"company names and ticker symbols unchanged. Do not add or remove keys. "
        f"For objects in arrays, translate only their text fields. Reply with JSON only."
    )


async def translate_entity(
    session: AsyncSession, entity_type: str, entity: Any, language: str
) -> tuple[ContentTranslation | None, str]:
    """Returns (row, action) where action ∈ {'generated','skipped','failed','noop'}."""
    if language == "en" or not is_supported_language(language):
        return None, "noop"
    bundle = extract_bundle(entity_type, entity)
    if not bundle:
        return None, "noop"
    h = source_hash(bundle)

    existing = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id == entity.id,
            ContentTranslation.language == language,
        )
    )
    if existing is not None:
        if existing.source == "curated":
            return existing, "skipped"  # never overwrite curated
        if existing.status == "active" and existing.source_hash == h:
            return existing, "skipped"  # fresh

    # Generate
    client = get_llm_client("standard")
    raw = await client.complete(
        _prompt(language),
        [{"role": "user", "content": json.dumps(bundle, ensure_ascii=False)}],
        temperature=0.2, max_tokens=1500, response_format="json",
    )
    status = "failed"
    translated: dict | None = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and validate_bundle(entity_type, bundle, parsed):
            verdict = await moderate_output(
                json.dumps(parsed, ensure_ascii=False), surface="content", language=language
            )
            if verdict.allowed:
                translated, status = parsed, "active"
    except (ValueError, TypeError, KeyError):
        translated, status = None, "failed"

    row = await _upsert(session, entity_type, entity.id, language, translated, h, status)
    return row, ("generated" if status == "active" else "failed")


async def _upsert(session, entity_type, entity_id, language, translated, h, status):
    row = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id == entity_id,
            ContentTranslation.language == language,
        )
    )
    payload = translated if translated is not None else {}
    if row is None:
        row = ContentTranslation(
            entity_type=entity_type, entity_id=entity_id, language=language,
            translated_json=payload, source="auto", source_hash=h, status=status,
        )
        session.add(row)
    else:
        row.translated_json = payload
        row.source = "auto"
        row.source_hash = h
        row.status = status
    await session.flush()
    return row
```

> Read `backend/app/services/moderation.py` and confirm the `ModerationResult` field name for "allowed" (likely a NamedTuple field — could be `allowed`, `safe`, or positional). Use the real attribute in `verdict.allowed`. Confirm `get_llm_client("standard")` and `.complete(...)` signature (it is: `complete(system_prompt, messages, temperature, max_tokens, response_format)`).

Run the test → PASS (fix the `verdict.allowed` attr name + mock to match reality). Ruff.

- [ ] **Step 3: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/translation_service.py backend/tests/test_translation_service.py && git commit -m "feat(i18n): translation service — Gemini auto-translate + structural/moderation gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Admin endpoints — generate, curated, coverage

**Files:**
- Modify: `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`
- Test: `backend/tests/test_admin_translations.py`

- [ ] **Step 1: Failing test** (mock `translate_entity` so no real LLM calls)

Create `backend/tests/test_admin_translations.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_coverage_empty(admin_client):
    r = await admin_client.get("/admin/translations/coverage?language=fr")
    assert r.status_code == 200
    body = r.json()
    assert "modules" in body and "lessons" in body  # per-entity-type buckets


async def test_curated_override_roundtrip(admin_client, gb_single_lesson):
    lesson_id = gb_single_lesson  # fixture/inline: create one GB lesson, return id
    r = await admin_client.put("/admin/translations/curated", json={
        "entity_type": "lesson", "entity_id": str(lesson_id), "language": "fr",
        "translated_json": {"title": "Bonjour", "body": "Monde"},
    })
    assert r.status_code == 200
    cov = await admin_client.get("/admin/translations/coverage?language=fr")
    assert cov.json()["lessons"]["active"] >= 1
```

> Build a single GB lesson inline if there's no fixture (mirror `test_market_completion_reward.py`'s content creation). The `generate` endpoint test can patch `translation_service.translate_entity` to a stub returning an `active` row, asserting the counts — add it if time permits; the curated + coverage paths are the must-haves.

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_translations.py -v` → FAIL.

- [ ] **Step 2: Schemas**

In `backend/app/schemas/admin.py`, add:

```python
class TranslationGenerateRequest(BaseModel):
    language: str
    market_code: str | None = None


class TranslationGenerateResult(BaseModel):
    translated: int = 0
    skipped_fresh: int = 0
    failed: int = 0


class CuratedTranslationRequest(BaseModel):
    entity_type: str  # module|level|lesson
    entity_id: uuid.UUID
    language: str
    translated_json: dict


class CoverageBucket(BaseModel):
    active: int = 0
    failed: int = 0
    missing: int = 0


class TranslationCoverageOut(BaseModel):
    language: str
    modules: CoverageBucket
    levels: CoverageBucket
    lessons: CoverageBucket
```

(Ensure `uuid` + `BaseModel` are imported in that file.)

- [ ] **Step 3: Endpoints**

In `backend/app/routers/admin.py`, add (under the admin auth dependency the other admin routes use). Iterate modules/levels/lessons; for generate, call `translate_entity` per entity; for coverage, count `ContentTranslation` rows by status vs total entities. Use the real content models (`Module`, `Level`, `Lesson`) and gate generate by `market_code` when supplied:

```python
@router.post("/translations/generate", response_model=TranslationGenerateResult)
async def generate_translations(
    body: TranslationGenerateRequest, session: AsyncSession = Depends(get_session),
):
    from app.models.content import Lesson, Level, Module
    from app.services.translation_service import translate_entity

    res = TranslationGenerateResult()
    mod_q = select(Module)
    if body.market_code:
        mod_q = mod_q.where(Module.market_code == body.market_code)
    modules = (await session.scalars(mod_q)).all()
    module_ids = [m.id for m in modules]
    levels = (await session.scalars(select(Level).where(Level.module_id.in_(module_ids)))).all() if module_ids else []
    lessons = (await session.scalars(select(Lesson).where(Lesson.module_id.in_(module_ids)))).all() if module_ids else []

    for etype, items in (("module", modules), ("level", levels), ("lesson", lessons)):
        for ent in items:
            _row, action = await translate_entity(session, etype, ent, body.language)
            if action == "generated":
                res.translated += 1
            elif action == "skipped":
                res.skipped_fresh += 1
            elif action == "failed":
                res.failed += 1
            # action == "noop" (empty bundle / unsupported) → not counted
    await session.commit()
    return res
```

(`translate_entity` returns `(row, action)` per Task 3 — `extract_bundle`/`source_hash` need not be re-imported here for the tally.)

Add `PUT /translations/curated` (validate structure via `validate_bundle` against the entity's extracted bundle; store `source="curated", status="active"`, `source_hash` of the CURRENT english bundle) and `GET /translations/coverage` (for each entity type: total entities in scope, count active/failed rows for the language, missing = total − active − failed). Return `TranslationCoverageOut`.

- [ ] **Step 4: Run + ruff + commit**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_translations.py -v` → PASS. Ruff.

```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_admin_translations.py && git commit -m "feat(i18n): admin translation generate/curated/coverage endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Content-language availability setting

**Files:**
- Modify: `backend/app/services/app_settings.py`, `backend/app/schemas/admin.py`, `backend/app/routers/admin.py`
- Test: `backend/tests/test_content_language_setting.py`

- [ ] **Step 1: Failing test**

```python
import pytest
from app.services.app_settings import get_enabled_content_languages, set_enabled_content_languages

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_defaults_empty_then_settable(db_session):
    assert await get_enabled_content_languages(db_session) == []
    await set_enabled_content_languages(db_session, ["fr", "es"])
    assert set(await get_enabled_content_languages(db_session)) == {"fr", "es"}


async def test_rejects_unsupported(db_session):
    with pytest.raises(ValueError):
        await set_enabled_content_languages(db_session, ["xx"])
```

Run → FAIL.

- [ ] **Step 2: Implement**

In `backend/app/services/app_settings.py` (mirror `set_alert_emails`'s JSON-list shape):

```python
_CONTENT_LANGUAGES_KEY = "content_languages.enabled"


async def get_enabled_content_languages(session: AsyncSession) -> list[str]:
    import json
    raw = await get_setting(session, _CONTENT_LANGUAGES_KEY)
    if raw:
        try:
            vals = json.loads(raw)
            if isinstance(vals, list):
                return [str(v) for v in vals]
        except (ValueError, TypeError):
            pass
    return []


async def set_enabled_content_languages(session: AsyncSession, langs: list[str]) -> None:
    import json
    from app.core.languages import is_supported_language
    for code in langs:
        if code == "en" or not is_supported_language(code):
            raise ValueError(f"unsupported content language {code!r}")
    await set_setting(session, _CONTENT_LANGUAGES_KEY, json.dumps(langs))
```

Wire into the admin `/settings` GET/PUT: add `enabled_content_languages: list[str] = []` to `AdminSettingsOut` and `enabled_content_languages: list[str] | None = None` to `AdminSettingsUpdate`; read in GET, set-if-not-None in PUT (mirror the D coin-bonus wiring exactly).

- [ ] **Step 3: Run + ruff + commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/app_settings.py backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/test_content_language_setting.py && git commit -m "feat(i18n): admin-flippable enabled-content-languages setting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Language-aware serving + `machine_translated`

**Files:**
- Create: `backend/app/services/content_localize.py`
- Modify: `backend/app/routers/content.py`, `backend/app/schemas/content.py`, `backend/app/services/next_lesson_service.py`, `backend/app/services/revise_service.py`
- Test: `backend/tests/test_content_localized_serving.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/test_content_localized_serving.py`. Create one GB module+lesson, a `ContentTranslation` (active, auto) for the lesson in `fr`, enable `fr` content, register a child with `language="fr"`, and assert the lesson detail serves French + `machine_translated=true`; a child with `language="en"` sees English + `machine_translated=false`; and with `fr` NOT enabled, the `fr` child still sees English (kill-switch). Mirror the auth + content-creation patterns from `test_market_completion_reward.py`.

```python
# skeleton — fill in fixtures per the repo's conventions
async def test_localized_lesson_served_when_enabled(client, db_session, ...):
    # ... create GB lesson, fr ContentTranslation(active, auto), enable fr ...
    r = await client.get(f"/lessons/{lesson_id}")   # as fr child
    assert r.json()["content_json"]["title"] == "<fr title>"
    assert r.json()["machine_translated"] is True

async def test_english_when_language_not_enabled(client, db_session, ...):
    # fr translation exists but fr NOT in enabled_content_languages
    r = await client.get(f"/lessons/{lesson_id}")   # as fr child
    assert r.json()["machine_translated"] is False
    assert r.json()["content_json"]["title"] == "<english title>"
```

Run → FAIL.

- [ ] **Step 2: Implement the helper**

Create `backend/app/services/content_localize.py`:

```python
from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_translation import ContentTranslation
from app.services.app_settings import get_enabled_content_languages
from app.services.content_i18n import apply_bundle


async def language_active(session: AsyncSession, language: str) -> bool:
    """Whether content should be localized for this language (kill-switch)."""
    if language == "en":
        return False
    return language in set(await get_enabled_content_languages(session))


async def load_translations(
    session: AsyncSession, entity_type: str, entity_ids: list[uuid.UUID], language: str
) -> dict[uuid.UUID, ContentTranslation]:
    if not entity_ids or language == "en":
        return {}
    rows = (await session.scalars(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.language == language,
            ContentTranslation.status == "active",
            ContentTranslation.entity_id.in_(entity_ids),
        )
    )).all()
    return {r.entity_id: r for r in rows}


def localize_fields(
    entity_type: str, fields: dict, translation: ContentTranslation | None
) -> tuple[dict, bool]:
    """Return (possibly-localized fields, machine_translated)."""
    if translation is None:
        return fields, False
    localized = apply_bundle(entity_type, fields, translation.translated_json)
    return localized, translation.source == "auto"
```

- [ ] **Step 3: Wire into the content router**

In `backend/app/schemas/content.py`, add `machine_translated: bool = False` to `ModuleOut`, `LessonOut`, and `LessonSummary`.

In `backend/app/routers/content.py`, for each serving site:
- compute `lang = current_user.language` and `active = await language_active(session, lang)`.
- `list_modules`: if `active`, `load_translations("module", [m.id...], lang)`; for each module build `title` via `localize_fields("module", {"title": m.title, "conversation_prompt": ...}, tr.get(m.id))` → use the localized `title`, set `machine_translated`.
- `module lessons` / `level lessons` summaries: localize the `title` (derived via `derive_lesson_title` on the localized `content_json`) — load lesson translations, and for the summary `title`, apply the bundle to `content_json` then derive the title; set `machine_translated`.
- `lesson detail` (`GET /lessons/{id}`): localize the full `content_json` via `localize_fields("lesson", lesson.content_json or {}, tr)`; set `machine_translated`.

Keep English path a no-op (`active is False` → no loads, `machine_translated=False`). Read each builder and apply minimally.

- [ ] **Step 4: Wire next-lesson + revise**

In `next_lesson_service.py` and `revise_service.py`, wherever lesson/module text (title/content) is returned to the user, apply the same localize helper keyed on the user's language (load translations for the entities involved; fall back to English; carry `machine_translated` if those payloads expose it — if they don't surface a flag, at minimum serve the localized text). Read both services and localize the user-facing strings; keep English byte-identical.

- [ ] **Step 5: Run + ruff + commit**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_localized_serving.py -v` and the existing content/next-lesson/revise tests → PASS (no regression for English). Ruff.

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/content_localize.py backend/app/routers/content.py backend/app/schemas/content.py backend/app/services/next_lesson_service.py backend/app/services/revise_service.py backend/tests/test_content_localized_serving.py && git commit -m "feat(i18n): language-aware content serving + machine_translated label

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Frontend — machine-translated badge + admin translations UI

**Files:**
- Create: `frontend/src/components/child/MachineTranslatedBadge.tsx`
- Modify: lesson/module consumers to render the badge when `machine_translated`; `frontend/src/api/content.ts` types; `frontend/src/api/admin.ts` + admin settings/translations UI; `frontend/src/locales/en/*` keys.
- Test: `frontend/src/components/child/__tests__/MachineTranslatedBadge.test.tsx`

- [ ] **Step 1: Failing test**

```typescript
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
import { MachineTranslatedBadge } from '../MachineTranslatedBadge';

describe('MachineTranslatedBadge', () => {
  it('renders the label', () => {
    render(<MachineTranslatedBadge />);
    expect(screen.getByText(/machineTranslated/i)).toBeInTheDocument();
  });
  it('a11y clean', async () => {
    const { container } = render(<MachineTranslatedBadge />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Implement badge + types**

Create `frontend/src/components/child/MachineTranslatedBadge.tsx` (sky-blue muted chip, i18n key `common:machineTranslated` = "Machine-translated"; small, `text-xs`, muted). Add `machine_translated?: boolean` to the lesson/module TS types in `frontend/src/api/content.ts`. Render the badge in the lesson view (`Lesson.tsx`) and module/lesson lists where the flag is true — read those components and add a minimal mount.

- [ ] **Step 3: Admin translations UI**

In `frontend/src/api/admin.ts`, add types + calls for generate (`POST /admin/translations/generate`), coverage (`GET /admin/translations/coverage`), and the `enabled_content_languages` field on admin settings. In the admin settings page, add: a multi-select / checkboxes to toggle `enabled_content_languages`, and a small "Generate translations" control (pick language → POST generate → show counts) + a coverage display. Mirror existing admin settings markup; all strings i18n'd (admin namespace). Keep it functional, not fancy.

- [ ] **Step 4: Verify + commit**

Run: `cd frontend && npx tsc -b && npm run lint && npx vitest run src/components/child/__tests__/MachineTranslatedBadge.test.tsx` → clean + PASS.

```bash
cd /Users/leeashmore/investikid && git add frontend/src/components/child/MachineTranslatedBadge.tsx frontend/src/api/content.ts frontend/src/api/admin.ts frontend/src/pages/child/Lesson.tsx frontend/src/locales/en && git add -A frontend/src/components/admin frontend/src/pages && git commit -m "feat(i18n): machine-translated badge + admin translations/coverage UI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(Adjust `git add` to exactly the files changed.)

---

### Task 8: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`. All green. The key regression: an `en` user's content is byte-identical (no localize path taken).
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. All green; `no-literal-string` clean.
- [ ] **Step 3: Smoke the pipeline locally (optional but recommended)** — with a real LLM key absent, the unit tests mock it; do NOT call the live LLM in CI. Note in the PR that an operator runs `POST /admin/translations/generate` post-deploy.
- [ ] **Step 4: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (badge is UI-visible).
- [ ] **Step 5: Push + green CI** — `git push origin testing`; watch all jobs green (Backend runs).
- [ ] **Step 6: Promote (snapshot question)** — carries a prod migration (`content_translations`). **Ask whether to snapshot prod first.** Merge testing→staging→main on green CI (Railway applies `alembic upgrade head`), then the manual Vercel prod deploy. Verify `/health` 200. E1 ships **inert** (no content language enabled, no translations generated) — confirm an `en` user sees no change. Hand off to the operator: generate a language batch → review coverage → optionally add curated overrides → enable the language.

---

## Self-Review

**Spec coverage:**
- Unit 1 `ContentTranslation` model + migration → Task 1. ✓
- Unit 2 extraction (extract/source_hash/apply, transcript-excluded) → Task 2. ✓
- Unit 3 translation service (idempotency/staleness/curated + structural+moderation gate) → Task 3. ✓
- Unit 4 admin generate/curated/coverage → Task 4. ✓
- Unit 5 language-aware serving (localize, English no-op) → Task 6. ✓
- Unit 6 `machine_translated` label + badge → Task 6 (schema) + Task 7 (UI). ✓
- Unit 7 content-language availability kill-switch (gates serving) → Task 5 (setting) + Task 6 (`language_active` gate). ✓
- Unit 8 migration → Task 1. ✓
- Scope = no transcripts → Task 2 (`_LESSON_FIELDS` excludes transcript). ✓
- Rollout: inert-on-deploy, snapshot question, testing→staging→main, Vercel → Task 8. ✓

**Placeholder scan:** No TBDs. `translate_entity` now returns `(row, action)` consistently across Task 3 (impl + tests) and Task 4 (tally). Model/migration/extraction/service code is complete; serving + admin-UI wiring are precise read-then-mount instructions against named sites (consistent with this codebase's plans).

**Type/name consistency:** `extract_bundle`/`source_hash`/`apply_bundle`/`validate_bundle` (Task 2) consumed in Tasks 3, 4, 6. `translate_entity` returns `(row, action)` (Task 3) and Task 4 tallies on `action`. `ContentTranslation` (Task 1) used in Tasks 3, 4, 6. `get_enabled_content_languages`/`set_enabled_content_languages` (Task 5) used in Task 6's `language_active` + admin. `machine_translated` added to schemas (Task 6) and rendered (Task 7). `localize_fields`/`load_translations`/`language_active` (Task 6) consistent. Migration `c2e5f8a9b0c1` chains `b1d4e5f6a7c8`. **One verification flagged inline for the implementer:** confirm the `ModerationResult` "allowed" attribute name in `backend/app/services/moderation.py` (Task 3) and read the real `.complete()` signature before finalizing.
```
