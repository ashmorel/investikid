# Multi-Market Backend Implementation Plan (Sub-project C2a)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track XP per market (a new `UserMarketProgress` table) alongside the unchanged global `UserProgress.xp`, add a switchable `active_market_code` with lazy enrollment, market-tag Revise records, and expose the market/switch/progress APIs — invisibly (active defaults to home=GB).

**Architecture:** Additive layer. `UserProgress` stays the global engagement row. A single `award_xp` seam wraps the existing `record_xp` and upserts the active market's `UserMarketProgress` row (resolving the active market from `progress.user_id` when not passed), keeping the invariant `sum(per-market xp) == UserProgress.xp`. Content gating + Revise move from `home_market_code` → `active_market_code` (which defaults to home, so behavior is unchanged).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest.

**Spec:** `docs/superpowers/specs/2026-06-18-multimarket-backend-design.md`
**Branch:** `testing`. Current Alembic head: `c2d3e4f5a6b7`.

---

## File Structure

- Create `backend/app/models/market_progress.py` — `UserMarketProgress` model.
- Modify `backend/app/models/user.py` — `User.active_market_code`.
- Modify `backend/app/models/skill_profile.py` — `WeakConcept.market_code`.
- Modify `backend/app/models/__init__.py` — register `UserMarketProgress`.
- Create `backend/alembic/versions/<rev>_multimarket_progress.py` — table + backfill + 2 columns.
- Create `backend/app/services/market_progress_service.py` — `award_xp`, `_add_market_xp`, `ensure_enrolled`, per-market reads.
- Modify the 5 award sites to call `award_xp`.
- Modify `backend/app/routers/content.py`, `app/services/next_lesson_service.py`, `app/services/recommendation_service.py` — gate by `active_market_code`.
- Modify `backend/app/services/revise_service.py` + `app/services/skill_profile_service.py` — tag/filter weak-concepts by active market.
- Create `backend/app/routers/markets.py` — `GET /markets`, `POST /me/active-market`, `GET /me/markets`. (Or add to an existing router; a dedicated one is cleaner.)
- Modify `backend/app/schemas/user.py` — `UserProfile.active_market_code`.
- Modify `backend/app/main.py` (or wherever routers are included) — include the markets router.
- Tests under `backend/tests/`.

---

### Task 1: `UserMarketProgress` model + `active_market_code` + `WeakConcept.market_code`

**Files:**
- Create: `backend/app/models/market_progress.py`
- Modify: `backend/app/models/user.py`, `backend/app/models/skill_profile.py`, `backend/app/models/__init__.py`
- Test: `backend/tests/test_market_progress_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_progress_model.py`:

```python
import pytest

from app.models.market_progress import UserMarketProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_user_market_progress_composite_pk(db_session, registered_user):
    ump = UserMarketProgress(user_id=registered_user.id, market_code="GB", xp=40)
    db_session.add(ump)
    await db_session.flush()
    fetched = await db_session.get(UserMarketProgress, (registered_user.id, "GB"))
    assert fetched is not None
    assert fetched.xp == 40
    assert fetched.market_code == "GB"
```

> Adapt `registered_user` to the project's real fixture that yields a persisted `User` (grep `tests/conftest.py` / existing tests for the fixture that creates a user, e.g. `user`, `child_user`). The `markets` table is auto-seeded for tests by the existing conftest autouse fixture, so the FK is satisfiable.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_market_progress_model.py -q`
Expected: FAIL (`ModuleNotFoundError: app.models.market_progress`).

- [ ] **Step 3: Create the model**

Create `backend/app/models/market_progress.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserMarketProgress(Base):
    """Per-market learning progress (XP). One row per (user, market). The row's
    existence means the user is enrolled in that market. Global engagement
    (streak/coins/goal/level/total-XP) stays on UserProgress."""
    __tablename__ = "user_market_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), primary_key=True
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
```

Register it: in `backend/app/models/__init__.py`, add `from app.models.market_progress import UserMarketProgress  # noqa: F401` (matching the file's existing import style + sort order — run `ruff check --fix` on it after).

- [ ] **Step 4: Add `User.active_market_code`**

In `backend/app/models/user.py`, add to `User` after `home_market_code`:
```python
    active_market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=False, default="GB", server_default="GB"
    )
```

- [ ] **Step 5: Add `WeakConcept.market_code`**

In `backend/app/models/skill_profile.py`, add to `WeakConcept` after `concept`:
```python
    market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=False, default="GB", server_default="GB", index=True
    )
```
(`String` and `ForeignKey` are already imported there — confirm.)

- [ ] **Step 6: Run the test + ruff**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_market_progress_model.py -q && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/models/`
Expected: PASS; ruff clean.

- [ ] **Step 7: Commit**

```bash
cd "/Users/leeashmore/investikid" && git add backend/app/models/market_progress.py backend/app/models/user.py backend/app/models/skill_profile.py backend/app/models/__init__.py backend/tests/test_market_progress_model.py && git commit -m "feat(market): UserMarketProgress + active_market_code + WeakConcept.market_code

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Migration (table + backfill GB=xp + 2 columns)

**Files:**
- Create: `backend/alembic/versions/d3e4f5a6b7c8_multimarket_progress.py`

- [ ] **Step 1: Confirm head**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/alembic" heads`
Expected: single head `c2d3e4f5a6b7`. Use it as `down_revision`. **Verify the chosen revision id `d3e4f5a6b7c8` is not already used:** `grep -rn "d3e4f5a6b7c8" alembic/versions` → no match (if it collides, pick another free id and update the filename + `revision`).

- [ ] **Step 2: Write the migration**

Create `backend/alembic/versions/d3e4f5a6b7c8_multimarket_progress.py`:

```python
"""multi-market progress: user_market_progress + active_market_code + weak_concept market (C2a)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-18 16:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_market_progress",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.PrimaryKeyConstraint("user_id", "market_code"),
    )
    op.create_index("ix_user_market_progress_user_id", "user_market_progress", ["user_id"])

    # Backfill: every user gets a GB row = their current global XP (all current
    # content is GB, so sum(per-market) == UserProgress.xp holds post-migration).
    op.execute(
        """
        INSERT INTO user_market_progress (user_id, market_code, xp, created_at)
        SELECT u.id, 'GB', COALESCE(up.xp, 0), now()
        FROM users u
        LEFT JOIN user_progress up ON up.user_id = u.id
        """
    )

    op.add_column(
        "users",
        sa.Column("active_market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_users_active_market", "users", "markets", ["active_market_code"], ["code"])

    op.add_column(
        "weak_concepts",
        sa.Column("market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_weak_concepts_market", "weak_concepts", "markets", ["market_code"], ["code"])
    op.create_index("ix_weak_concepts_market_code", "weak_concepts", ["market_code"])


def downgrade() -> None:
    op.drop_index("ix_weak_concepts_market_code", table_name="weak_concepts")
    op.drop_constraint("fk_weak_concepts_market", "weak_concepts", type_="foreignkey")
    op.drop_column("weak_concepts", "market_code")
    op.drop_constraint("fk_users_active_market", "users", type_="foreignkey")
    op.drop_column("users", "active_market_code")
    op.drop_index("ix_user_market_progress_user_id", table_name="user_market_progress")
    op.drop_table("user_market_progress")
```

> If `sa.dialects.postgresql.UUID` isn't resolvable that way, `import sqlalchemy.dialects.postgresql as pg` and use `pg.UUID(as_uuid=True)`. Match the UUID column type used by other migrations in `alembic/versions/` (grep one for `UUID(`).

- [ ] **Step 3: Apply + round-trip**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/alembic" upgrade head` → `Running upgrade c2d3e4f5a6b7 -> d3e4f5a6b7c8`. Then `alembic heads` → single head. Then `alembic downgrade -1 && alembic upgrade head` → both clean.

- [ ] **Step 4: ruff + commit**

```bash
cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check alembic/versions/d3e4f5a6b7c8_multimarket_progress.py
cd "/Users/leeashmore/investikid" && git add backend/alembic/versions/d3e4f5a6b7c8_multimarket_progress.py && git commit -m "feat(market): migration — user_market_progress + active_market_code + weak_concept market (backfill GB)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: The `award_xp` seam + route the 5 award sites + invariant test

**Files:**
- Create: `backend/app/services/market_progress_service.py`
- Modify: `backend/app/routers/content.py:439`, `app/services/revise_service.py:230`, `app/services/simulator_rewards.py:37,128`, `app/services/gamification_service.py:174`
- Test: `backend/tests/test_award_xp_seam.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_award_xp_seam.py`:

```python
import pytest

from app.models.market_progress import UserMarketProgress
from app.models.user import UserProgress
from app.services.market_progress_service import award_xp

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_award_xp_updates_global_and_active_market(db_session, registered_user):
    # registered_user defaults active_market_code 'GB'
    progress = UserProgress(user_id=registered_user.id, xp=0)
    db_session.add(progress)
    await db_session.flush()

    await award_xp(db_session, progress, 25)
    await db_session.flush()

    assert progress.xp == 25  # global total
    gb = await db_session.get(UserMarketProgress, (registered_user.id, "GB"))
    assert gb is not None and gb.xp == 25  # per-market (lazy-created)


async def test_award_xp_invariant_across_two_markets(db_session, registered_user):
    progress = UserProgress(user_id=registered_user.id, xp=0)
    db_session.add(progress)
    await db_session.flush()

    await award_xp(db_session, progress, 10, market_code="GB")
    await award_xp(db_session, progress, 7, market_code="US")
    await db_session.flush()

    rows = (await db_session.scalars(
        __import__("sqlalchemy").select(UserMarketProgress).where(
            UserMarketProgress.user_id == registered_user.id
        )
    )).all()
    assert sum(r.xp for r in rows) == progress.xp == 17  # invariant
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError: market_progress_service`).

- [ ] **Step 3: Implement the seam**

Create `backend/app/services/market_progress_service.py`:

```python
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress
from app.services.xp_service import XpResult, record_xp


async def _add_market_xp(session: AsyncSession, user_id, market_code: str, amount: int) -> None:
    """Upsert the (user, market) row and add XP (= lazy enrollment)."""
    row = await session.get(UserMarketProgress, (user_id, market_code))
    if row is None:
        row = UserMarketProgress(user_id=user_id, market_code=market_code, xp=0)
        session.add(row)
    row.xp += amount


async def award_xp(
    session: AsyncSession,
    progress: UserProgress,
    amount: int,
    *,
    market_code: str | None = None,
    today: date | None = None,
) -> XpResult:
    """Canonical XP-award seam: updates the GLOBAL total/level/goal (via record_xp)
    AND the active market's per-market row. When market_code is omitted, it is
    resolved from the user's active_market_code. Keeps sum(per-market) == global."""
    result = record_xp(progress, amount, today=today)
    if market_code is None:
        market_code = await session.scalar(
            select(User.active_market_code).where(User.id == progress.user_id)
        ) or "GB"
    await _add_market_xp(session, progress.user_id, market_code, amount)
    return result


async def ensure_enrolled(session: AsyncSession, user_id, market_code: str) -> None:
    """Create the (user, market) progress row if absent (no XP change)."""
    if await session.get(UserMarketProgress, (user_id, market_code)) is None:
        session.add(UserMarketProgress(user_id=user_id, market_code=market_code, xp=0))
```

- [ ] **Step 4: Route the 5 award sites through `award_xp`**

Read each site, then replace `record_xp(progress, X[, today=...])` with `await award_xp(session, progress, X[, today=...])`. The sites already have `session` in scope (they're async DB code); confirm and pass it. Specifics:
- `app/routers/content.py:439`: `goal = await award_xp(session, progress, awarded, today=today_local)`.
- `app/services/revise_service.py:230`: `return await award_xp(session, progress, awarded, today=today)`.
- `app/services/simulator_rewards.py:37`: `await award_xp(session, progress, awarded)`; `:128`: `await award_xp(session, progress, xp)`.
- `app/services/gamification_service.py:174`: `await award_xp(session, progress, challenge.xp_reward)` (this awards to a group member — `award_xp` resolves that member's active market from `progress.user_id`, which is correct).

Import `award_xp` in each file (from `app.services.market_progress_service`). Remove the now-unused `record_xp` import ONLY if no other use remains in that file (grep first — `content.py` also calls `record_daily_activity`; keep that import line). Each of these functions is already `async` (they `await` session ops); confirm before adding `await`.

- [ ] **Step 5: Run tests + the existing XP/award tests (no regression)**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_award_xp_seam.py tests/test_xp_service.py tests/test_revise_service.py tests/test_simulator.py tests/test_gamification.py -q`
(Use the real filenames — grep for the simulator-rewards + gamification test modules.) All pass. The existing tests prove global XP/level/goal behavior is unchanged.

- [ ] **Step 6: ruff + commit**

```bash
cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/services/market_progress_service.py app/routers/content.py app/services/
cd "/Users/leeashmore/investikid" && git add -A && git commit -m "feat(market): award_xp seam updates global + active-market XP (invariant)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Content + Revise gate by active market

**Files:**
- Modify: `backend/app/routers/content.py`, `app/services/next_lesson_service.py`, `app/services/recommendation_service.py`
- Modify: `backend/app/services/revise_service.py`, `app/services/skill_profile_service.py`
- Test: `backend/tests/test_active_market_gating.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_active_market_gating.py`:

```python
import pytest

from app.models.content import Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_content_follows_active_market_not_home(client, db_session, current_user_row):
    # current_user_row is the authenticated client's User. Default home/active = GB.
    db_session.add(Module(topic="savings", title="GB Mod C2a", country_codes=[],
                          is_premium=False, order_index=950, icon="💷", market_code="GB"))
    db_session.add(Module(topic="savings", title="US Mod C2a", country_codes=[],
                          is_premium=False, order_index=951, icon="💵", market_code="US"))
    await db_session.flush()

    titles = lambda: [m["title"] for m in (client.get("/content/modules")).json()]
    # default active = GB
    t = [m["title"] for m in (await client.get("/content/modules")).json()]
    assert "GB Mod C2a" in t and "US Mod C2a" not in t

    # switch active to US
    current_user_row.active_market_code = "US"
    await db_session.flush()
    t = [m["title"] for m in (await client.get("/content/modules")).json()]
    assert "US Mod C2a" in t and "GB Mod C2a" not in t
```

> Adapt to real fixtures: the authenticated `client` + a handle to its `User` row (`current_user_row` — grep how existing tests mutate the logged-in user; if there isn't a direct handle, load the user by the client's identity within `db_session`). If `client` and `db_session` aren't the same session, follow the existing content tests' pattern for making inserts visible to the request.

- [ ] **Step 2: Run it — FAIL** (content still gates by home; switching active has no effect).

- [ ] **Step 3: Swap the 5 gate sites home → active**

In `app/routers/content.py` (`_get_accessible_module` + `list_modules`), `app/services/next_lesson_service.py`, and `app/services/recommendation_service.py` (both gates), replace every `is_module_in_market(<m>.market_code, <user>.home_market_code)` with `is_module_in_market(<m>.market_code, <user>.active_market_code)`. (These are the exact sites C1 set to `home_market_code`.) No other logic changes.

- [ ] **Step 4: Tag + filter Revise weak-concepts by active market**

- In `app/services/revise_service.py:262` and `app/services/skill_profile_service.py:71`, where a `WeakConcept(...)` is created, add `market_code=user.active_market_code` (confirm the `user` object is in scope at each; if only `user_id` is present, load the user's `active_market_code` or thread the active market into the function).
- In `app/services/revise_service.py`, the session-building / due-items queries that select `WeakConcept` rows for a user must also filter `WeakConcept.market_code == user.active_market_code` so Revise is per-market. Read `build_session` / `get_due_items` / `get_due_count` and add the market filter to each `select(WeakConcept)...where(...)`.

- [ ] **Step 5: Run tests (gating + Revise no-regression)**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_active_market_gating.py tests/test_market_content_filter.py tests/test_next_lesson_service.py tests/test_next_lesson_endpoint.py tests/test_recommendation_enhanced.py tests/test_revise_service.py -q`
Expected: all pass. (A default GB user is unaffected since active=home=GB; the new test proves switching active changes content.)

- [ ] **Step 6: ruff + commit**

```bash
cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/
cd "/Users/leeashmore/investikid" && git add -A && git commit -m "feat(market): content + Revise gate by active market

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Markets / switch / per-market progress APIs

**Files:**
- Create: `backend/app/routers/markets.py`
- Modify: `backend/app/schemas/user.py` (`UserProfile.active_market_code`), the app's router registration (`app/main.py` or equivalent)
- Test: `backend/tests/test_markets_api.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_markets_api.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_list_markets(client):
    rows = (await client.get("/markets")).json()
    by_code = {m["code"]: m for m in rows}
    assert set(by_code) == {"GB", "US", "AU", "CA", "IE", "ES", "FR", "DE", "HK", "SG"}
    assert by_code["GB"]["has_content"] is True
    assert by_code["US"]["has_content"] is False
    assert by_code["GB"]["is_active"] is True   # default active
    assert by_code["GB"]["enrolled"] is True     # backfilled / default


async def test_switch_active_market_lazy_enrolls(client):
    r = await client.post("/me/active-market", json={"market_code": "US"})
    assert r.status_code == 200
    assert r.json()["active_market_code"] == "US"
    rows = {m["code"]: m for m in (await client.get("/markets")).json()}
    assert rows["US"]["is_active"] is True
    assert rows["US"]["enrolled"] is True  # lazily enrolled on switch


async def test_switch_unknown_market_422(client):
    r = await client.post("/me/active-market", json={"market_code": "ZZ"})
    assert r.status_code == 422
```

> If the test `client`'s GB enrollment isn't present (depends on whether the client user got a backfilled/auto row), make `test_list_markets`'s `enrolled` assertion robust: a freshly-registered test user may not have a `UserMarketProgress` row until they earn XP or switch. If so, either (a) have registration call `ensure_enrolled(session, user.id, home_market_code)`, or (b) relax the assertion to `enrolled in (True, False)` for GB and keep the lazy-enroll assertion in `test_switch_active_market_lazy_enrolls`. PREFER (a): enroll the user in their home market at registration (one `ensure_enrolled` call in the registration path) so home is always enrolled — add that and assert `enrolled is True`.

- [ ] **Step 2: Run it — FAIL** (no `/markets` router).

- [ ] **Step 3: Implement the router**

Create `backend/app/routers/markets.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.market import Market
from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.services.content_service import compute_level
from app.services.market_progress_service import ensure_enrolled

router = APIRouter(tags=["markets"])


class MarketOut(BaseModel):
    code: str
    name: str
    currency_code: str
    has_content: bool
    enrolled: bool
    is_active: bool


class SwitchMarketRequest(BaseModel):
    market_code: str


@router.get("/markets", response_model=list[MarketOut])
async def list_markets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    markets = (await session.scalars(
        select(Market).where(Market.is_active.is_(True)).order_by(Market.code)
    )).all()
    enrolled = {
        c for c in (await session.scalars(
            select(UserMarketProgress.market_code).where(
                UserMarketProgress.user_id == current_user.id
            )
        )).all()
    }
    return [
        MarketOut(
            code=m.code, name=m.name, currency_code=m.currency_code,
            has_content=m.has_content, enrolled=m.code in enrolled,
            is_active=m.code == current_user.active_market_code,
        )
        for m in markets
    ]


@router.post("/me/active-market")
async def switch_active_market(
    payload: SwitchMarketRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, payload.market_code)
    if market is None or not market.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown market")
    current_user.active_market_code = payload.market_code
    await ensure_enrolled(session, current_user.id, payload.market_code)
    await session.commit()
    return {"active_market_code": current_user.active_market_code}


class MarketProgressOut(BaseModel):
    market_code: str
    xp: int


class MarketsProgressEnvelope(BaseModel):
    markets: list[MarketProgressOut]
    total_xp: int
    level: int


@router.get("/me/markets", response_model=MarketsProgressEnvelope)
async def my_market_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(UserMarketProgress).where(UserMarketProgress.user_id == current_user.id)
    )).all()
    progress = await session.get(UserProgress, current_user.id)
    total = progress.xp if progress else 0
    return MarketsProgressEnvelope(
        markets=[MarketProgressOut(market_code=r.market_code, xp=r.xp) for r in rows],
        total_xp=total,
        level=compute_level(total),
    )
```

> Verify the imports resolve to real symbols: `get_current_user` (its real module), `get_session`, `compute_level` (it's in `content_service.py`). Adjust import paths to match the codebase. Register the router where others are included (grep `include_router(` in `app/main.py` and add `app.include_router(markets.router)`). If there's a global API prefix, the paths become `<prefix>/markets` etc. — match the test URLs to the real prefix.

- [ ] **Step 4: `active_market_code` on the profile + enroll-at-registration**

- In `backend/app/schemas/user.py`, add to `UserProfile` (after `home_market_code`): `active_market_code: str = "GB"`.
- In the registration path (where a new `User` + `UserProgress` are created — grep `auth.py` / the register handler), call `await ensure_enrolled(session, user.id, user.home_market_code)` so every user is enrolled in their home market from day one.

- [ ] **Step 5: Run the API tests + ruff**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_markets_api.py -q && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/routers/markets.py app/schemas/user.py`
Expected: PASS; ruff clean.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/investikid" && git add -A && git commit -m "feat(market): /markets, POST /me/active-market, /me/markets APIs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full verification + promote

- [ ] **Step 1: Full suite + ruff**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check . && "/Users/leeashmore/Local Repo/.venv/bin/pytest" -q`
Expected: ruff clean; full suite green. (If `tests/test_users.py::test_get_progress_reflects_lesson_completion` fails ONLY with a `2026-06-18 == 2026-06-19`-style date assertion, that's the known pre-existing UTC-vs-local midnight flake — passes on CI's UTC runners; ignore it. Any other failure must be fixed.)

- [ ] **Step 2: Invariant + regression sanity**

Confirm: (a) the `award_xp` invariant test is green; (b) existing XP/level/streak/digest/push tests are green (global engagement unchanged); (c) a default (GB, active=home) user sees identical content + progress to before.

- [ ] **Step 3: Push to testing + green CI**

```bash
git push origin testing
```
Watch all 6 CI jobs green (backend runs the migration + full suite).

- [ ] **Step 4: Promote testing → staging → main**

Merge testing → staging (watch CI), then staging → main (watch CI; Railway deploys backend + runs the migration on prod). **This migration adds `user_market_progress` + columns on `users` and `weak_concepts` in prod — before it reaches prod, ASK THE USER whether to snapshot the prod DB first** (standing rule). After deploy, confirm prod `/health` 200 and that `/users/me` returns `active_market_code: "GB"` and `GET /markets` lists the 10 markets.

---

## Self-Review

**Spec coverage:**
- Unit 1 `UserMarketProgress` → Task 1 + Task 2 (migration). ✓
- Unit 2 `active_market_code` → Task 1 (column) + Task 2 (migration) + Task 5 (profile + switch API). ✓
- Unit 3 `WeakConcept.market_code` + per-market Revise → Task 1 (column), Task 2 (migration), Task 4 (tag + filter). ✓
- Unit 4 award seam (5 sites, invariant) → Task 3. ✓
- Unit 5 content gate → active → Task 4. ✓
- Unit 6 APIs (`/markets`, `/me/active-market`, `/me/markets`, profile field) → Task 5. ✓
- Unit 7 migration (table + backfill GB=xp + 2 cols, clean downgrade) → Task 2. ✓
- Non-goals respected (no frontend, no currency-follows-market, no rewards, no un-enroll, streak/coins/goal/caps stay global, LessonCompletion unchanged). ✓
- Testing: model, award+invariant, switch+lazy-enroll, active-market gating, Revise per-market, migration backfill, regression → Tasks 1–6. ✓
- Rollout: snapshot prompt → Task 6 Step 4. ✓

**Placeholder scan:** none — full code for model, migration, seam, router; integration points (5 award sites, 5 gate sites, 2 weak-concept creations, Revise queries, registration enroll) are exact instructions with the precise edit, not deferred work.

**Type/name consistency:** `award_xp(session, progress, amount, *, market_code=None, today=None)` (Task 3) used in Task 3 routing; `ensure_enrolled(session, user_id, market_code)` (Task 3) used in Task 5; `UserMarketProgress(user_id, market_code, xp)` composite PK (Task 1) used in the seam (Task 3), migration (Task 2), and APIs (Task 5); `active_market_code` column (Task 1) → migration (Task 2) → gates (Task 4) → profile/switch (Task 5); `is_module_in_market` (from C1) reused in Task 4; `compute_level` (content_service) used in Task 5. Consistent.
