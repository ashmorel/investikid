# Video Link Health + Admin Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect dead/unavailable lesson videos automatically (periodic Railway-cron check + email alert) and surface them in an admin "Video health" page with quick edit + on-demand re-check.

**Architecture:** An async checker pings YouTube's oEmbed endpoint per video lesson, classifies the result (ok/dead/unknown), and upserts a `video_health` table. The admin page reads that table and can trigger a fresh check; a `python -m app.video_health.run` cron command runs the same check on a schedule and emails the configured admin alert recipients only when videos are dead.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + httpx (backend); React 18 + Vite + TS + TanStack Query + Tailwind v4 + Vitest/vitest-axe (frontend).

---

## Reference facts (verified — read before starting)

- **Spec:** `invest-ed/docs/superpowers/specs/2026-06-05-video-link-health-design.md`.
- **Alembic head:** `c9d0e1f2a3b4` (verify: nothing chains from it — `grep -rl "down_revision.*c9d0e1f2a3b4" backend/alembic/versions/` is empty). The new migration chains from it. `alembic upgrade head` may hang locally → rely on CI; verify the chain offline via grep.
- **httpx** `0.27.0` is a dependency (`backend/requirements.txt`). Use `httpx.AsyncClient`.
- **Models:** `app/models/content.py` has `Lesson(id, module_id, level_id, type, content_json, xp_reward, order_index)`, `Level`, `Module(id, title, ...)`. Video lessons have `type == "video"`, `content_json["youtube_id"]`.
- **Email/alerting (REUSE — do NOT add a template):** `app/services/alerting.py` already sends admin alerts: it calls `recipients = await get_alert_emails(session)` (`app/services/app_settings.py`) and `get_email_sender().send(session, to=<recipient>, template="admin_llm_alert", context={"headline","detail","timestamp"})` (`app/services/email.py`). The `admin_llm_alert` template renders `headline` + `detail` + `timestamp`. Read `app/services/alerting.py` and reuse its public send function if one exists; otherwise mirror lines ~20-40 (loop recipients, send `admin_llm_alert`). In dev/CI `email_backend="logging"` so nothing is actually sent.
- **Admin router:** `app/routers/admin.py` — `router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])`; imports `get_session`, models, and schemas from `app.schemas.admin`; uses `selectinload`. Add the two new endpoints here (already admin-auth'd) or a focused new router `app/routers/video_health.py` included with the same dependency — **put them in `admin.py` for consistency**.
- **Cron pattern:** mirror `app/seed/run.py` — `from app.core.database import async_session_factory`, `async with async_session_factory() as session: ...; await session.commit()`, run via `asyncio.run(main())`.
- **Frontend admin API** (`frontend/src/api/admin.ts`): TanStack-Query hooks (`useFeedback`, `useModules`, …) over `adminFetch<T>(path, init)`. Add `useVideoHealth()` + a `useCheckVideoHealth()` mutation + types here.
- **Admin list pattern to mirror:** `frontend/src/components/admin/FeedbackList.tsx` (read-only table, light theme: `text-ink`, `text-muted-foreground`, `border-line`, badge classes like `bg-danger-100 text-danger-700`). Default export, used as a route element.
- **Admin sidebar:** `frontend/src/components/admin/AdminSidebar.tsx` `NAV_ITEMS` array (`{to, label, icon, end}`). Routes are registered in `frontend/src/App.tsx` under `<Route path="/admin" element={<AdminLayout/>}>` (e.g. `<Route path="feedback" element={<FeedbackList/>} />`).
- **Test fixtures:** async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` (per-test rollback). `admin_client` is an authenticated admin session — check `tests/conftest.py` for its exact name/usage and mirror an existing admin endpoint test (e.g. `tests/test_admin_*.py`). **No real network in tests** — patch the checker's HTTP client. Local Postgres may hang → rely on CI.

## Commands

- Backend (from `invest-ed/backend`): test `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`.
- Frontend (from `invest-ed/frontend`): `npx tsc -b`; `npm run lint` (known-OK warnings: `button.tsx` + `Market.tsx`); `npm test`; `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. NEVER read/modify any `.env`. CI's 6 jobs gate the Railway deploy.

---

## Task 1: `video_health` model + migration

**Files:**
- Create: `invest-ed/backend/app/models/video_health.py`
- Modify: `invest-ed/backend/app/models/__init__.py` (export, if the package re-exports models — check first)
- Create: `invest-ed/backend/alembic/versions/d0e1f2a3b4c5_add_video_health.py`
- Test: `invest-ed/backend/tests/test_video_health_model.py`

- [ ] **Step 1: Write the failing model test**

Create `tests/test_video_health_model.py`:

```python
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_video_health_row_roundtrips(db_session):
    m = Module(topic="savings", title="VH Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m); await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv); await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": "abc123"})
    db_session.add(lesson); await db_session.flush()

    from datetime import UTC, datetime
    vh = VideoHealth(lesson_id=lesson.id, youtube_id="abc123", status="ok",
                     http_status=200, checked_at=datetime.now(UTC))
    db_session.add(vh); await db_session.flush()

    got = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert got is not None and got.status == "ok" and got.youtube_id == "abc123"
```

- [ ] **Step 2: Run it — expect ImportError**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_model.py -v`
Expected: FAIL — `cannot import name 'VideoHealth'`.

- [ ] **Step 3: Create the model**

Create `app/models/video_health.py` (mirror an existing model's imports/`Base`; check `app/models/content.py` for the `Base`, `Mapped`, `mapped_column`, `UUID`, timestamp conventions):

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VideoHealth(Base):
    __tablename__ = "video_health"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    youtube_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | dead | unknown
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

> Adjust `Base`/`UUID` import to match the project's actual convention if `content.py` differs. If `app/models/__init__.py` explicitly imports each model (so Alembic autogenerate/metadata sees it), add `from app.models.video_health import VideoHealth  # noqa: F401`.

- [ ] **Step 4: Run the model test — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_model.py -v`
Expected: PASS. (If the test DB builds the schema from metadata via conftest, the table exists from the model alone.)

- [ ] **Step 5: Write the migration**

Create `alembic/versions/d0e1f2a3b4c5_add_video_health.py`:

```python
"""add video_health table

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-05

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_health",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", UUID(as_uuid=True),
                  sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("youtube_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("video_health")
```

- [ ] **Step 6: Verify chain + ruff + commit**

Run: `cd invest-ed/backend && grep -rl "down_revision.*c9d0e1f2a3b4" alembic/versions/` (expect: only the new file) and `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/models/video_health.py alembic/versions/d0e1f2a3b4c5_add_video_health.py tests/test_video_health_model.py`
Then:
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/video_health.py invest-ed/backend/alembic/versions/d0e1f2a3b4c5_add_video_health.py invest-ed/backend/tests/test_video_health_model.py
# include app/models/__init__.py only if you modified it
git commit -m "feat(video-health): video_health table + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Checker service

**Files:**
- Create: `invest-ed/backend/app/services/video_health_service.py`
- Test: `invest-ed/backend/tests/test_video_health_service.py`

**Interface (used by Tasks 3 & 4):**
- `oembed_url(youtube_id: str) -> str`
- `classify(http_status: int | None) -> str` → `"ok"` (200) / `"dead"` (404, 401) / `"unknown"` (anything else or None)
- `async def check_all_videos(session, *, client: httpx.AsyncClient | None = None) -> dict` → upserts `video_health` rows and returns `{"ok": int, "dead": int, "unknown": int, "dead_items": [{"lesson_id","youtube_id","module_title","lesson_title"}]}`.

- [ ] **Step 1: Write the failing service test**

Create `tests/test_video_health_service.py`. Use a stub transport so no real network is hit (httpx supports `MockTransport`):

```python
import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth
from app.services.video_health_service import check_all_videos, classify

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_classify():
    assert classify(200) == "ok"
    assert classify(404) == "dead"
    assert classify(401) == "dead"
    assert classify(500) == "unknown"
    assert classify(429) == "unknown"
    assert classify(None) == "unknown"


async def _video_lesson(db_session, youtube_id, title="V"):
    m = Module(topic="savings", title=f"Mod {title}", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m); await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv); await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "c"})
    db_session.add(lesson); await db_session.flush()
    return m, lesson


async def test_check_all_classifies_and_upserts(db_session):
    _, ok_lesson = await _video_lesson(db_session, "liveID", "ok")
    _, dead_lesson = await _video_lesson(db_session, "deadID", "dead")

    def handler(request: httpx.Request) -> httpx.Response:
        # oembed returns 200 for live, 404 for dead.
        return httpx.Response(200 if "liveID" in str(request.url) else 404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await check_all_videos(db_session, client=client)
    await client.aclose()
    await db_session.flush()

    assert summary["ok"] >= 1 and summary["dead"] >= 1
    assert any(d["youtube_id"] == "deadID" for d in summary["dead_items"])
    ok_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == ok_lesson.id))
    dead_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == dead_lesson.id))
    assert ok_row.status == "ok"
    assert dead_row.status == "dead"


async def test_blank_youtube_id_is_dead(db_session):
    _, lesson = await _video_lesson(db_session, "", "blank")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)  # should not even be called for blank id

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await check_all_videos(db_session, client=client)
    await client.aclose()
    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "dead"
```

- [ ] **Step 2: Run it — expect ImportError/FAIL**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_service.py -v`
Expected: FAIL — module/function not defined.

- [ ] **Step 3: Implement the service**

Create `app/services/video_health_service.py`:

```python
import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Module
from app.models.video_health import VideoHealth

_TIMEOUT = 8.0
_CONCURRENCY = 5


def oembed_url(youtube_id: str) -> str:
    return (
        "https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={youtube_id}&format=json"
    )


def classify(http_status: int | None) -> str:
    if http_status == 200:
        return "ok"
    if http_status in (401, 404):
        return "dead"
    return "unknown"


async def _probe(client: httpx.AsyncClient, youtube_id: str, sem: asyncio.Semaphore) -> tuple[str, int | None]:
    if not youtube_id:
        return "dead", None
    async with sem:
        try:
            resp = await client.get(oembed_url(youtube_id), timeout=_TIMEOUT)
            return classify(resp.status_code), resp.status_code
        except httpx.HTTPError:
            return "unknown", None  # transient — never alerted


async def check_all_videos(
    session: AsyncSession, *, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    rows = (await session.execute(
        select(Lesson, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.type == "video")
    )).all()

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient()
    sem = asyncio.Semaphore(_CONCURRENCY)
    try:
        results = await asyncio.gather(*[
            _probe(client, (lesson.content_json or {}).get("youtube_id", ""), sem)
            for lesson, _ in rows
        ])
    finally:
        if owns_client:
            await client.aclose()

    # Clean up stale rows (lessons that are gone / no longer video).
    valid_ids = [lesson.id for lesson, _ in rows]
    if valid_ids:
        await session.execute(delete(VideoHealth).where(VideoHealth.lesson_id.notin_(valid_ids)))
    else:
        await session.execute(delete(VideoHealth))

    now = datetime.now(UTC)
    summary: dict[str, Any] = {"ok": 0, "dead": 0, "unknown": 0, "dead_items": []}
    for (lesson, module_title), (status, http_status) in zip(rows, results):
        yt = (lesson.content_json or {}).get("youtube_id", "")
        existing = await session.scalar(
            select(VideoHealth).where(VideoHealth.lesson_id == lesson.id)
        )
        if existing is None:
            session.add(VideoHealth(
                lesson_id=lesson.id, youtube_id=yt, status=status,
                http_status=http_status, checked_at=now,
            ))
        else:
            existing.youtube_id = yt
            existing.status = status
            existing.http_status = http_status
            existing.checked_at = now
        summary[status] += 1
        if status == "dead":
            summary["dead_items"].append({
                "lesson_id": str(lesson.id), "youtube_id": yt,
                "module_title": module_title,
                "lesson_title": (lesson.content_json or {}).get("caption") or "Video lesson",
            })
    await session.flush()
    return summary
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_service.py -v`
Expected: all pass.

- [ ] **Step 5: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/video_health_service.py tests/test_video_health_service.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/video_health_service.py invest-ed/backend/tests/test_video_health_service.py
git commit -m "feat(video-health): oEmbed checker service (ok/dead/unknown + upsert)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Admin endpoints + schemas

**Files:**
- Modify: `invest-ed/backend/app/schemas/admin.py` (add response schemas)
- Modify: `invest-ed/backend/app/routers/admin.py` (two endpoints)
- Test: `invest-ed/backend/tests/test_video_health_admin.py`

- [ ] **Step 1: Write the failing endpoint test**

Create `tests/test_video_health_admin.py`. Mirror an existing admin endpoint test in the suite for the authenticated admin client + login flow (READ a sibling `tests/test_admin_*.py` first; use the suite's real admin fixture). Patch the service's HTTP so the check is deterministic:

```python
import httpx
import pytest

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_video(db_session, youtube_id):
    m = Module(topic="savings", title="VH Admin Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m); await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv); await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "Intro"})
    db_session.add(lesson); await db_session.flush()
    return lesson


async def test_check_then_list(admin_client, db_session, monkeypatch):
    lesson = await _seed_video(db_session, "deadID")

    # Force the checker's client to return 404 for everything.
    import app.services.video_health_service as svc
    real = svc.check_all_videos

    async def patched(session, *, client=None):
        def handler(req): return httpx.Response(404)
        c = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await real(session, client=c)
        finally:
            await c.aclose()
    monkeypatch.setattr(svc, "check_all_videos", patched)

    r = await admin_client.post("/admin/video-health/check")
    assert r.status_code == 200
    assert r.json()["summary"]["dead"] >= 1

    r2 = await admin_client.get("/admin/video-health")
    assert r2.status_code == 200
    item = next(i for i in r2.json() if i["lesson_id"] == str(lesson.id))
    assert item["status"] == "dead"
    assert item["youtube_id"] == "deadID"


async def test_video_health_requires_admin(client):
    r = await client.get("/admin/video-health")
    assert r.status_code in (401, 403)
```

> If the admin router imports `check_all_videos` by name (`from app.services.video_health_service import check_all_videos`) rather than calling it via the module, monkeypatching `svc.check_all_videos` won't be seen by the router — in that case patch where the router looks it up (`app.routers.admin.check_all_videos`). Choose the import style in Step 3 to make this straightforward (import the module: `from app.services import video_health_service` and call `video_health_service.check_all_videos(...)`).

- [ ] **Step 2: Run it — expect FAIL (404 route)**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_admin.py -v`
Expected: FAIL — endpoints don't exist.

- [ ] **Step 3: Add schemas**

In `app/schemas/admin.py`, add:

```python
class VideoHealthItem(BaseModel):
    lesson_id: uuid.UUID
    module_id: uuid.UUID
    module_title: str
    lesson_title: str
    youtube_id: str
    status: str | None  # ok | dead | unknown | None (never checked)
    http_status: int | None
    checked_at: datetime | None

    model_config = {"from_attributes": True}


class VideoHealthCheckResult(BaseModel):
    summary: dict
    items: list[VideoHealthItem]
```
(`uuid`, `datetime`, `BaseModel` are imported in that file already — confirm and add if missing.)

- [ ] **Step 4: Add the endpoints**

In `app/routers/admin.py`, import the service module + model + schemas:
```python
from app.services import video_health_service
from app.models.video_health import VideoHealth
from app.schemas.admin import VideoHealthItem, VideoHealthCheckResult  # add to existing admin-schema import
```
Add a helper + the two routes:

```python
async def _video_health_items(session: AsyncSession) -> list[VideoHealthItem]:
    rows = (await session.execute(
        select(Lesson, Module.id, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.type == "video")
        .order_by(Module.order_index, Lesson.order_index)
    )).all()
    health = {
        h.lesson_id: h
        for h in (await session.scalars(select(VideoHealth))).all()
    }
    out: list[VideoHealthItem] = []
    for lesson, module_id, module_title in rows:
        h = health.get(lesson.id)
        out.append(VideoHealthItem(
            lesson_id=lesson.id, module_id=module_id, module_title=module_title,
            lesson_title=(lesson.content_json or {}).get("caption") or "Video lesson",
            youtube_id=(lesson.content_json or {}).get("youtube_id", ""),
            status=h.status if h else None,
            http_status=h.http_status if h else None,
            checked_at=h.checked_at if h else None,
        ))
    return out


@router.get("/video-health", response_model=list[VideoHealthItem])
async def admin_video_health(session: AsyncSession = Depends(get_session)):
    return await _video_health_items(session)


@router.post("/video-health/check", response_model=VideoHealthCheckResult)
async def admin_video_health_check(session: AsyncSession = Depends(get_session)):
    summary = await video_health_service.check_all_videos(session)
    await session.commit()
    items = await _video_health_items(session)
    return VideoHealthCheckResult(summary=summary, items=items)
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_admin.py -v`
Expected: pass.

- [ ] **Step 6: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/admin.py invest-ed/backend/app/routers/admin.py invest-ed/backend/tests/test_video_health_admin.py
git commit -m "feat(video-health): admin list + check endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Cron command + email alert

**Files:**
- Create: `invest-ed/backend/app/video_health/__init__.py` (empty)
- Create: `invest-ed/backend/app/video_health/run.py`
- Test: `invest-ed/backend/tests/test_video_health_cron.py`

- [ ] **Step 1: Read the alerting helper**

Read `app/services/alerting.py` to find its public "send admin alert" function and signature (it loops `get_alert_emails(session)` and sends `template="admin_llm_alert"` with `{headline, detail, timestamp}`). Reuse that function from the cron. If it has no reusable public function, the cron will replicate the loop (Step 3 shows the fallback).

- [ ] **Step 2: Write the failing cron test**

Create `tests/test_video_health_cron.py`:

```python
import httpx
import pytest

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_video(db_session, youtube_id):
    m = Module(topic="savings", title="Cron Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m); await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv); await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "Intro"})
    db_session.add(lesson); await db_session.flush()
    return lesson


async def test_run_emails_only_when_dead(db_session, monkeypatch):
    await _seed_video(db_session, "deadID")

    sent: list[dict] = []

    async def fake_alert(session, headline, detail):
        sent.append({"headline": headline, "detail": detail})

    from app.video_health import run as cron
    # checker returns dead for everything
    async def fake_check(session, *, client=None):
        return {"ok": 0, "dead": 1, "unknown": 0,
                "dead_items": [{"lesson_id": "x", "youtube_id": "deadID",
                                "module_title": "Cron Mod", "lesson_title": "Intro"}]}
    monkeypatch.setattr(cron, "check_all_videos", fake_check)
    monkeypatch.setattr(cron, "send_video_alert", fake_alert)

    await cron.run(db_session)
    assert len(sent) == 1 and "deadID" in sent[0]["detail"]


async def test_run_no_email_when_all_ok(db_session, monkeypatch):
    sent: list[dict] = []
    from app.video_health import run as cron

    async def fake_check(session, *, client=None):
        return {"ok": 2, "dead": 0, "unknown": 1, "dead_items": []}

    async def fake_alert(session, headline, detail):
        sent.append({"headline": headline})

    monkeypatch.setattr(cron, "check_all_videos", fake_check)
    monkeypatch.setattr(cron, "send_video_alert", fake_alert)
    await cron.run(db_session)
    assert sent == []
```

- [ ] **Step 3: Implement the cron**

Create `app/video_health/__init__.py` (empty) and `app/video_health/run.py`:

```python
import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.services.app_settings import get_alert_emails
from app.services.email import get_email_sender
from app.services.video_health_service import check_all_videos


async def send_video_alert(session: AsyncSession, headline: str, detail: str) -> None:
    recipients = await get_alert_emails(session)
    if not recipients:
        return
    sender = get_email_sender()
    timestamp = datetime.now(UTC).isoformat()
    for to in recipients:
        await sender.send(
            session, to=to, template="admin_llm_alert",
            context={"headline": headline, "detail": detail, "timestamp": timestamp},
        )


async def run(session: AsyncSession) -> dict:
    summary = await check_all_videos(session)
    if summary["dead"]:
        lines = "\n".join(
            f"- {d['module_title']} → {d['lesson_title']} (youtube_id: {d['youtube_id'] or '∅'})"
            for d in summary["dead_items"]
        )
        await send_video_alert(
            session,
            headline=f"{summary['dead']} lesson video(s) are unavailable",
            detail=f"Update them in Admin → Video health.\n\n{lines}",
        )
    await session.commit()
    return summary


async def main() -> None:
    async with async_session_factory() as session:
        summary = await run(session)
    print(f"Video health check complete: {summary['ok']} ok, {summary['dead']} dead, {summary['unknown']} unknown.")


if __name__ == "__main__":
    asyncio.run(main())
```

> If `alerting.py` already exposes a suitable public function, import and call it inside `send_video_alert` instead of re-looping recipients (keep the `send_video_alert` wrapper name so the tests' monkeypatch target is stable).

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_cron.py -v`
Expected: pass.

- [ ] **Step 5: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/video_health/ tests/test_video_health_cron.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/video_health/ invest-ed/backend/tests/test_video_health_cron.py
git commit -m "feat(video-health): cron command + admin email alert on dead videos

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Frontend admin "Video health" page

**Files:**
- Modify: `invest-ed/frontend/src/api/admin.ts` (types + hooks)
- Create: `invest-ed/frontend/src/components/admin/VideoHealthList.tsx`
- Modify: `invest-ed/frontend/src/components/admin/AdminSidebar.tsx` (nav entry)
- Modify: `invest-ed/frontend/src/App.tsx` (route)
- Test: `invest-ed/frontend/src/components/admin/__tests__/VideoHealthList.test.tsx`

- [ ] **Step 1: Add API types + hooks**

In `src/api/admin.ts`, add:

```typescript
export interface VideoHealthItem {
  lesson_id: string;
  module_id: string;
  module_title: string;
  lesson_title: string;
  youtube_id: string;
  status: 'ok' | 'dead' | 'unknown' | null;
  http_status: number | null;
  checked_at: string | null;
}

export function useVideoHealth() {
  return useQuery({ queryKey: ['admin', 'video-health'], queryFn: () => adminFetch<VideoHealthItem[]>('/admin/video-health') });
}

export function useCheckVideoHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<{ summary: Record<string, number>; items: VideoHealthItem[] }>(
      '/admin/video-health/check', { method: 'POST' },
    ),
    onSuccess: (data) => qc.setQueryData(['admin', 'video-health'], data.items),
  });
}
```
(Match the file's existing imports — `useQuery`/`useMutation`/`useQueryClient` from `@tanstack/react-query` are already imported there for the other hooks; confirm.)

- [ ] **Step 2: Write the failing component test**

Create `src/components/admin/__tests__/VideoHealthList.test.tsx` (mirror `FeedbackList`/sibling admin test setup; wrap in QueryClientProvider; mock `@/api/admin`):

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import VideoHealthList from '../VideoHealthList';

const check = vi.fn().mockResolvedValue({ summary: {}, items: [] });
vi.mock('@/api/admin', () => ({
  useVideoHealth: () => ({
    data: [
      { lesson_id: 'l1', module_id: 'm1', module_title: 'Savings', lesson_title: 'Compound', youtube_id: 'deadID', status: 'dead', http_status: 404, checked_at: '2026-06-05T00:00:00Z' },
      { lesson_id: 'l2', module_id: 'm2', module_title: 'Stocks', lesson_title: 'What is a stock', youtube_id: 'liveID', status: 'ok', http_status: 200, checked_at: '2026-06-05T00:00:00Z' },
    ],
    isLoading: false, isError: false,
  }),
  useCheckVideoHealth: () => ({ mutate: check, isPending: false }),
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

describe('VideoHealthList', () => {
  it('renders statuses and flags the dead video', () => {
    wrap(<VideoHealthList />);
    expect(screen.getByText('Compound')).toBeInTheDocument();
    expect(screen.getByText(/dead/i)).toBeInTheDocument();
    expect(screen.getByText(/^ok$/i)).toBeInTheDocument();
  });

  it('Check now triggers a re-check', async () => {
    wrap(<VideoHealthList />);
    await userEvent.click(screen.getByRole('button', { name: /check now/i }));
    expect(check).toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<VideoHealthList />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 3: Run it — expect FAIL (no component)**

Run: `cd invest-ed/frontend && npm test -- VideoHealthList`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the page**

Create `src/components/admin/VideoHealthList.tsx` (light admin theme, mirror `FeedbackList`):

```tsx
import { Link } from 'react-router-dom';
import { useVideoHealth, useCheckVideoHealth } from '@/api/admin';

const STATUS_BADGE: Record<string, string> = {
  ok: 'bg-success-100 text-success-700',
  dead: 'bg-danger-100 text-danger-700',
  unknown: 'bg-accent-100 text-accent-700',
};

function badge(status: string | null) {
  const key = status ?? 'unchecked';
  const cls = status ? STATUS_BADGE[status] ?? 'bg-muted text-muted-foreground' : 'bg-muted text-muted-foreground';
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>{key}</span>;
}

export default function VideoHealthList() {
  const { data, isLoading, isError } = useVideoHealth();
  const check = useCheckVideoHealth();

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">Video health</h1>
        <button
          type="button"
          onClick={() => check.mutate()}
          disabled={check.isPending}
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {check.isPending ? 'Checking…' : 'Check now'}
        </button>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-danger-500">Failed to load video health.</p>}

      {data && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-muted-foreground">
              <th className="py-2 pr-4">Module</th>
              <th className="py-2 pr-4">Lesson</th>
              <th className="py-2 pr-4">YouTube ID</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Checked</th>
              <th className="py-2 pr-4">Edit</th>
            </tr>
          </thead>
          <tbody>
            {data.map((v) => (
              <tr key={v.lesson_id} className="border-b border-line">
                <td className="py-2 pr-4 text-ink">{v.module_title}</td>
                <td className="py-2 pr-4 text-ink">{v.lesson_title}</td>
                <td className="py-2 pr-4 font-mono text-muted-foreground">{v.youtube_id || '∅'}</td>
                <td className="py-2 pr-4">{badge(v.status)}</td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {v.checked_at ? new Date(v.checked_at).toLocaleDateString() : '—'}
                </td>
                <td className="py-2 pr-4">
                  <Link to={`/admin/modules/${v.module_id}`} className="text-brand-700 hover:underline">Edit</Link>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={6} className="py-4 text-muted-foreground">No video lessons.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
```
> The Edit link targets the module editor (`/admin/modules/:moduleId`) — the closest existing route that reaches the lesson. If a more direct lesson-edit route exists (check `App.tsx` admin routes), link to that instead.

- [ ] **Step 5: Wire the route + sidebar**

In `src/App.tsx`, add under the admin `<Route path="/admin" …>` block (near the `feedback` route):
```tsx
import VideoHealthList from '@/components/admin/VideoHealthList';
// ...
<Route path="video-health" element={<VideoHealthList />} />
```
In `src/components/admin/AdminSidebar.tsx`, add to `NAV_ITEMS` (after Feedback):
```tsx
{ to: '/admin/video-health', label: 'Video health', icon: '🎬', end: false },
```

- [ ] **Step 6: Run tests + tsc + lint**

Run: `cd invest-ed/frontend && npm test -- VideoHealthList && npx tsc -b && npm run lint`
Expected: tests pass; tsc clean; lint clean (known warnings only).

- [ ] **Step 7: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/admin.ts invest-ed/frontend/src/components/admin/VideoHealthList.tsx invest-ed/frontend/src/components/admin/AdminSidebar.tsx invest-ed/frontend/src/App.tsx invest-ed/frontend/src/components/admin/__tests__/VideoHealthList.test.tsx
git commit -m "feat(video-health): admin Video health page + sidebar entry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Docs (Railway cron) + full regression + push

**Files:**
- Modify: `invest-ed/AGENTS.md` and/or `invest-ed/docs/superpowers/PROGRESS.md` (record the feature + Railway cron setup note)

- [ ] **Step 1: Document the Railway cron setup**

Add a short note (in `PROGRESS.md` post-launch section and a one-liner in `AGENTS.md`): to enable the periodic check, add a Railway **cron service** in the backend project running `python -m app.video_health.run` on a schedule (e.g. daily `0 6 * * *`). It reuses the existing DB + `ALERT`/`admin_alert_email` config and only emails when a video is dead. On-demand checks are available in Admin → Video health.

- [ ] **Step 2: Backend regression**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: ruff clean; tests pass (rely on CI if local Postgres hangs).

- [ ] **Step 3: Frontend regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except the known warnings; tests pass; build OK.

- [ ] **Step 4: Commit docs + push**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/AGENTS.md invest-ed/docs/superpowers/PROGRESS.md
git commit -m "docs(video-health): record feature + Railway cron setup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
```
Confirm all 6 CI jobs green.

---

## Self-review notes

- **Spec coverage:** table (T1), checker + classify/transient-unknown/blank-dead/upsert/stale-cleanup (T2), admin list + check endpoints + auth (T3), cron + email-only-when-dead reusing `admin_llm_alert`/`get_alert_emails` (T4), admin page + sidebar + Check now + a11y (T5), Railway-cron doc + regression (T6). Known oEmbed-200-≠-embeddable limitation is documented in the spec (no code owed).
- **Placeholder scan:** concrete code + tests in every step; the two judgement notes (monkeypatch target import-style; Edit-link route) tell the implementer exactly what to verify.
- **Type consistency:** `check_all_videos(session, *, client=None) -> {ok,dead,unknown,dead_items}`, `classify`, `send_video_alert(session, headline, detail)`, `run(session)`, `VideoHealthItem`/`VideoHealthCheckResult` (BE) and `VideoHealthItem`/`useVideoHealth`/`useCheckVideoHealth` (FE) are used consistently across tasks. Migration `d0e1f2a3b4c5` ← `c9d0e1f2a3b4`.
- **Risk:** CI doesn't run `alembic upgrade head` (as found earlier), so the table is exercised in tests via metadata create_all; the migration SQL is simple `create_table` (low risk) and runs on Railway deploy. The checker never hits the network in tests (MockTransport / monkeypatch).
