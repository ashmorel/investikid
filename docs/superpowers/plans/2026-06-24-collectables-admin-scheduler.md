# Collectables B2 — Admin Drop Scheduler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin console page to schedule limited-edition collectable drops (which item, rarity, unlock rule, window) over a dev-supplied art pool, writing the same `cosmetic_items` columns the B1 grant engine already reads.

**Architecture:** A "drop" stays a `CosmeticItem` row with the B1 limited-drop columns set (B1 unchanged). One new boolean column `drop_eligible` marks dev-supplied pool art. A thin admin service (`collectables_admin_service.py`) holds list/schedule/edit/unschedule logic with all guardrails; an admin router (`collectables_admin.py`) exposes it under `/admin/collectables`; a single React page (`CollectablesAdmin.tsx`) drives it.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend); React + TanStack Query + react-i18next + vitest/vitest-axe (frontend).

## Global Constraints

- **Migration:** hand-written, chained, off head `c4d5e6f7a8b9`. Run `alembic heads` first to confirm the head is still `c4d5e6f7a8b9` before writing the revision.
- **Async backend tests:** every test module starts with `pytestmark = pytest.mark.asyncio(loop_scope="session")`; use the `client` / `admin_client` / `db_session` fixtures from `backend/tests/conftest.py` — never a raw `AsyncClient`.
- **Valid `unlock_type` values (exact):** `streak_days`, `window_xp`, `window_lessons`, `window_arcade` (the B1 `_EVALUATORS` keys). Source of truth: `app.services.collectables_service._EVALUATORS`.
- **Valid `rarity` values (exact):** `legendary`, `epic`, `rare`, `common`.
- **No hard-delete anywhere.** Earned items must never be destroyed — the `CosmeticItem` / `UserCosmetic` cascade is never triggered by B2.
- **Live drop is rule-frozen:** once a drop's window is open (`live`), only `available_until` may change.
- **Shop filter invariant:** the buyable shop shows only `unlock_type IS NULL AND drop_eligible IS false`. Unscheduled pool art must never appear in the free/coin shop.
- **WCAG 2.2 AA:** new UI ships with a `vitest-axe` check; rarity is conveyed by text label, not colour alone. (Admin is web-only — no native/iOS constraints apply, but do not regress the shared components.)
- **Never read or modify any `.env`.**
- **Commits** end with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## File Structure

**Backend**
- `backend/app/models/cosmetics.py` — add `drop_eligible` column (Task 1).
- `backend/alembic/versions/<rev>_drop_eligible.py` — additive migration off `c4d5e6f7a8b9` (Task 1).
- `backend/app/routers/cosmetics.py` — tighten `_shop_state` filter (Task 1).
- `backend/app/seed/cosmetics.py` — mark `founders_crown` `drop_eligible=true`; upsert the new field (Task 1).
- `backend/app/services/collectables_admin_service.py` — list/schedule/edit/unschedule logic + validation + `AdminError` (Task 2).
- `backend/app/routers/collectables_admin.py` — Pydantic schemas + endpoints; register in `main.py` (Task 3).
- `backend/tests/test_collectables_admin.py` — service + router tests (Tasks 2 & 3).

**Frontend**
- `frontend/src/api/adminCollectables.ts` — types + TanStack Query hooks (Task 4).
- `frontend/src/components/admin/CollectablesAdmin.tsx` — the page (Task 4).
- `frontend/src/components/admin/AdminSidebar.tsx` — nav item (Task 4).
- `frontend/src/App.tsx` — lazy route `/admin/collectables` (Task 4).
- `frontend/src/locales/en/admin.json` — copy keys (Task 4).
- `frontend/src/components/admin/__tests__/CollectablesAdmin.test.tsx` — vitest + axe (Task 4).

---

### Task 1: Data model — `drop_eligible` column, migration, shop-filter tighten, seed

**Files:**
- Modify: `backend/app/models/cosmetics.py:25` (add column after `unlock_threshold`)
- Create: `backend/alembic/versions/d5e6f7a8b9c0_drop_eligible.py`
- Modify: `backend/app/routers/cosmetics.py:79-83` (`_shop_state` query)
- Modify: `backend/app/seed/cosmetics.py:43-46` (founders_crown spec) and `:66-70` (upsert update path)
- Test: `backend/tests/test_collectables_admin.py` (new file — shop-filter regression only in this task)

**Interfaces:**
- Consumes: existing `CosmeticItem` model; existing `_shop_state` in `cosmetics.py`.
- Produces: `CosmeticItem.drop_eligible: bool` (NOT NULL, default false). Shop excludes rows where `drop_eligible` is true. Migration revision id `d5e6f7a8b9c0`, down_revision `c4d5e6f7a8b9`.

- [ ] **Step 1: Confirm the migration head**

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && alembic heads`
Expected: prints `c4d5e6f7a8b9 (head)`. If it prints anything else, STOP and set the new migration's `down_revision` to whatever the actual single head is.

- [ ] **Step 2: Write the failing shop-filter regression test**

Create `backend/tests/test_collectables_admin.py`:

```python
# backend/tests/test_collectables_admin.py
import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem
from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unscheduled_pool_item_hidden_from_shop(client, db_session):
    # A drop-eligible pool item with no unlock_type must NOT appear in the buyable shop.
    db_session.add(CosmeticItem(
        slug="_pool_hat", name="Pool Hat", emoji="🎩", type="accessory",
        coin_cost=0, is_premium=False, drop_eligible=True, unlock_type=None,
    ))
    await db_session.commit()
    await _register_and_login(client, email="shopper@example.com", username="shopper")
    r = await client.get("/cosmetics")
    assert r.status_code == 200
    slugs = {i["slug"] for i in r.json()["items"]}
    assert "_pool_hat" not in slugs
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py::test_unscheduled_pool_item_hidden_from_shop -v`
Expected: FAIL — either `TypeError: 'drop_eligible' is an invalid keyword argument` (column missing) or the assertion fails (filter not applied yet).

- [ ] **Step 4: Add the model column**

In `backend/app/models/cosmetics.py`, add after line 25 (`unlock_threshold`):

```python
    drop_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
```

(`Boolean` is already imported on line 4.)

- [ ] **Step 5: Write the migration**

Create `backend/alembic/versions/d5e6f7a8b9c0_drop_eligible.py`:

```python
"""collectables: drop_eligible marker for admin-schedulable pool items

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-24 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cosmetic_items",
        sa.Column("drop_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("cosmetic_items", "drop_eligible")
```

- [ ] **Step 6: Tighten the shop filter**

In `backend/app/routers/cosmetics.py`, change the `_shop_state` query (currently `.where(CosmeticItem.unlock_type.is_(None))`):

```python
    items = (
        await session.scalars(
            select(CosmeticItem)
            .where(
                CosmeticItem.unlock_type.is_(None),
                CosmeticItem.drop_eligible.is_(False),
            )
            .order_by(CosmeticItem.coin_cost)
        )
    ).all()
```

- [ ] **Step 7: Mark the founders_crown seed drop-eligible**

In `backend/app/seed/cosmetics.py`, in the `founders_crown` CATALOG entry (around line 43), add `"drop_eligible": True,` to the dict. Then in the upsert update branch (around line 66-70, the `else:` path that copies fields onto an existing item), add:

```python
            item.drop_eligible = spec.get("drop_eligible", False)
```

- [ ] **Step 8: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py::test_unscheduled_pool_item_hidden_from_shop -v`
Expected: PASS.

- [ ] **Step 9: Run the existing cosmetics + seed tests for regressions**

Run: `cd backend && python -m pytest tests/test_cosmetics.py tests/test_collectables.py -v`
Expected: PASS (the seed test that counts catalog items still passes — `drop_eligible` is additive; founders_crown stays excluded from the buyable shop because its `unlock_type` is set).

- [ ] **Step 10: Lint + commit**

Run: `cd backend && ruff check app/ tests/ --fix && ruff check app/ tests/`
Expected: no errors.

```bash
git add backend/app/models/cosmetics.py backend/alembic/versions/d5e6f7a8b9c0_drop_eligible.py backend/app/routers/cosmetics.py backend/app/seed/cosmetics.py backend/tests/test_collectables_admin.py
git commit -m "feat(collectables): drop_eligible marker + shop-filter tighten (B2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Admin service — list / schedule / edit / unschedule with guardrails

**Files:**
- Create: `backend/app/services/collectables_admin_service.py`
- Test: `backend/tests/test_collectables_admin.py` (append service tests)

**Interfaces:**
- Consumes: `CosmeticItem`, `UserCosmetic` models; `app.services.collectables_service._EVALUATORS` (for valid unlock types); `CosmeticItem.drop_eligible` (Task 1).
- Produces:
  - `VALID_UNLOCK_TYPES: frozenset[str]`, `VALID_RARITIES: frozenset[str]`
  - `class AdminError(Exception)` with `.code: str`
  - `@dataclass class DropView: item: CosmeticItem; status: str; owned_count: int`
  - `def drop_status(item, now) -> str` → `"scheduled" | "live" | "ended"`
  - `async def list_pool(session) -> list[CosmeticItem]`
  - `async def list_drops(session, now) -> list[DropView]`
  - `async def schedule_drop(session, *, item_id, rarity, unlock_type, unlock_threshold, available_from, available_until) -> CosmeticItem`
  - `async def edit_drop(session, *, item_id, now, rarity=None, unlock_type=None, unlock_threshold=None, available_from=None, available_until=None) -> CosmeticItem`
  - `async def unschedule_drop(session, *, item_id, now) -> CosmeticItem`
  - Error codes raised: `not_found`, `not_drop_eligible`, `already_scheduled`, `not_a_drop`, `bad_unlock_type`, `bad_rarity`, `bad_threshold`, `bad_window`, `live_locked`, `ended_locked`, `owned_cannot_unschedule`.

- [ ] **Step 1: Write the failing service tests**

Append to `backend/tests/test_collectables_admin.py`:

```python
import uuid
from datetime import UTC, datetime, timedelta

from app.models.cosmetics import UserCosmetic
from app.services import collectables_admin_service as svc


def _pool_item(slug="_pool_a"):
    return CosmeticItem(slug=slug, name="A", emoji="🎩", type="accessory",
                        coin_cost=0, is_premium=False, drop_eligible=True)


async def test_schedule_then_listed_as_scheduled(db_session):
    item = _pool_item("_sched_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    pool = await svc.list_pool(db_session)
    assert item.id not in {p.id for p in pool}  # left the pool
    drops = await svc.list_drops(db_session, now)
    row = next(d for d in drops if d.item.id == item.id)
    assert row.status == "scheduled"
    assert row.owned_count == 0


async def test_schedule_rejects_invalid(db_session):
    item = _pool_item("_sched_bad")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    for kwargs, code in [
        (dict(unlock_type="nope"), "bad_unlock_type"),
        (dict(rarity="ultra"), "bad_rarity"),
        (dict(unlock_threshold=0), "bad_threshold"),
        (dict(available_until=now), "bad_window"),  # until <= from
    ]:
        base = dict(item_id=item.id, rarity="rare", unlock_type="streak_days",
                    unlock_threshold=5, available_from=now + timedelta(days=1),
                    available_until=now + timedelta(days=8))
        base.update(kwargs)
        with pytest.raises(svc.AdminError) as ei:
            await svc.schedule_drop(db_session, **base)
        assert ei.value.code == code


async def test_live_drop_only_enddate_editable(db_session):
    item = _pool_item("_live_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    # already live: from in the past, until in the future
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
    )
    # changing the rule on a live drop is rejected
    with pytest.raises(svc.AdminError) as ei:
        await svc.edit_drop(db_session, item_id=item.id, now=now, unlock_threshold=99)
    assert ei.value.code == "live_locked"
    # ending early IS allowed
    new_end = now + timedelta(hours=1)
    await svc.edit_drop(db_session, item_id=item.id, now=now, available_until=new_end)
    refreshed = await db_session.get(CosmeticItem, item.id)
    assert refreshed.available_until == new_end


async def test_unschedule_blocked_when_owned(db_session):
    item = _pool_item("_owned_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    # a child owns it
    u = User(email="o@e.com", username="owno", hashed_password="x",
             dob=datetime(2012, 1, 1), country_code="GB")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserCosmetic(user_id=u.id, item_id=item.id))
    await db_session.flush()
    with pytest.raises(svc.AdminError) as ei:
        await svc.unschedule_drop(db_session, item_id=item.id, now=now)
    assert ei.value.code == "owned_cannot_unschedule"


async def test_unschedule_clears_fields_when_clean(db_session):
    item = _pool_item("_clean_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    await svc.unschedule_drop(db_session, item_id=item.id, now=now)
    refreshed = await db_session.get(CosmeticItem, item.id)
    assert refreshed.unlock_type is None
    assert refreshed.rarity is None
    assert refreshed.available_from is None
    assert refreshed.drop_eligible is True  # still a pool item
```

(The `User(...)` constructor fields mirror the model — if `hashed_password`/`dob` differ from the real columns, adjust to the actual `app.models.user.User` required fields; do not invent columns.)

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py -v -k "schedule or live or unschedule"`
Expected: FAIL — `ModuleNotFoundError: app.services.collectables_admin_service`.

- [ ] **Step 3: Write the service**

Create `backend/app/services/collectables_admin_service.py`:

```python
"""Admin authoring for limited-edition collectable drops (B2).

A "drop" is a CosmeticItem with unlock_type set; B2 lets an admin schedule a
drop over a dev-supplied "pool" item (drop_eligible=True, unlock_type=None).
All guardrails live here so the router stays thin. Never deletes anything —
earned items are immutable.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.services.collectables_service import _EVALUATORS

VALID_UNLOCK_TYPES: frozenset[str] = frozenset(_EVALUATORS.keys())
VALID_RARITIES: frozenset[str] = frozenset({"legendary", "epic", "rare", "common"})


class AdminError(Exception):
    """Carries a stable error code the router maps to an HTTP status."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class DropView:
    item: CosmeticItem
    status: str
    owned_count: int


def drop_status(item: CosmeticItem, now: datetime) -> str:
    if item.available_from is not None and now < item.available_from:
        return "scheduled"
    if item.available_until is not None and now > item.available_until:
        return "ended"
    return "live"


def _validate(rarity, unlock_type, unlock_threshold, available_from, available_until) -> None:
    if unlock_type not in VALID_UNLOCK_TYPES:
        raise AdminError("bad_unlock_type")
    if rarity not in VALID_RARITIES:
        raise AdminError("bad_rarity")
    if not isinstance(unlock_threshold, int) or unlock_threshold <= 0:
        raise AdminError("bad_threshold")
    if available_from is None or available_until is None or available_until <= available_from:
        raise AdminError("bad_window")


async def _owned_count(session: AsyncSession, item_id: uuid.UUID) -> int:
    return int(await session.scalar(
        select(func.count()).select_from(UserCosmetic).where(UserCosmetic.item_id == item_id)
    ) or 0)


async def _get_item(session: AsyncSession, item_id: uuid.UUID) -> CosmeticItem:
    item = await session.get(CosmeticItem, item_id)
    if item is None:
        raise AdminError("not_found")
    return item


async def list_pool(session: AsyncSession) -> list[CosmeticItem]:
    return list((await session.scalars(
        select(CosmeticItem)
        .where(CosmeticItem.drop_eligible.is_(True), CosmeticItem.unlock_type.is_(None))
        .order_by(CosmeticItem.name)
    )).all())


async def list_drops(session: AsyncSession, now: datetime) -> list[DropView]:
    drops = list((await session.scalars(
        select(CosmeticItem)
        .where(CosmeticItem.drop_eligible.is_(True), CosmeticItem.unlock_type.is_not(None))
        .order_by(CosmeticItem.available_from)
    )).all())
    out: list[DropView] = []
    for d in drops:
        out.append(DropView(item=d, status=drop_status(d, now), owned_count=await _owned_count(session, d.id)))
    return out


async def schedule_drop(
    session: AsyncSession, *, item_id: uuid.UUID, rarity: str, unlock_type: str,
    unlock_threshold: int, available_from: datetime, available_until: datetime,
) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if not item.drop_eligible:
        raise AdminError("not_drop_eligible")
    if item.unlock_type is not None:
        raise AdminError("already_scheduled")
    _validate(rarity, unlock_type, unlock_threshold, available_from, available_until)
    item.rarity = rarity
    item.unlock_type = unlock_type
    item.unlock_threshold = unlock_threshold
    item.available_from = available_from
    item.available_until = available_until
    await session.flush()
    return item


async def edit_drop(
    session: AsyncSession, *, item_id: uuid.UUID, now: datetime,
    rarity: str | None = None, unlock_type: str | None = None,
    unlock_threshold: int | None = None, available_from: datetime | None = None,
    available_until: datetime | None = None,
) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if item.unlock_type is None:
        raise AdminError("not_a_drop")
    status = drop_status(item, now)
    if status == "ended":
        raise AdminError("ended_locked")
    if status == "live":
        if any(v is not None for v in (rarity, unlock_type, unlock_threshold, available_from)):
            raise AdminError("live_locked")
        if available_until is None or available_until <= (item.available_from or now):
            raise AdminError("bad_window")
        item.available_until = available_until
    else:  # scheduled — full replace, all fields required
        _validate(rarity, unlock_type, unlock_threshold, available_from, available_until)
        item.rarity = rarity
        item.unlock_type = unlock_type
        item.unlock_threshold = unlock_threshold
        item.available_from = available_from
        item.available_until = available_until
    await session.flush()
    return item


async def unschedule_drop(session: AsyncSession, *, item_id: uuid.UUID, now: datetime) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if item.unlock_type is None:
        raise AdminError("not_a_drop")
    if drop_status(item, now) != "scheduled":
        raise AdminError("owned_cannot_unschedule")  # only not-yet-started drops revert
    if await _owned_count(session, item_id) > 0:
        raise AdminError("owned_cannot_unschedule")
    item.unlock_type = None
    item.unlock_threshold = None
    item.rarity = None
    item.available_from = None
    item.available_until = None
    await session.flush()
    return item
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py -v`
Expected: PASS (all service tests + the Task 1 shop-filter test).

- [ ] **Step 5: Lint + commit**

Run: `cd backend && ruff check app/ tests/ --fix && ruff check app/ tests/`
Expected: no errors.

```bash
git add backend/app/services/collectables_admin_service.py backend/tests/test_collectables_admin.py
git commit -m "feat(collectables): admin scheduler service (list/schedule/edit/unschedule) (B2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Admin router — `/admin/collectables` endpoints

**Files:**
- Create: `backend/app/routers/collectables_admin.py`
- Modify: `backend/app/main.py` (import + `include_router`)
- Test: `backend/tests/test_collectables_admin.py` (append HTTP-level tests)

**Interfaces:**
- Consumes: `collectables_admin_service` functions + `AdminError` (Task 2); `get_current_admin` from `app.routers.admin_auth`; `get_session` from `app.core.database`.
- Produces: HTTP API:
  - `GET /admin/collectables/pool` → `list[PoolItemOut]`
  - `GET /admin/collectables` → `list[DropOut]`
  - `POST /admin/collectables` (body `ScheduleIn`) → `DropOut`
  - `PATCH /admin/collectables/{item_id}` (body `EditIn`) → `DropOut`
  - `POST /admin/collectables/{item_id}/unschedule` → `PoolItemOut`
  - Error mapping: `not_found`→404; `not_drop_eligible`/`already_scheduled`/`not_a_drop`/`live_locked`/`ended_locked`/`owned_cannot_unschedule`→409; `bad_*`→400.

- [ ] **Step 1: Write the failing router tests**

Append to `backend/tests/test_collectables_admin.py`:

```python
async def _seed_pool(db_session, slug="_api_a"):
    item = CosmeticItem(slug=slug, name="API A", emoji="🎩", type="accessory",
                        coin_cost=0, is_premium=False, drop_eligible=True)
    db_session.add(item)
    await db_session.commit()
    return item


async def test_requires_admin(client, db_session):
    await _register_and_login(client, email="plain@example.com", username="plain")
    r = await client.get("/admin/collectables")
    assert r.status_code == 401


async def test_schedule_via_api_and_leaves_pool(admin_client, db_session):
    item = await _seed_pool(db_session, "_api_sched")
    now = datetime.now(UTC)
    body = {
        "item_id": str(item.id), "rarity": "rare", "unlock_type": "streak_days",
        "unlock_threshold": 5,
        "available_from": (now + timedelta(days=1)).isoformat(),
        "available_until": (now + timedelta(days=8)).isoformat(),
    }
    r = await admin_client.post("/admin/collectables", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "scheduled"
    pool = await admin_client.get("/admin/collectables/pool")
    assert str(item.id) not in {p["item_id"] for p in pool.json()}


async def test_schedule_bad_unlock_type_400(admin_client, db_session):
    item = await _seed_pool(db_session, "_api_bad")
    now = datetime.now(UTC)
    body = {
        "item_id": str(item.id), "rarity": "rare", "unlock_type": "nope",
        "unlock_threshold": 5,
        "available_from": (now + timedelta(days=1)).isoformat(),
        "available_until": (now + timedelta(days=8)).isoformat(),
    }
    r = await admin_client.post("/admin/collectables", json=body)
    assert r.status_code == 400
    assert r.json()["detail"] == "bad_unlock_type"


async def test_scheduled_drop_grants_via_b1_engine(admin_client, db_session):
    # Proves B2 output (a scheduled, live drop) feeds the unchanged B1 grant engine.
    from app.models.user import User, UserProgress
    from app.services import collectables_service

    item = await _seed_pool(db_session, "_api_grant")
    now = datetime.now(UTC)
    # schedule it already-live with a streak threshold of 3
    body = {
        "item_id": str(item.id), "rarity": "rare", "unlock_type": "streak_days",
        "unlock_threshold": 3,
        "available_from": (now - timedelta(days=1)).isoformat(),
        "available_until": (now + timedelta(days=7)).isoformat(),
    }
    assert (await admin_client.post("/admin/collectables", json=body)).status_code == 200

    u = await db_session.scalar(select(User).where(User.email == "admin@example.com"))
    p = await db_session.get(UserProgress, u.id) or UserProgress(user_id=u.id)
    p.streak_count = 5
    db_session.add(p)
    await db_session.flush()
    granted = await collectables_service.grant_eligible(db_session, p)
    assert "_api_grant" in granted
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py -v -k "admin or api or grant or requires"`
Expected: FAIL — 404s (router not mounted yet).

- [ ] **Step 3: Write the router**

Create `backend/app/routers/collectables_admin.py`:

```python
"""Admin endpoints to schedule limited-edition collectable drops (B2)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.routers.admin_auth import get_current_admin
from app.services import collectables_admin_service as svc

router = APIRouter(
    prefix="/admin/collectables",
    tags=["admin-collectables"],
    dependencies=[Depends(get_current_admin)],
)

_CONFLICT_CODES = {
    "not_drop_eligible", "already_scheduled", "not_a_drop",
    "live_locked", "ended_locked", "owned_cannot_unschedule",
}


def _raise(e: svc.AdminError) -> NoReturn:
    if e.code == "not_found":
        raise HTTPException(status.HTTP_404_NOT_FOUND, e.code)
    if e.code in _CONFLICT_CODES:
        raise HTTPException(status.HTTP_409_CONFLICT, e.code)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, e.code)


class PoolItemOut(BaseModel):
    item_id: uuid.UUID
    slug: str
    name: str
    emoji: str
    type: str


class DropOut(PoolItemOut):
    rarity: str | None
    unlock_type: str | None
    unlock_threshold: int | None
    available_from: datetime | None
    available_until: datetime | None
    status: str
    owned_count: int


class ScheduleIn(BaseModel):
    item_id: uuid.UUID
    rarity: str
    unlock_type: str
    unlock_threshold: int
    available_from: datetime
    available_until: datetime


class EditIn(BaseModel):
    rarity: str | None = None
    unlock_type: str | None = None
    unlock_threshold: int | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None


def _pool_out(item) -> PoolItemOut:
    return PoolItemOut(item_id=item.id, slug=item.slug, name=item.name, emoji=item.emoji, type=item.type)


def _drop_out(view: svc.DropView) -> DropOut:
    i = view.item
    return DropOut(
        item_id=i.id, slug=i.slug, name=i.name, emoji=i.emoji, type=i.type,
        rarity=i.rarity, unlock_type=i.unlock_type, unlock_threshold=i.unlock_threshold,
        available_from=i.available_from, available_until=i.available_until,
        status=view.status, owned_count=view.owned_count,
    )


@router.get("/pool", response_model=list[PoolItemOut])
async def get_pool(session: AsyncSession = Depends(get_session)) -> list[PoolItemOut]:
    return [_pool_out(i) for i in await svc.list_pool(session)]


@router.get("", response_model=list[DropOut])
async def get_drops(session: AsyncSession = Depends(get_session)) -> list[DropOut]:
    return [_drop_out(v) for v in await svc.list_drops(session, datetime.now(UTC))]


@router.post("", response_model=DropOut)
async def schedule(payload: ScheduleIn, session: AsyncSession = Depends(get_session)) -> DropOut:
    try:
        item = await svc.schedule_drop(
            session, item_id=payload.item_id, rarity=payload.rarity,
            unlock_type=payload.unlock_type, unlock_threshold=payload.unlock_threshold,
            available_from=payload.available_from, available_until=payload.available_until,
        )
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    return _drop_out(svc.DropView(item=item, status=svc.drop_status(item, datetime.now(UTC)),
                                  owned_count=0))


@router.patch("/{item_id}", response_model=DropOut)
async def edit(item_id: uuid.UUID, payload: EditIn, session: AsyncSession = Depends(get_session)) -> DropOut:
    now = datetime.now(UTC)
    try:
        item = await svc.edit_drop(
            session, item_id=item_id, now=now, rarity=payload.rarity,
            unlock_type=payload.unlock_type, unlock_threshold=payload.unlock_threshold,
            available_from=payload.available_from, available_until=payload.available_until,
        )
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    owned = await svc._owned_count(session, item_id)
    return _drop_out(svc.DropView(item=item, status=svc.drop_status(item, now), owned_count=owned))


@router.post("/{item_id}/unschedule", response_model=PoolItemOut)
async def unschedule(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> PoolItemOut:
    try:
        item = await svc.unschedule_drop(session, item_id=item_id, now=datetime.now(UTC))
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    return _pool_out(item)
```

- [ ] **Step 4: Register the router in `main.py`**

In `backend/app/main.py`, add near the other admin router imports (around line 22):

```python
from app.routers import collectables_admin as collectables_admin_router
```

and near the other `include_router` calls (around line 218):

```python
    application.include_router(collectables_admin_router.router)
```

- [ ] **Step 5: Run the router tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_collectables_admin.py -v`
Expected: PASS (all tasks' tests).

- [ ] **Step 6: Lint + full backend gate + commit**

Run: `cd backend && ruff check app/ tests/ --fix && ruff check app/ tests/ && python -m pytest tests/test_collectables_admin.py tests/test_collectables.py tests/test_cosmetics.py -q`
Expected: no lint errors; all pass.

```bash
git add backend/app/routers/collectables_admin.py backend/app/main.py backend/tests/test_collectables_admin.py
git commit -m "feat(collectables): admin scheduler router /admin/collectables (B2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Frontend — client lib, admin page, nav, route, copy

**Files:**
- Create: `frontend/src/api/adminCollectables.ts`
- Create: `frontend/src/components/admin/CollectablesAdmin.tsx`
- Modify: `frontend/src/components/admin/AdminSidebar.tsx` (NAV_ITEMS)
- Modify: `frontend/src/App.tsx` (lazy import + route)
- Modify: `frontend/src/locales/en/admin.json` (copy)
- Test: `frontend/src/components/admin/__tests__/CollectablesAdmin.test.tsx`

**Interfaces:**
- Consumes: backend API from Task 3 (`/admin/collectables*`); `apiFetch` from `@/api/client`; `ConfirmDialog` from `@/components/admin/ConfirmDialog`.
- Produces: page reachable at `/admin/collectables`; hooks `usePool`, `useDrops`, `useScheduleDrop`, `useEditDrop`, `useUnscheduleDrop`; types `PoolItem`, `Drop`.

- [ ] **Step 1: Write the client lib**

Create `frontend/src/api/adminCollectables.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export const UNLOCK_TYPES = ['streak_days', 'window_xp', 'window_lessons', 'window_arcade'] as const;
export const RARITIES = ['common', 'rare', 'epic', 'legendary'] as const;
export type UnlockType = (typeof UNLOCK_TYPES)[number];
export type Rarity = (typeof RARITIES)[number];
export type DropStatus = 'scheduled' | 'live' | 'ended';

export interface PoolItem {
  item_id: string;
  slug: string;
  name: string;
  emoji: string;
  type: string;
}

export interface Drop extends PoolItem {
  rarity: Rarity | null;
  unlock_type: UnlockType | null;
  unlock_threshold: number | null;
  available_from: string | null;
  available_until: string | null;
  status: DropStatus;
  owned_count: number;
}

export interface ScheduleBody {
  item_id: string;
  rarity: Rarity;
  unlock_type: UnlockType;
  unlock_threshold: number;
  available_from: string;
  available_until: string;
}

const POOL_KEY = ['admin', 'collectables', 'pool'];
const DROPS_KEY = ['admin', 'collectables', 'drops'];

export function usePool() {
  return useQuery({ queryKey: POOL_KEY, queryFn: () => apiFetch<PoolItem[]>('/admin/collectables/pool') });
}

export function useDrops() {
  return useQuery({ queryKey: DROPS_KEY, queryFn: () => apiFetch<Drop[]>('/admin/collectables') });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: POOL_KEY });
    qc.invalidateQueries({ queryKey: DROPS_KEY });
  };
}

export function useScheduleDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ScheduleBody) =>
      apiFetch<Drop>('/admin/collectables', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useEditDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ itemId, body }: { itemId: string; body: Partial<ScheduleBody> }) =>
      apiFetch<Drop>(`/admin/collectables/${itemId}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useUnscheduleDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (itemId: string) =>
      apiFetch<PoolItem>(`/admin/collectables/${itemId}/unschedule`, { method: 'POST' }),
    onSuccess: invalidate,
  });
}
```

- [ ] **Step 2: Add copy keys**

In `frontend/src/locales/en/admin.json`, add a `collectables` block (place alphabetically among the existing top-level keys):

```json
  "collectables": {
    "title": "Collectables",
    "scheduledHeading": "Scheduled drops",
    "scheduleHeading": "Schedule a drop",
    "poolItemLabel": "Drop-ready item",
    "poolEmpty": "No drop-ready art yet — ask a developer to ship drop-eligible cosmetics.",
    "rarityLabel": "Rarity",
    "unlockTypeLabel": "Unlock rule",
    "thresholdLabel": "Threshold",
    "fromLabel": "Available from",
    "untilLabel": "Available until",
    "save": "Save drop",
    "endEarly": "End early",
    "editEndDate": "Edit end date",
    "unschedule": "Unschedule",
    "colItem": "Item",
    "colRarity": "Rarity",
    "colUnlock": "Unlock",
    "colWindow": "Window",
    "colStatus": "Status",
    "colOwned": "Owned",
    "statusScheduled": "Scheduled",
    "statusLive": "Live",
    "statusEnded": "Ended",
    "ownedNote": "{{count}} kids already earned this — they keep it.",
    "confirmEndEarly": "End this drop now? Kids who already earned it keep it; no new kids can earn it.",
    "confirmUnschedule": "Remove this scheduled drop? It returns to the art pool, unscheduled.",
    "unlock": {
      "streak_days": "Streak days",
      "window_xp": "XP earned in window",
      "window_lessons": "Lessons in window",
      "window_arcade": "Arcade points in window"
    }
  },
```

Also add the sidebar nav label — find the `sidebar.items` block in the same file and add:

```json
      "collectables": "Collectables",
```

- [ ] **Step 3: Write the page component**

Create `frontend/src/components/admin/CollectablesAdmin.tsx`:

```tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  usePool, useDrops, useScheduleDrop, useEditDrop, useUnscheduleDrop,
  UNLOCK_TYPES, RARITIES, type Drop, type Rarity, type UnlockType,
} from '@/api/adminCollectables';
import ConfirmDialog from '@/components/admin/ConfirmDialog';

function toLocalInput(iso: string | null): string {
  return iso ? iso.slice(0, 16) : '';
}
function fromLocalInput(local: string): string {
  return new Date(local).toISOString();
}

export default function CollectablesAdmin() {
  const { t } = useTranslation('admin');
  const { data: pool = [] } = usePool();
  const { data: drops = [] } = useDrops();
  const schedule = useScheduleDrop();
  const edit = useEditDrop();
  const unschedule = useUnscheduleDrop();

  const [itemId, setItemId] = useState('');
  const [rarity, setRarity] = useState<Rarity>('rare');
  const [unlockType, setUnlockType] = useState<UnlockType>('streak_days');
  const [threshold, setThreshold] = useState(5);
  const [from, setFrom] = useState('');
  const [until, setUntil] = useState('');

  const [confirm, setConfirm] = useState<{ kind: 'end' | 'unschedule'; drop: Drop } | null>(null);

  async function onSchedule(e: React.FormEvent) {
    e.preventDefault();
    if (!itemId || !from || !until) return;
    await schedule.mutateAsync({
      item_id: itemId, rarity, unlock_type: unlockType, unlock_threshold: threshold,
      available_from: fromLocalInput(from), available_until: fromLocalInput(until),
    });
    setItemId(''); setFrom(''); setUntil('');
  }

  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-semibold text-ink">{t('collectables.title')}</h2>

      {/* Scheduled drops list */}
      <h3 className="mb-2 text-sm font-bold text-muted-foreground">{t('collectables.scheduledHeading')}</h3>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50 text-left">
              <th className="px-3 py-2">{t('collectables.colItem')}</th>
              <th className="px-3 py-2">{t('collectables.colRarity')}</th>
              <th className="px-3 py-2">{t('collectables.colUnlock')}</th>
              <th className="px-3 py-2">{t('collectables.colStatus')}</th>
              <th className="px-3 py-2">{t('collectables.colOwned')}</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {drops.map((d) => (
              <tr key={d.item_id} className="border-b last:border-b-0">
                <td className="px-3 py-2"><span aria-hidden="true">{d.emoji}</span> {d.name}</td>
                <td className="px-3 py-2">{d.rarity}</td>
                <td className="px-3 py-2">
                  {d.unlock_type ? t(`collectables.unlock.${d.unlock_type}`) : ''} ≥ {d.unlock_threshold}
                </td>
                <td className="px-3 py-2">{t(`collectables.status${d.status[0].toUpperCase()}${d.status.slice(1)}`)}</td>
                <td className="px-3 py-2">{d.owned_count}</td>
                <td className="px-3 py-2 text-right">
                  {d.status === 'scheduled' && (
                    <button type="button" className="text-sm font-bold text-brand-700"
                      onClick={() => setConfirm({ kind: 'unschedule', drop: d })}>
                      {t('collectables.unschedule')}
                    </button>
                  )}
                  {d.status === 'live' && (
                    <button type="button" className="text-sm font-bold text-red-700"
                      onClick={() => setConfirm({ kind: 'end', drop: d })}>
                      {t('collectables.endEarly')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Schedule a drop */}
      <h3 className="mb-2 mt-8 text-sm font-bold text-muted-foreground">{t('collectables.scheduleHeading')}</h3>
      {pool.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('collectables.poolEmpty')}</p>
      ) : (
        <form onSubmit={onSchedule} className="flex max-w-lg flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.poolItemLabel')}
            <select className="rounded border px-2 py-2 text-base" value={itemId}
              onChange={(e) => setItemId(e.target.value)} required>
              <option value="" disabled>—</option>
              {pool.map((p) => <option key={p.item_id} value={p.item_id}>{p.emoji} {p.name}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.rarityLabel')}
            <select className="rounded border px-2 py-2 text-base" value={rarity}
              onChange={(e) => setRarity(e.target.value as Rarity)}>
              {RARITIES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.unlockTypeLabel')}
            <select className="rounded border px-2 py-2 text-base" value={unlockType}
              onChange={(e) => setUnlockType(e.target.value as UnlockType)}>
              {UNLOCK_TYPES.map((u) => <option key={u} value={u}>{t(`collectables.unlock.${u}`)}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.thresholdLabel')}
            <input type="number" min={1} className="rounded border px-2 py-2 text-base" value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))} required />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.fromLabel')}
            <input type="datetime-local" className="rounded border px-2 py-2 text-base" value={from}
              onChange={(e) => setFrom(e.target.value)} required />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.untilLabel')}
            <input type="datetime-local" className="rounded border px-2 py-2 text-base" value={until}
              onChange={(e) => setUntil(e.target.value)} required />
          </label>
          <button type="submit" disabled={schedule.isPending}
            className="min-h-[44px] rounded-xl bg-brand-600 px-4 font-bold text-white hover:bg-brand-700">
            {t('collectables.save')}
          </button>
        </form>
      )}

      {confirm && (
        <ConfirmDialog
          open
          title={confirm.kind === 'end' ? t('collectables.endEarly') : t('collectables.unschedule')}
          message={
            (confirm.kind === 'end' ? t('collectables.confirmEndEarly') : t('collectables.confirmUnschedule')) +
            (confirm.drop.owned_count > 0 ? ' ' + t('collectables.ownedNote', { count: confirm.drop.owned_count }) : '')
          }
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            if (confirm.kind === 'end') {
              await edit.mutateAsync({ itemId: confirm.drop.item_id, body: { available_until: new Date().toISOString() } });
            } else {
              await unschedule.mutateAsync(confirm.drop.item_id);
            }
            setConfirm(null);
          }}
        />
      )}
    </div>
  );
}
```

> **`ConfirmDialog` interface (verified):** default export, props `{ open: boolean; title: string; message?: string; onConfirm: () => void; onCancel: () => void }`. It renders `role="dialog"` with `aria-label={title}` and focuses Cancel on open. Use `message` (not `description`). Do not modify `ConfirmDialog` itself.

- [ ] **Step 4: Add the nav item**

In `frontend/src/components/admin/AdminSidebar.tsx`, add to `NAV_ITEMS` (after the `arcade-words` entry):

```tsx
  { to: '/admin/collectables', tKey: 'sidebar.items.collectables', icon: '💎', end: false },
```

- [ ] **Step 5: Add the lazy route**

In `frontend/src/App.tsx`, add the lazy import (near line 55, after `ArcadeWordBank`):

```tsx
const CollectablesAdmin = lazy(() => import('@/components/admin/CollectablesAdmin'));
```

and the route (after the `arcade-words` route, ~line 139):

```tsx
          <Route path="collectables" element={<CollectablesAdmin />} />
```

- [ ] **Step 6: Write the test**

Create `frontend/src/components/admin/__tests__/CollectablesAdmin.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import CollectablesAdmin from '../CollectablesAdmin';

const scheduleMut = vi.fn().mockResolvedValue({});
const editMut = vi.fn().mockResolvedValue({});
const unscheduleMut = vi.fn().mockResolvedValue({});

vi.mock('@/api/adminCollectables', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)();
  return {
    ...actual,
    usePool: () => ({ data: [{ item_id: 'p1', slug: 'crown', name: 'Crown', emoji: '👑', type: 'accessory' }] }),
    useDrops: () => ({ data: [
      { item_id: 'd1', slug: 'hat', name: 'Hat', emoji: '🎩', type: 'accessory', rarity: 'rare',
        unlock_type: 'streak_days', unlock_threshold: 7, available_from: '2026-07-01T00:00:00Z',
        available_until: '2026-07-31T00:00:00Z', status: 'live', owned_count: 3 },
    ] }),
    useScheduleDrop: () => ({ mutateAsync: scheduleMut, isPending: false }),
    useEditDrop: () => ({ mutateAsync: editMut, isPending: false }),
    useUnscheduleDrop: () => ({ mutateAsync: unscheduleMut, isPending: false }),
  };
});

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.count != null ? `${k}:${o.count}` : k) }),
}));

describe('CollectablesAdmin', () => {
  beforeEach(() => { scheduleMut.mockClear(); editMut.mockClear(); unscheduleMut.mockClear(); });

  it('lists a live drop with its owned count', () => {
    render(<CollectablesAdmin />);
    expect(screen.getByText('Hat')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('schedules a drop from the pool', async () => {
    render(<CollectablesAdmin />);
    fireEvent.change(screen.getByDisplayValue('—'), { target: { value: 'p1' } });
    const dts = document.querySelectorAll('input[type="datetime-local"]');
    fireEvent.change(dts[0], { target: { value: '2026-08-01T00:00' } });
    fireEvent.change(dts[1], { target: { value: '2026-08-08T00:00' } });
    fireEvent.click(screen.getByText('collectables.save'));
    await waitFor(() => expect(scheduleMut).toHaveBeenCalledTimes(1));
    expect(scheduleMut.mock.calls[0][0].item_id).toBe('p1');
  });

  it('has no axe violations', async () => {
    const { container } = render(<CollectablesAdmin />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 7: Run the frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/admin/__tests__/CollectablesAdmin.test.tsx`
Expected: tsc 0 errors; lint 0 errors; 3 tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/adminCollectables.ts frontend/src/components/admin/CollectablesAdmin.tsx frontend/src/components/admin/AdminSidebar.tsx frontend/src/App.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/CollectablesAdmin.test.tsx
git commit -m "feat(collectables): admin drop scheduler page (B2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Full verification + ship + docs

**Files:** none new — verification, deploy, docs.

- [ ] **Step 1: Full backend gate**

Run: `cd backend && ruff check app/ tests/ && python -m pytest tests/test_collectables_admin.py tests/test_collectables.py tests/test_cosmetics.py -q`
Expected: no lint errors; all pass. (If the local Postgres hangs ~90s+ on a DB-backed test, it is environmental — rely on CI.)

- [ ] **Step 2: Full frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/admin && npm run build`
Expected: tsc 0; lint 0; admin tests pass; build clean.

- [ ] **Step 3: Confirm the full suite is at the env-only baseline**

Run: `cd frontend && npx vitest run 2>&1 | grep -iE "Test Files|Tests |Unhandled"`
Expected: no `Unhandled` line; failure count no higher than the known env-only timeout baseline (the child-Lesson/Module/Simulator/Stock/Level timeout files).

- [ ] **Step 4: Ask about a prod snapshot, then push**

The `d5e6f7a8b9c0` migration is additive (a `NOT NULL DEFAULT false` boolean — backfills safely). Per the standing rule, ASK the human whether to snapshot the prod DB before pushing. After their answer:

```bash
git push origin main
```

- [ ] **Step 5: Watch CI green**

Run: `gh run list --branch main --limit 1` (or monitor). Wait for the CI run on the pushed HEAD to complete `success`. Railway runs `alembic upgrade head` on green CI; a migration failure would crash-loop the backend (it would stop serving), so confirm green before claiming live.

- [ ] **Step 6: Deploy the web frontend (two-step) + verify live**

```bash
cd frontend && vercel --prod --force
# then alias the printed deployment hash to the pinned domain:
vercel alias set <deployment-hash>-investikid.vercel.app app.investikid.ai
```

Then verify: `curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.investikid.ai/admin/collectables` → expect `401` (deployed + admin-gated, not `404`).

- [ ] **Step 7: cap sync ios (keep native current)**

Run: `cd frontend && npm run build && npx cap sync ios`
Expected: sync finished. (Admin is web-only; this only keeps the native shell's bundled web assets current.)

- [ ] **Step 8: Update docs**

Add a "Limited-Edition Collectables B2" entry to `docs/MASTER-BACKLOG.md` (live-in-prod section) noting: migration `d5e6f7a8b9c0` (additive `drop_eligible`), the `/admin/collectables` scheduler, the art-pool model, the lifecycle guardrails, and that B3 (Home featured-drop card) remains the last sub-project. Commit:

```bash
git add docs/MASTER-BACKLOG.md
git commit -m "docs: record Collectables B2 admin scheduler live in prod

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```

(Also refresh the `project_arcade` memory entry + the MEMORY.md index line — outside the repo, done by the controller.)

---

## Notes for the implementer

- **DRY:** the four valid `unlock_type` values come from `_EVALUATORS` (backend) and the `UNLOCK_TYPES` constant (frontend) — do not hardcode a fifth anywhere.
- **YAGNI:** no per-market scoping, no separate `collectable_drops` table, no LLM suggestions, no analytics — all explicitly out of scope (B3 and beyond).
- **Do not touch B1 read paths** (`collectables_service`, `GET /collectables`, the grant seam). The only B1-adjacent edit is the shop filter in `cosmetics.py` (Task 1), covered by a regression test.
