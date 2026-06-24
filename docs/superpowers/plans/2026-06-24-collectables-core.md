# Limited-Edition Collectables — Core (B1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kids earn time-limited, rarity-tagged collectable cosmetics by meeting a per-drop goal during its window; surfaced as a "Limited" shelf in Penny's Shop. (B1 of 3 — admin scheduler = B2, Home card = B3.)

**Architecture:** Add availability/rarity/unlock fields to `CosmeticItem` (migration). A `collectables_service` holds a registry of `unlock_type` evaluators and a `grant_eligible(progress)` that auto-grants any met, active, un-owned drop (idempotent). It's hooked as a defensive side-effect inside the canonical `award_xp` seam (instant grant on any learning action) plus a nightly reconcile cron. A `GET /collectables` endpoint feeds a "Limited" shelf; limited items are earned-only (excluded from the coin shop + buy-guarded).

**Tech Stack:** FastAPI + async SQLAlchemy + Alembic (Postgres); React + TS + React Query + react-i18next + Tailwind; pytest (`pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures); vitest + vitest-axe.

## Global Constraints

- **Migration:** hand-written, chained Alembic. New revision's `down_revision = "b3c4d5e6f7a8"` (current head). Check `alembic heads` first. **Ask the user before the prod migration whether to snapshot first.**
- **Discriminator (verbatim):** an item is a **limited drop** iff `unlock_type IS NOT NULL` (earned-only). A drop is **active** iff `unlock_type IS NOT NULL AND now ∈ [available_from, available_until]`.
- **Earned-only:** limited items are NEVER coin-buyable — excluded from the normal shop shelves AND the buy endpoint returns `403 not_buyable` for them.
- **Grant is idempotent** (a `UserCosmetic` already exists for (user,item) → skip) and **never breaks a learning flow** (grant_eligible catches its own errors, returns `[]`).
- **Unlock evaluators (B1):** `streak_days` (current `UserProgress.streak_count`), `window_xp` (Σ `Lesson.xp_reward` over `LessonCompletion.completed_at >= available_from`), `window_lessons` (count of those completions), `window_arcade` (Σ `ArcadeScore.points` where `created_at >= available_from`). The registry is the extension point; `event_completed` is NOT in B1.
- **Rarity values:** `common` / `rare` / `epic` / `legendary` (null for normal items).
- **CSRF:** the new `POST /internal/collectables/reconcile` cron MUST be added to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py` (else the GitHub-Actions cron gets 403).
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures. Test schema built from models via `create_all`.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. Backend deploys on green CI; web is a manual two-step Vercel deploy.
- GOTCHA: local test Postgres can hang after a killed pytest run (~90s+ = environmental → rely on CI). Frontend has ~68 pre-existing local base-URL vitest failures (pass in CI) — ignore; run only affected tests + tsc + lint + build.

---

### Task 1: Migration + CosmeticItem fields

**Files:**
- Create: `backend/alembic/versions/c4d5e6f7a8b9_collectables_fields.py`
- Modify: `backend/app/models/cosmetics.py`
- Test: `backend/tests/test_collectables_columns.py`

**Interfaces:**
- Produces: `CosmeticItem.available_from/available_until: datetime|None`, `.rarity: str|None`, `.unlock_type: str|None`, `.unlock_threshold: int|None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_collectables_columns.py
import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_cosmetic_item_has_collectable_fields(db_session):
    item = CosmeticItem(slug="_t_drop", name="T", emoji="👑", type="accessory", coin_cost=0, is_premium=False,
                        rarity="legendary", unlock_type="streak_days", unlock_threshold=7)
    db_session.add(item); await db_session.flush()
    got = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == "_t_drop"))
    assert got.rarity == "legendary"
    assert got.unlock_type == "streak_days"
    assert got.unlock_threshold == 7
    assert got.available_from is None and got.available_until is None  # nullable
```

- [ ] **Step 2: Run — expect FAIL** (`TypeError: 'rarity' is an invalid keyword argument`)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_collectables_columns.py -q`

- [ ] **Step 3: Add columns to the model**

In `backend/app/models/cosmetics.py`, inside `class CosmeticItem`, after `is_premium`, add (ensure `DateTime` is imported from sqlalchemy — it already is):

```python
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(12), nullable=True)
    unlock_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unlock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

(`datetime` is already imported at the top of the file; `Integer`/`String` too — verify and add only what's missing.)

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/c4d5e6f7a8b9_collectables_fields.py
"""collectables: availability window + rarity + unlock rule on cosmetic_items

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-24 14:00:00.000000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("cosmetic_items", sa.Column("available_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cosmetic_items", sa.Column("available_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cosmetic_items", sa.Column("rarity", sa.String(length=12), nullable=True))
    op.add_column("cosmetic_items", sa.Column("unlock_type", sa.String(length=20), nullable=True))
    op.add_column("cosmetic_items", sa.Column("unlock_threshold", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("cosmetic_items", "unlock_threshold")
    op.drop_column("cosmetic_items", "unlock_type")
    op.drop_column("cosmetic_items", "rarity")
    op.drop_column("cosmetic_items", "available_until")
    op.drop_column("cosmetic_items", "available_from")
```

- [ ] **Step 5: Verify + commit**

Run: `alembic heads` (expect single head `c4d5e6f7a8b9`); `python -m pytest tests/test_collectables_columns.py -q`; `python -m ruff check app/models/cosmetics.py alembic/versions/c4d5e6f7a8b9_collectables_fields.py`

```bash
git add backend/app/models/cosmetics.py backend/alembic/versions/c4d5e6f7a8b9_collectables_fields.py backend/tests/test_collectables_columns.py
git commit -m "feat(collectables): availability window + rarity + unlock rule on cosmetic_items"
```

---

### Task 2: Grant engine (`collectables_service`)

**Files:**
- Create: `backend/app/services/collectables_service.py`
- Test: `backend/tests/test_collectables_service.py`

**Interfaces:**
- Consumes: Task-1 `CosmeticItem` fields; `UserProgress` (`streak_count`, `user_id`), `Lesson`/`LessonCompletion`, `ArcadeScore`, `UserCosmetic`.
- Produces:
  - `async def is_drop_active(item, now) -> bool`
  - `async def progress_for(session, progress, item) -> int`
  - `async def grant_eligible(session, progress) -> list[str]` — grants met active un-owned drops; returns granted slugs; never raises.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_collectables_service.py
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from app.models.user import User, UserProgress
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.services.collectables_service import grant_eligible, progress_for
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _user(client, db_session, email, *, streak=0):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    p = await db_session.get(UserProgress, u.id) or UserProgress(user_id=u.id)
    p.streak_count = streak
    db_session.add(p); await db_session.commit()
    return u, p

def _drop(slug, utype, thr, *, open_days_ago=1, closes_in_days=7):
    now = datetime.now(UTC)
    return CosmeticItem(slug=slug, name=slug, emoji="👑", type="accessory", coin_cost=0, is_premium=False,
                        rarity="legendary", unlock_type=utype, unlock_threshold=thr,
                        available_from=now - timedelta(days=open_days_ago),
                        available_until=now + timedelta(days=closes_in_days))

async def test_streak_drop_granted_when_met_and_idempotent(client, db_session):
    u, p = await _user(client, db_session, "col_s@example.com", streak=7)
    drop = _drop("_d_streak", "streak_days", 7); db_session.add(drop); await db_session.commit()
    granted = await grant_eligible(db_session, p)
    assert "_d_streak" in granted
    owned = await db_session.scalar(select(UserCosmetic).where(UserCosmetic.user_id == u.id, UserCosmetic.item_id == drop.id))
    assert owned is not None and owned.equipped is False
    # idempotent
    assert await grant_eligible(db_session, p) == []

async def test_streak_drop_not_granted_when_below_threshold(client, db_session):
    _, p = await _user(client, db_session, "col_lo@example.com", streak=3)
    db_session.add(_drop("_d_streak2", "streak_days", 7)); await db_session.commit()
    assert "_d_streak2" not in await grant_eligible(db_session, p)

async def test_closed_window_never_granted(client, db_session):
    _, p = await _user(client, db_session, "col_closed@example.com", streak=99)
    db_session.add(_drop("_d_closed", "streak_days", 1, open_days_ago=30, closes_in_days=-1)); await db_session.commit()
    assert "_d_closed" not in await grant_eligible(db_session, p)
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError`)

Run: `python -m pytest tests/test_collectables_service.py -q`

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/collectables_service.py
"""Limited-edition collectables: evaluate per-drop goals and auto-grant earned drops.
A drop is a CosmeticItem with unlock_type set; active iff now is within its window."""
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.content import Lesson, LessonCompletion
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import UserProgress

log = logging.getLogger(__name__)


def is_drop_active(item: CosmeticItem, now: datetime) -> bool:
    if item.unlock_type is None:
        return False
    if item.available_from is not None and now < item.available_from:
        return False
    if item.available_until is not None and now > item.available_until:
        return False
    return True


async def _streak_days(session, progress, item) -> int:
    return progress.streak_count


async def _window_xp(session, progress, item) -> int:
    stmt = (select(func.coalesce(func.sum(Lesson.xp_reward), 0))
            .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
            .where(LessonCompletion.user_id == progress.user_id,
                   LessonCompletion.completed_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


async def _window_lessons(session, progress, item) -> int:
    stmt = (select(func.count()).select_from(LessonCompletion)
            .where(LessonCompletion.user_id == progress.user_id,
                   LessonCompletion.completed_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


async def _window_arcade(session, progress, item) -> int:
    stmt = (select(func.coalesce(func.sum(ArcadeScore.points), 0))
            .where(ArcadeScore.user_id == progress.user_id,
                   ArcadeScore.created_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


_EVALUATORS: dict[str, Callable[[AsyncSession, UserProgress, CosmeticItem], Awaitable[int]]] = {
    "streak_days": _streak_days,
    "window_xp": _window_xp,
    "window_lessons": _window_lessons,
    "window_arcade": _window_arcade,
}


async def progress_for(session: AsyncSession, progress: UserProgress, item: CosmeticItem) -> int:
    ev = _EVALUATORS.get(item.unlock_type or "")
    if ev is None:
        return 0
    return await ev(session, progress, item)


async def grant_eligible(session: AsyncSession, progress: UserProgress) -> list[str]:
    """Grant any active, un-owned drop whose goal the user meets. Idempotent.
    Defensive: never raises into the caller's (XP) flow."""
    try:
        now = datetime.now(UTC)
        drops = (await session.scalars(select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None)))).all()
        active = [d for d in drops if is_drop_active(d, now) and d.unlock_type in _EVALUATORS]
        if not active:
            return []
        owned_ids = set((await session.scalars(
            select(UserCosmetic.item_id).where(UserCosmetic.user_id == progress.user_id))).all())
        granted: list[str] = []
        for d in active:
            if d.id in owned_ids:
                continue
            if await progress_for(session, progress, d) >= (d.unlock_threshold or 0):
                session.add(UserCosmetic(user_id=progress.user_id, item_id=d.id, equipped=False,
                                         unlocked_at=now))
                granted.append(d.slug)
        if granted:
            await session.flush()
        return granted
    except Exception:  # never break the learning flow
        log.exception("grant_eligible failed")
        return []
```

- [ ] **Step 4: Run — expect PASS** + lint + commit

Run: `python -m pytest tests/test_collectables_service.py -q && python -m ruff check app/services/collectables_service.py tests/test_collectables_service.py`

```bash
git add backend/app/services/collectables_service.py backend/tests/test_collectables_service.py
git commit -m "feat(collectables): grant engine (unlock evaluators + idempotent grant_eligible)"
```

---

### Task 3: Hook into award_xp + reconcile cron

**Files:**
- Modify: `backend/app/services/xp_service.py` (add `granted_collectables` to `XpResult`)
- Modify: `backend/app/services/market_progress_service.py` (call `grant_eligible` in `award_xp`)
- Modify: `backend/app/routers/internal.py` (add `/collectables/reconcile`)
- Modify: `backend/app/core/csrf.py` (`_DEFAULT_EXEMPT_PATHS`)
- Test: `backend/tests/test_collectables_reconcile.py`

**Interfaces:**
- Consumes: `grant_eligible` (Task 2).
- Produces: `XpResult.granted_collectables: list[str]`; `award_xp` populates it; `POST /internal/collectables/reconcile`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_collectables_reconcile.py
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from app.models.user import User, UserProgress
from app.models.cosmetics import CosmeticItem, UserCosmetic
from tests.test_content import _register_and_login
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_reconcile_grants_eligible(client, db_session):
    await _register_and_login(client, email="rec@example.com", username="rec")
    u = await db_session.scalar(select(User).where(User.email == "rec@example.com"))
    p = await db_session.get(UserProgress, u.id) or UserProgress(user_id=u.id)
    p.streak_count = 10; db_session.add(p)
    now = datetime.now(UTC)
    db_session.add(CosmeticItem(slug="_rec_drop", name="R", emoji="👑", type="accessory", coin_cost=0,
                                is_premium=False, rarity="rare", unlock_type="streak_days", unlock_threshold=5,
                                available_from=now - timedelta(days=1), available_until=now + timedelta(days=1)))
    await db_session.commit()
    r = await client.post("/internal/collectables/reconcile")
    assert r.status_code == 200
    item = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == "_rec_drop"))
    owned = await db_session.scalar(select(UserCosmetic).where(UserCosmetic.user_id == u.id, UserCosmetic.item_id == item.id))
    assert owned is not None
```

- [ ] **Step 2: Run — expect FAIL** (404 on the endpoint)

Run: `python -m pytest tests/test_collectables_reconcile.py -q`

- [ ] **Step 3: Add the `XpResult` field**

In `backend/app/services/xp_service.py`, add to the `XpResult` dataclass: `granted_collectables: list[str] = field(default_factory=list)` (import `field` from dataclasses if needed). `record_xp` does NOT set it (it's pure); `award_xp` does.

- [ ] **Step 4: Hook `award_xp`**

In `backend/app/services/market_progress_service.py` `award_xp`, after `await _add_market_xp(...)` and before `return result`:

```python
    from app.services.collectables_service import grant_eligible
    result.granted_collectables = await grant_eligible(session, progress)
    return result
```

(`grant_eligible` is defensive — a failure returns `[]` and never breaks the XP commit.)

- [ ] **Step 5: Add the reconcile cron**

In `backend/app/routers/internal.py`, following the existing cron pattern (look at `/subscriptions/reconcile`), add:

```python
@router.post("/collectables/reconcile")
async def trigger_collectables_reconcile(
    _auth: None = Depends(verify_cron_secret),   # use whatever auth dependency the sibling crons use
    session: AsyncSession = Depends(get_session),
):
    from app.services.collectables_service import grant_eligible
    from app.models.user import UserProgress
    from sqlalchemy import select
    progresses = (await session.scalars(select(UserProgress).where(UserProgress.streak_count > 0))).all()
    total = 0
    for p in progresses:
        total += len(await grant_eligible(session, p))
    await session.commit()
    return {"status": "ok", "granted": total}
```

Match the auth dependency the other crons in this file use (read the file — it's a `verify_cron_secret`/Header pattern). Sweeping only `streak_count > 0` keeps it cheap; the award_xp seam covers everyone active.

- [ ] **Step 6: CSRF allowlist**

In `backend/app/core/csrf.py`, add `"/internal/collectables/reconcile"` to `_DEFAULT_EXEMPT_PATHS`.

- [ ] **Step 7: Run — expect PASS** + a regression on the XP seam + lint + commit

Run: `python -m pytest tests/test_collectables_reconcile.py tests/test_collectables_service.py -q && python -m ruff check app/services/xp_service.py app/services/market_progress_service.py app/routers/internal.py app/core/csrf.py`

```bash
git add backend/app/services/xp_service.py backend/app/services/market_progress_service.py backend/app/routers/internal.py backend/app/core/csrf.py backend/tests/test_collectables_reconcile.py
git commit -m "feat(collectables): grant on award_xp seam + nightly reconcile cron"
```

---

### Task 4: Child API + shop guards

**Files:**
- Create: `backend/app/routers/collectables.py` (+ register the router in the app)
- Create: `backend/app/schemas/collectables.py`
- Modify: `backend/app/routers/cosmetics.py` (`_shop_state` excludes drops; `buy_item` 403 for drops)
- Test: `backend/tests/test_collectables_api.py`

**Interfaces:**
- Consumes: `progress_for`, `is_drop_active` (Task 2).
- Produces: `GET /collectables` → `{ active: [DropOut], owned: [OwnedOut] }`; buy-guard + shelf-exclusion.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_collectables_api.py
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem
from tests.test_cosmetics_api import _login_with_coins, _item
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _seed_drop(db_session, slug="_api_drop"):
    now = datetime.now(UTC)
    d = CosmeticItem(slug=slug, name="Crown", emoji="👑", type="accessory", coin_cost=0, is_premium=False,
                     rarity="legendary", unlock_type="streak_days", unlock_threshold=7,
                     available_from=now - timedelta(days=1), available_until=now + timedelta(days=3))
    db_session.add(d); await db_session.commit(); return d

async def test_collectables_lists_active_drop_with_progress(client, db_session):
    await _login_with_coins(client, db_session, coins=0)
    await _seed_drop(db_session)
    r = await client.get("/collectables")
    assert r.status_code == 200
    body = r.json()
    drop = next(d for d in body["active"] if d["slug"] == "_api_drop")
    assert drop["rarity"] == "legendary"
    assert drop["goal"]["type"] == "streak_days" and drop["goal"]["threshold"] == 7
    assert drop["earned"] is False

async def test_normal_shop_excludes_drops(client, db_session):
    await _login_with_coins(client, db_session, coins=0)
    await _seed_drop(db_session, slug="_api_drop2")
    body = (await client.get("/cosmetics")).json()
    assert all(i["slug"] != "_api_drop2" for i in body["items"])

async def test_buying_a_drop_is_rejected(client, db_session):
    await _login_with_coins(client, db_session, coins=1000)
    d = await _seed_drop(db_session, slug="_api_drop3")
    r = await client.post(f"/cosmetics/{d.id}/buy")
    assert r.status_code == 403
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_collectables_api.py -q`

- [ ] **Step 3: Schemas**

```python
# backend/app/schemas/collectables.py
from pydantic import BaseModel

class GoalOut(BaseModel):
    type: str
    threshold: int
    current: int

class DropOut(BaseModel):
    slug: str
    name: str
    emoji: str
    type: str
    rarity: str | None
    ends_at: str | None
    goal: GoalOut
    earned: bool

class OwnedOut(BaseModel):
    slug: str
    name: str
    emoji: str
    type: str
    rarity: str | None
    equipped: bool

class CollectablesResponse(BaseModel):
    active: list[DropOut]
    owned: list[OwnedOut]
```

- [ ] **Step 4: The endpoint**

```python
# backend/app/routers/collectables.py
from datetime import datetime, UTC
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.collectables import CollectablesResponse, DropOut, GoalOut, OwnedOut
from app.services.collectables_service import is_drop_active, progress_for

router = APIRouter(prefix="/collectables", tags=["collectables"])

@router.get("", response_model=CollectablesResponse)
async def list_collectables(current_user: User = Depends(get_current_user),
                            session: AsyncSession = Depends(get_session)):
    now = datetime.now(UTC)
    progress = await session.get(UserProgress, current_user.id) or UserProgress(user_id=current_user.id, streak_count=0)
    owned_rows = {r.item_id: r for r in (await session.scalars(
        select(UserCosmetic).where(UserCosmetic.user_id == current_user.id))).all()}
    drops = (await session.scalars(select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None)))).all()

    active = []
    for d in drops:
        if not is_drop_active(d, now):
            continue
        active.append(DropOut(
            slug=d.slug, name=d.name, emoji=d.emoji, type=d.type, rarity=d.rarity,
            ends_at=d.available_until.isoformat() if d.available_until else None,
            goal=GoalOut(type=d.unlock_type, threshold=d.unlock_threshold or 0,
                         current=await progress_for(session, progress, d)),
            earned=d.id in owned_rows,
        ))
    owned = [OwnedOut(slug=d.slug, name=d.name, emoji=d.emoji, type=d.type, rarity=d.rarity,
                      equipped=bool(owned_rows.get(d.id) and owned_rows[d.id].equipped))
             for d in drops if d.id in owned_rows]
    return CollectablesResponse(active=active, owned=owned)
```

Register the router where the other routers are included (find `app.include_router(cosmetics...)` in the app factory and add `collectables.router` beside it). Apply the same auth/rate-limit middleware the sibling child routers use.

- [ ] **Step 5: Shop guards** in `backend/app/routers/cosmetics.py`

In `_shop_state`, change the items query to exclude drops:
```python
select(CosmeticItem).where(CosmeticItem.unlock_type.is_(None)).order_by(CosmeticItem.coin_cost)
```
In `buy_item`, after loading `item` and the not-found check, add:
```python
    if item.unlock_type is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_buyable")
```

- [ ] **Step 6: Run — expect PASS** + lint + commit

Run: `python -m pytest tests/test_collectables_api.py tests/test_cosmetics_api.py -q && python -m ruff check app/routers/collectables.py app/schemas/collectables.py app/routers/cosmetics.py`

```bash
git add backend/app/routers/collectables.py backend/app/schemas/collectables.py backend/app/routers/cosmetics.py backend/app/main.py backend/tests/test_collectables_api.py
git commit -m "feat(collectables): GET /collectables + earned-only shop guards"
```
(Adjust the `main.py` path to wherever the app factory / router registration lives.)

---

### Task 5: Seed an example drop

**Files:**
- Modify: `backend/app/seed/cosmetics.py`
- Test: `backend/tests/test_collectables_seed.py`

**Interfaces:**
- Consumes: Task-1 fields. Produces: one seeded active drop on deploy.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_collectables_seed.py
import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem
from app.seed.cosmetics import seed_cosmetics
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_seed_creates_a_limited_drop(db_session):
    await seed_cosmetics(db_session); await db_session.commit()
    drop = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None)))
    assert drop is not None
    assert drop.rarity in {"common", "rare", "epic", "legendary"}
    assert drop.unlock_threshold and drop.unlock_threshold > 0
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_collectables_seed.py -q`

- [ ] **Step 3: Add the drop to `CATALOG` + extend the upsert**

In `backend/app/seed/cosmetics.py`: read how the upsert copies fields (it refreshes name/emoji/cost/premium/type). Extend it to also copy `available_from`, `available_until`, `rarity`, `unlock_type`, `unlock_threshold` (using `spec.get(...)` so normal items default to None). Add one drop to `CATALOG`:

```python
    # ── Limited drops ────────────────────────────────────────────────────────
    {"slug": "founders_crown", "name": "Founder's Crown", "emoji": "👑", "type": "accessory",
     "coin_cost": 0, "is_premium": False, "rarity": "legendary",
     "unlock_type": "streak_days", "unlock_threshold": 7,
     "available_from": _drop_window()[0], "available_until": _drop_window()[1]},
```

Add a helper near the top so the window is always "open now for 30 days" on each seed (idempotent refresh keeps it open):
```python
from datetime import UTC, datetime, timedelta
def _drop_window():
    now = datetime.now(UTC)
    return now - timedelta(days=1), now + timedelta(days=30)
```

- [ ] **Step 4: Run — expect PASS** + lint + commit

Run: `python -m pytest tests/test_collectables_seed.py tests/test_cosmetics_seed.py -q && python -m ruff check app/seed/cosmetics.py`

```bash
git add backend/app/seed/cosmetics.py backend/tests/test_collectables_seed.py
git commit -m "feat(collectables): seed the Founder's Crown limited drop + upsert new fields"
```

---

### Task 6: Frontend — collectables client + Limited shelf + earn toast

**Files:**
- Create: `frontend/src/api/collectables.ts` (client + `useCollectables` hook + types)
- Create: `frontend/src/components/child/shop/LimitedShelf.tsx`
- Modify: `frontend/src/pages/child/Shop.tsx` (render the shelf)
- Modify: `frontend/src/locales/en/child.json` (`limited.*` strings)
- Modify: the lesson-complete flow to toast `granted_collectables` (find where the lesson-complete response's reward feedback is shown — `grep -rn "granted_collectables\|reward\|xp_awarded" frontend/src/pages/child` and the content API client; surface a toast when the array is non-empty)
- Test: `frontend/src/api/__tests__/collectables.test.ts` + `frontend/src/components/child/shop/__tests__/LimitedShelf.test.tsx`

**Interfaces:**
- Consumes: `GET /collectables` (Task 4); `granted_collectables` on the lesson-complete response (Task 3).

- [ ] **Step 1: Write the failing tests** — (a) `collectables.test.ts`: `getCollectables()` calls `/collectables`; (b) `LimitedShelf.test.tsx`: given a mocked active drop `{slug, rarity:'legendary', goal:{type:'streak_days',threshold:7,current:3}, ends_at, earned:false}`, the shelf renders the name, a rarity badge, and a "3 / 7" progress; given an `earned:true` drop it shows an "Earned" state; `vitest-axe`-clean.

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/api/__tests__/collectables.test.ts src/components/child/shop/__tests__/LimitedShelf.test.tsx`

- [ ] **Step 3: Implement the client + hook**

```ts
// frontend/src/api/collectables.ts
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type CollectableGoal = { type: string; threshold: number; current: number };
export type CollectableDrop = { slug: string; name: string; emoji: string; type: string;
  rarity: string | null; ends_at: string | null; goal: CollectableGoal; earned: boolean };
export type OwnedCollectable = { slug: string; name: string; emoji: string; type: string;
  rarity: string | null; equipped: boolean };
export type CollectablesState = { active: CollectableDrop[]; owned: OwnedCollectable[] };

export const getCollectables = () => apiFetch<CollectablesState>('/collectables');
export function useCollectables() {
  return useQuery({ queryKey: ['collectables'], queryFn: getCollectables });
}
```

- [ ] **Step 4: Implement `LimitedShelf`** — a section titled "Limited collectables" rendering `active` drops (each: emoji/name, a rarity badge via a `RARITY_STYLE` map e.g. `{ legendary: 'bg-amber-100 text-amber-800', epic: 'bg-purple-100 text-purple-800', rare: 'bg-sky-100 text-sky-800', common: 'bg-gray-100 text-gray-700' }`, a countdown to `ends_at`, and the goal: if `earned` show "Earned ✓"; else a progress bar + "current / threshold" with the goal label) and the `owned` collection below. Use the existing i18n + `min-h-[44px]` + `role`/`aria` patterns from `Shop.tsx`. The `<Penny>`/emoji for the item: drops are accessory/skin types — render the item's `emoji` as the shelf icon (matching how the normal shop tiles show `item.emoji`). Add `limited.*` i18n keys (title, earned, endsIn, goal labels per type, emptyActive).

- [ ] **Step 5: Wire it into `Shop.tsx`** — render `<LimitedShelf />` above or below the existing tabs (its own section, NOT a coin tab). It uses `useCollectables()`; while loading show a small spinner; if `active` and `owned` are both empty, render nothing (or a one-line "No limited items right now").

- [ ] **Step 6: Earn toast** — in the lesson-complete handler, when the response's `granted_collectables` is a non-empty array, show a celebratory toast (reuse the existing reward-toast mechanism — the simulator/lesson reward toast pattern). Keep it to the lesson-complete path for B1 (other earn paths show up on the Limited shelf's "Earned" state). Update the content API type to include `granted_collectables?: string[]`.

- [ ] **Step 7: Run — expect PASS** + tsc + lint + build + commit

Run: `cd frontend && npx vitest run src/api/__tests__/collectables.test.ts src/components/child/shop && npx tsc --noEmit && npm run lint && npm run build`

```bash
git add frontend/src/api/collectables.ts frontend/src/components/child/shop/ frontend/src/pages/child/Shop.tsx frontend/src/locales/en/child.json
git commit -m "feat(collectables): Limited shelf in the shop + earn toast"
```

---

### Task 7: Full verification + ship

**Files:** none.

- [ ] **Step 1: Backend gate** — `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app tests && python -m pytest tests/test_collectables_columns.py tests/test_collectables_service.py tests/test_collectables_reconcile.py tests/test_collectables_api.py tests/test_collectables_seed.py tests/test_cosmetics_api.py -q` → all pass, ruff clean.
- [ ] **Step 2: Frontend gate** — `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/api/__tests__/collectables.test.ts src/components/child/shop && npm run build`; then full suite once and confirm only the ~68 env-only base-URL failures + ZERO unhandled errors.
- [ ] **Step 3: Migration snapshot gate (STANDING RULE)** — before the prod migration `c4d5e6f7a8b9`, **ask the user whether to snapshot the prod DB first.** Wait for the answer.
- [ ] **Step 4: Push + watch CI** — `git push origin main`; `gh run watch "$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status`. CI green → Railway applies the migration + redeploys + the seed adds the Founder's Crown drop.
- [ ] **Step 5: Web deploy + alias** — `cd frontend && vercel --prod --force --yes` then `vercel alias set <hash>-investikid.vercel.app app.investikid.ai`.
- [ ] **Step 6: `cap sync ios`** (shop UI changed).
- [ ] **Step 7: Verify live** in the user's Chrome: `/shop` shows the Limited shelf with the Founder's Crown (7-day-streak goal + countdown + progress); the buy endpoint rejects it; reaching the streak grants it (verify the grant via the `/collectables` `earned` flag, or simulate by checking the reconcile endpoint).
- [ ] **Step 8: Update docs/memory** — MASTER-BACKLOG + `project_arcade`/collectables memory (B1 live; engine + criteria; migration id); record **B2 (admin scheduler) + B3 (Home card) are the next sub-projects.**

---

## Notes for the implementer

- **Earned-only is load-bearing:** a limited item must never be coin-buyable. Two guards (shelf exclusion + buy 403) — keep both.
- **grant_eligible must never break the XP path:** it catches its own exceptions and returns `[]`. Don't remove that guard.
- **Idempotency:** the `(user_id, item_id)` PK on `UserCosmetic` + the owned-set check prevent double-grants; tests assert a second `grant_eligible` grants nothing.
- The `award_xp` hook means EVERY xp-earning action (lesson/quiz/revise/arcade/sim) can complete a goal — that's intended. The early-return when there are no active drops keeps the hot path cheap.
- Equipping an earned collectable goes through the existing equip flow + slot rules — no new equip logic.
