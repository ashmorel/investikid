# Video Lessons Curation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the operator's hand-curated YouTube video lessons (archived in the GB/US/HK regen, purged ~2026-07-22) and re-attach them to the current curriculum, plus add an on-demand YouTube "suggest videos" source — both through one admin video-curation review queue.

**Architecture:** A new `VideoCandidate` review-queue table holds candidates from two sources (`recovered` = salvaged from archived modules, `suggested` = YouTube-API search). An admin page lists `pending` candidates with an embedded preview; approving one creates a `video` lesson in a chosen level (gated on the existing video-health embeddability check). Tasks 1–5 are Sub-project A (salvage, time-sensitive); Tasks 6–7 are Sub-project B (forward suggestion), reusing A's queue + approve flow.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic (backend); React 18 + Vite + TanStack Query + Tailwind + shadcn/ui (admin frontend); YouTube Data API v3 (`settings.youtube_api_key`); existing `video_health_service`.

## Global Constraints

- Kids' app, **WCAG 2.2 AA** on new admin UI — new page needs a `vitest-axe` test.
- DB change = **hand-written, chained Alembic migration**; current head is **`d4f6b8c0e2a1`** (verify with `alembic heads` before writing the migration). **Ask the user before applying the prod migration whether to snapshot first.**
- Admin endpoints reuse the admin router (already mounted behind admin auth); cron endpoints live in `app/routers/internal.py`, auth via `X-Cron-Secret` == `settings.cron_secret`, and **must** be added to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py`.
- Only **embeddable, non-age-restricted** videos may be approved into a lesson.
- Frontend: **no literal strings in JSX** (`i18next/no-literal-string` is an error) — all copy via `useTranslation('admin')` + keys in `frontend/src/locales/en/admin.json`.
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures (see existing `backend/tests/`).
- Beta: commit straight to `main`; backend ships on green CI, web via manual `vercel --prod` + alias (out of scope here — frontend tasks just need to pass `tsc`/lint/test/build).

**Reference (verified) facts:**
- `Lesson` (`app/models/content.py`): `id`, `module_id` (FK modules, NOT NULL), `level_id` (FK levels, nullable), `type: str`, `content_json: dict (JSON)`, `xp_reward: int = 10`, `order_index: int`.
- A `video` lesson's `content_json`: `{"video_source": "youtube", "youtube_id": "<id>", "caption": "<title>"}`. `validate_lesson_content_json("video", content_json)` (`app/schemas/admin.py`) enforces a non-empty `youtube_id`.
- Module: `id`, `topic: str(30)`, `market_code: str(2)`, `published: bool`, `archived_at: datetime|None`, `order_index`.
- Level: `id`, `module_id`, `title`, `order_index`.
- Purge (`app/services/module_purge_service.py`): deletes modules with `archived_at < now - retention_days`, cascading to lessons.
- Existing single-video embeddability probe: `_embeddable(client, youtube_id) -> bool` in `app/services/video_health_service.py` (uses `settings.youtube_api_key`).
- Internal cron endpoint pattern (`app/routers/internal.py`): `X-Cron-Secret` header, 503 if `settings.cron_secret` unset, 401 on mismatch (`secrets.compare_digest`).

---

## Task 1: `VideoCandidate` model + migration

**Files:**
- Modify: `backend/app/models/content.py` (append the model)
- Create: `backend/alembic/versions/<rev>_add_video_candidates.py`
- Test: `backend/tests/test_video_candidate_model.py`

**Interfaces:**
- Produces: `VideoCandidate` ORM model with columns `id, youtube_id, title, thumbnail_url, source, market_code, origin_context, suggested_module_id, suggested_level_id, embeddable, health_detail, status, created_lesson_id, created_at`; statuses are plain strings `"pending"|"approved"|"skipped"`, sources `"recovered"|"suggested"`; unique constraint `uq_video_candidate_video_market (youtube_id, market_code)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_video_candidate_model.py
import uuid
import pytest
from sqlalchemy import select
from app.models.content import VideoCandidate

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_video_candidate_persists_with_defaults(db_session):
    c = VideoCandidate(
        youtube_id="abc123", title="Compound interest explained",
        source="recovered", market_code="GB", origin_context="saving / Old Saving Module",
    )
    db_session.add(c)
    await db_session.flush()
    got = (await db_session.scalars(select(VideoCandidate))).one()
    assert got.status == "pending"          # server default
    assert got.embeddable is None
    assert got.suggested_module_id is None
    assert got.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_video_candidate_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'VideoCandidate'`.

- [ ] **Step 3: Add the model**

Append to `backend/app/models/content.py` (it already imports `uuid`, `datetime`, `Mapped`, `mapped_column`, `String`, `Integer`, `Boolean`, `DateTime`, `ForeignKey`, `UUID`, `JSON`):

```python
class VideoCandidate(Base):
    """Review queue for video lessons awaiting an operator's approval. Fed by the
    recovered-videos extraction and the YouTube suggestion endpoint; an approved
    candidate becomes a `video` Lesson."""
    __tablename__ = "video_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(12), nullable=False)  # recovered | suggested
    market_code: Mapped[str] = mapped_column(String(2), ForeignKey("markets.code"), nullable=False, index=True)
    origin_context: Mapped[str | None] = mapped_column(String(300), nullable=True)
    suggested_module_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="SET NULL"), nullable=True
    )
    suggested_level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.id", ondelete="SET NULL"), nullable=True
    )
    embeddable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    health_detail: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="pending", index=True)
    created_lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("youtube_id", "market_code", name="uq_video_candidate_video_market"),
    )
```

Ensure `from sqlalchemy import UniqueConstraint, func` is present at the top of the file (add to the existing `sqlalchemy` import line if missing).

- [ ] **Step 4: Write the migration**

Confirm head: `cd backend && alembic heads` → `d4f6b8c0e2a1`. Create `backend/alembic/versions/e7c1a2b3d4f5_add_video_candidates.py`:

```python
"""add video_candidates review queue

Revision ID: e7c1a2b3d4f5
Revises: d4f6b8c0e2a1
Create Date: 2026-06-23 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "e7c1a2b3d4f5"
down_revision: str | None = "d4f6b8c0e2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_candidates",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("youtube_id", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("origin_context", sa.String(length=300), nullable=True),
        sa.Column("suggested_module_id", UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_level_id", UUID(as_uuid=True), nullable=True),
        sa.Column("embeddable", sa.Boolean(), nullable=True),
        sa.Column("health_detail", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="pending", nullable=False),
        sa.Column("created_lesson_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.ForeignKeyConstraint(["suggested_module_id"], ["modules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_level_id"], ["levels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_id", "market_code", name="uq_video_candidate_video_market"),
    )
    op.create_index("ix_video_candidates_market_code", "video_candidates", ["market_code"])
    op.create_index("ix_video_candidates_status", "video_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_video_candidates_status", table_name="video_candidates")
    op.drop_index("ix_video_candidates_market_code", table_name="video_candidates")
    op.drop_table("video_candidates")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && alembic upgrade head && pytest tests/test_video_candidate_model.py -v`
Expected: migration applies; test PASSES. Also run `alembic heads` → single head `e7c1a2b3d4f5`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/content.py backend/alembic/versions/e7c1a2b3d4f5_add_video_candidates.py backend/tests/test_video_candidate_model.py
git commit -m "feat(video): VideoCandidate review-queue model + migration"
```

---

## Task 2: single-video embeddability helper

**Files:**
- Modify: `backend/app/services/video_health_service.py`
- Test: `backend/tests/test_video_embeddability.py`

**Interfaces:**
- Produces: `async def video_embeddability(youtube_id: str, *, client: httpx.AsyncClient | None = None) -> tuple[bool, str | None]` — returns `(True, None)` when embeddable + not age-restricted, else `(False, reason)` where reason ∈ `{"not_found", "embedding_disabled", "age_restricted", "api_error"}`. Reused by Tasks 3, 4, 6.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_video_embeddability.py
import httpx
import pytest
from app.services.video_health_service import video_embeddability

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _client(payload):
    def handler(request):
        return httpx.Response(200, json=payload)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))

async def test_embeddable_ok():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (True, None)

async def test_embedding_disabled():
    payload = {"items": [{"status": {"embeddable": False}, "contentDetails": {"contentRating": {}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (False, "embedding_disabled")

async def test_age_restricted():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {"ytRating": "ytAgeRestricted"}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (False, "age_restricted")

async def test_not_found():
    async with _client({"items": []}) as c:
        assert await video_embeddability("vid", client=c) == (False, "not_found")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_video_embeddability.py -v`
Expected: FAIL — `ImportError: cannot import name 'video_embeddability'`.

- [ ] **Step 3: Add the helper**

Add to `backend/app/services/video_health_service.py` (it already imports `httpx` and `settings`; `_TIMEOUT` exists):

```python
async def video_embeddability(
    youtube_id: str, *, client: httpx.AsyncClient | None = None
) -> tuple[bool, str | None]:
    """Single-video health probe. (True, None) if embeddable AND not age-restricted,
    else (False, reason). reason: not_found | embedding_disabled | age_restricted | api_error."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=status,contentDetails&id={youtube_id}&key={settings.youtube_api_key}",
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return False, "api_error"
        items = resp.json().get("items", [])
        if not items:
            return False, "not_found"
        item = items[0]
        if item.get("contentDetails", {}).get("contentRating", {}).get("ytRating") == "ytAgeRestricted":
            return False, "age_restricted"
        if not item.get("status", {}).get("embeddable", False):
            return False, "embedding_disabled"
        return True, None
    except (httpx.HTTPError, ValueError):
        return False, "api_error"
    finally:
        if owns_client:
            await client.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_video_embeddability.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/video_health_service.py backend/tests/test_video_embeddability.py
git commit -m "feat(video): single-video embeddability/age-restriction helper"
```

---

## Task 3: recovered-video extraction + cron endpoint (DEADLINE-CRITICAL)

**Files:**
- Create: `backend/app/services/video_salvage_service.py`
- Modify: `backend/app/routers/internal.py` (add endpoint), `backend/app/core/csrf.py` (exempt path)
- Create: `.github/workflows/video-candidates-extract.yml`
- Test: `backend/tests/test_video_salvage_service.py`

**Interfaces:**
- Consumes: `VideoCandidate` (Task 1), `video_embeddability` (Task 2).
- Produces: `async def extract_recovered_candidates(session, *, client=None) -> dict` returning `{"found": int, "created": int}`; idempotent (dedup on `(youtube_id, market_code)`); sets `suggested_module_id`/`suggested_level_id` by topic-match and backfills `embeddable`/`health_detail`. Endpoint `POST /internal/video-candidates/extract`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_video_salvage_service.py
import datetime as dt
import httpx
import pytest
from sqlalchemy import select
from app.models.content import Module, Level, Lesson, VideoCandidate
from app.services.video_salvage_service import extract_recovered_candidates

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _ok_client():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]}
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))

async def _seed(db_session):
    # archived module (old) with a video lesson, + a current published module same topic
    old = Module(topic="saving", title="Old Saving", market_code="GB", order_index=0,
                 published=True, archived_at=dt.datetime.now(dt.UTC))
    new = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add_all([old, new]); await db_session.flush()
    new_level = Level(module_id=new.id, title="Level 1", order_index=0)
    old_level = Level(module_id=old.id, title="Old L1", order_index=0)
    db_session.add_all([new_level, old_level]); await db_session.flush()
    db_session.add(Lesson(module_id=old.id, level_id=old_level.id, type="video",
                          content_json={"video_source": "youtube", "youtube_id": "vid1", "caption": "Saving 101"},
                          xp_reward=10, order_index=0))
    await db_session.flush()
    return new, new_level

async def test_extracts_archived_video_and_topic_matches(db_session):
    new, new_level = await _seed(db_session)
    async with _ok_client() as c:
        res = await extract_recovered_candidates(db_session, client=c)
    assert res == {"found": 1, "created": 1}
    cand = (await db_session.scalars(select(VideoCandidate))).one()
    assert cand.youtube_id == "vid1"
    assert cand.source == "recovered"
    assert cand.market_code == "GB"
    assert cand.suggested_module_id == new.id          # topic-matched to current module
    assert cand.suggested_level_id == new_level.id
    assert cand.embeddable is True

async def test_extraction_is_idempotent(db_session):
    await _seed(db_session)
    async with _ok_client() as c:
        await extract_recovered_candidates(db_session, client=c)
        res2 = await extract_recovered_candidates(db_session, client=c)
    assert res2["created"] == 0
    assert len((await db_session.scalars(select(VideoCandidate))).all()) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_video_salvage_service.py -v`
Expected: FAIL — module `video_salvage_service` not found.

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/video_salvage_service.py
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module, VideoCandidate
from app.services.video_health_service import video_embeddability


async def _topic_match(session: AsyncSession, *, topic: str, market_code: str) -> tuple[object, object]:
    """Current published, non-archived module with the same topic + market → (module_id, level_id)
    of its first level. Returns (None, None) on no match."""
    module = (await session.scalars(
        select(Module).where(
            Module.topic == topic, Module.market_code == market_code,
            Module.published.is_(True), Module.archived_at.is_(None),
        ).order_by(Module.order_index)
    )).first()
    if module is None:
        return None, None
    level = (await session.scalars(
        select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
    )).first()
    return module.id, (level.id if level else None)


async def extract_recovered_candidates(
    session: AsyncSession, *, client: httpx.AsyncClient | None = None
) -> dict:
    """Scan ARCHIVED modules for video lessons; create a recovered VideoCandidate for each
    (idempotent on youtube_id+market), topic-matched to the current curriculum, health-backfilled."""
    owns = client is None
    client = client or httpx.AsyncClient()
    found = created = 0
    try:
        rows = (await session.execute(
            select(Lesson, Module)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.archived_at.is_not(None), Lesson.type == "video")
        )).all()
        for lesson, module in rows:
            cj = lesson.content_json or {}
            youtube_id = cj.get("youtube_id")
            if not youtube_id:
                continue
            found += 1
            exists = (await session.scalars(select(VideoCandidate).where(
                VideoCandidate.youtube_id == youtube_id,
                VideoCandidate.market_code == module.market_code,
            ))).first()
            if exists:
                continue
            mod_id, lvl_id = await _topic_match(session, topic=module.topic, market_code=module.market_code)
            embeddable, detail = await video_embeddability(youtube_id, client=client)
            session.add(VideoCandidate(
                youtube_id=youtube_id,
                title=cj.get("caption") or f"Video ({youtube_id})",
                source="recovered", market_code=module.market_code,
                origin_context=f"{module.topic} / {module.title}",
                suggested_module_id=mod_id, suggested_level_id=lvl_id,
                embeddable=embeddable, health_detail=detail,
            ))
            created += 1
        await session.commit()
        return {"found": found, "created": created}
    finally:
        if owns:
            await client.aclose()
```

- [ ] **Step 4: Run service tests**

Run: `cd backend && pytest tests/test_video_salvage_service.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Add the cron endpoint + CSRF exemption**

In `backend/app/routers/internal.py` (mirror the existing `video-health/run` endpoint — same imports: `Header`, `secrets`, `settings`, `get_session`):

```python
@router.post("/video-candidates/extract")
async def trigger_video_candidate_extract(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    from app.services.video_salvage_service import extract_recovered_candidates
    return await extract_recovered_candidates(session)
```

In `backend/app/core/csrf.py`, add to `_DEFAULT_EXEMPT_PATHS`:

```python
    "/internal/video-candidates/extract",
```

- [ ] **Step 6: Add a manual-trigger workflow**

Create `.github/workflows/video-candidates-extract.yml` (modeled on the existing cron workflow; `workflow_dispatch` only — this is run once):

```yaml
name: Video candidates extract (one-off)
on:
  workflow_dispatch:
jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger extraction
        env:
          CRON_SECRET: ${{ secrets.CRON_SECRET }}
          BACKEND_URL: ${{ vars.BACKEND_URL }}
        run: |
          curl -sS -X POST --retry 4 --retry-delay 5 \
            -H "X-Cron-Secret: $CRON_SECRET" \
            "$BACKEND_URL/internal/video-candidates/extract"
```

- [ ] **Step 7: Add an endpoint auth test**

```python
# append to backend/tests/test_video_salvage_service.py
async def test_extract_endpoint_requires_cron_secret(client):
    r = await client.post("/internal/video-candidates/extract")  # no header
    assert r.status_code in (401, 503)
```

Run: `cd backend && pytest tests/test_video_salvage_service.py -v` → all PASS. Verify with `ruff check app`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/video_salvage_service.py backend/app/routers/internal.py backend/app/core/csrf.py .github/workflows/video-candidates-extract.yml backend/tests/test_video_salvage_service.py
git commit -m "feat(video): recovered-video extraction service + cron endpoint"
```

---

## Task 4: admin list / approve / skip endpoints

**Files:**
- Create: `backend/app/routers/video_curation.py` (admin router) + register it in `backend/app/main.py`
- Modify: `backend/app/schemas/admin.py` (add response/request schemas)
- Test: `backend/tests/test_video_curation_api.py`

**Interfaces:**
- Consumes: `VideoCandidate` (Task 1), `video_embeddability` (Task 2), `validate_lesson_content_json` (`app/schemas/admin.py`).
- Produces: `GET /admin/video-candidates?market=&status=pending` → `list[VideoCandidateOut]`; `POST /admin/video-candidates/{id}/approve` body `{module_id, level_id}` → creates a `video` Lesson, sets candidate `approved` + `created_lesson_id`; `POST /admin/video-candidates/{id}/skip` → `skipped`. Approve 409s if `embeddable` is not True.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_video_curation_api.py
import uuid
import pytest
from sqlalchemy import select
from app.models.content import Module, Level, Lesson, VideoCandidate

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _candidate(db_session, *, embeddable=True):
    m = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add(m); await db_session.flush()
    lvl = Level(module_id=m.id, title="L1", order_index=0)
    db_session.add(lvl); await db_session.flush()
    c = VideoCandidate(youtube_id="vid1", title="Saving 101", source="recovered",
                       market_code="GB", suggested_module_id=m.id, suggested_level_id=lvl.id,
                       embeddable=embeddable)
    db_session.add(c); await db_session.flush()
    return c, m, lvl

async def test_list_pending(admin_client, db_session):
    await _candidate(db_session)
    r = await admin_client.get("/admin/video-candidates?status=pending")
    assert r.status_code == 200
    assert r.json()[0]["youtube_id"] == "vid1"

async def test_approve_creates_video_lesson(admin_client, db_session):
    c, m, lvl = await _candidate(db_session)
    r = await admin_client.post(f"/admin/video-candidates/{c.id}/approve",
                                json={"module_id": str(m.id), "level_id": str(lvl.id)})
    assert r.status_code == 200
    lesson = (await db_session.scalars(select(Lesson).where(Lesson.type == "video"))).one()
    assert lesson.content_json["youtube_id"] == "vid1"
    assert lesson.level_id == lvl.id
    refreshed = await db_session.get(VideoCandidate, c.id)
    await db_session.refresh(refreshed)
    assert refreshed.status == "approved"
    assert refreshed.created_lesson_id == lesson.id

async def test_approve_blocked_when_not_embeddable(admin_client, db_session):
    c, m, lvl = await _candidate(db_session, embeddable=False)
    r = await admin_client.post(f"/admin/video-candidates/{c.id}/approve",
                                json={"module_id": str(m.id), "level_id": str(lvl.id)})
    assert r.status_code == 409

async def test_skip(admin_client, db_session):
    c, m, lvl = await _candidate(db_session)
    r = await admin_client.post(f"/admin/video-candidates/{c.id}/skip")
    assert r.status_code == 200
    refreshed = await db_session.get(VideoCandidate, c.id)
    await db_session.refresh(refreshed)
    assert refreshed.status == "skipped"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_video_curation_api.py -v`
Expected: FAIL — routes 404 (router not registered).

- [ ] **Step 3: Add schemas**

Append to `backend/app/schemas/admin.py`:

```python
class VideoCandidateOut(BaseModel):
    id: uuid.UUID
    youtube_id: str
    title: str
    thumbnail_url: str | None
    source: str
    market_code: str
    origin_context: str | None
    suggested_module_id: uuid.UUID | None
    suggested_level_id: uuid.UUID | None
    embeddable: bool | None
    health_detail: str | None
    status: str

    model_config = {"from_attributes": True}


class ApproveCandidateIn(BaseModel):
    module_id: uuid.UUID
    level_id: uuid.UUID
```

- [ ] **Step 4: Add the router + register it**

```python
# backend/app/routers/video_curation.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Level, VideoCandidate
from app.routers.admin import require_admin  # existing admin-auth dependency
from app.schemas.admin import ApproveCandidateIn, VideoCandidateOut

router = APIRouter(prefix="/admin/video-candidates", tags=["admin-video"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[VideoCandidateOut])
async def list_candidates(
    status: str = "pending", market: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(VideoCandidate).where(VideoCandidate.status == status)
    if market:
        q = q.where(VideoCandidate.market_code == market)
    return (await session.scalars(q.order_by(VideoCandidate.created_at))).all()


@router.post("/{candidate_id}/approve", response_model=VideoCandidateOut)
async def approve_candidate(
    candidate_id: uuid.UUID, payload: ApproveCandidateIn,
    session: AsyncSession = Depends(get_session),
):
    cand = await session.get(VideoCandidate, candidate_id)
    if cand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate not found")
    if cand.embeddable is not True:
        raise HTTPException(status.HTTP_409_CONFLICT, "video failed the embeddability/safety check")
    level = await session.get(Level, payload.level_id)
    if level is None or level.module_id != payload.module_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "level does not belong to module")
    next_order = ((await session.scalar(
        select(Lesson.order_index).where(Lesson.level_id == level.id).order_by(Lesson.order_index.desc())
    )) or -1) + 1
    lesson = Lesson(
        module_id=payload.module_id, level_id=level.id, type="video",
        content_json={"video_source": "youtube", "youtube_id": cand.youtube_id, "caption": cand.title},
        xp_reward=10, order_index=next_order,
    )
    session.add(lesson)
    await session.flush()
    cand.status = "approved"
    cand.created_lesson_id = lesson.id
    await session.commit()
    await session.refresh(cand)
    return cand


@router.post("/{candidate_id}/skip", response_model=VideoCandidateOut)
async def skip_candidate(candidate_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    cand = await session.get(VideoCandidate, candidate_id)
    if cand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate not found")
    cand.status = "skipped"
    await session.commit()
    await session.refresh(cand)
    return cand
```

Register in `backend/app/main.py` next to the other admin routers: `from app.routers import video_curation` and `app.include_router(video_curation.router)`.

> NOTE: confirm the exact admin-auth dependency name in `app/routers/admin.py` (the report shows admin endpoints share an auth guard — use whatever the existing admin router uses, e.g. `require_admin` or a router-level `dependencies=[Depends(get_current_admin)]`). Match it exactly.

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_video_curation_api.py -v`
Expected: 4 PASS. `ruff check app`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/video_curation.py backend/app/main.py backend/app/schemas/admin.py backend/tests/test_video_curation_api.py
git commit -m "feat(video): admin list/approve/skip video-candidate endpoints"
```

---

## Task 5: admin Video Curation page (frontend)

**Files:**
- Create: `frontend/src/api/videoCuration.ts`, `frontend/src/components/admin/VideoCuration.tsx`
- Modify: `frontend/src/components/admin/AdminSidebar.tsx`, `frontend/src/App.tsx`, `frontend/src/locales/en/admin.json`
- Test: `frontend/src/components/admin/__tests__/VideoCuration.test.tsx`

**Interfaces:**
- Consumes: backend endpoints from Task 4. Uses the existing `adminFetch` helper (`frontend/src/api/admin.ts`) and `marketApi.list()` for the market filter; modules/levels for the re-place dropdowns via existing admin module hooks.
- Produces: route `/admin/video-curation`, sidebar item `sidebar.items.videoCuration`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/admin/__tests__/VideoCuration.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import VideoCuration from '../VideoCuration';
import * as api from '@/api/videoCuration';

vi.mock('@/api/videoCuration');

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.mocked(api.listVideoCandidates).mockResolvedValue([
    { id: '1', youtube_id: 'vid1', title: 'Saving 101', source: 'recovered', market_code: 'GB',
      suggested_module_id: 'm1', suggested_level_id: 'l1', embeddable: true, health_detail: null,
      status: 'pending', origin_context: 'saving / Old', thumbnail_url: null },
  ]);
});

describe('VideoCuration', () => {
  it('renders pending candidates with an approve action', async () => {
    wrap(<VideoCuration />);
    expect(await screen.findByText('Saving 101')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<VideoCuration />);
    await screen.findByText('Saving 101');
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/VideoCuration.test.tsx`
Expected: FAIL — modules not found.

- [ ] **Step 3: API client**

```ts
// frontend/src/api/videoCuration.ts
import { adminFetch } from './admin';

export type VideoCandidate = {
  id: string; youtube_id: string; title: string; thumbnail_url: string | null;
  source: 'recovered' | 'suggested'; market_code: string; origin_context: string | null;
  suggested_module_id: string | null; suggested_level_id: string | null;
  embeddable: boolean | null; health_detail: string | null; status: string;
};

export const listVideoCandidates = (market?: string) =>
  adminFetch<VideoCandidate[]>(`/admin/video-candidates?status=pending${market ? `&market=${market}` : ''}`);

export const approveVideoCandidate = (id: string, body: { module_id: string; level_id: string }) =>
  adminFetch<VideoCandidate>(`/admin/video-candidates/${id}/approve`, { method: 'POST', body: JSON.stringify(body) });

export const skipVideoCandidate = (id: string) =>
  adminFetch<VideoCandidate>(`/admin/video-candidates/${id}/skip`, { method: 'POST' });
```

- [ ] **Step 4: Page component**

```tsx
// frontend/src/components/admin/VideoCuration.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { listVideoCandidates, approveVideoCandidate, skipVideoCandidate } from '@/api/videoCuration';

export default function VideoCuration() {
  const { t } = useTranslation('admin');
  const qc = useQueryClient();
  const [market, setMarket] = useState<string>('');
  const candidatesQ = useQuery({
    queryKey: ['admin', 'video-candidates', market],
    queryFn: () => listVideoCandidates(market || undefined),
  });
  const approve = useMutation({
    mutationFn: (v: { id: string; module_id: string; level_id: string }) =>
      approveVideoCandidate(v.id, { module_id: v.module_id, level_id: v.level_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'video-candidates'] }),
  });
  const skip = useMutation({
    mutationFn: (id: string) => skipVideoCandidate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'video-candidates'] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-extrabold text-ink">{t('videoCuration.heading')}</h1>
      <p className="text-sm text-muted-foreground">{t('videoCuration.subtitle')}</p>
      <ul className="space-y-4">
        {(candidatesQ.data ?? []).map((c) => (
          <li key={c.id} className="rounded-xl border border-line bg-card p-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <iframe
                title={c.title}
                src={`https://www.youtube.com/embed/${c.youtube_id}`}
                className="aspect-video w-full sm:w-80"
                allow="encrypted-media"
              />
              <div className="flex-1 space-y-2">
                <div className="font-semibold text-ink">{c.title}</div>
                <div className="text-xs text-muted-foreground">
                  {c.source} · {c.market_code} · {c.origin_context}
                </div>
                {c.embeddable === false && (
                  <p className="text-xs font-semibold text-red-600">
                    {t('videoCuration.blocked', { reason: c.health_detail ?? '' })}
                  </p>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={c.embeddable !== true || !c.suggested_module_id || !c.suggested_level_id || approve.isPending}
                    onClick={() => approve.mutate({ id: c.id, module_id: c.suggested_module_id!, level_id: c.suggested_level_id! })}
                    className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {t('videoCuration.approve')}
                  </button>
                  <button
                    type="button"
                    disabled={skip.isPending}
                    onClick={() => skip.mutate(c.id)}
                    className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink"
                  >
                    {t('videoCuration.skip')}
                  </button>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
      {candidatesQ.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">{t('videoCuration.empty')}</p>
      )}
    </div>
  );
}
```

> Re-placement dropdowns: this MVP approves to the topic-matched `suggested_module_id/level_id`. If you want operator override of the home in this task, add module + level `<select>`s sourced from the existing `useModules()` hook + a per-module levels fetch, writing the chosen ids into the `approve.mutate` call. Keep it a follow-up if it bloats the task.

- [ ] **Step 5: Wire route + sidebar + i18n**

In `frontend/src/App.tsx`: `const VideoCuration = lazy(() => import('@/components/admin/VideoCuration'));` and under the `/admin` route add `<Route path="video-curation" element={<VideoCuration />} />`.

In `frontend/src/components/admin/AdminSidebar.tsx` `NAV_ITEMS`, add after `video-health`:
```ts
  { to: '/admin/video-curation', tKey: 'sidebar.items.videoCuration', icon: '🎞️', end: false },
```

In `frontend/src/locales/en/admin.json`, add `"videoCuration": "Video curation"` under `sidebar.items`, and a top-level block:
```json
  "videoCuration": {
    "heading": "Video curation",
    "subtitle": "Review recovered and suggested videos, then approve them into lessons.",
    "approve": "Approve into lesson",
    "skip": "Skip",
    "blocked": "Can't embed this video ({{reason}}).",
    "empty": "No videos waiting for review."
  }
```

- [ ] **Step 6: Run tests + verify**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/VideoCuration.test.tsx && npx tsc --noEmit && npx eslint src/components/admin/VideoCuration.tsx src/api/videoCuration.ts`
Expected: tests PASS, tsc + eslint clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/videoCuration.ts frontend/src/components/admin/VideoCuration.tsx frontend/src/components/admin/AdminSidebar.tsx frontend/src/App.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/VideoCuration.test.tsx
git commit -m "feat(video): admin Video Curation page"
```

---

## Task 6: YouTube suggestion endpoint (Sub-project B)

**Files:**
- Create: `backend/app/services/video_suggest_service.py`
- Modify: `backend/app/routers/video_curation.py` (add `/suggest`), `backend/app/schemas/admin.py`
- Test: `backend/tests/test_video_suggest_service.py`

**Interfaces:**
- Consumes: `VideoCandidate`, `video_embeddability`, `Module`/`Level`.
- Produces: `async def suggest_videos(session, *, module_id, level_id, client=None) -> dict` returning `{"created": int}`; queries YouTube `search.list` (`safeSearch=strict`) for the module's topic/title + market, keeps only embeddable/non-age-restricted, inserts `source="suggested"` candidates (idempotent). Endpoint `POST /admin/video-candidates/suggest`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_video_suggest_service.py
import httpx
import pytest
from sqlalchemy import select
from app.models.content import Module, Level, VideoCandidate
from app.services.video_suggest_service import suggest_videos

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _client():
    def handler(request):
        if "search" in str(request.url):
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "ytA"}, "snippet": {"title": "Saving for kids",
                 "thumbnails": {"medium": {"url": "http://t/A.jpg"}}}},
            ]})
        # videos.list health probe
        return httpx.Response(200, json={"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))

async def test_suggest_inserts_embeddable_candidates(db_session):
    m = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add(m); await db_session.flush()
    lvl = Level(module_id=m.id, title="L1", order_index=0); db_session.add(lvl); await db_session.flush()
    async with _client() as c:
        res = await suggest_videos(db_session, module_id=m.id, level_id=lvl.id, client=c)
    assert res["created"] == 1
    cand = (await db_session.scalars(select(VideoCandidate))).one()
    assert cand.source == "suggested"
    assert cand.youtube_id == "ytA"
    assert cand.suggested_module_id == m.id
    assert cand.embeddable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_video_suggest_service.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/video_suggest_service.py
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Level, Module, VideoCandidate
from app.services.video_health_service import video_embeddability

_SEARCH = "https://www.googleapis.com/youtube/v3/search"


async def suggest_videos(
    session: AsyncSession, *, module_id, level_id, client: httpx.AsyncClient | None = None
) -> dict:
    module = await session.get(Module, module_id)
    if module is None:
        return {"created": 0}
    owns = client is None
    client = client or httpx.AsyncClient()
    created = 0
    try:
        query = f"{module.title} {module.topic} for kids money lesson"
        resp = await client.get(_SEARCH, params={
            "part": "snippet", "type": "video", "videoEmbeddable": "true",
            "safeSearch": "strict", "maxResults": 8, "q": query, "key": settings.youtube_api_key,
        }, timeout=10.0)
        if resp.status_code != 200:
            return {"created": 0}
        for item in resp.json().get("items", []):
            yt = item.get("id", {}).get("videoId")
            if not yt:
                continue
            if (await session.scalars(select(VideoCandidate).where(
                VideoCandidate.youtube_id == yt, VideoCandidate.market_code == module.market_code,
            ))).first():
                continue
            embeddable, detail = await video_embeddability(yt, client=client)
            if not embeddable:
                continue
            snip = item.get("snippet", {})
            session.add(VideoCandidate(
                youtube_id=yt, title=(snip.get("title") or yt)[:300],
                thumbnail_url=snip.get("thumbnails", {}).get("medium", {}).get("url"),
                source="suggested", market_code=module.market_code,
                origin_context=f"{module.topic} / {module.title}",
                suggested_module_id=module.id, suggested_level_id=level_id,
                embeddable=True, health_detail=detail,
            ))
            created += 1
        await session.commit()
        return {"created": created}
    finally:
        if owns:
            await client.aclose()
```

- [ ] **Step 4: Add the endpoint**

In `backend/app/schemas/admin.py`:
```python
class SuggestVideosIn(BaseModel):
    module_id: uuid.UUID
    level_id: uuid.UUID
```

In `backend/app/routers/video_curation.py`:
```python
from app.schemas.admin import SuggestVideosIn
from app.services.video_suggest_service import suggest_videos

@router.post("/suggest")
async def suggest(payload: SuggestVideosIn, session: AsyncSession = Depends(get_session)):
    return await suggest_videos(session, module_id=payload.module_id, level_id=payload.level_id)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_video_suggest_service.py tests/test_video_curation_api.py -v` → PASS. `ruff check app`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/video_suggest_service.py backend/app/routers/video_curation.py backend/app/schemas/admin.py backend/tests/test_video_suggest_service.py
git commit -m "feat(video): YouTube suggest-videos endpoint"
```

---

## Task 7: "Suggest videos" frontend action (Sub-project B)

**Files:**
- Modify: `frontend/src/api/videoCuration.ts`, `frontend/src/components/admin/VideoCuration.tsx`, `frontend/src/locales/en/admin.json`
- Test: extend `frontend/src/components/admin/__tests__/VideoCuration.test.tsx`

**Interfaces:**
- Consumes: `POST /admin/video-candidates/suggest` (Task 6).
- Produces: a "Suggest videos" control that takes a module + level and refetches the queue.

- [ ] **Step 1: Write the failing test** (add to the existing test file)

```tsx
it('calls suggest then refetches', async () => {
  vi.mocked(api.suggestVideos).mockResolvedValue({ created: 2 });
  wrap(<VideoCuration />);
  await screen.findByText('Saving 101');
  await userEvent.click(screen.getByRole('button', { name: /suggest videos/i }));
  // a module + level must be chosen first; assert the call fired with ids
  expect(api.suggestVideos).toHaveBeenCalled();
});
```
(import `userEvent` from `@testing-library/user-event`.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/VideoCuration.test.tsx` → FAIL (`suggestVideos` undefined / no button).

- [ ] **Step 3: Add the client fn + UI control**

Add to `frontend/src/api/videoCuration.ts`:
```ts
export const suggestVideos = (body: { module_id: string; level_id: string }) =>
  adminFetch<{ created: number }>(`/admin/video-candidates/suggest`, { method: 'POST', body: JSON.stringify(body) });
```

In `VideoCuration.tsx`, add a small "Suggest videos" section: two `<select>`s (module from `useModules()`, level from a per-module levels fetch) + a button calling a `useMutation(suggestVideos)` whose `onSuccess` invalidates `['admin','video-candidates']`. Reuse the existing module/level admin hooks; gate the button until both ids are chosen. All copy via `t('videoCuration.suggest')` etc.

Add i18n keys: `"suggest": "Suggest videos"`, `"suggestModule": "Module"`, `"suggestLevel": "Level"`, `"suggested": "Added {{count}} suggestions."`.

- [ ] **Step 4: Run tests + verify**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/VideoCuration.test.tsx && npx tsc --noEmit && npx eslint src/components/admin/VideoCuration.tsx src/api/videoCuration.ts`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/videoCuration.ts frontend/src/components/admin/VideoCuration.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/VideoCuration.test.tsx
git commit -m "feat(video): Suggest videos action on the curation page"
```

---

## Final verification (after all tasks)

- [ ] Backend: `cd backend && ruff check app && pytest -q` (full suite green).
- [ ] Frontend: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run build`.
- [ ] **Prod migration:** ask the user whether to snapshot, then apply `e7c1a2b3d4f5` per `docs/deployment-environments.md`.
- [ ] **Run the extraction once** (deadline item): trigger `video-candidates-extract.yml` (`gh workflow run`) BEFORE ~2026-07-22, then review/approve the recovered videos in `/admin/video-curation`.
- [ ] Update `docs/MASTER-BACKLOG.md` (move into "Live in prod") + this plan's checkboxes.
- [ ] `cd frontend && npx cap sync ios && npx cap sync android` (the new admin page rides the next native build; bump build numbers per the deploy doc).

## Self-review notes

- **Spec coverage:** VideoCandidate table (Task 1) ✓; extraction + purge-defusing cron (Task 3) ✓; topic-match (Task 3 `_topic_match`) ✓; health gating (Task 2 helper, used in 3/4/6) ✓; admin queue + approve→lesson + skip (Tasks 4–5) ✓; forward YouTube suggestion (Tasks 6–7) ✓; WCAG/axe (Task 5) ✓; migration + snapshot ask (Task 1 + final) ✓.
- **Deviation flagged:** the spec's re-placement "editable module/level dropdowns" are MVP'd in Task 5 as approve-to-suggested-home, with the dropdown override called out as an in-task or follow-up addition — confirm with the user which they want when executing Task 5.
- **Confirm at execution:** the exact admin-auth dependency symbol in `app/routers/admin.py` (Task 4 Step 4 note) and that `app/models/content.py` already imports `func` + `UniqueConstraint` (Task 1 Step 3).
