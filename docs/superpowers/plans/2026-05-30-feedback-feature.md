# Feedback Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let child and parent users submit bug reports, feature requests, and general feedback, stored in PostgreSQL with email notification and a read-only admin view.

**Architecture:** A `Feedback` table captures the submitter via nullable `user_id` (children, who have `User` rows) or `parent_email` (parents, who authenticate via magic-link session only), with a `submitter_role` discriminator. Two POST endpoints (`/feedback` for children, `/parent/feedback` for parents) share a request schema and persistence helper. An admin endpoint lists feedback. Frontend reuses the existing BottomSheet (mobile) / Dialog (desktop) pattern.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, slowapi, Pydantic v2, Resend email, React 18, Vite, TanStack Query, Tailwind, Vitest.

**Working directories:** Backend `/Users/leeashmore/Local Repo/invest-ed/backend`, frontend `/Users/leeashmore/Local Repo/invest-ed/frontend`.

**Backend test command:** `/Users/leeashmore/Local Repo/.venv/bin/pytest` run from `invest-ed/backend`.

**Frontend test command:** `npm test` run from `invest-ed/frontend` (vitest). Install with `npm ci --legacy-peer-deps`.

**Baseline:** Backend 463 passed (4 pre-existing failures unrelated to this work: `test_admin_prerequisites` self-reference, `test_coach_endpoint::test_coach_chat_parses_action`, `test_security::test_requirements_fully_pinned`, and one more). Frontend all passing + tsc clean.

**Commit convention:** End commit messages with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`. Commit from repo root `/Users/leeashmore/Local Repo` (the git root is the parent of `invest-ed`).

---

## File Structure

### New files
- `backend/app/models/feedback.py` — `Feedback` SQLAlchemy model
- `backend/app/schemas/feedback.py` — `FeedbackCreate`, `FeedbackOut`, `FeedbackListResponse`
- `backend/app/services/feedback_service.py` — persistence helper + email notification
- `backend/app/routers/feedback.py` — child `POST /feedback` + admin `GET /admin/feedback`
- `backend/alembic/versions/a1b2c3d4e5f6_add_feedback_table.py` — migration
- `backend/tests/test_feedback.py` — backend tests
- `frontend/src/api/feedback.ts` — feedback API client + types
- `frontend/src/components/child/FeedbackDialog.tsx` — shared submit dialog
- `frontend/src/components/child/__tests__/FeedbackDialog.test.tsx` — component tests
- `frontend/src/components/admin/FeedbackList.tsx` — admin read-only list

### Modified files
- `backend/app/core/config.py` — add `feedback_notify_email` setting
- `backend/app/models/__init__.py` — register `Feedback`
- `backend/app/main.py` — register feedback router
- `backend/app/routers/parent_auth.py` — add parent `POST /parent/feedback` endpoint
- `frontend/src/components/child/ProfileMenu.tsx` — add "Send Feedback" item
- `frontend/src/pages/ParentDashboard.tsx` — add "Send Feedback" button
- `frontend/src/api/admin.ts` — add `useFeedback` hook + types
- `frontend/src/components/admin/AdminSidebar.tsx` — add Feedback nav item
- `frontend/src/App.tsx` — add `/admin/feedback` route

---

## Task 1: Feedback Model + Config Setting

**Files:**
- Create: `backend/app/models/feedback.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/core/config.py:20-21` (after `email_from`)

- [ ] **Step 1: Write the model**

Create `backend/app/models/feedback.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    parent_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitter_role: Mapped[str] = mapped_column(String(20), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
```

- [ ] **Step 2: Register the model**

In `backend/app/models/__init__.py`, add after the `cosmetics` import line (keep alphabetical-ish ordering consistent with the file):

```python
from app.models.feedback import Feedback  # noqa: F401
```

- [ ] **Step 3: Add config setting**

In `backend/app/core/config.py`, add directly after the `email_from` line (currently line 20):

```python
    feedback_notify_email: str = ""
```

- [ ] **Step 4: Verify import works**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.models import Feedback; from app.core.config import settings; print(Feedback.__tablename__, repr(settings.feedback_notify_email))"`
Expected: `feedback ''`

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/feedback.py invest-ed/backend/app/models/__init__.py invest-ed/backend/app/core/config.py
git commit -m "feat: add Feedback model and notify-email config

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_feedback_table.py`

The current migration head is `f5a6b7c8d9e0`. This migration chains from it.

- [ ] **Step 1: Write the migration**

Create `backend/alembic/versions/a1b2c3d4e5f6_add_feedback_table.py`:

```python
"""add feedback table

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-05-30 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("parent_email", sa.String(length=255), nullable=True),
        sa.Column("submitter_role", sa.String(length=20), nullable=False),
        sa.Column("feedback_type", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
```

- [ ] **Step 2: Verify migration is the new head**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/alembic heads`
Expected: `a1b2c3d4e5f6 (head)`

- [ ] **Step 3: Verify it applies against the test database**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head`
Expected: completes without error (ends at `a1b2c3d4e5f6`). If the local dev DB is not running, this step may be skipped — the migration correctness is verified by the test suite in later tasks which creates tables from metadata.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/alembic/versions/a1b2c3d4e5f6_add_feedback_table.py
git commit -m "feat: add feedback table migration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Feedback Schemas

**Files:**
- Create: `backend/app/schemas/feedback.py`

- [ ] **Step 1: Write the schemas**

Create `backend/app/schemas/feedback.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FeedbackType = Literal["bug", "feature", "general"]


class FeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    message: str = Field(min_length=1, max_length=2000)
    page_url: str | None = Field(default=None, max_length=500)


class FeedbackCreateResponse(BaseModel):
    id: uuid.UUID


class FeedbackOut(BaseModel):
    id: uuid.UUID
    submitter: str
    submitter_role: str
    feedback_type: str
    message: str
    page_url: str | None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: list[FeedbackOut]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 2: Verify import**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackListResponse, FeedbackCreateResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/feedback.py
git commit -m "feat: add feedback schemas

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Feedback Service (persistence + email notification)

**Files:**
- Create: `backend/app/services/feedback_service.py`
- Test: `backend/tests/test_feedback.py` (created here, expanded in Task 7)

The service exposes one function that persists a row and sends a best-effort
notification email. Email failures are swallowed (logged) so they never fail the
submission. The email uses Resend directly (the existing `email.py` templates are
user-facing with CTA buttons; feedback notification is a plain internal email, so
it does not reuse those templates).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_feedback.py`:

```python
import uuid

import pytest

from app.models.feedback import Feedback
from app.services.feedback_service import create_feedback


@pytest.mark.asyncio
async def test_create_feedback_child(db_session):
    fb = await create_feedback(
        db_session,
        feedback_type="bug",
        message="quiz timer broken",
        page_url="/lessons/1",
        user_id=uuid.uuid4(),
        parent_email=None,
        submitter_role="child",
    )
    assert fb.id is not None
    assert fb.submitter_role == "child"
    assert fb.feedback_type == "bug"
    assert fb.parent_email is None


@pytest.mark.asyncio
async def test_create_feedback_parent(db_session):
    fb = await create_feedback(
        db_session,
        feedback_type="feature",
        message="please add dark mode",
        page_url=None,
        user_id=None,
        parent_email="mum@example.com",
        submitter_role="parent",
    )
    assert fb.parent_email == "mum@example.com"
    assert fb.user_id is None
    assert fb.submitter_role == "parent"
```

NOTE: confirm the session fixture name. Inspect `backend/tests/conftest.py` for the
async DB session fixture (commonly `db_session` or `session`). Use whatever name
the existing tests use; if it differs from `db_session`, rename in all tests in
this file accordingly.

- [ ] **Step 2: Run test to verify it fails**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_feedback.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.feedback_service'`

- [ ] **Step 3: Write the service**

Create `backend/app/services/feedback_service.py`:

```python
from __future__ import annotations

import asyncio
import logging
import uuid

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)

_TYPE_LABEL = {
    "bug": "Bug Report",
    "feature": "Feature Request",
    "general": "Feedback",
}


async def create_feedback(
    session: AsyncSession,
    *,
    feedback_type: str,
    message: str,
    page_url: str | None,
    user_id: uuid.UUID | None,
    parent_email: str | None,
    submitter_role: str,
) -> Feedback:
    fb = Feedback(
        feedback_type=feedback_type,
        message=message,
        page_url=page_url,
        user_id=user_id,
        parent_email=parent_email,
        submitter_role=submitter_role,
    )
    session.add(fb)
    await session.flush()
    return fb


async def notify_feedback(
    *,
    submitter: str,
    submitter_role: str,
    feedback_type: str,
    message: str,
    page_url: str | None,
) -> None:
    """Best-effort notification email. Never raises."""
    if settings.email_backend != "resend" or not settings.feedback_notify_email:
        return
    label = _TYPE_LABEL.get(feedback_type, "Feedback")
    subject = f"[Invest-Ed] {label} from {submitter}"
    text = (
        f"Type: {label}\n"
        f"From: {submitter} ({submitter_role})\n"
        f"Page: {page_url or 'n/a'}\n\n"
        f"{message}\n"
    )
    try:
        resend.api_key = settings.resend_api_key
        params: resend.Emails.SendParams = {
            "from": settings.email_from,
            "to": [settings.feedback_notify_email],
            "subject": subject,
            "text": text,
        }
        await asyncio.to_thread(resend.Emails.send, params)
    except Exception:  # noqa: BLE001 — notification must never fail submission
        logger.exception("Failed to send feedback notification email")
```

- [ ] **Step 4: Run test to verify it passes**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_feedback.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/feedback_service.py invest-ed/backend/tests/test_feedback.py
git commit -m "feat: add feedback service with email notification

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Child Feedback Router + Admin List Endpoint

**Files:**
- Create: `backend/app/routers/feedback.py`
- Modify: `backend/app/main.py:132` (after admin router registration)

This router holds the child `POST /feedback` and the admin `GET /admin/feedback`.
(The parent endpoint lives in `parent_auth.py` in Task 6 because it depends on the
parent session dependency defined there.)

- [ ] **Step 1: Write the router**

Create `backend/app/routers/feedback.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.feedback import Feedback
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.routers.users import get_current_user
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackCreateResponse,
    FeedbackListResponse,
    FeedbackOut,
)
from app.services.feedback_service import create_feedback, notify_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackCreateResponse, status_code=201)
@limiter.limit("5/hour")
async def submit_feedback(
    request: Request,
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    fb = await create_feedback(
        session,
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        user_id=current_user.id,
        parent_email=None,
        submitter_role="child",
    )
    await session.commit()
    await notify_feedback(
        submitter=current_user.username,
        submitter_role="child",
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
    )
    return FeedbackCreateResponse(id=fb.id)


admin_router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)]
)


@admin_router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    session: AsyncSession = Depends(get_session),
    feedback_type: str | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    base = select(Feedback)
    count_q = select(func.count()).select_from(Feedback)
    if feedback_type:
        base = base.where(Feedback.feedback_type == feedback_type)
        count_q = count_q.where(Feedback.feedback_type == feedback_type)

    total = await session.scalar(count_q) or 0

    rows = (
        await session.execute(
            base.order_by(Feedback.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    # Resolve child usernames in one query
    user_ids = [r.user_id for r in rows if r.user_id is not None]
    usernames: dict = {}
    if user_ids:
        user_rows = (
            await session.execute(
                select(User.id, User.username).where(User.id.in_(user_ids))
            )
        ).all()
        usernames = {uid: uname for uid, uname in user_rows}

    items = [
        FeedbackOut(
            id=r.id,
            submitter=(
                usernames.get(r.user_id, "(deleted user)")
                if r.submitter_role == "child"
                else (r.parent_email or "(unknown)")
            ),
            submitter_role=r.submitter_role,
            feedback_type=r.feedback_type,
            message=r.message,
            page_url=r.page_url,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return FeedbackListResponse(items=items, total=total, page=page, per_page=per_page)
```

- [ ] **Step 2: Register both routers in main.py**

In `backend/app/main.py`, add the import near the other router imports (top of file with the other `from app.routers import ... as ..._router` lines — match the existing import style in that file), then register after line 132 (`application.include_router(admin_router.router)`):

```python
    application.include_router(feedback_router.router)
    application.include_router(feedback_router.admin_router)
```

Use an import consistent with the file's existing convention, e.g.:

```python
from app.routers import feedback as feedback_router
```

- [ ] **Step 3: Verify app boots**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.main import app; print([r.path for r in app.routes if 'feedback' in r.path])"`
Expected: list containing `/feedback` and `/admin/feedback`

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/feedback.py invest-ed/backend/app/main.py
git commit -m "feat: add child feedback + admin list endpoints

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Parent Feedback Endpoint

**Files:**
- Modify: `backend/app/routers/parent_auth.py`

The parent endpoint reuses `get_current_parent` (returns the parent's email).
Add it to the parent router. Confirm the parent router's prefix first: open
`backend/app/routers/parent_auth.py` and check the `APIRouter(prefix=...)`. The
endpoint path below assumes prefix `/parent`. If the prefix is `/parent/auth`,
register a second small router with prefix `/parent` in this file instead, so the
path is exactly `/parent/feedback`. Adjust to land on `/parent/feedback`.

- [ ] **Step 1: Add imports to parent_auth.py**

At the top of `backend/app/routers/parent_auth.py`, add (merge with existing import lines):

```python
from app.core.rate_limit import limiter
from app.schemas.feedback import FeedbackCreate, FeedbackCreateResponse
from app.services.feedback_service import create_feedback, notify_feedback
```

- [ ] **Step 2: Add the endpoint**

Append this endpoint to `backend/app/routers/parent_auth.py`. If the file's
`router` has prefix `/parent`, use `@router.post("/feedback", ...)`. If the prefix
is `/parent/auth`, create a dedicated router in this file:

```python
parent_feedback_router = APIRouter(prefix="/parent", tags=["parent"])


@parent_feedback_router.post(
    "/feedback", response_model=FeedbackCreateResponse, status_code=201
)
@limiter.limit("5/hour")
async def submit_parent_feedback(
    request: Request,
    payload: FeedbackCreate,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    fb = await create_feedback(
        session,
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        user_id=None,
        parent_email=parent_email,
        submitter_role="parent",
    )
    await session.commit()
    await notify_feedback(
        submitter=parent_email,
        submitter_role="parent",
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
    )
    return FeedbackCreateResponse(id=fb.id)
```

`Request`, `APIRouter`, `Depends`, `AsyncSession`, `get_session`, and
`get_current_parent` are already imported in this file (verify; add any missing).

- [ ] **Step 3: Register the parent feedback router (only if a new router was created)**

If you created `parent_feedback_router`, register it in `backend/app/main.py`
after the parent router registration (line 129 area):

```python
    application.include_router(parent_auth_router.parent_feedback_router)
```

If you instead added the endpoint to the existing `/parent`-prefixed router, no
new registration is needed.

- [ ] **Step 4: Verify the route exists**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/python -c "from app.main import app; print('/parent/feedback' in [r.path for r in app.routes])"`
Expected: `True`

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/parent_auth.py invest-ed/backend/app/main.py
git commit -m "feat: add parent feedback endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Backend Endpoint Tests

**Files:**
- Modify: `backend/tests/test_feedback.py`

Add endpoint-level tests. Inspect `backend/tests/conftest.py` and an existing
router test (e.g. `tests/test_billing.py` or `tests/test_admin_*`) to copy the
exact fixtures for: an authenticated child client, an authenticated parent
session, and the admin token header. Use those same fixtures here. The tests
below use placeholder fixture names — replace with the real ones from conftest.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_feedback.py`:

```python
@pytest.mark.asyncio
async def test_child_submit_feedback_endpoint(auth_client):
    resp = await auth_client.post(
        "/feedback",
        json={"feedback_type": "bug", "message": "timer broke", "page_url": "/lessons/1"},
    )
    assert resp.status_code == 201
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_submit_feedback_rejects_blank_message(auth_client):
    resp = await auth_client.post(
        "/feedback",
        json={"feedback_type": "bug", "message": "", "page_url": None},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_rejects_bad_type(auth_client):
    resp = await auth_client.post(
        "/feedback",
        json={"feedback_type": "spam", "message": "hi", "page_url": None},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_requires_auth(client):
    resp = await client.post(
        "/feedback",
        json={"feedback_type": "bug", "message": "x", "page_url": None},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_feedback(auth_client, admin_headers):
    await auth_client.post(
        "/feedback",
        json={"feedback_type": "feature", "message": "dark mode", "page_url": "/home"},
    )
    resp = await auth_client.get("/admin/feedback", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["feedback_type"] in {"bug", "feature", "general"}
    assert "submitter" in body["items"][0]


@pytest.mark.asyncio
async def test_admin_list_feedback_filters_by_type(auth_client, admin_headers):
    await auth_client.post(
        "/feedback",
        json={"feedback_type": "bug", "message": "a bug", "page_url": None},
    )
    resp = await auth_client.get("/admin/feedback?type=bug", headers=admin_headers)
    assert resp.status_code == 200
    assert all(i["feedback_type"] == "bug" for i in resp.json()["items"])
```

IMPORTANT — fixture discovery: before running, read `tests/conftest.py` to find
the real names for (a) an authenticated child HTTP client, (b) an unauthenticated
client, (c) admin auth headers. Common patterns in this repo: a `client` fixture
plus a login helper, and admin tests build a `{"Authorization": f"Bearer {token}"}`
header from `settings.admin_token`. Wire these tests to the actual fixtures. If the
test client is synchronous (`TestClient`), drop `await` and `@pytest.mark.asyncio`
on the endpoint tests accordingly — match the style of existing router tests.

- [ ] **Step 2: Run tests to verify they pass**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_feedback.py -v`
Expected: all PASS. If auth/rate-limit fixtures cause flakiness, confirm against
the existing router tests how they handle the limiter (some suites set a high
limit or disable it in test config).

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/tests/test_feedback.py
git commit -m "test: add feedback endpoint tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Frontend Feedback API Client

**Files:**
- Create: `frontend/src/api/feedback.ts`

- [ ] **Step 1: Write the API client**

Create `frontend/src/api/feedback.ts`:

```typescript
import { useMutation } from '@tanstack/react-query';
import { apiFetch } from './client';

export type FeedbackType = 'bug' | 'feature' | 'general';

export interface FeedbackPayload {
  feedback_type: FeedbackType;
  message: string;
  page_url: string | null;
}

export interface FeedbackCreateResponse {
  id: string;
}

/**
 * Submit feedback. `audience` selects the endpoint:
 * - 'child'  → POST /feedback        (child cookie session)
 * - 'parent' → POST /parent/feedback (parent magic-link session)
 */
export function useSubmitFeedback(audience: 'child' | 'parent') {
  const path = audience === 'parent' ? '/parent/feedback' : '/feedback';
  return useMutation({
    mutationFn: (payload: FeedbackPayload) =>
      apiFetch<FeedbackCreateResponse>(path, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  });
}
```

- [ ] **Step 2: Typecheck**

Run from `invest-ed/frontend`:
`npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/feedback.ts
git commit -m "feat: add frontend feedback API client

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: FeedbackDialog Component

**Files:**
- Create: `frontend/src/components/child/FeedbackDialog.tsx`

Mirrors the `ProfileMenu` pattern: BottomSheet on mobile, Dialog on desktop, via
`useMediaQuery`. Uses the toast system (`useToast` from `@/hooks/use-toast`).

- [ ] **Step 1: Write the component**

Create `frontend/src/components/child/FeedbackDialog.tsx`:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useToast } from '@/hooks/use-toast';
import { useSubmitFeedback, type FeedbackType } from '@/api/feedback';

const TYPE_OPTIONS: { value: FeedbackType; label: string }[] = [
  { value: 'bug', label: 'Bug Report' },
  { value: 'feature', label: 'Feature Request' },
  { value: 'general', label: 'General Feedback' },
];

const PLACEHOLDER: Record<FeedbackType, string> = {
  bug: 'Describe the bug you encountered…',
  feature: 'What feature would you like to see?',
  general: 'Share your thoughts…',
};

const MAX = 2000;

export function FeedbackDialog({
  open,
  onOpenChange,
  audience,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  audience: 'child' | 'parent';
}) {
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const { toast } = useToast();
  const submit = useSubmitFeedback(audience);
  const [type, setType] = useState<FeedbackType>('bug');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  function reset() {
    setType('bug');
    setMessage('');
    setError('');
  }

  function handleSubmit() {
    setError('');
    submit.mutate(
      { feedback_type: type, message, page_url: window.location.pathname },
      {
        onSuccess: () => {
          toast({ title: 'Thanks for your feedback!' });
          reset();
          onOpenChange(false);
        },
        onError: () => setError('Could not send feedback. Please try again.'),
      },
    );
  }

  const body = (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="feedback-type" className="text-sm font-medium">
          Type
        </label>
        <select
          id="feedback-type"
          className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={type}
          onChange={(e) => setType(e.target.value as FeedbackType)}
        >
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="feedback-message" className="text-sm font-medium">
          Message
        </label>
        <textarea
          id="feedback-message"
          className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder={PLACEHOLDER[type]}
          value={message}
          maxLength={MAX}
          aria-describedby="feedback-counter"
          onChange={(e) => setMessage(e.target.value)}
        />
        <p id="feedback-counter" className="text-right text-xs text-muted-foreground">
          {message.length} / {MAX}
        </p>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">{error}</p>
      )}
      <Button
        type="button"
        disabled={submit.isPending || message.trim().length === 0}
        onClick={handleSubmit}
      >
        {submit.isPending ? 'Sending…' : 'Send Feedback'}
      </Button>
    </div>
  );

  return isMobile ? (
    <BottomSheet open={open} onOpenChange={onOpenChange} title="Send feedback">
      {body}
    </BottomSheet>
  ) : (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send feedback</DialogTitle>
        </DialogHeader>
        {body}
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Typecheck**

Run from `invest-ed/frontend`:
`npx tsc -b`
Expected: no errors. (If `useMediaQuery` is a default vs named export, match the
import style used in `ProfileMenu.tsx`, which imports `{ useMediaQuery }`.)

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/FeedbackDialog.tsx
git commit -m "feat: add FeedbackDialog component

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: FeedbackDialog Tests

**Files:**
- Create: `frontend/src/components/child/__tests__/FeedbackDialog.test.tsx`

Inspect a sibling test (e.g. `frontend/src/components/child/__tests__/Coach.test.tsx`)
for the exact render/provider helpers (QueryClientProvider wrapper, render util).
Reuse them.

- [ ] **Step 1: Write the test**

Create `frontend/src/components/child/__tests__/FeedbackDialog.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FeedbackDialog } from '../FeedbackDialog';
import * as client from '@/api/client';

function renderDialog() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <FeedbackDialog open onOpenChange={() => {}} audience="child" />
    </QueryClientProvider>,
  );
}

describe('FeedbackDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: true, // desktop (min-width:768px) → Dialog
      media: '', onchange: null,
      addListener: vi.fn(), removeListener: vi.fn(),
      addEventListener: vi.fn(), removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    } as unknown as MediaQueryList);
  });

  it('shows the type and message fields', () => {
    renderDialog();
    expect(screen.getByLabelText('Type')).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toBeInTheDocument();
  });

  it('updates the character counter', () => {
    renderDialog();
    const box = screen.getByLabelText('Message');
    fireEvent.change(box, { target: { value: 'hello' } });
    expect(screen.getByText('5 / 2000')).toBeInTheDocument();
  });

  it('submits feedback and posts to /feedback', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 'abc' });
    renderDialog();
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'a bug' } });
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(spy.mock.calls[0][0]).toBe('/feedback');
  });
});
```

NOTE: The `useMediaQuery` hook likely wraps `window.matchMedia`. Confirm by reading
`frontend/src/hooks/useMediaQuery.ts`; if it reads `matches` differently, adjust the
mock so the desktop branch (Dialog) renders. If the repo already has a matchMedia
test helper/setup, prefer that over the inline mock.

- [ ] **Step 2: Run the test**

Run from `invest-ed/frontend`:
`npm test -- FeedbackDialog`
Expected: 3 passing.

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/__tests__/FeedbackDialog.test.tsx
git commit -m "test: add FeedbackDialog tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 11: Wire Entry Points (Child ProfileMenu + Parent Dashboard)

**Files:**
- Modify: `frontend/src/components/child/ProfileMenu.tsx`
- Modify: `frontend/src/pages/ParentDashboard.tsx`

- [ ] **Step 1: Add "Send Feedback" to ProfileMenu**

In `frontend/src/components/child/ProfileMenu.tsx`:

1. Add import:
```tsx
import { FeedbackDialog } from '@/components/child/FeedbackDialog';
```
2. Add state near the other `useState` calls:
```tsx
const [feedbackOpen, setFeedbackOpen] = useState(false);
```
3. Add a menu item between Profile and the separator/Log out (inside
`DropdownMenuContent`):
```tsx
<DropdownMenuItem onSelect={() => setFeedbackOpen(true)}>
  Send Feedback
</DropdownMenuItem>
```
4. Render the dialog alongside the existing editor sheet/dialog (inside the
returned fragment, after the existing BottomSheet/Dialog block):
```tsx
<FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="child" />
```

- [ ] **Step 2: Add "Send Feedback" to ParentDashboard**

In `frontend/src/pages/ParentDashboard.tsx`:

1. Add imports:
```tsx
import { useState } from 'react';
import { FeedbackDialog } from '@/components/child/FeedbackDialog';
```
(If `useState` is already imported, merge.)
2. Add state inside the component:
```tsx
const [feedbackOpen, setFeedbackOpen] = useState(false);
```
3. In the header, change the right-hand side from a single Log out button to a
group with a Feedback button. Replace the existing Log out `<Button>` block with:
```tsx
<div className="flex items-center gap-1">
  <Button variant="ghost" size="sm" onClick={() => setFeedbackOpen(true)}>
    Send Feedback
  </Button>
  <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
    Log out
  </Button>
</div>
```
4. Render the dialog before the closing `</main>`:
```tsx
<FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="parent" />
```

- [ ] **Step 3: Typecheck**

Run from `invest-ed/frontend`:
`npx tsc -b`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/ProfileMenu.tsx invest-ed/frontend/src/pages/ParentDashboard.tsx
git commit -m "feat: add Send Feedback entry points for child and parent

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 12: Admin Feedback List (API hook + component + route + nav)

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Create: `frontend/src/components/admin/FeedbackList.tsx`
- Modify: `frontend/src/components/admin/AdminSidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add types + hook to admin.ts**

In `frontend/src/api/admin.ts`, add types near the other interfaces:

```typescript
export interface AdminFeedback {
  id: string;
  submitter: string;
  submitter_role: string;
  feedback_type: 'bug' | 'feature' | 'general';
  message: string;
  page_url: string | null;
  created_at: string;
}

export interface AdminFeedbackList {
  items: AdminFeedback[];
  total: number;
  page: number;
  per_page: number;
}
```

And add a hook near the other `useQuery` hooks:

```typescript
export function useFeedback(params: { type?: string; page: number }) {
  const search = new URLSearchParams();
  if (params.type) search.set('type', params.type);
  search.set('page', String(params.page));
  const qs = search.toString();
  return useQuery({
    queryKey: ['admin', 'feedback', params.type ?? 'all', params.page],
    queryFn: () => adminFetch<AdminFeedbackList>(`/admin/feedback?${qs}`),
  });
}
```

- [ ] **Step 2: Create the FeedbackList component**

Create `frontend/src/components/admin/FeedbackList.tsx`:

```tsx
import { useState } from 'react';
import { useFeedback } from '@/api/admin';

const TYPE_BADGE: Record<string, string> = {
  bug: 'bg-red-100 text-red-800',
  feature: 'bg-blue-100 text-blue-800',
  general: 'bg-slate-100 text-slate-800',
};

const TYPE_LABEL: Record<string, string> = {
  bug: 'Bug',
  feature: 'Feature',
  general: 'General',
};

export default function FeedbackList() {
  const [type, setType] = useState('');
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useFeedback({ type: type || undefined, page });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-50">Feedback</h1>
        <label className="text-sm text-slate-300">
          <span className="mr-2">Filter</span>
          <select
            className="rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-slate-100"
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="bug">Bug</option>
            <option value="feature">Feature</option>
            <option value="general">General</option>
          </select>
        </label>
      </div>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      {isError && <p className="text-red-400">Failed to load feedback.</p>}

      {data && (
        <>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-slate-400">
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Message</th>
                <th className="py-2 pr-4">Page</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((f) => (
                <tr key={f.id} className="border-b border-slate-800 align-top text-slate-200">
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {new Date(f.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {f.submitter}
                    <span className="ml-1 text-xs text-slate-500">({f.submitter_role})</span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[f.feedback_type] ?? ''}`}>
                      {TYPE_LABEL[f.feedback_type] ?? f.feedback_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4 max-w-md">{f.message}</td>
                  <td className="py-2 pr-4 text-slate-400">{f.page_url ?? '—'}</td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-slate-500">No feedback yet.</td></tr>
              )}
            </tbody>
          </table>

          <div className="mt-4 flex items-center justify-between text-sm text-slate-300">
            <button
              className="rounded border border-slate-600 px-3 py-1 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button
              className="rounded border border-slate-600 px-3 py-1 disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add nav item to AdminSidebar**

In `frontend/src/components/admin/AdminSidebar.tsx`, add to `NAV_ITEMS`:

```tsx
  { to: '/admin/feedback', label: 'Feedback', icon: '💬', end: false },
```

- [ ] **Step 4: Add the route in App.tsx**

In `frontend/src/App.tsx`, add the import with the other admin imports:

```tsx
import FeedbackList from '@/components/admin/FeedbackList';
```

And add inside the `/admin` route block (after the challenges routes):

```tsx
          <Route path="feedback" element={<FeedbackList />} />
```

- [ ] **Step 5: Typecheck + run frontend tests**

Run from `invest-ed/frontend`:
`npx tsc -b && npm test -- FeedbackDialog`
Expected: tsc clean, FeedbackDialog tests pass.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/admin.ts invest-ed/frontend/src/components/admin/FeedbackList.tsx invest-ed/frontend/src/components/admin/AdminSidebar.tsx invest-ed/frontend/src/App.tsx
git commit -m "feat: add admin feedback list page

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 13: Full Regression + Close-Out

**Files:** none (verification only)

- [ ] **Step 1: Backend full suite**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/pytest -q`
Expected: all new feedback tests pass; total failures still the 4 known
pre-existing ones (no new failures). Note the pass count went up by the number of
new tests vs the 463 baseline.

- [ ] **Step 2: Frontend full suite + typecheck**

Run from `invest-ed/frontend`:
`npx tsc -b && npm test`
Expected: tsc clean, all tests pass (baseline count + new FeedbackDialog tests).

- [ ] **Step 3: Lint (match project tooling)**

Run from `invest-ed/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/ruff check app/`
Expected: no new violations in feedback files.

- [ ] **Step 4: Final commit (if lint produced fixes)**

```bash
cd "/Users/leeashmore/Local Repo"
git add -A
git commit -m "chore: feedback feature lint cleanup

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

If nothing changed, skip this step.

---

## Self-Review Notes (for the executor)

- **Submitter model:** `user_id` (child) XOR `parent_email` (parent), discriminated by `submitter_role`. The child endpoint and parent endpoint each set exactly one.
- **CSRF:** `apiFetch` auto-attaches `X-CSRF-Token` for POST. Admin uses Bearer token and is CSRF-exempt via the `/admin/` prefix. No CSRF work needed.
- **Rate limiting:** `@limiter.limit("5/hour")` requires a `request: Request` parameter on the endpoint — present in both POST handlers.
- **Email:** notification is best-effort and only fires when `email_backend == "resend"` and `feedback_notify_email` is set. Tests run with logging backend, so no email is sent during tests.
- **Fixture names:** Tasks 7 and 10 require confirming real fixture/util names from `conftest.py` and sibling tests before running. This is called out inline.
- **Parent router prefix:** Task 6 requires confirming the parent router prefix so the path resolves to exactly `/parent/feedback`.
