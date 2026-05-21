# Content Management Admin Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based admin panel for creating, editing, reordering, and deleting modules/lessons, badges, and challenges — replacing seed-file-based content management.

**Architecture:** Bearer-token auth via `ADMIN_TOKEN` env var. New `/admin` FastAPI router. Frontend `/admin` route in existing React app with sidebar nav, flat CRUD pages, and type-specific lesson editors.

**Tech Stack:** FastAPI, SQLAlchemy async, React 18, TypeScript, TanStack Query, Tailwind CSS, Radix UI

---

### Task 1: Backend — Admin Auth + Config + CORS/CSRF Updates

**Files:**
- Modify: `backend/app/core/config.py` (add `admin_token` setting)
- Create: `backend/app/routers/admin_auth.py` (auth dependency)
- Modify: `backend/app/core/csrf.py` (exempt `/admin/` prefix)
- Modify: `backend/app/main.py` (add `PUT` to CORS methods, `Authorization` to CORS headers)
- Create: `backend/tests/test_admin_auth.py`

- [ ] **Step 1: Write failing tests for admin auth**

Create `backend/tests/test_admin_auth.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-token-xyz"}


@pytest.mark.asyncio
async def test_admin_stats_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/stats")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing or invalid admin token"


@pytest.mark.asyncio
async def test_admin_stats_rejects_bad_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/stats", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_accepts_valid_token(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_auth.py -v`
Expected: FAIL — no `/admin/stats` endpoint, no admin auth

- [ ] **Step 3: Add `admin_token` to config**

In `backend/app/core/config.py`, add to the `Settings` class after `privacy_notice_version`:

```python
    # Admin panel
    admin_token: str = "test-admin-token-xyz"
```

- [ ] **Step 4: Create admin auth dependency**

Create `backend/app/routers/admin_auth.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


async def get_current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None or creds.credentials != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin token",
        )
    return "admin"
```

- [ ] **Step 5: Create minimal admin router with /stats endpoint**

Create `backend/app/routers/admin.py`:

```python
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.gamification import Badge, Challenge
from app.routers.admin_auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    modules = await session.scalar(select(func.count()).select_from(Module))
    lessons = await session.scalar(select(func.count()).select_from(Lesson))
    badges = await session.scalar(select(func.count()).select_from(Badge))
    challenges = await session.scalar(select(func.count()).select_from(Challenge))
    return {
        "modules": modules or 0,
        "lessons": lessons or 0,
        "badges": badges or 0,
        "challenges": challenges or 0,
    }
```

- [ ] **Step 6: Register router + update CORS + exempt CSRF**

In `backend/app/main.py`:

1. Add import: `from app.routers import admin as admin_router`
2. Add after `billing_router` include: `application.include_router(admin_router.router)`
3. Update CORS `allow_methods` to include `"PUT"`:
   `allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],`
4. Update CORS `allow_headers` to include `"Authorization"`:
   `allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],`

In `backend/app/core/csrf.py`, add `/admin/` to the exempt prefixes:

```python
_DEFAULT_EXEMPT_PREFIXES = ("/consent/request/", "/admin/")
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_auth.py -v`
Expected: 3/3 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/config.py backend/app/routers/admin_auth.py backend/app/routers/admin.py backend/app/main.py backend/app/core/csrf.py backend/tests/test_admin_auth.py
git commit -m "feat(admin): add admin auth, config, stats endpoint, CORS/CSRF updates"
```

---

### Task 2: Backend — Admin Schemas + Content JSON Validation

**Files:**
- Create: `backend/app/schemas/admin.py`
- Create: `backend/tests/test_admin_schemas.py`

- [ ] **Step 1: Write failing tests for content JSON validation**

Create `backend/tests/test_admin_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.admin import LessonCreate


def test_card_lesson_valid():
    lesson = LessonCreate(
        type="card",
        content_json={"title": "Test", "body": "Body text"},
        xp_reward=10,
        order_index=0,
    )
    assert lesson.content_json["title"] == "Test"


def test_card_lesson_missing_body():
    with pytest.raises(ValidationError, match="Card requires.*body"):
        LessonCreate(
            type="card",
            content_json={"title": "Test"},
            xp_reward=10,
            order_index=0,
        )


def test_quiz_lesson_valid():
    lesson = LessonCreate(
        type="quiz",
        content_json={
            "question": "Q?",
            "choices": ["A", "B", "C"],
            "answer_index": 1,
            "explanation": "Because B",
        },
        xp_reward=25,
        order_index=0,
    )
    assert lesson.type == "quiz"


def test_quiz_lesson_too_few_choices():
    with pytest.raises(ValidationError, match="at least 2 choices"):
        LessonCreate(
            type="quiz",
            content_json={
                "question": "Q?",
                "choices": ["A"],
                "answer_index": 0,
                "explanation": "Exp",
            },
            xp_reward=25,
            order_index=0,
        )


def test_quiz_lesson_invalid_answer_index():
    with pytest.raises(ValidationError, match="answer_index"):
        LessonCreate(
            type="quiz",
            content_json={
                "question": "Q?",
                "choices": ["A", "B"],
                "answer_index": 5,
                "explanation": "Exp",
            },
            xp_reward=25,
            order_index=0,
        )


def test_scenario_lesson_valid():
    lesson = LessonCreate(
        type="scenario",
        content_json={
            "prompt": "Scenario prompt",
            "choices": [
                {"label": "A", "outcome": "Result A"},
                {"label": "B", "outcome": "Result B"},
            ],
            "correct_index": 0,
        },
        xp_reward=20,
        order_index=0,
    )
    assert lesson.type == "scenario"


def test_scenario_lesson_missing_outcome():
    with pytest.raises(ValidationError, match="label.*outcome"):
        LessonCreate(
            type="scenario",
            content_json={
                "prompt": "P",
                "choices": [{"label": "A"}],
                "correct_index": 0,
            },
            xp_reward=20,
            order_index=0,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_schemas.py -v`
Expected: FAIL — `app.schemas.admin` does not exist

- [ ] **Step 3: Create admin schemas**

Create `backend/app/schemas/admin.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


# ── Module ──────────────────────────────────────────────────────────
class ModuleCreate(BaseModel):
    topic: str
    title: str
    icon: str = "📚"
    is_premium: bool = False
    country_codes: list[str] = []
    order_index: int


class ModuleUpdate(BaseModel):
    topic: str | None = None
    title: str | None = None
    icon: str | None = None
    is_premium: bool | None = None
    country_codes: list[str] | None = None


class ModuleOut(BaseModel):
    id: uuid.UUID
    topic: str
    title: str
    icon: str
    is_premium: bool
    country_codes: list[str]
    order_index: int
    lesson_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── Lesson ──────────────────────────────────────────────────────────
class LessonCreate(BaseModel):
    type: Literal["card", "quiz", "scenario"]
    content_json: dict
    xp_reward: int
    order_index: int

    @field_validator("content_json")
    @classmethod
    def validate_content(cls, v: dict, info) -> dict:
        lesson_type = info.data.get("type")
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
        return v


class LessonUpdate(BaseModel):
    type: Literal["card", "quiz", "scenario"] | None = None
    content_json: dict | None = None
    xp_reward: int | None = None


class LessonOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    type: str
    content_json: dict
    xp_reward: int
    order_index: int

    model_config = ConfigDict(from_attributes=True)


# ── Badge ───────────────────────────────────────────────────────────
class BadgeCreate(BaseModel):
    name: str
    description: str
    icon_url: str
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"]
    condition_value: int


class BadgeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"] | None = None
    condition_value: int | None = None


class BadgeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    condition_type: str
    condition_value: int

    model_config = ConfigDict(from_attributes=True)


# ── Challenge ───────────────────────────────────────────────────────
class ChallengeCreate(BaseModel):
    title: str
    description: str
    type: Literal["lessons_completed", "xp_earned", "streak"]
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool = False


class ChallengeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: Literal["lessons_completed", "xp_earned", "streak"] | None = None
    target_value: int | None = None
    xp_reward: int | None = None
    badge_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_premium: bool | None = None


class ChallengeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    type: str
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool

    model_config = ConfigDict(from_attributes=True)


# ── Reorder ─────────────────────────────────────────────────────────
class ReorderItem(BaseModel):
    id: uuid.UUID
    order_index: int


class ReorderRequest(BaseModel):
    order: list[ReorderItem]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_schemas.py -v`
Expected: 7/7 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/admin.py backend/tests/test_admin_schemas.py
git commit -m "feat(admin): add admin schemas with content_json validation"
```

---

### Task 3: Backend — Module & Lesson CRUD Endpoints

**Files:**
- Modify: `backend/app/routers/admin.py` (add module + lesson endpoints)
- Create: `backend/tests/test_admin_modules.py`

- [ ] **Step 1: Write failing tests for module CRUD**

Create `backend/tests/test_admin_modules.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

HEADERS = {"Authorization": "Bearer test-admin-token-xyz"}


@pytest.mark.asyncio
async def test_module_crud_lifecycle():
    """Create → read → update → reorder → delete a module."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        resp = await ac.post("/admin/modules", json={
            "topic": "test_topic", "title": "Test Module", "icon": "🧪",
            "is_premium": False, "country_codes": [], "order_index": 0,
        }, headers=HEADERS)
        assert resp.status_code == 200
        module = resp.json()
        module_id = module["id"]
        assert module["topic"] == "test_topic"
        assert module["lesson_count"] == 0

        # List
        resp = await ac.get("/admin/modules", headers=HEADERS)
        assert resp.status_code == 200
        modules = resp.json()
        assert any(m["id"] == module_id for m in modules)

        # Update
        resp = await ac.put(f"/admin/modules/{module_id}", json={
            "title": "Updated Module",
        }, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Module"

        # Delete
        resp = await ac.delete(f"/admin/modules/{module_id}", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify deleted
        resp = await ac.get("/admin/modules", headers=HEADERS)
        assert not any(m["id"] == module_id for m in resp.json())


@pytest.mark.asyncio
async def test_lesson_crud_lifecycle():
    """Create module → add lessons → reorder → update → delete."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create module first
        resp = await ac.post("/admin/modules", json={
            "topic": "lessons_test", "title": "Lesson Test Module", "icon": "📝",
            "is_premium": False, "country_codes": [], "order_index": 0,
        }, headers=HEADERS)
        module_id = resp.json()["id"]

        # Create card lesson
        resp = await ac.post(f"/admin/modules/{module_id}/lessons", json={
            "type": "card",
            "content_json": {"title": "Card Title", "body": "Card body"},
            "xp_reward": 10, "order_index": 0,
        }, headers=HEADERS)
        assert resp.status_code == 200
        lesson_id = resp.json()["id"]
        assert resp.json()["type"] == "card"

        # Create quiz lesson
        resp = await ac.post(f"/admin/modules/{module_id}/lessons", json={
            "type": "quiz",
            "content_json": {
                "question": "Q?", "choices": ["A", "B"],
                "answer_index": 0, "explanation": "Because A",
            },
            "xp_reward": 25, "order_index": 1,
        }, headers=HEADERS)
        assert resp.status_code == 200
        quiz_id = resp.json()["id"]

        # List lessons
        resp = await ac.get(f"/admin/modules/{module_id}/lessons", headers=HEADERS)
        assert len(resp.json()) == 2

        # Update lesson
        resp = await ac.put(f"/admin/lessons/{lesson_id}", json={
            "content_json": {"title": "Updated Card", "body": "Updated body"},
        }, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["content_json"]["title"] == "Updated Card"

        # Delete lesson
        resp = await ac.delete(f"/admin/lessons/{lesson_id}", headers=HEADERS)
        assert resp.status_code == 200

        # Verify lesson count
        resp = await ac.get(f"/admin/modules/{module_id}/lessons", headers=HEADERS)
        assert len(resp.json()) == 1

        # Cleanup module
        await ac.delete(f"/admin/modules/{module_id}", headers=HEADERS)


@pytest.mark.asyncio
async def test_module_reorder():
    """Create two modules, reorder them."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp1 = await ac.post("/admin/modules", json={
            "topic": "t1", "title": "First", "icon": "1️⃣",
            "order_index": 0, "country_codes": [],
        }, headers=HEADERS)
        id1 = resp1.json()["id"]

        resp2 = await ac.post("/admin/modules", json={
            "topic": "t2", "title": "Second", "icon": "2️⃣",
            "order_index": 1, "country_codes": [],
        }, headers=HEADERS)
        id2 = resp2.json()["id"]

        # Swap order
        resp = await ac.patch("/admin/modules/reorder", json={
            "order": [
                {"id": id1, "order_index": 1},
                {"id": id2, "order_index": 0},
            ],
        }, headers=HEADERS)
        assert resp.status_code == 200

        # Verify new order
        resp = await ac.get("/admin/modules", headers=HEADERS)
        modules = resp.json()
        m1 = next(m for m in modules if m["id"] == id1)
        m2 = next(m for m in modules if m["id"] == id2)
        assert m1["order_index"] == 1
        assert m2["order_index"] == 0

        # Cleanup
        await ac.delete(f"/admin/modules/{id1}", headers=HEADERS)
        await ac.delete(f"/admin/modules/{id2}", headers=HEADERS)


@pytest.mark.asyncio
async def test_lesson_content_validation_rejects_invalid():
    """Invalid content_json should return 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/admin/modules", json={
            "topic": "val_test", "title": "Validation Test", "icon": "⚠️",
            "order_index": 0, "country_codes": [],
        }, headers=HEADERS)
        module_id = resp.json()["id"]

        # Card missing body
        resp = await ac.post(f"/admin/modules/{module_id}/lessons", json={
            "type": "card", "content_json": {"title": "No body"},
            "xp_reward": 10, "order_index": 0,
        }, headers=HEADERS)
        assert resp.status_code == 422

        # Cleanup
        await ac.delete(f"/admin/modules/{module_id}", headers=HEADERS)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_modules.py -v`
Expected: FAIL — endpoints don't exist yet

- [ ] **Step 3: Implement module & lesson CRUD endpoints**

Replace `backend/app/routers/admin.py` with the full implementation:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.gamification import Badge, Challenge, UserBadge
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    BadgeCreate,
    BadgeOut,
    BadgeUpdate,
    ChallengeCreate,
    ChallengeOut,
    ChallengeUpdate,
    LessonCreate,
    LessonOut,
    LessonUpdate,
    ModuleCreate,
    ModuleOut,
    ModuleUpdate,
    ReorderRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# ── Stats ───────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    modules = await session.scalar(select(func.count()).select_from(Module))
    lessons = await session.scalar(select(func.count()).select_from(Lesson))
    badges = await session.scalar(select(func.count()).select_from(Badge))
    challenges = await session.scalar(select(func.count()).select_from(Challenge))
    return {
        "modules": modules or 0,
        "lessons": lessons or 0,
        "badges": badges or 0,
        "challenges": challenges or 0,
    }


# ── Modules ─────────────────────────────────────────────────────────
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
        )
        for m in modules
    ]


@router.post("/modules", response_model=ModuleOut)
async def create_module(payload: ModuleCreate, session: AsyncSession = Depends(get_session)):
    module = Module(
        topic=payload.topic, title=payload.title, icon=payload.icon,
        is_premium=payload.is_premium, country_codes=payload.country_codes,
        order_index=payload.order_index,
    )
    session.add(module)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=0,
    )


@router.put("/modules/{module_id}", response_model=ModuleOut)
async def update_module(
    module_id: uuid.UUID, payload: ModuleUpdate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id, options=[selectinload(Module.lessons)])
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(module, field, value)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=len(module.lessons),
    )


@router.delete("/modules/{module_id}")
async def delete_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    await session.delete(module)
    await session.commit()
    return {"status": "ok"}


@router.patch("/modules/reorder")
async def reorder_modules(payload: ReorderRequest, session: AsyncSession = Depends(get_session)):
    for item in payload.order:
        await session.execute(
            update(Module).where(Module.id == item.id).values(order_index=item.order_index)
        )
    await session.commit()
    return {"status": "ok"}


# ── Lessons ─────────────────────────────────────────────────────────
@router.get("/modules/{module_id}/lessons", response_model=list[LessonOut])
async def list_lessons(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order_index)
    )
    return list(result.all())


@router.post("/modules/{module_id}/lessons", response_model=LessonOut)
async def create_lesson(
    module_id: uuid.UUID, payload: LessonCreate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    lesson = Lesson(
        module_id=module_id, type=payload.type, content_json=payload.content_json,
        xp_reward=payload.xp_reward, order_index=payload.order_index,
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: uuid.UUID, payload: LessonUpdate, session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    update_data = payload.model_dump(exclude_unset=True)
    # If both type and content_json are being updated, validate together
    if "content_json" in update_data:
        effective_type = update_data.get("type", lesson.type)
        LessonCreate(
            type=effective_type, content_json=update_data["content_json"],
            xp_reward=update_data.get("xp_reward", lesson.xp_reward),
            order_index=lesson.order_index,
        )
    for field, value in update_data.items():
        setattr(lesson, field, value)
    await session.commit()
    await session.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await session.delete(lesson)
    await session.commit()
    return {"status": "ok"}


@router.patch("/modules/{module_id}/lessons/reorder")
async def reorder_lessons(
    module_id: uuid.UUID, payload: ReorderRequest, session: AsyncSession = Depends(get_session),
):
    for item in payload.order:
        await session.execute(
            update(Lesson).where(Lesson.id == item.id, Lesson.module_id == module_id)
            .values(order_index=item.order_index)
        )
    await session.commit()
    return {"status": "ok"}


# ── Badges ──────────────────────────────────────────────────────────
@router.get("/badges", response_model=list[BadgeOut])
async def list_badges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Badge))
    return list(result.all())


@router.post("/badges", response_model=BadgeOut)
async def create_badge(payload: BadgeCreate, session: AsyncSession = Depends(get_session)):
    badge = Badge(**payload.model_dump())
    session.add(badge)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.put("/badges/{badge_id}", response_model=BadgeOut)
async def update_badge(
    badge_id: uuid.UUID, payload: BadgeUpdate, session: AsyncSession = Depends(get_session),
):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(badge, field, value)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.delete("/badges/{badge_id}")
async def delete_badge(badge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    # Check for user references
    earned_count = await session.scalar(
        select(func.count()).select_from(UserBadge).where(UserBadge.badge_id == badge_id)
    )
    if earned_count and earned_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete badge — {earned_count} user(s) have earned it",
        )
    await session.delete(badge)
    await session.commit()
    return {"status": "ok"}


# ── Challenges ──────────────────────────────────────────────────────
@router.get("/challenges", response_model=list[ChallengeOut])
async def list_challenges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Challenge).order_by(Challenge.starts_at.desc()))
    return list(result.all())


@router.post("/challenges", response_model=ChallengeOut)
async def create_challenge(payload: ChallengeCreate, session: AsyncSession = Depends(get_session)):
    challenge = Challenge(**payload.model_dump())
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.put("/challenges/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(
    challenge_id: uuid.UUID, payload: ChallengeUpdate, session: AsyncSession = Depends(get_session),
):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(challenge, field, value)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.delete("/challenges/{challenge_id}")
async def delete_challenge(challenge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    await session.delete(challenge)
    await session.commit()
    return {"status": "ok"}


# ── Utility ─────────────────────────────────────────────────────────
@router.get("/countries")
async def list_countries(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(User.country_code).where(User.country_code.isnot(None)).distinct()
    )
    return sorted(result.all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_modules.py -v`
Expected: 4/4 PASS

- [ ] **Step 5: Run full backend test suite**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/ -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_admin_modules.py
git commit -m "feat(admin): add module, lesson, badge, challenge CRUD endpoints"
```

---

### Task 4: Backend — Badge & Challenge CRUD Tests

**Files:**
- Create: `backend/tests/test_admin_badges_challenges.py`

- [ ] **Step 1: Write tests for badge and challenge CRUD**

Create `backend/tests/test_admin_badges_challenges.py`:

```python
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient

from app.main import app

HEADERS = {"Authorization": "Bearer test-admin-token-xyz"}


@pytest.mark.asyncio
async def test_badge_crud_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        resp = await ac.post("/admin/badges", json={
            "name": "Test Badge",
            "description": "A test badge",
            "icon_url": "🏅",
            "condition_type": "lesson_count",
            "condition_value": 5,
        }, headers=HEADERS)
        assert resp.status_code == 200
        badge = resp.json()
        badge_id = badge["id"]
        assert badge["name"] == "Test Badge"

        # List
        resp = await ac.get("/admin/badges", headers=HEADERS)
        assert resp.status_code == 200
        assert any(b["id"] == badge_id for b in resp.json())

        # Update
        resp = await ac.put(f"/admin/badges/{badge_id}", json={
            "description": "Updated description",
        }, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

        # Delete
        resp = await ac.delete(f"/admin/badges/{badge_id}", headers=HEADERS)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_challenge_crud_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        resp = await ac.post("/admin/challenges", json={
            "title": "Test Challenge",
            "description": "Complete 3 lessons",
            "type": "lessons_completed",
            "target_value": 3,
            "xp_reward": 50,
            "starts_at": "2026-05-21T00:00:00Z",
            "ends_at": "2026-05-28T00:00:00Z",
            "is_premium": False,
        }, headers=HEADERS)
        assert resp.status_code == 200
        challenge = resp.json()
        challenge_id = challenge["id"]
        assert challenge["title"] == "Test Challenge"

        # List
        resp = await ac.get("/admin/challenges", headers=HEADERS)
        assert resp.status_code == 200
        assert any(c["id"] == challenge_id for c in resp.json())

        # Update
        resp = await ac.put(f"/admin/challenges/{challenge_id}", json={
            "title": "Updated Challenge",
        }, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Challenge"

        # Delete
        resp = await ac.delete(f"/admin/challenges/{challenge_id}", headers=HEADERS)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_countries_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/countries", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run tests**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_admin_badges_challenges.py -v`
Expected: 3/3 PASS (endpoints already implemented in Task 3)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_admin_badges_challenges.py
git commit -m "test(admin): add badge, challenge, and countries endpoint tests"
```

---

### Task 5: Frontend — Admin API Client + Auth Token Store

**Files:**
- Create: `frontend/src/api/admin.ts`
- Create: `frontend/src/lib/adminAuth.ts`

- [ ] **Step 1: Create admin auth helper**

Create `frontend/src/lib/adminAuth.ts`:

```typescript
const STORAGE_KEY = 'invest-ed-admin-token';

export function getAdminToken(): string | null {
  return sessionStorage.getItem(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEY, token);
}

export function clearAdminToken(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}
```

- [ ] **Step 2: Create admin API client**

Create `frontend/src/api/admin.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from './client';
import { getAdminToken, clearAdminToken } from '@/lib/adminAuth';

// ── Types ──────────────────────────────────────────────────────────
export interface AdminStats {
  modules: number;
  lessons: number;
  badges: number;
  challenges: number;
}

export interface AdminModule {
  id: string;
  topic: string;
  title: string;
  icon: string;
  is_premium: boolean;
  country_codes: string[];
  order_index: number;
  lesson_count: number;
}

export interface AdminLesson {
  id: string;
  module_id: string;
  type: 'card' | 'quiz' | 'scenario';
  content_json: Record<string, unknown>;
  xp_reward: number;
  order_index: number;
}

export interface AdminBadge {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  condition_type: string;
  condition_value: number;
}

export interface AdminChallenge {
  id: string;
  title: string;
  description: string;
  type: string;
  target_value: number;
  xp_reward: number;
  badge_id: string | null;
  starts_at: string;
  ends_at: string;
  is_premium: boolean;
}

// ── Fetch helper ───────────────────────────────────────────────────
async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  if (!token) throw new ApiError(401, 'No admin token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearAdminToken();
    throw new ApiError(401, 'Invalid admin token');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// ── Stats ──────────────────────────────────────────────────────────
export function useAdminStats() {
  return useQuery({ queryKey: ['admin', 'stats'], queryFn: () => adminFetch<AdminStats>('/admin/stats') });
}

// ── Modules ────────────────────────────────────────────────────────
export function useModules() {
  return useQuery({ queryKey: ['admin', 'modules'], queryFn: () => adminFetch<AdminModule[]>('/admin/modules') });
}

export function useCreateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminModule, 'id' | 'lesson_count'>) =>
      adminFetch<AdminModule>('/admin/modules', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'modules'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminModule, 'id' | 'lesson_count'>>) =>
      adminFetch<AdminModule>(`/admin/modules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'modules'] }),
  });
}

export function useDeleteModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/modules/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'modules'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useReorderModules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (order: { id: string; order_index: number }[]) =>
      adminFetch('/admin/modules/reorder', { method: 'PATCH', body: JSON.stringify({ order }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'modules'] }),
  });
}

// ── Lessons ────────────────────────────────────────────────────────
export function useLessons(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'lessons', moduleId],
    queryFn: () => adminFetch<AdminLesson[]>(`/admin/modules/${moduleId}/lessons`),
    enabled: !!moduleId,
  });
}

export function useCreateLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, ...data }: { moduleId: string } & Omit<AdminLesson, 'id' | 'module_id'>) =>
      adminFetch<AdminLesson>(`/admin/modules/${moduleId}/lessons`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['admin', 'lessons', vars.moduleId] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
  });
}

export function useUpdateLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminLesson, 'id' | 'module_id'>>) =>
      adminFetch<AdminLesson>(`/admin/lessons/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export function useDeleteLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/lessons/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin'] });
    },
  });
}

export function useReorderLessons() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, order }: { moduleId: string; order: { id: string; order_index: number }[] }) =>
      adminFetch(`/admin/modules/${moduleId}/lessons/reorder`, { method: 'PATCH', body: JSON.stringify({ order }) }),
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['admin', 'lessons', vars.moduleId] }),
  });
}

// ── Badges ─────────────────────────────────────────────────────────
export function useBadges() {
  return useQuery({ queryKey: ['admin', 'badges'], queryFn: () => adminFetch<AdminBadge[]>('/admin/badges') });
}

export function useCreateBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminBadge, 'id'>) =>
      adminFetch<AdminBadge>('/admin/badges', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'badges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminBadge, 'id'>>) =>
      adminFetch<AdminBadge>(`/admin/badges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'badges'] }),
  });
}

export function useDeleteBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/badges/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'badges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

// ── Challenges ─────────────────────────────────────────────────────
export function useChallenges() {
  return useQuery({ queryKey: ['admin', 'challenges'], queryFn: () => adminFetch<AdminChallenge[]>('/admin/challenges') });
}

export function useCreateChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminChallenge, 'id'>) =>
      adminFetch<AdminChallenge>('/admin/challenges', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminChallenge, 'id'>>) =>
      adminFetch<AdminChallenge>(`/admin/challenges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }),
  });
}

export function useDeleteChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/challenges/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

// ── Countries ──────────────────────────────────────────────────────
export function useCountries() {
  return useQuery({ queryKey: ['admin', 'countries'], queryFn: () => adminFetch<string[]>('/admin/countries') });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/adminAuth.ts frontend/src/api/admin.ts
git commit -m "feat(admin): add frontend admin API client and auth helpers"
```

---

### Task 6: Frontend — Admin Login + Layout + Dashboard + Routing

**Files:**
- Create: `frontend/src/components/admin/AdminLogin.tsx`
- Create: `frontend/src/components/admin/AdminLayout.tsx`
- Create: `frontend/src/components/admin/AdminSidebar.tsx`
- Create: `frontend/src/components/admin/AdminDashboard.tsx`
- Modify: `frontend/src/App.tsx` (add `/admin` routes)
- Create: `frontend/src/components/admin/__tests__/AdminLogin.test.tsx`
- Create: `frontend/src/components/admin/__tests__/AdminDashboard.test.tsx`

- [ ] **Step 1: Write failing tests for AdminLogin**

Create `frontend/src/components/admin/__tests__/AdminLogin.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AdminLogin from '../AdminLogin';

const mockSetToken = vi.fn();
vi.mock('@/lib/adminAuth', () => ({
  getAdminToken: () => null,
  setAdminToken: (t: string) => mockSetToken(t),
  clearAdminToken: vi.fn(),
}));

describe('AdminLogin', () => {
  beforeEach(() => { mockSetToken.mockClear(); });

  it('renders token input and submit button', () => {
    render(<AdminLogin onAuthenticated={vi.fn()} />);
    expect(screen.getByLabelText(/admin token/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls onAuthenticated when token is submitted', () => {
    const onAuth = vi.fn();
    render(<AdminLogin onAuthenticated={onAuth} />);
    fireEvent.change(screen.getByLabelText(/admin token/i), { target: { value: 'my-token' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(mockSetToken).toHaveBeenCalledWith('my-token');
    expect(onAuth).toHaveBeenCalled();
  });

  it('does not submit with empty token', () => {
    const onAuth = vi.fn();
    render(<AdminLogin onAuthenticated={onAuth} />);
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(onAuth).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Write failing tests for AdminDashboard**

Create `frontend/src/components/admin/__tests__/AdminDashboard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminDashboard from '../AdminDashboard';

vi.mock('@/api/admin', () => ({
  useAdminStats: () => ({
    data: { modules: 12, lessons: 49, badges: 5, challenges: 3 },
    isLoading: false,
  }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('AdminDashboard', () => {
  it('renders stat cards with counts', () => {
    render(<AdminDashboard />, { wrapper });
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('49')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders section headings', () => {
    render(<AdminDashboard />, { wrapper });
    expect(screen.getByText(/modules/i)).toBeInTheDocument();
    expect(screen.getByText(/badges/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin --reporter=verbose`
Expected: FAIL — components don't exist

- [ ] **Step 4: Implement AdminLogin**

Create `frontend/src/components/admin/AdminLogin.tsx`:

```tsx
import { useState } from 'react';
import { setAdminToken } from '@/lib/adminAuth';

interface AdminLoginProps {
  onAuthenticated: () => void;
}

export default function AdminLogin({ onAuthenticated }: AdminLoginProps) {
  const [token, setToken] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim()) return;
    setAdminToken(token.trim());
    onAuthenticated();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-8">
        <h1 className="mb-6 text-xl font-bold text-slate-50">📚 Invest-Ed Admin</h1>
        <label htmlFor="admin-token" className="mb-2 block text-sm text-slate-400">
          Admin Token
        </label>
        <input
          id="admin-token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="mb-4 w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          placeholder="Enter admin token"
          autoComplete="off"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: Implement AdminSidebar**

Create `frontend/src/components/admin/AdminSidebar.tsx`:

```tsx
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', icon: '📊', end: true },
  { to: '/admin/modules', label: 'Modules', icon: '📖', end: false },
  { to: '/admin/badges', label: 'Badges', icon: '🏆', end: false },
  { to: '/admin/challenges', label: 'Challenges', icon: '⚡', end: false },
];

export default function AdminSidebar() {
  return (
    <aside className="flex w-52 flex-col border-r border-slate-700 bg-slate-900 p-4">
      <div className="mb-6 text-lg font-bold text-slate-50">📚 Invest-Ed Admin</div>
      <nav className="flex flex-col gap-1" aria-label="Admin navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm ${
                isActive ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`
            }
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-slate-700 pt-4">
        <a href="/" className="text-sm text-slate-500 hover:text-slate-300">← Back to App</a>
      </div>
    </aside>
  );
}
```

- [ ] **Step 6: Implement AdminDashboard**

Create `frontend/src/components/admin/AdminDashboard.tsx`:

```tsx
import { useAdminStats } from '@/api/admin';

const CARDS = [
  { key: 'modules' as const, label: 'Modules', icon: '📖', color: 'text-green-400' },
  { key: 'lessons' as const, label: 'Lessons', icon: '📝', color: 'text-blue-400' },
  { key: 'badges' as const, label: 'Badges', icon: '🏆', color: 'text-yellow-400' },
  { key: 'challenges' as const, label: 'Challenges', icon: '⚡', color: 'text-orange-400' },
];

export default function AdminDashboard() {
  const { data: stats, isLoading } = useAdminStats();

  return (
    <div>
      <h2 className="mb-2 text-xl font-semibold text-slate-50">Dashboard</h2>
      <p className="mb-6 text-sm text-slate-400">Content overview</p>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div key={card.key} className="rounded-lg border border-slate-700 bg-slate-900 p-5">
            <div className="text-sm text-slate-500">{card.icon} {card.label}</div>
            <div className="mt-1 text-3xl font-bold text-slate-50">
              {isLoading ? '—' : stats?.[card.key] ?? 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Implement AdminLayout**

Create `frontend/src/components/admin/AdminLayout.tsx`:

```tsx
import { useState, useCallback, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { getAdminToken, clearAdminToken } from '@/lib/adminAuth';
import AdminLogin from './AdminLogin';
import AdminSidebar from './AdminSidebar';

export default function AdminLayout() {
  const [authed, setAuthed] = useState(() => !!getAdminToken());
  const navigate = useNavigate();

  const handleAuthenticated = useCallback(() => setAuthed(true), []);

  // Listen for 401 errors to log out
  useEffect(() => {
    function on401(e: Event) {
      if (e instanceof CustomEvent && e.detail?.status === 401) {
        clearAdminToken();
        setAuthed(false);
      }
    }
    window.addEventListener('admin-auth-error', on401);
    return () => window.removeEventListener('admin-auth-error', on401);
  }, []);

  if (!authed) return <AdminLogin onAuthenticated={handleAuthenticated} />;

  return (
    <div className="flex min-h-screen bg-slate-950">
      <AdminSidebar />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 8: Add admin routes to App.tsx**

Add import at top of `frontend/src/App.tsx`:
```tsx
import AdminLayout from '@/components/admin/AdminLayout';
import AdminDashboard from '@/components/admin/AdminDashboard';
```

Add routes before the `*` catch-all route:
```tsx
        {/* Admin routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
        </Route>
```

Placeholder routes for modules/badges/challenges pages will be added in later tasks.

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin --reporter=verbose`
Expected: All tests pass

- [ ] **Step 10: Run full frontend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run --reporter=verbose`
Expected: All 325+ existing tests still pass

- [ ] **Step 11: Commit**

```bash
git add frontend/src/components/admin/AdminLogin.tsx frontend/src/components/admin/AdminSidebar.tsx frontend/src/components/admin/AdminDashboard.tsx frontend/src/components/admin/AdminLayout.tsx frontend/src/App.tsx frontend/src/components/admin/__tests__/AdminLogin.test.tsx frontend/src/components/admin/__tests__/AdminDashboard.test.tsx
git commit -m "feat(admin): add admin login, layout, sidebar, dashboard, and routing"
```

---

### Task 7: Frontend — Shared Components (OrderArrows + ConfirmDialog)

**Files:**
- Create: `frontend/src/components/admin/OrderArrows.tsx`
- Create: `frontend/src/components/admin/ConfirmDialog.tsx`
- Create: `frontend/src/components/admin/__tests__/OrderArrows.test.tsx`
- Create: `frontend/src/components/admin/__tests__/ConfirmDialog.test.tsx`

- [ ] **Step 1: Write failing tests for OrderArrows**

Create `frontend/src/components/admin/__tests__/OrderArrows.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OrderArrows from '../OrderArrows';

describe('OrderArrows', () => {
  it('renders up and down buttons', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} />);
    expect(screen.getByRole('button', { name: /move up/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /move down/i })).toBeInTheDocument();
  });

  it('calls onMoveUp when up button clicked', () => {
    const onUp = vi.fn();
    render(<OrderArrows onMoveUp={onUp} onMoveDown={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /move up/i }));
    expect(onUp).toHaveBeenCalledTimes(1);
  });

  it('calls onMoveDown when down button clicked', () => {
    const onDown = vi.fn();
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={onDown} />);
    fireEvent.click(screen.getByRole('button', { name: /move down/i }));
    expect(onDown).toHaveBeenCalledTimes(1);
  });

  it('disables up button when isFirst', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} isFirst />);
    expect(screen.getByRole('button', { name: /move up/i })).toBeDisabled();
  });

  it('disables down button when isLast', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} isLast />);
    expect(screen.getByRole('button', { name: /move down/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Write failing tests for ConfirmDialog**

Create `frontend/src/components/admin/__tests__/ConfirmDialog.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ConfirmDialog from '../ConfirmDialog';

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(<ConfirmDialog open={false} title="Delete?" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByText('Delete?')).not.toBeInTheDocument();
  });

  it('renders title and message when open', () => {
    render(<ConfirmDialog open title="Delete Module?" message="This cannot be undone." onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText('Delete Module?')).toBeInTheDocument();
    expect(screen.getByText('This cannot be undone.')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open title="Delete?" onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button clicked', () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Delete?" onConfirm={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('has proper dialog role and aria-label', () => {
    render(<ConfirmDialog open title="Delete?" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Implement OrderArrows**

Create `frontend/src/components/admin/OrderArrows.tsx`:

```tsx
interface OrderArrowsProps {
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export default function OrderArrows({ onMoveUp, onMoveDown, isFirst, isLast }: OrderArrowsProps) {
  return (
    <div className="flex gap-1">
      <button
        type="button"
        onClick={onMoveUp}
        disabled={isFirst}
        aria-label="Move up"
        className="rounded px-1 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ↑
      </button>
      <button
        type="button"
        onClick={onMoveDown}
        disabled={isLast}
        aria-label="Move down"
        className="rounded px-1 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ↓
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Implement ConfirmDialog**

Create `frontend/src/components/admin/ConfirmDialog.tsx`:

```tsx
import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel }: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" role="dialog" aria-label={title}>
      <div className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-6">
        <h3 className="mb-2 text-lg font-semibold text-slate-50">{title}</h3>
        {message && <p className="mb-4 text-sm text-slate-400">{message}</p>}
        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-500"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin/__tests__/OrderArrows.test.tsx src/components/admin/__tests__/ConfirmDialog.test.tsx --reporter=verbose`
Expected: 10/10 PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/admin/OrderArrows.tsx frontend/src/components/admin/ConfirmDialog.tsx frontend/src/components/admin/__tests__/OrderArrows.test.tsx frontend/src/components/admin/__tests__/ConfirmDialog.test.tsx
git commit -m "feat(admin): add OrderArrows and ConfirmDialog shared components"
```

---

### Task 8: Frontend — ModuleList + ModuleForm Components

**Files:**
- Create: `frontend/src/components/admin/ModuleList.tsx`
- Create: `frontend/src/components/admin/ModuleForm.tsx`
- Create: `frontend/src/components/admin/__tests__/ModuleList.test.tsx`
- Create: `frontend/src/components/admin/__tests__/ModuleForm.test.tsx`
- Modify: `frontend/src/App.tsx` (add module routes)

- [ ] **Step 1: Write failing tests for ModuleList**

Create `frontend/src/components/admin/__tests__/ModuleList.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleList from '../ModuleList';

const mockModules = [
  { id: '1', topic: 'stocks', title: 'Intro to Stocks', icon: '📈', is_premium: false, country_codes: [], order_index: 0, lesson_count: 3 },
  { id: '2', topic: 'savings', title: 'Compound Interest', icon: '🏦', is_premium: true, country_codes: ['GB'], order_index: 1, lesson_count: 2 },
];

const mockReorder = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/admin', () => ({
  useModules: () => ({ data: mockModules, isLoading: false }),
  useReorderModules: () => ({ mutate: mockReorder }),
  useDeleteModule: () => ({ mutate: mockDelete }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ModuleList', () => {
  it('renders module titles', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText('Intro to Stocks')).toBeInTheDocument();
    expect(screen.getByText('Compound Interest')).toBeInTheDocument();
  });

  it('shows premium badge for premium modules', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
  });

  it('shows lesson count', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText(/3 lessons/i)).toBeInTheDocument();
  });

  it('renders new module button', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByRole('link', { name: /new module/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Write failing tests for ModuleForm**

Create `frontend/src/components/admin/__tests__/ModuleForm.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleForm from '../ModuleForm';

const mockCreate = vi.fn();
const mockUpdate = vi.fn();

vi.mock('@/api/admin', () => ({
  useModules: () => ({ data: [], isLoading: false }),
  useCreateModule: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateModule: () => ({ mutateAsync: mockUpdate, isPending: false }),
  useLessons: () => ({ data: [], isLoading: false }),
  useCountries: () => ({ data: ['GB', 'US'], isLoading: false }),
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

describe('ModuleForm', () => {
  it('renders form fields for create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByLabelText(/topic/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/icon/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/premium/i)).toBeInTheDocument();
  });

  it('renders save button', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Implement ModuleList**

Create `frontend/src/components/admin/ModuleList.tsx`:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useModules, useReorderModules, useDeleteModule } from '@/api/admin';
import OrderArrows from './OrderArrows';
import ConfirmDialog from './ConfirmDialog';
import type { AdminModule } from '@/api/admin';

export default function ModuleList() {
  const { data: modules = [], isLoading } = useModules();
  const reorder = useReorderModules();
  const deleteMod = useDeleteModule();
  const [deleteTarget, setDeleteTarget] = useState<AdminModule | null>(null);

  function handleMove(index: number, direction: 'up' | 'down') {
    const sorted = [...modules].sort((a, b) => a.order_index - b.order_index);
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;
    const updated = sorted.map((m, i) => {
      if (i === index) return { id: m.id, order_index: sorted[swapIdx].order_index };
      if (i === swapIdx) return { id: m.id, order_index: sorted[index].order_index };
      return { id: m.id, order_index: m.order_index };
    });
    reorder.mutate(updated);
  }

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  const sorted = [...modules].sort((a, b) => a.order_index - b.order_index);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Modules</h2>
        <Link
          to="/admin/modules/new"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
        >
          + New Module
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {sorted.map((m, i) => (
          <div
            key={m.id}
            className={`flex items-center gap-3 rounded-lg border bg-slate-900 p-3 ${
              m.is_premium ? 'border-yellow-500/30' : 'border-slate-700'
            }`}
          >
            <span className="text-xl">{m.icon}</span>
            <div className="flex-1">
              <div className="font-medium text-slate-50">{m.title}</div>
              <div className="text-xs text-slate-500">
                {m.topic} · {m.lesson_count} lessons
                {m.country_codes.length > 0 && ` · ${m.country_codes.join(', ')}`}
                {m.is_premium && <span className="ml-1 text-yellow-500">⭐ Premium</span>}
              </div>
            </div>
            <OrderArrows
              onMoveUp={() => handleMove(i, 'up')}
              onMoveDown={() => handleMove(i, 'down')}
              isFirst={i === 0}
              isLast={i === sorted.length - 1}
            />
            <Link to={`/admin/modules/${m.id}`} className="text-xs text-blue-400 hover:text-blue-300">
              Edit
            </Link>
            <button
              type="button"
              onClick={() => setDeleteTarget(m)}
              className="text-xs text-red-400 hover:text-red-300"
            >
              Delete
            </button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.title}"?`}
        message="This will permanently delete the module and all its lessons."
        onConfirm={() => { if (deleteTarget) deleteMod.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
```

- [ ] **Step 4: Implement ModuleForm**

Create `frontend/src/components/admin/ModuleForm.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useModules, useCreateModule, useUpdateModule,
  useLessons, useCreateLesson, useUpdateLesson, useDeleteLesson, useReorderLessons,
  useCountries,
} from '@/api/admin';
import type { AdminLesson } from '@/api/admin';
import OrderArrows from './OrderArrows';
import LessonForm from './LessonForm';
import ConfirmDialog from './ConfirmDialog';

export default function ModuleForm() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const isEdit = !!moduleId && moduleId !== 'new';

  const { data: modules = [] } = useModules();
  const existing = isEdit ? modules.find((m) => m.id === moduleId) : undefined;
  const { data: lessons = [] } = useLessons(isEdit ? moduleId : '');
  const { data: countries = [] } = useCountries();

  const createMod = useCreateModule();
  const updateMod = useUpdateModule();
  const createLesson = useCreateLesson();
  const updateLesson = useUpdateLesson();
  const deleteLesson = useDeleteLesson();
  const reorderLessons = useReorderLessons();

  const [topic, setTopic] = useState('');
  const [title, setTitle] = useState('');
  const [icon, setIcon] = useState('📚');
  const [isPremium, setIsPremium] = useState(false);
  const [countryCodes, setCountryCodes] = useState<string[]>([]);
  const [editingLesson, setEditingLesson] = useState<AdminLesson | null>(null);
  const [showNewLesson, setShowNewLesson] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminLesson | null>(null);

  useEffect(() => {
    if (existing) {
      setTopic(existing.topic);
      setTitle(existing.title);
      setIcon(existing.icon);
      setIsPremium(existing.is_premium);
      setCountryCodes(existing.country_codes);
    }
  }, [existing]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && moduleId) {
      await updateMod.mutateAsync({ id: moduleId, topic, title, icon, is_premium: isPremium, country_codes: countryCodes });
    } else {
      const maxOrder = modules.reduce((max, m) => Math.max(max, m.order_index), -1);
      await createMod.mutateAsync({ topic, title, icon, is_premium: isPremium, country_codes: countryCodes, order_index: maxOrder + 1 });
    }
    navigate('/admin/modules');
  }

  function toggleCountry(code: string) {
    setCountryCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function handleLessonMove(index: number, direction: 'up' | 'down') {
    const sorted = [...lessons].sort((a, b) => a.order_index - b.order_index);
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;
    const updated = sorted.map((l, i) => {
      if (i === index) return { id: l.id, order_index: sorted[swapIdx].order_index };
      if (i === swapIdx) return { id: l.id, order_index: sorted[index].order_index };
      return { id: l.id, order_index: l.order_index };
    });
    if (moduleId) reorderLessons.mutate({ moduleId, order: updated });
  }

  const sortedLessons = [...lessons].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="max-w-2xl">
      <h2 className="mb-4 text-xl font-semibold text-slate-50">
        {isEdit ? 'Edit Module' : 'New Module'}
      </h2>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div>
          <label htmlFor="mod-topic" className="mb-1 block text-sm text-slate-400">Topic</label>
          <input id="mod-topic" value={topic} onChange={(e) => setTopic(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="mod-title" className="mb-1 block text-sm text-slate-400">Title</label>
          <input id="mod-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="mod-icon" className="mb-1 block text-sm text-slate-400">Icon</label>
            <input id="mod-icon" value={icon} onChange={(e) => setIcon(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="flex items-end gap-2 pb-2">
            <input id="mod-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800" />
            <label htmlFor="mod-premium" className="text-sm text-slate-400">Premium</label>
          </div>
        </div>
        <div>
          <span className="mb-1 block text-sm text-slate-400">Countries (empty = global)</span>
          <div className="flex flex-wrap gap-2">
            {countries.map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => toggleCountry(code)}
                className={`rounded-md px-3 py-1 text-xs ${
                  countryCodes.includes(code)
                    ? 'bg-blue-600 text-white'
                    : 'border border-slate-600 bg-slate-800 text-slate-400'
                }`}
              >
                {code}
              </button>
            ))}
          </div>
        </div>

        {/* Lessons section — only in edit mode */}
        {isEdit && moduleId && (
          <div className="mt-4 border-t border-slate-700 pt-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-medium text-slate-50">Lessons ({sortedLessons.length})</h3>
              <button type="button" onClick={() => { setEditingLesson(null); setShowNewLesson(true); }}
                className="text-sm text-blue-400 hover:text-blue-300">+ Add Lesson</button>
            </div>
            <div className="flex flex-col gap-2">
              {sortedLessons.map((l, i) => (
                <div key={l.id} className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                  <OrderArrows
                    onMoveUp={() => handleLessonMove(i, 'up')}
                    onMoveDown={() => handleLessonMove(i, 'down')}
                    isFirst={i === 0}
                    isLast={i === sortedLessons.length - 1}
                  />
                  <span className={`rounded px-2 py-0.5 text-xs ${
                    l.type === 'card' ? 'bg-blue-500/20 text-blue-400'
                    : l.type === 'quiz' ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                  }`}>{l.type}</span>
                  <span className="flex-1 truncate text-sm text-slate-50">
                    {(l.content_json as Record<string, string>).title
                      || (l.content_json as Record<string, string>).question
                      || (l.content_json as Record<string, string>).prompt
                      || 'Untitled'}
                  </span>
                  <span className="text-xs text-slate-500">{l.xp_reward} XP</span>
                  <button type="button" onClick={() => { setEditingLesson(l); setShowNewLesson(false); }}
                    className="text-xs text-blue-400">Edit</button>
                  <button type="button" onClick={() => setDeleteTarget(l)}
                    className="text-xs text-red-400">Delete</button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 flex gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">
            Save
          </button>
          <button type="button" onClick={() => navigate('/admin/modules')}
            className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">
            Cancel
          </button>
        </div>
      </form>

      {/* Lesson edit/create modal */}
      {(editingLesson || showNewLesson) && moduleId && (
        <LessonForm
          moduleId={moduleId}
          lesson={editingLesson ?? undefined}
          nextOrderIndex={sortedLessons.length}
          onClose={() => { setEditingLesson(null); setShowNewLesson(false); }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete lesson?`}
        message="This will permanently delete this lesson."
        onConfirm={() => { if (deleteTarget) deleteLesson.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
```

- [ ] **Step 5: Add module routes to App.tsx**

In `frontend/src/App.tsx`, add imports:
```tsx
import ModuleList from '@/components/admin/ModuleList';
import ModuleForm from '@/components/admin/ModuleForm';
```

Add inside the admin `<Route>`:
```tsx
          <Route path="modules" element={<ModuleList />} />
          <Route path="modules/new" element={<ModuleForm />} />
          <Route path="modules/:moduleId" element={<ModuleForm />} />
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin/__tests__/ModuleList.test.tsx src/components/admin/__tests__/ModuleForm.test.tsx --reporter=verbose`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/admin/ModuleList.tsx frontend/src/components/admin/ModuleForm.tsx frontend/src/App.tsx frontend/src/components/admin/__tests__/ModuleList.test.tsx frontend/src/components/admin/__tests__/ModuleForm.test.tsx
git commit -m "feat(admin): add ModuleList and ModuleForm with inline lesson management"
```

---

### Task 9: Frontend — LessonForm Component (Type-Specific Editors)

**Files:**
- Create: `frontend/src/components/admin/LessonForm.tsx`
- Create: `frontend/src/components/admin/__tests__/LessonForm.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/admin/__tests__/LessonForm.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LessonForm from '../LessonForm';

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock('@/api/admin', () => ({
  useCreateLesson: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: mockUpdate, isPending: false }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('LessonForm', () => {
  it('renders type selector with card, quiz, scenario', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByRole('button', { name: /card/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /quiz/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /scenario/i })).toBeInTheDocument();
  });

  it('shows card fields by default', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/body/i)).toBeInTheDocument();
  });

  it('shows quiz fields when quiz type selected', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /quiz/i }));
    expect(screen.getByLabelText(/question/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/explanation/i)).toBeInTheDocument();
  });

  it('shows scenario fields when scenario type selected', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /scenario/i }));
    expect(screen.getByLabelText(/prompt/i)).toBeInTheDocument();
  });

  it('renders XP reward field', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByLabelText(/xp reward/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement LessonForm**

Create `frontend/src/components/admin/LessonForm.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useCreateLesson, useUpdateLesson } from '@/api/admin';
import type { AdminLesson } from '@/api/admin';

const TYPES = ['card', 'quiz', 'scenario'] as const;
type LessonType = (typeof TYPES)[number];

const DEFAULT_XP: Record<LessonType, number> = { card: 10, quiz: 25, scenario: 20 };

interface LessonFormProps {
  moduleId: string;
  lesson?: AdminLesson;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LessonForm({ moduleId, lesson, nextOrderIndex, onClose }: LessonFormProps) {
  const isEdit = !!lesson;
  const createLesson = useCreateLesson();
  const updateLesson = useUpdateLesson();

  const [type, setType] = useState<LessonType>((lesson?.type as LessonType) ?? 'card');
  const [xpReward, setXpReward] = useState(lesson?.xp_reward ?? DEFAULT_XP.card);

  // Card fields
  const [cardTitle, setCardTitle] = useState('');
  const [cardBody, setCardBody] = useState('');

  // Quiz fields
  const [question, setQuestion] = useState('');
  const [choices, setChoices] = useState<string[]>(['', '']);
  const [answerIndex, setAnswerIndex] = useState(0);
  const [explanation, setExplanation] = useState('');

  // Scenario fields
  const [prompt, setPrompt] = useState('');
  const [scenarioChoices, setScenarioChoices] = useState<{ label: string; outcome: string }[]>([
    { label: '', outcome: '' },
    { label: '', outcome: '' },
  ]);
  const [correctIndex, setCorrectIndex] = useState(0);

  // Load existing lesson data
  useEffect(() => {
    if (!lesson) return;
    const cj = lesson.content_json as Record<string, unknown>;
    if (lesson.type === 'card') {
      setCardTitle((cj.title as string) ?? '');
      setCardBody((cj.body as string) ?? '');
    } else if (lesson.type === 'quiz') {
      setQuestion((cj.question as string) ?? '');
      setChoices((cj.choices as string[]) ?? ['', '']);
      setAnswerIndex((cj.answer_index as number) ?? 0);
      setExplanation((cj.explanation as string) ?? '');
    } else if (lesson.type === 'scenario') {
      setPrompt((cj.prompt as string) ?? '');
      setScenarioChoices((cj.choices as { label: string; outcome: string }[]) ?? [{ label: '', outcome: '' }, { label: '', outcome: '' }]);
      setCorrectIndex((cj.correct_index as number) ?? 0);
    }
  }, [lesson]);

  function handleTypeChange(newType: LessonType) {
    setType(newType);
    setXpReward(DEFAULT_XP[newType]);
  }

  function buildContentJson(): Record<string, unknown> {
    if (type === 'card') return { title: cardTitle, body: cardBody };
    if (type === 'quiz') return { question, choices, answer_index: answerIndex, explanation };
    return { prompt, choices: scenarioChoices, correct_index: correctIndex };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const content_json = buildContentJson();
    if (isEdit && lesson) {
      await updateLesson.mutateAsync({ id: lesson.id, type, content_json, xp_reward: xpReward });
    } else {
      await createLesson.mutateAsync({ moduleId, type, content_json, xp_reward: xpReward, order_index: nextOrderIndex });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-lg border border-slate-700 bg-slate-900 p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="mb-4 text-lg font-semibold text-slate-50">
          {isEdit ? 'Edit Lesson' : 'New Lesson'}
        </h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Type selector */}
          <div className="flex gap-2">
            {TYPES.map((t) => (
              <button
                key={t}
                type="button"
                aria-label={t}
                onClick={() => handleTypeChange(t)}
                className={`rounded-full px-4 py-1 text-sm ${
                  type === t ? 'bg-blue-600 text-white' : 'border border-slate-600 text-slate-400'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* XP Reward */}
          <div>
            <label htmlFor="lesson-xp" className="mb-1 block text-sm text-slate-400">XP Reward</label>
            <input id="lesson-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))}
              className="w-24 rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>

          {/* Card fields */}
          {type === 'card' && (
            <>
              <div>
                <label htmlFor="card-title" className="mb-1 block text-sm text-slate-400">Title</label>
                <input id="card-title" value={cardTitle} onChange={(e) => setCardTitle(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <label htmlFor="card-body" className="mb-1 block text-sm text-slate-400">Body</label>
                <textarea id="card-body" value={cardBody} onChange={(e) => setCardBody(e.target.value)} required rows={3}
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
            </>
          )}

          {/* Quiz fields */}
          {type === 'quiz' && (
            <>
              <div>
                <label htmlFor="quiz-question" className="mb-1 block text-sm text-slate-400">Question</label>
                <input id="quiz-question" value={question} onChange={(e) => setQuestion(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-slate-400">Choices</span>
                {choices.map((c, i) => (
                  <div key={i} className="mb-2 flex items-center gap-2">
                    <input
                      type="radio"
                      name="quiz-answer"
                      checked={answerIndex === i}
                      onChange={() => setAnswerIndex(i)}
                      className="h-4 w-4"
                      aria-label={`Mark choice ${i + 1} as correct`}
                    />
                    <input
                      value={c}
                      onChange={(e) => { const nc = [...choices]; nc[i] = e.target.value; setChoices(nc); }}
                      className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-3 py-1 text-slate-50"
                      placeholder={`Choice ${i + 1}`}
                      required
                    />
                    {choices.length > 2 && (
                      <button type="button" onClick={() => {
                        const nc = choices.filter((_, j) => j !== i);
                        setChoices(nc);
                        if (answerIndex >= nc.length) setAnswerIndex(nc.length - 1);
                      }} className="text-red-400">✕</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => setChoices([...choices, ''])}
                  className="text-sm text-blue-400">+ Add Choice</button>
              </div>
              <div>
                <label htmlFor="quiz-explanation" className="mb-1 block text-sm text-slate-400">Explanation</label>
                <input id="quiz-explanation" value={explanation} onChange={(e) => setExplanation(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
            </>
          )}

          {/* Scenario fields */}
          {type === 'scenario' && (
            <>
              <div>
                <label htmlFor="scenario-prompt" className="mb-1 block text-sm text-slate-400">Prompt</label>
                <textarea id="scenario-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} required rows={2}
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-slate-400">Choices</span>
                {scenarioChoices.map((c, i) => (
                  <div key={i} className="mb-3 rounded-md border border-slate-700 bg-slate-800 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <input
                        type="radio"
                        name="scenario-correct"
                        checked={correctIndex === i}
                        onChange={() => setCorrectIndex(i)}
                        className="h-4 w-4"
                        aria-label={`Mark choice ${i + 1} as correct`}
                      />
                      <input
                        value={c.label}
                        onChange={(e) => { const nc = [...scenarioChoices]; nc[i] = { ...nc[i], label: e.target.value }; setScenarioChoices(nc); }}
                        className="flex-1 rounded-md border border-slate-600 bg-slate-900 px-3 py-1 text-slate-50"
                        placeholder="Label"
                        required
                      />
                      {scenarioChoices.length > 2 && (
                        <button type="button" onClick={() => {
                          const nc = scenarioChoices.filter((_, j) => j !== i);
                          setScenarioChoices(nc);
                          if (correctIndex >= nc.length) setCorrectIndex(nc.length - 1);
                        }} className="text-red-400">✕</button>
                      )}
                    </div>
                    <input
                      value={c.outcome}
                      onChange={(e) => { const nc = [...scenarioChoices]; nc[i] = { ...nc[i], outcome: e.target.value }; setScenarioChoices(nc); }}
                      className="ml-6 w-[calc(100%-1.5rem)] rounded-md border border-slate-600 bg-slate-900 px-3 py-1 text-sm text-slate-50"
                      placeholder="Outcome message"
                      required
                    />
                  </div>
                ))}
                <button type="button" onClick={() => setScenarioChoices([...scenarioChoices, { label: '', outcome: '' }])}
                  className="text-sm text-blue-400">+ Add Choice</button>
              </div>
            </>
          )}

          <div className="mt-2 flex gap-3">
            <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">
              {isEdit ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={onClose}
              className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin/__tests__/LessonForm.test.tsx --reporter=verbose`
Expected: 5/5 PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/admin/LessonForm.tsx frontend/src/components/admin/__tests__/LessonForm.test.tsx
git commit -m "feat(admin): add LessonForm with type-specific editors for card, quiz, scenario"
```

---

### Task 10: Frontend — BadgeList, BadgeForm, ChallengeList, ChallengeForm

**Files:**
- Create: `frontend/src/components/admin/BadgeList.tsx`
- Create: `frontend/src/components/admin/BadgeForm.tsx`
- Create: `frontend/src/components/admin/ChallengeList.tsx`
- Create: `frontend/src/components/admin/ChallengeForm.tsx`
- Create: `frontend/src/components/admin/__tests__/BadgeList.test.tsx`
- Create: `frontend/src/components/admin/__tests__/ChallengeList.test.tsx`
- Modify: `frontend/src/App.tsx` (add badge/challenge routes)

- [ ] **Step 1: Write failing tests for BadgeList**

Create `frontend/src/components/admin/__tests__/BadgeList.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BadgeList from '../BadgeList';

vi.mock('@/api/admin', () => ({
  useBadges: () => ({
    data: [
      { id: '1', name: 'First Steps', description: 'Complete 1 lesson', icon_url: '🌟', condition_type: 'lesson_count', condition_value: 1 },
      { id: '2', name: 'Streak Master', description: '7 day streak', icon_url: '🔥', condition_type: 'streak_days', condition_value: 7 },
    ],
    isLoading: false,
  }),
  useDeleteBadge: () => ({ mutate: vi.fn() }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('BadgeList', () => {
  it('renders badge names', () => {
    render(<BadgeList />, { wrapper });
    expect(screen.getByText('First Steps')).toBeInTheDocument();
    expect(screen.getByText('Streak Master')).toBeInTheDocument();
  });

  it('renders new badge button', () => {
    render(<BadgeList />, { wrapper });
    expect(screen.getByRole('link', { name: /new badge/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Write failing tests for ChallengeList**

Create `frontend/src/components/admin/__tests__/ChallengeList.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChallengeList from '../ChallengeList';

vi.mock('@/api/admin', () => ({
  useChallenges: () => ({
    data: [
      { id: '1', title: 'Weekly Sprint', description: 'Complete 3 lessons', type: 'lessons_completed', target_value: 3, xp_reward: 50, badge_id: null, starts_at: '2026-05-21T00:00:00Z', ends_at: '2026-05-28T00:00:00Z', is_premium: false },
    ],
    isLoading: false,
  }),
  useDeleteChallenge: () => ({ mutate: vi.fn() }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ChallengeList', () => {
  it('renders challenge titles', () => {
    render(<ChallengeList />, { wrapper });
    expect(screen.getByText('Weekly Sprint')).toBeInTheDocument();
  });

  it('renders new challenge button', () => {
    render(<ChallengeList />, { wrapper });
    expect(screen.getByRole('link', { name: /new challenge/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Implement BadgeList**

Create `frontend/src/components/admin/BadgeList.tsx`:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useBadges, useDeleteBadge } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminBadge } from '@/api/admin';

export default function BadgeList() {
  const { data: badges = [], isLoading } = useBadges();
  const deleteBadge = useDeleteBadge();
  const [deleteTarget, setDeleteTarget] = useState<AdminBadge | null>(null);

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Badges</h2>
        <Link to="/admin/badges/new" className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500">
          + New Badge
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {badges.map((b) => (
          <div key={b.id} className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3">
            <span className="text-xl">{b.icon_url}</span>
            <div className="flex-1">
              <div className="font-medium text-slate-50">{b.name}</div>
              <div className="text-xs text-slate-500">{b.condition_type} ≥ {b.condition_value}</div>
            </div>
            <Link to={`/admin/badges/${b.id}`} className="text-xs text-blue-400">Edit</Link>
            <button type="button" onClick={() => setDeleteTarget(b)} className="text-xs text-red-400">Delete</button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This badge will be permanently deleted. Deletion will fail if users have earned it."
        onConfirm={() => { if (deleteTarget) deleteBadge.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
```

- [ ] **Step 4: Implement BadgeForm**

Create `frontend/src/components/admin/BadgeForm.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBadges, useCreateBadge, useUpdateBadge } from '@/api/admin';

const CONDITION_TYPES = ['lesson_count', 'streak_days', 'module_complete', 'xp_total'] as const;

export default function BadgeForm() {
  const { badgeId } = useParams<{ badgeId: string }>();
  const navigate = useNavigate();
  const isEdit = !!badgeId && badgeId !== 'new';

  const { data: badges = [] } = useBadges();
  const existing = isEdit ? badges.find((b) => b.id === badgeId) : undefined;
  const createBadge = useCreateBadge();
  const updateBadge = useUpdateBadge();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [iconUrl, setIconUrl] = useState('🏅');
  const [conditionType, setConditionType] = useState<string>('lesson_count');
  const [conditionValue, setConditionValue] = useState(1);

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setDescription(existing.description);
      setIconUrl(existing.icon_url);
      setConditionType(existing.condition_type);
      setConditionValue(existing.condition_value);
    }
  }, [existing]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = { name, description, icon_url: iconUrl, condition_type: conditionType as typeof CONDITION_TYPES[number], condition_value: conditionValue };
    if (isEdit && badgeId) {
      await updateBadge.mutateAsync({ id: badgeId, ...data });
    } else {
      await createBadge.mutateAsync(data);
    }
    navigate('/admin/badges');
  }

  return (
    <div className="max-w-lg">
      <h2 className="mb-4 text-xl font-semibold text-slate-50">{isEdit ? 'Edit Badge' : 'New Badge'}</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="badge-name" className="mb-1 block text-sm text-slate-400">Name</label>
          <input id="badge-name" value={name} onChange={(e) => setName(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="badge-desc" className="mb-1 block text-sm text-slate-400">Description</label>
          <textarea id="badge-desc" value={description} onChange={(e) => setDescription(e.target.value)} required rows={2}
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="badge-icon" className="mb-1 block text-sm text-slate-400">Icon</label>
          <input id="badge-icon" value={iconUrl} onChange={(e) => setIconUrl(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="badge-cond-type" className="mb-1 block text-sm text-slate-400">Condition Type</label>
            <select id="badge-cond-type" value={conditionType} onChange={(e) => setConditionType(e.target.value)}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50">
              {CONDITION_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="w-32">
            <label htmlFor="badge-cond-val" className="mb-1 block text-sm text-slate-400">Value</label>
            <input id="badge-cond-val" type="number" value={conditionValue} onChange={(e) => setConditionValue(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
        </div>
        <div className="mt-2 flex gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">Save</button>
          <button type="button" onClick={() => navigate('/admin/badges')}
            className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancel</button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: Implement ChallengeList**

Create `frontend/src/components/admin/ChallengeList.tsx`:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useChallenges, useDeleteChallenge } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminChallenge } from '@/api/admin';

export default function ChallengeList() {
  const { data: challenges = [], isLoading } = useChallenges();
  const deleteChallenge = useDeleteChallenge();
  const [deleteTarget, setDeleteTarget] = useState<AdminChallenge | null>(null);

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Challenges</h2>
        <Link to="/admin/challenges/new" className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500">
          + New Challenge
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {challenges.map((c) => {
          const now = new Date();
          const isActive = new Date(c.starts_at) <= now && now <= new Date(c.ends_at);
          return (
            <div key={c.id} className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3">
              <div className="flex-1">
                <div className="font-medium text-slate-50">{c.title}</div>
                <div className="text-xs text-slate-500">
                  {c.type} · target: {c.target_value} · {c.xp_reward} XP
                  {c.is_premium && <span className="ml-1 text-yellow-500">⭐</span>}
                </div>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs ${isActive ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                {isActive ? 'Active' : 'Expired'}
              </span>
              <Link to={`/admin/challenges/${c.id}`} className="text-xs text-blue-400">Edit</Link>
              <button type="button" onClick={() => setDeleteTarget(c)} className="text-xs text-red-400">Delete</button>
            </div>
          );
        })}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.title}"?`}
        message="This challenge will be permanently deleted."
        onConfirm={() => { if (deleteTarget) deleteChallenge.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
```

- [ ] **Step 6: Implement ChallengeForm**

Create `frontend/src/components/admin/ChallengeForm.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChallenges, useCreateChallenge, useUpdateChallenge, useBadges } from '@/api/admin';

const CHALLENGE_TYPES = ['lessons_completed', 'xp_earned', 'streak'] as const;

export default function ChallengeForm() {
  const { challengeId } = useParams<{ challengeId: string }>();
  const navigate = useNavigate();
  const isEdit = !!challengeId && challengeId !== 'new';

  const { data: challenges = [] } = useChallenges();
  const { data: badges = [] } = useBadges();
  const existing = isEdit ? challenges.find((c) => c.id === challengeId) : undefined;
  const createChallenge = useCreateChallenge();
  const updateChallenge = useUpdateChallenge();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<string>('lessons_completed');
  const [targetValue, setTargetValue] = useState(1);
  const [xpReward, setXpReward] = useState(50);
  const [badgeId, setBadgeId] = useState<string | null>(null);
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [isPremium, setIsPremium] = useState(false);

  useEffect(() => {
    if (existing) {
      setTitle(existing.title);
      setDescription(existing.description);
      setType(existing.type);
      setTargetValue(existing.target_value);
      setXpReward(existing.xp_reward);
      setBadgeId(existing.badge_id);
      setStartsAt(existing.starts_at.slice(0, 16));
      setEndsAt(existing.ends_at.slice(0, 16));
      setIsPremium(existing.is_premium);
    }
  }, [existing]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = {
      title, description,
      type: type as typeof CHALLENGE_TYPES[number],
      target_value: targetValue, xp_reward: xpReward,
      badge_id: badgeId || null,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      is_premium: isPremium,
    };
    if (isEdit && challengeId) {
      await updateChallenge.mutateAsync({ id: challengeId, ...data });
    } else {
      await createChallenge.mutateAsync(data);
    }
    navigate('/admin/challenges');
  }

  return (
    <div className="max-w-lg">
      <h2 className="mb-4 text-xl font-semibold text-slate-50">{isEdit ? 'Edit Challenge' : 'New Challenge'}</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="ch-title" className="mb-1 block text-sm text-slate-400">Title</label>
          <input id="ch-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="ch-desc" className="mb-1 block text-sm text-slate-400">Description</label>
          <textarea id="ch-desc" value={description} onChange={(e) => setDescription(e.target.value)} required rows={2}
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-type" className="mb-1 block text-sm text-slate-400">Type</label>
            <select id="ch-type" value={type} onChange={(e) => setType(e.target.value)}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50">
              {CHALLENGE_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="w-28">
            <label htmlFor="ch-target" className="mb-1 block text-sm text-slate-400">Target</label>
            <input id="ch-target" type="number" value={targetValue} onChange={(e) => setTargetValue(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="w-28">
            <label htmlFor="ch-xp" className="mb-1 block text-sm text-slate-400">XP</label>
            <input id="ch-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
        </div>
        <div>
          <label htmlFor="ch-badge" className="mb-1 block text-sm text-slate-400">Linked Badge (optional)</label>
          <select id="ch-badge" value={badgeId ?? ''} onChange={(e) => setBadgeId(e.target.value || null)}
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50">
            <option value="">None</option>
            {badges.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-starts" className="mb-1 block text-sm text-slate-400">Starts At</label>
            <input id="ch-starts" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="flex-1">
            <label htmlFor="ch-ends" className="mb-1 block text-sm text-slate-400">Ends At</label>
            <input id="ch-ends" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input id="ch-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800" />
          <label htmlFor="ch-premium" className="text-sm text-slate-400">Premium only</label>
        </div>
        <div className="mt-2 flex gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">Save</button>
          <button type="button" onClick={() => navigate('/admin/challenges')}
            className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancel</button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 7: Add badge/challenge routes to App.tsx**

In `frontend/src/App.tsx`, add imports:
```tsx
import BadgeList from '@/components/admin/BadgeList';
import BadgeForm from '@/components/admin/BadgeForm';
import ChallengeList from '@/components/admin/ChallengeList';
import ChallengeForm from '@/components/admin/ChallengeForm';
```

Add inside the admin `<Route>`:
```tsx
          <Route path="badges" element={<BadgeList />} />
          <Route path="badges/new" element={<BadgeForm />} />
          <Route path="badges/:badgeId" element={<BadgeForm />} />
          <Route path="challenges" element={<ChallengeList />} />
          <Route path="challenges/new" element={<ChallengeForm />} />
          <Route path="challenges/:challengeId" element={<ChallengeForm />} />
```

- [ ] **Step 8: Run tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/admin/__tests__/BadgeList.test.tsx src/components/admin/__tests__/ChallengeList.test.tsx --reporter=verbose`
Expected: 4/4 PASS

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/admin/BadgeList.tsx frontend/src/components/admin/BadgeForm.tsx frontend/src/components/admin/ChallengeList.tsx frontend/src/components/admin/ChallengeForm.tsx frontend/src/App.tsx frontend/src/components/admin/__tests__/BadgeList.test.tsx frontend/src/components/admin/__tests__/ChallengeList.test.tsx
git commit -m "feat(admin): add badge and challenge list/form components with routing"
```

---

### Task 11: Frontend — Accessibility Tests

**Files:**
- Create: `frontend/tests/a11y/admin.a11y.test.tsx`

- [ ] **Step 1: Write accessibility tests**

Create `frontend/tests/a11y/admin.a11y.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe, toHaveNoViolations } from 'jest-axe';
import AdminLogin from '@/components/admin/AdminLogin';
import AdminDashboard from '@/components/admin/AdminDashboard';
import OrderArrows from '@/components/admin/OrderArrows';
import ConfirmDialog from '@/components/admin/ConfirmDialog';

expect.extend(toHaveNoViolations);

vi.mock('@/api/admin', () => ({
  useAdminStats: () => ({
    data: { modules: 12, lessons: 49, badges: 5, challenges: 3 },
    isLoading: false,
  }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Admin a11y', () => {
  it('AdminLogin has no a11y violations', async () => {
    const { container } = render(<AdminLogin onAuthenticated={vi.fn()} />, { wrapper });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('AdminDashboard has no a11y violations', async () => {
    const { container } = render(<AdminDashboard />, { wrapper });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('OrderArrows has no a11y violations', async () => {
    const { container } = render(
      <OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} />,
      { wrapper },
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ConfirmDialog has no a11y violations when open', async () => {
    const { container } = render(
      <ConfirmDialog open title="Delete?" message="Are you sure?" onConfirm={vi.fn()} onCancel={vi.fn()} />,
      { wrapper },
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run a11y tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run tests/a11y/admin.a11y.test.tsx --reporter=verbose`
Expected: 4/4 PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/a11y/admin.a11y.test.tsx
git commit -m "test(admin): add accessibility tests for admin components"
```

---

### Task 12: Full Regression

**Files:** None (verification only)

- [ ] **Step 1: Run full backend tests**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/ -v`
Expected: All tests pass (existing + new admin tests)

- [ ] **Step 2: Run full frontend tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run --reporter=verbose`
Expected: All tests pass (325+ existing + new admin tests)

- [ ] **Step 3: Run TypeScript check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`
Expected: Clean, no errors

- [ ] **Step 4: Run lint**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx eslint src/ --ext .ts,.tsx`
Expected: Clean

- [ ] **Step 5: Verify build**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Final commit if any fixes needed**

If regression revealed issues, fix and commit. Otherwise, all done.
