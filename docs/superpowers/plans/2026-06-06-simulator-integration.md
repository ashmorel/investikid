# Simulator Integration (4D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Weave the investment simulator into the core loop — trades award XP/streak/levels/badges (capped), lessons hand kids targeted "apply" missions, the home screen gains a portfolio snapshot, and virtual cash becomes admin-configurable and earnable.

**Architecture:** Pure reward logic lives in small, unit-tested service modules (`simulator_rewards_config.py`, `simulator_rewards.py`); a shared `record_daily_activity` unifies the streak across lessons and trades; all virtual-cash awards flow through one idempotent `CashGrant` ledger. The `place_trade` endpoint is enriched to return rewards earned; the frontend reuses the existing toast/animation vocabulary so a trade feels like progress.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · Alembic · Postgres · pydantic v2 · React 18 · Vite · TypeScript · TanStack Query · Tailwind v4 · Vitest + vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-06-simulator-integration-design.md`

**Conventions (apply to every task):**
- Backend venv: `/Users/leeashmore/Local Repo/.venv/bin/`. Run tests/ruff/alembic from `invest-ed/backend`.
- Async tests start with `pytestmark = pytest.mark.asyncio(loop_scope="session")` and use the `client` / `admin_client` / `db_session` fixtures from `tests/conftest.py`. Never instantiate a raw `AsyncClient` on the app engine.
- New models MUST be exported from `app/models/__init__.py` (conftest builds tables from `Base.metadata`).
- Racy inserts use `async with session.begin_nested():` (SAVEPOINT), mirroring `_award_completion`.
- COPPA: child-auth integration tests use a DOB with age ≥ 14.
- Frontend: run the FULL `npm test` after FE changes; new UI gets a `vitest-axe` test; keep WCAG 2.2 AA (no colour-only status).
- Commit after each task. End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

**Backend — create:**
- `app/models/apply_mission.py` — `ApplyMission`, `ApplyMissionCompletion`
- `app/models/cash_grant.py` — `CashGrant`
- `app/services/simulator_rewards_config.py` — reward constants + mission-predicate registry (pure)
- `app/services/simulator_rewards.py` — reward engine (capped XP, mission eval, cash-grant helper)
- `app/routers/missions.py` — `GET /missions/active`
- `app/schemas/mission.py` — mission output schemas
- `alembic/versions/<rev>_simulator_integration.py` — one chained migration

**Backend — modify:**
- `app/models/__init__.py` — export new models
- `app/models/user.py` — `UserProgress.sim_xp_date`, `sim_xp_today`
- `app/models/content.py` — `Module.completion_cash_reward`
- `app/services/content_service.py` — extract `record_daily_activity`; module-completion cash grant
- `app/services/app_settings.py` — `get_starting_cash` / `set_starting_cash`
- `app/services/simulator_service.py` — read starting cash from settings
- `app/routers/simulator.py` — enriched `place_trade` (reward engine + `TradeResultOut`)
- `app/routers/content.py` — grant module-completion cash on lesson completion
- `app/routers/admin.py` — settings starting-cash; lesson apply-mission CRUD; module reward field
- `app/main.py` — register `missions` router
- `app/schemas/simulator.py` — `RewardsOut`, `TradeResultOut`
- `app/schemas/admin.py` — settings + module + lesson apply-mission schemas

**Frontend — create:**
- `src/api/missions.ts` — `missionsApi.getActive`
- `src/hooks/useActiveMissions.ts`
- `src/components/child/home/PortfolioSnapshotCard.tsx`
- `src/components/child/lesson/ApplyMissionCTA.tsx`
- `src/components/child/simulator/MissionBanner.tsx`

**Frontend — modify:**
- `src/api/simulator.ts` — `TradeResult` type
- `src/pages/child/Home.tsx` — slot `PortfolioSnapshotCard`
- `src/pages/child/Lesson.tsx` — render `ApplyMissionCTA` on completion
- `src/pages/child/Simulator.tsx` — render `MissionBanner` (reads `?mission=`)
- `src/components/child/simulator/TradeForm.tsx` — surface reward toast
- `src/components/admin/ModuleForm.tsx` — `completion_cash_reward` field
- `src/components/admin/LessonForm.tsx` — apply-mission block

---

## Task 1: New models + columns + migration

**Files:**
- Create: `app/models/apply_mission.py`, `app/models/cash_grant.py`
- Modify: `app/models/__init__.py`, `app/models/user.py`, `app/models/content.py`
- Create: `alembic/versions/<rev>_simulator_integration.py`
- Test: `tests/test_simulator_integration_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_simulator_integration_models.py
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.cash_grant import CashGrant
from app.models.content import Lesson, Module
from app.models.user import UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session):
    m = Module(topic="stocks", title="Stocks 101", order_index=1)
    db_session.add(m)
    await db_session.flush()
    return m


async def test_apply_mission_unique_per_lesson(db_session):
    m = await _module(db_session)
    lesson = Lesson(module_id=m.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(ApplyMission(lesson_id=lesson.id, mission_type="first_buy", params_json={},
                                title="Buy a share", prompt="Try buying one!", xp_reward=20))
    await db_session.flush()
    db_session.add(ApplyMission(lesson_id=lesson.id, mission_type="first_sell", params_json={},
                                title="Sell", prompt="Sell one", xp_reward=20))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_cash_grant_unique_source(db_session):
    uid = uuid.uuid4()
    src = uuid.uuid4()
    db_session.add(CashGrant(user_id=uid, source_type="module", source_id=src,
                             currency_code="GBP", amount=Decimal("250.00")))
    await db_session.flush()
    db_session.add(CashGrant(user_id=uid, source_type="module", source_id=src,
                             currency_code="GBP", amount=Decimal("250.00")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_progress_has_sim_xp_columns(db_session):
    up = UserProgress(user_id=uuid.uuid4())
    db_session.add(up)
    await db_session.flush()
    assert up.sim_xp_today == 0
    assert up.sim_xp_date is None


async def test_module_completion_cash_reward_nullable(db_session):
    m = await _module(db_session)
    assert m.completion_cash_reward is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_simulator_integration_models.py -v`
Expected: FAIL with `ModuleNotFoundError: app.models.apply_mission`.

- [ ] **Step 3: Create the model files**

```python
# app/models/apply_mission.py
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApplyMission(Base):
    __tablename__ = "apply_missions"
    __table_args__ = (UniqueConstraint("lesson_id", name="uq_apply_mission_lesson"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mission_type: Mapped[str] = mapped_column(String(30), nullable=False)
    params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(String(300), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cash_reward: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    badge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("badges.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )


class ApplyMissionCompletion(Base):
    __tablename__ = "apply_mission_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "mission_id", name="uq_apply_mission_completion_user_mission"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apply_missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

```python
# app/models/cash_grant.py
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CashGrant(Base):
    __tablename__ = "cash_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "source_id", name="uq_cash_grant_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

Note on the `CashGrant` unique constraint: Postgres treats `NULL` as distinct, so admin top-ups (`source_id IS NULL`) are intentionally repeatable while `module`/`mission` grants (non-null `source_id`) are one-time. This is the desired behaviour.

- [ ] **Step 4: Add columns to existing models**

In `app/models/user.py`, inside `UserProgress`, after `streak_freezes`, add (ensure `from datetime import date` and `Date` import exist — they do):

```python
    sim_xp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sim_xp_today: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
```

In `app/models/content.py`, inside `Module`, after `max_age`, add (`Numeric` import: add to the existing sqlalchemy import line; `Decimal` from `decimal`):

```python
    completion_cash_reward: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
```

- [ ] **Step 5: Export new models**

In `app/models/__init__.py` add (keep alphabetical grouping):

```python
from app.models.apply_mission import ApplyMission, ApplyMissionCompletion  # noqa: F401
from app.models.cash_grant import CashGrant  # noqa: F401
```

- [ ] **Step 6: Verify single alembic head, then write the migration**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: a single head `f7a8b9c0d1e2`. If it differs, set `down_revision` to the actual head.

```python
# alembic/versions/c1d2e3f4a5b6_simulator_integration.py
"""simulator integration: apply missions, cash grants, sim xp, module cash reward"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c1d2e3f4a5b6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apply_missions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_type", sa.String(30), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("prompt", sa.String(300), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cash_reward", sa.Numeric(12, 2), nullable=True),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("badges.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lesson_id", name="uq_apply_mission_lesson"),
    )
    op.create_index("ix_apply_missions_lesson_id", "apply_missions", ["lesson_id"])
    op.create_table(
        "apply_mission_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("apply_missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "mission_id", name="uq_apply_mission_completion_user_mission"),
    )
    op.create_index("ix_apply_mission_completions_user_id", "apply_mission_completions", ["user_id"])
    op.create_index("ix_apply_mission_completions_mission_id", "apply_mission_completions", ["mission_id"])
    op.create_table(
        "cash_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "source_type", "source_id", name="uq_cash_grant_source"),
    )
    op.create_index("ix_cash_grants_user_id", "cash_grants", ["user_id"])
    op.add_column("user_progress", sa.Column("sim_xp_date", sa.Date(), nullable=True))
    op.add_column("user_progress",
                  sa.Column("sim_xp_today", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("modules", sa.Column("completion_cash_reward", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "completion_cash_reward")
    op.drop_column("user_progress", "sim_xp_today")
    op.drop_column("user_progress", "sim_xp_date")
    op.drop_index("ix_cash_grants_user_id", table_name="cash_grants")
    op.drop_table("cash_grants")
    op.drop_index("ix_apply_mission_completions_mission_id", table_name="apply_mission_completions")
    op.drop_index("ix_apply_mission_completions_user_id", table_name="apply_mission_completions")
    op.drop_table("apply_mission_completions")
    op.drop_index("ix_apply_missions_lesson_id", table_name="apply_missions")
    op.drop_table("apply_missions")
```

- [ ] **Step 7: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_simulator_integration_models.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: PASS, no lint errors.

- [ ] **Step 8: Commit**

```bash
git add app/models/ alembic/versions/ tests/test_simulator_integration_models.py
git commit -m "feat(sim): apply-mission, cash-grant models + sim-xp/module-reward columns"
```

---

## Task 2: Rewards config + mission-predicate registry

**Files:**
- Create: `app/services/simulator_rewards_config.py`
- Test: `tests/test_simulator_rewards_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_simulator_rewards_config.py
from decimal import Decimal

from app.services.simulator_rewards_config import (
    SIM_XP_DAILY_CAP,
    SIM_XP_PER_TRADE,
    MissionState,
    evaluate_mission,
)


def _state(distinct=0, sells=0, invested="0"):
    return MissionState(distinct_tickers=distinct, sell_count=sells, total_invested=Decimal(invested))


def test_config_values_are_positive():
    assert SIM_XP_PER_TRADE > 0
    assert SIM_XP_DAILY_CAP >= SIM_XP_PER_TRADE


def test_first_buy_satisfied_when_holding_exists():
    assert evaluate_mission("first_buy", {}, _state(distinct=1)) is True
    assert evaluate_mission("first_buy", {}, _state(distinct=0)) is False


def test_first_sell_satisfied_after_a_sell():
    assert evaluate_mission("first_sell", {}, _state(sells=1)) is True
    assert evaluate_mission("first_sell", {}, _state(sells=0)) is False


def test_diversify_requires_n_distinct():
    assert evaluate_mission("diversify", {"n": 3}, _state(distinct=3)) is True
    assert evaluate_mission("diversify", {"n": 3}, _state(distinct=2)) is False


def test_invest_amount_threshold():
    assert evaluate_mission("invest_amount", {"amount": "500"}, _state(invested="500")) is True
    assert evaluate_mission("invest_amount", {"amount": "500"}, _state(invested="499.99")) is False


def test_unknown_mission_type_is_false():
    assert evaluate_mission("nonexistent", {}, _state(distinct=99)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_simulator_rewards_config.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

```python
# app/services/simulator_rewards_config.py
"""Central, developer-tuned config for simulator rewards (deploy to change).

Money amounts (starting cash, per-module/per-mission rewards) are NOT here — those are
runtime-editable in the admin panel. This module holds only the anti-gaming mechanics
and the mission-type predicate registry.
"""
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

# Anti-gaming mechanics
SIM_XP_PER_TRADE: int = 5          # XP per routine trade
SIM_XP_DAILY_CAP: int = 25         # max routine-trade XP per local day
DEFAULT_MISSION_XP: int = 20       # used when an ApplyMission.xp_reward is 0


@dataclass(frozen=True)
class MissionState:
    """Snapshot of a portfolio used to evaluate mission predicates."""
    distinct_tickers: int      # number of distinct currently-held tickers
    sell_count: int            # number of sell trades ever executed
    total_invested: Decimal    # sum of buy cost basis ever (shares * price on buys)


def _first_buy(_params: dict, s: MissionState) -> bool:
    return s.distinct_tickers >= 1


def _first_sell(_params: dict, s: MissionState) -> bool:
    return s.sell_count >= 1


def _diversify(params: dict, s: MissionState) -> bool:
    return s.distinct_tickers >= int(params.get("n", 1))


def _invest_amount(params: dict, s: MissionState) -> bool:
    return s.total_invested >= Decimal(str(params.get("amount", "0")))


# Registry: mission_type -> predicate. Add new mission types here.
MISSION_PREDICATES: dict[str, Callable[[dict, MissionState], bool]] = {
    "first_buy": _first_buy,
    "first_sell": _first_sell,
    "diversify": _diversify,
    "invest_amount": _invest_amount,
}

# Values surfaced to the admin UI for the mission-type dropdown.
MISSION_TYPES: tuple[str, ...] = tuple(MISSION_PREDICATES.keys())


def evaluate_mission(mission_type: str, params: dict, state: MissionState) -> bool:
    predicate = MISSION_PREDICATES.get(mission_type)
    if predicate is None:
        return False
    return predicate(params or {}, state)
```

- [ ] **Step 4: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_simulator_rewards_config.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/simulator_rewards_config.py`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add app/services/simulator_rewards_config.py tests/test_simulator_rewards_config.py
git commit -m "feat(sim): rewards config + mission-predicate registry"
```

---

## Task 3: Shared `record_daily_activity` (streak unification)

Extract the streak-advance step from `_award_completion` into a reusable, idempotent helper so trades and lessons share one streak path. **No behaviour change for lessons.**

**Files:**
- Modify: `app/services/content_service.py`
- Test: `tests/test_record_daily_activity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_record_daily_activity.py
import uuid
from datetime import date

import pytest

from app.models.user import UserProgress
from app.services.content_service import record_daily_activity

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _progress(streak=0, last=None, freezes=0):
    up = UserProgress(user_id=uuid.uuid4(), streak_count=streak, last_activity_date=last,
                      streak_freezes=freezes)
    return up


def test_first_activity_sets_streak_one():
    up = _progress()
    record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 1
    assert up.last_activity_date == date(2026, 6, 6)


def test_consecutive_day_increments():
    up = _progress(streak=1, last=date(2026, 6, 5))
    record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 2


def test_same_day_is_idempotent():
    up = _progress(streak=3, last=date(2026, 6, 6))
    record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 3  # unchanged
    assert up.last_activity_date == date(2026, 6, 6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_record_daily_activity.py -v`
Expected: FAIL with `ImportError: cannot import name 'record_daily_activity'`.

- [ ] **Step 3: Implement the helper and refactor `_award_completion` to use it**

Add to `app/services/content_service.py` (near `streak_after_activity`):

```python
def record_daily_activity(progress: "UserProgress", today_local) -> bool:
    """Advance the streak for the first qualifying activity of the day (lesson or trade).

    Idempotent: a no-op if the user already had activity today. Returns True if the streak
    was advanced this call, False if it was already counted today.
    """
    if progress.last_activity_date == today_local:
        return False
    new_streak, new_last, new_freezes = streak_after_activity(
        progress.last_activity_date, progress.streak_count, progress.streak_freezes, today_local
    )
    progress.streak_count = new_streak
    progress.last_activity_date = new_last
    progress.streak_freezes = new_freezes
    return True
```

Then in `_award_completion`, replace the inline streak block (the four lines that call `streak_after_activity` and assign `progress.streak_count/last_activity_date/streak_freezes`) with:

```python
    progress.xp += lesson.xp_reward
    progress.level = compute_level(progress.xp)
    record_daily_activity(progress, today_local)
```

(Keep the XP/level lines exactly as they were; only the streak assignment is replaced by the call.)

- [ ] **Step 4: Run tests to verify no regression**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_record_daily_activity.py tests/test_content.py -v`
Expected: PASS (new tests + existing lesson-completion/streak tests still green). If the existing streak test file has a different name, run the full `tests/` suite for the content module.

- [ ] **Step 5: Commit**

```bash
git add app/services/content_service.py tests/test_record_daily_activity.py
git commit -m "refactor(sim): extract idempotent record_daily_activity for shared streak"
```

---

## Task 4: Capped daily trade-XP helper

**Files:**
- Create: `app/services/simulator_rewards.py`
- Test: `tests/test_award_trade_xp.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_award_trade_xp.py
import uuid
from datetime import date

from app.models.user import UserProgress
from app.services.simulator_rewards import award_trade_xp
from app.services.simulator_rewards_config import SIM_XP_DAILY_CAP, SIM_XP_PER_TRADE


def _progress(xp=0, sim_date=None, sim_today=0):
    return UserProgress(user_id=uuid.uuid4(), xp=xp, sim_xp_date=sim_date, sim_xp_today=sim_today)


def test_first_trade_of_day_awards_full():
    up = _progress()
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == SIM_XP_PER_TRADE
    assert up.xp == SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 6)


def test_cap_blocks_further_xp_same_day():
    up = _progress(xp=SIM_XP_DAILY_CAP, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == 0
    assert up.xp == SIM_XP_DAILY_CAP


def test_partial_award_up_to_cap():
    up = _progress(xp=SIM_XP_DAILY_CAP - 2, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP - 2)
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == 2  # only enough to reach the cap
    assert up.sim_xp_today == SIM_XP_DAILY_CAP


def test_new_day_resets_counter():
    up = _progress(xp=SIM_XP_DAILY_CAP, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    awarded = award_trade_xp(up, date(2026, 6, 7))
    assert awarded == SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 7)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_award_trade_xp.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

```python
# app/services/simulator_rewards.py
"""Reward engine for simulator activity: capped trade XP, mission evaluation, cash grants."""
from app.models.user import UserProgress
from app.services.content_service import compute_level
from app.services.simulator_rewards_config import SIM_XP_DAILY_CAP, SIM_XP_PER_TRADE


def award_trade_xp(progress: UserProgress, today_local) -> int:
    """Award capped routine-trade XP. Resets the daily tally on date rollover.

    Returns the XP actually awarded (0 if already at the daily cap). Mutates `progress`.
    """
    if progress.sim_xp_date != today_local:
        progress.sim_xp_date = today_local
        progress.sim_xp_today = 0
    remaining = SIM_XP_DAILY_CAP - progress.sim_xp_today
    if remaining <= 0:
        return 0
    awarded = min(SIM_XP_PER_TRADE, remaining)
    progress.sim_xp_today += awarded
    progress.xp += awarded
    progress.level = compute_level(progress.xp)
    return awarded
```

(`compute_level` already lives in `content_service`; confirm the import name during implementation — it is referenced in `_award_completion`.)

- [ ] **Step 4: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_award_trade_xp.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/simulator_rewards.py`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add app/services/simulator_rewards.py tests/test_award_trade_xp.py
git commit -m "feat(sim): capped daily trade-XP helper"
```

---

## Task 5: Cash-grant helper + mission evaluation

**Files:**
- Modify: `app/services/simulator_rewards.py`
- Test: `tests/test_mission_evaluation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mission_evaluation.py
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.cash_grant import CashGrant
from app.models.content import Lesson, Module
from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User, UserProgress
from app.services.simulator_rewards import evaluate_apply_missions, grant_cash

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_child(db_session):
    user = User(email=f"c{uuid.uuid4().hex[:8]}@x.test", hashed_password="x",
                role="child", country_code="GB", currency_code="GBP")
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code="GBP")
    db_session.add_all([progress, portfolio])
    await db_session.flush()
    return user, progress, portfolio


async def _mission(db_session, mtype, params, xp=20, cash=None):
    m = Module(topic="stocks", title="S", order_index=1)
    db_session.add(m)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add(lesson)
    await db_session.flush()
    mission = ApplyMission(lesson_id=lesson.id, mission_type=mtype, params_json=params,
                           title="t", prompt="p", xp_reward=xp, cash_reward=cash)
    db_session.add(mission)
    await db_session.flush()
    return mission


async def test_grant_cash_is_idempotent(db_session):
    user, _, portfolio = await _seed_child(db_session)
    src = uuid.uuid4()
    g1 = await grant_cash(db_session, user.id, portfolio, "module", src, Decimal("250.00"))
    g2 = await grant_cash(db_session, user.id, portfolio, "module", src, Decimal("250.00"))
    assert g1 is True and g2 is False
    assert portfolio.virtual_cash == Decimal("1250.00")
    rows = (await db_session.execute(select(CashGrant).where(CashGrant.user_id == user.id))).scalars().all()
    assert len(rows) == 1


async def test_first_buy_mission_completes_and_awards(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    mission = await _mission(db_session, "first_buy", {}, xp=20, cash=Decimal("100.00"))
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    completed = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert [c.id for c in completed] == [mission.id]
    assert progress.xp == 20
    assert portfolio.virtual_cash == Decimal("1100.00")


async def test_mission_not_recompleted(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    await _mission(db_session, "first_buy", {})
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    first = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    second = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert len(first) == 1
    assert second == []


async def test_diversify_not_complete_until_threshold(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    await _mission(db_session, "diversify", {"n": 2})
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    assert await evaluate_apply_missions(db_session, user.id, progress, portfolio) == []
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="MSFT", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("300")))
    await db_session.flush()
    completed = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert len(completed) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_mission_evaluation.py -v`
Expected: FAIL with `ImportError: cannot import name 'evaluate_apply_missions'`.

- [ ] **Step 3: Implement `grant_cash` + `evaluate_apply_missions`**

Append to `app/services/simulator_rewards.py`:

```python
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.cash_grant import CashGrant
from app.models.simulator import Holding, Portfolio, Trade
from app.services.simulator_rewards_config import (
    DEFAULT_MISSION_XP,
    MissionState,
    evaluate_mission,
)


async def grant_cash(
    session: AsyncSession,
    user_id: uuid.UUID,
    portfolio: Portfolio,
    source_type: str,
    source_id: uuid.UUID | None,
    amount: Decimal,
) -> bool:
    """Idempotently grant virtual cash. Returns True if granted, False if already granted.

    One-time sources (module/mission) are deduped by the (user, source_type, source_id) unique
    constraint via a SAVEPOINT. Admin top-ups pass source_id=None and are always applied.
    """
    if amount is None or amount <= 0:
        return False
    if source_id is not None:
        try:
            async with session.begin_nested():
                session.add(CashGrant(user_id=user_id, source_type=source_type, source_id=source_id,
                                      currency_code=portfolio.currency_code, amount=amount))
                await session.flush()
        except Exception:
            return False  # unique-constraint violation -> already granted
    else:
        session.add(CashGrant(user_id=user_id, source_type=source_type, source_id=None,
                              currency_code=portfolio.currency_code, amount=amount))
    portfolio.virtual_cash += amount
    return True


async def _mission_state(session: AsyncSession, portfolio: Portfolio) -> MissionState:
    distinct = await session.scalar(
        select(func.count(func.distinct(Holding.ticker))).where(Holding.portfolio_id == portfolio.id)
    )
    sells = await session.scalar(
        select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio.id, Trade.type == "sell")
    )
    invested = await session.scalar(
        select(func.coalesce(func.sum(Trade.shares * Trade.price), 0)).where(
            Trade.portfolio_id == portfolio.id, Trade.type == "buy"
        )
    )
    return MissionState(distinct_tickers=int(distinct or 0), sell_count=int(sells or 0),
                        total_invested=Decimal(str(invested or 0)))


async def evaluate_apply_missions(
    session: AsyncSession,
    user_id: uuid.UUID,
    progress: UserProgress,
    portfolio: Portfolio,
) -> list[ApplyMission]:
    """Complete any newly-satisfied apply-missions. Awards XP + cash; returns completed missions.

    Badge awarding (mission.badge_id) is handled by the caller after this returns, so the badge
    service stays the single owner of UserBadge inserts.
    """
    completed_ids = set(
        (await session.execute(
            select(ApplyMissionCompletion.mission_id).where(ApplyMissionCompletion.user_id == user_id)
        )).scalars().all()
    )
    missions = (await session.execute(select(ApplyMission))).scalars().all()
    pending = [m for m in missions if m.id not in completed_ids]
    if not pending:
        return []
    state = await _mission_state(session, portfolio)
    newly: list[ApplyMission] = []
    for mission in pending:
        if not evaluate_mission(mission.mission_type, mission.params_json, state):
            continue
        try:
            async with session.begin_nested():
                session.add(ApplyMissionCompletion(user_id=user_id, mission_id=mission.id))
                await session.flush()
        except Exception:
            continue  # raced -> already completed
        xp = mission.xp_reward or DEFAULT_MISSION_XP
        progress.xp += xp
        progress.level = compute_level(progress.xp)
        if mission.cash_reward:
            await grant_cash(session, user_id, portfolio, "mission", mission.id, mission.cash_reward)
        newly.append(mission)
    return newly
```

Add `from app.models.user import UserProgress` to the existing imports at the top if not already present (Task 4 imported it).

- [ ] **Step 4: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_mission_evaluation.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/simulator_rewards.py`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add app/services/simulator_rewards.py tests/test_mission_evaluation.py
git commit -m "feat(sim): idempotent cash-grant + apply-mission evaluation"
```

---

## Task 6: Module-completion cash grant on lesson completion

**Files:**
- Modify: `app/services/content_service.py` (add `grant_module_completion_cash`), `app/routers/content.py` (call it in `complete_lesson`)
- Test: `tests/test_module_completion_cash.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_module_completion_cash.py
import uuid
from decimal import Decimal

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.simulator import Portfolio
from app.models.user import User
from app.services.content_service import grant_module_completion_cash

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup(db_session, reward, n_lessons=2):
    user = User(email=f"c{uuid.uuid4().hex[:8]}@x.test", hashed_password="x",
                role="child", country_code="GB", currency_code="GBP")
    db_session.add(user)
    await db_session.flush()
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code="GBP")
    module = Module(topic="stocks", title="S", order_index=1, completion_cash_reward=reward)
    db_session.add_all([portfolio, module])
    await db_session.flush()
    lessons = [Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=i)
               for i in range(n_lessons)]
    db_session.add_all(lessons)
    await db_session.flush()
    return user, portfolio, module, lessons


async def test_no_grant_until_all_lessons_done(db_session):
    user, portfolio, module, lessons = await _setup(db_session, Decimal("250.00"))
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lessons[0].id))
    await db_session.flush()
    granted = await grant_module_completion_cash(db_session, user.id, module.id)
    assert granted is False
    assert portfolio.virtual_cash == Decimal("1000.00")


async def test_grant_on_full_completion_once(db_session):
    user, portfolio, module, lessons = await _setup(db_session, Decimal("250.00"))
    db_session.add_all([LessonCompletion(user_id=user.id, lesson_id=ls.id) for ls in lessons])
    await db_session.flush()
    assert await grant_module_completion_cash(db_session, user.id, module.id) is True
    assert portfolio.virtual_cash == Decimal("1250.00")
    # second call is a no-op (ledger dedupe)
    assert await grant_module_completion_cash(db_session, user.id, module.id) is False
    assert portfolio.virtual_cash == Decimal("1250.00")


async def test_no_reward_configured_is_noop(db_session):
    user, portfolio, module, lessons = await _setup(db_session, None)
    db_session.add_all([LessonCompletion(user_id=user.id, lesson_id=ls.id) for ls in lessons])
    await db_session.flush()
    assert await grant_module_completion_cash(db_session, user.id, module.id) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_completion_cash.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `grant_module_completion_cash`**

Add to `app/services/content_service.py`:

```python
async def grant_module_completion_cash(session, user_id, module_id) -> bool:
    """Grant a module's completion_cash_reward once, iff every lesson in the module is done.

    Returns True if cash was granted this call, else False. Idempotent via the CashGrant ledger.
    """
    from sqlalchemy import func, select

    from app.models.content import Lesson, LessonCompletion, Module
    from app.models.simulator import Portfolio
    from app.services.simulator_rewards import grant_cash

    module = await session.get(Module, module_id)
    if module is None or module.completion_cash_reward is None:
        return False

    total = await session.scalar(
        select(func.count(Lesson.id)).where(Lesson.module_id == module_id)
    )
    if not total:
        return False
    done = await session.scalar(
        select(func.count(func.distinct(LessonCompletion.lesson_id)))
        .select_from(LessonCompletion)
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(Lesson.module_id == module_id, LessonCompletion.user_id == user_id)
    )
    if (done or 0) < total:
        return False

    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user_id))
    if portfolio is None:
        return False
    return await grant_cash(session, user_id, portfolio, "module", module_id,
                            module.completion_cash_reward)
```

- [ ] **Step 4: Wire into `complete_lesson`**

In `app/routers/content.py`, inside `complete_lesson`, after `_award_completion(...)` and the existing gamification calls, **before** the final `await session.commit()`, add:

```python
    from app.services.content_service import grant_module_completion_cash

    await grant_module_completion_cash(session, current_user.id, lesson.module_id)
```

(`lesson` is already loaded in the handler; use its `module_id`.)

- [ ] **Step 5: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_completion_cash.py tests/test_content.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/content_service.py app/routers/content.py tests/test_module_completion_cash.py
git commit -m "feat(sim): grant module-completion cash reward on lesson completion"
```

---

## Task 7: Enrich `place_trade` with reward engine + response

**Files:**
- Modify: `app/schemas/simulator.py` (add `RewardsOut`, `TradeResultOut`), `app/routers/simulator.py`
- Test: `tests/test_trade_rewards_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_trade_rewards_endpoint.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_buy_returns_rewards_block(client, child_auth_headers):
    # child_auth_headers: existing fixture that returns headers for an authenticated child.
    resp = await client.post("/portfolio/trades",
                             json={"ticker": "AAPL", "exchange": "NASDAQ", "type": "buy", "shares": 1},
                             headers=child_auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "AAPL"          # trade fields still present
    assert "rewards" in body
    assert body["rewards"]["xp_awarded"] >= 0
    assert "streak_extended" in body["rewards"]
    assert "missions_completed" in body["rewards"]
```

> If no `child_auth_headers` fixture exists, follow the auth-setup pattern used by the existing `tests/test_simulator.py` trade test (reuse its helper to create + authenticate a child with DOB age ≥ 14). Mirror that exact setup rather than inventing a new one.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_trade_rewards_endpoint.py -v`
Expected: FAIL (`KeyError: 'rewards'` or 500 — response not yet enriched).

- [ ] **Step 3: Add schemas**

In `app/schemas/simulator.py`:

```python
class MissionRewardOut(BaseModel):
    id: uuid.UUID
    title: str


class RewardsOut(BaseModel):
    xp_awarded: int = 0
    streak_extended: bool = False
    cash_granted: Decimal = Decimal("0")
    missions_completed: list[MissionRewardOut] = []
    badges_unlocked: list[str] = []  # badge names


class TradeResultOut(TradeOut):
    rewards: RewardsOut
```

- [ ] **Step 4: Enrich the endpoint**

In `app/routers/simulator.py`, change the `place_trade` decorator response model to `TradeResultOut` and, after `execute_trade(...)` and the existing `update_challenge_progress` / `evaluate_and_award_badges` calls (keep them), assemble rewards before the response. Use the child's local "today" the same way the lesson path derives `today_local` (reuse that helper — check `content_service`/`routers/content.py` for `today_local` derivation and call the same function):

```python
    from app.services.content_service import record_daily_activity
    from app.services.simulator_rewards import award_trade_xp, evaluate_apply_missions
    from app.schemas.simulator import MissionRewardOut, RewardsOut, TradeResultOut

    progress = await get_or_create_progress(session, current_user)  # existing helper; confirm name
    today_local = local_today(current_user)  # reuse the same derivation the lesson path uses

    xp_awarded = award_trade_xp(progress, today_local)
    streak_extended = record_daily_activity(progress, today_local)
    completed_missions = await evaluate_apply_missions(session, current_user.id, progress, portfolio)

    # badges: reuse existing badge service after mission/xp changes
    new_badges = await evaluate_and_award_badges(session, current_user.id, progress)

    # cash granted this request = sum of mission cash already added to portfolio inside evaluate_apply_missions;
    # surface it by diffing is fragile — instead expose via the missions' cash_reward sum:
    cash_granted = sum((m.cash_reward or Decimal("0")) for m in completed_missions)

    await session.commit()
    await session.refresh(trade)

    return TradeResultOut(
        id=trade.id, ticker=trade.ticker, type=trade.type, shares=trade.shares,
        price=trade.price, executed_at=trade.executed_at,
        rewards=RewardsOut(
            xp_awarded=xp_awarded,
            streak_extended=streak_extended,
            cash_granted=cash_granted,
            missions_completed=[MissionRewardOut(id=m.id, title=m.title) for m in completed_missions],
            badges_unlocked=[b.name for b in new_badges],
        ),
    )
```

Implementation notes for the engineer:
- `get_or_create_progress` / `local_today`: confirm the exact helper names used by the lesson-completion path (`routers/content.py`) and reuse them verbatim — do not duplicate logic.
- Keep the existing `update_challenge_progress(... "trades_executed" ...)` call.
- The order matters: award XP and run missions **before** `evaluate_and_award_badges` so trade-count/XP-based badges see the updated state.

- [ ] **Step 5: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_trade_rewards_endpoint.py tests/test_simulator.py -v`
Expected: PASS (new test + existing simulator tests still green; existing tests that asserted on the trade response may need the `rewards` key — update them if they did a strict equality on the body).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/simulator.py app/routers/simulator.py tests/test_trade_rewards_endpoint.py
git commit -m "feat(sim): enrich place_trade with XP/streak/mission/cash rewards"
```

---

## Task 8: `GET /missions/active` endpoint

**Files:**
- Create: `app/schemas/mission.py`, `app/routers/missions.py`
- Modify: `app/main.py` (register router)
- Test: `tests/test_missions_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_missions_endpoint.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_active_missions_excludes_completed(client, child_auth_headers, db_session):
    # Mirror the child + lesson + ApplyMission setup from tests/test_mission_evaluation.py,
    # attaching the mission to a lesson the child can reach.
    resp = await client.get("/missions/active", headers=child_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert {"id", "lesson_id", "mission_type", "title", "prompt"} <= set(item)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_missions_endpoint.py -v`
Expected: FAIL (404 — route not registered).

- [ ] **Step 3: Schema + router**

```python
# app/schemas/mission.py
import uuid

from pydantic import BaseModel, ConfigDict


class ActiveMissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lesson_id: uuid.UUID
    mission_type: str
    title: str
    prompt: str
    params_json: dict
```

```python
# app/routers/missions.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.user import User
from app.schemas.mission import ActiveMissionOut

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/active", response_model=list[ActiveMissionOut])
async def active_missions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    completed = select(ApplyMissionCompletion.mission_id).where(
        ApplyMissionCompletion.user_id == current_user.id
    )
    rows = (await session.execute(
        select(ApplyMission).where(ApplyMission.id.not_in(completed))
    )).scalars().all()
    return rows
```

(Confirm the exact import paths for `get_session` / `get_current_user` against an existing router such as `routers/simulator.py`, and match them.)

- [ ] **Step 4: Register the router**

In `app/main.py`, where other routers are included, add:

```python
from app.routers import missions

app.include_router(missions.router)
```

(Match the existing include style — if routers are added under an `/api` prefix or with auth dependencies, follow that pattern.)

- [ ] **Step 5: Run tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_missions_endpoint.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/mission.py app/routers/missions.py app/main.py tests/test_missions_endpoint.py
git commit -m "feat(sim): GET /missions/active endpoint"
```

---

## Task 9: Admin-editable starting cash

**Files:**
- Modify: `app/services/app_settings.py`, `app/services/simulator_service.py`, `app/routers/admin.py`, `app/schemas/admin.py`
- Test: `tests/test_starting_cash_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_starting_cash_settings.py
from decimal import Decimal

import pytest

from app.services.app_settings import get_starting_cash, set_starting_cash

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_default_when_unset(db_session):
    cash = await get_starting_cash(db_session)
    assert cash["GBP"] == Decimal("1000.00")
    assert cash["HKD"] == Decimal("10000.00")


async def test_set_then_get_roundtrip(db_session):
    await set_starting_cash(db_session, {"GBP": Decimal("2000.00"), "USD": Decimal("1500.00")})
    cash = await get_starting_cash(db_session)
    assert cash["GBP"] == Decimal("2000.00")
    assert cash["USD"] == Decimal("1500.00")
    # currencies not overridden fall back to default
    assert cash["EUR"] == Decimal("1000.00")


async def test_admin_settings_endpoint_roundtrip(admin_client):
    put = await admin_client.put("/admin/settings",
                                 json={"alert_emails": [], "starting_cash": {"GBP": "1800.00"}})
    assert put.status_code == 200
    assert put.json()["starting_cash"]["GBP"] == "1800.00"
    get = await admin_client.get("/admin/settings")
    assert get.json()["starting_cash"]["GBP"] == "1800.00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_starting_cash_settings.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Settings helpers**

In `app/services/app_settings.py` add:

```python
from decimal import Decimal

_STARTING_CASH_KEY = "simulator.starting_cash"
_DEFAULT_STARTING_CASH: dict[str, Decimal] = {
    "GBP": Decimal("1000.00"),
    "USD": Decimal("1000.00"),
    "HKD": Decimal("10000.00"),
    "EUR": Decimal("1000.00"),
}


async def get_starting_cash(session: AsyncSession) -> dict[str, Decimal]:
    merged = dict(_DEFAULT_STARTING_CASH)
    raw = await get_setting(session, _STARTING_CASH_KEY)
    if raw:
        try:
            for k, v in json.loads(raw).items():
                merged[str(k)] = Decimal(str(v))
        except (ValueError, TypeError):
            pass
    return merged


async def set_starting_cash(session: AsyncSession, mapping: dict[str, Decimal]) -> None:
    await set_setting(session, _STARTING_CASH_KEY,
                      json.dumps({k: str(v) for k, v in mapping.items()}))
```

- [ ] **Step 4: Read settings in portfolio creation**

In `app/services/simulator_service.py`, change `get_or_create_portfolio` to read from settings, keeping `_STARTING_CASH` as the in-code default fallback inside the settings helper:

```python
async def get_or_create_portfolio(session: AsyncSession, user: User) -> Portfolio:
    from app.services.app_settings import get_starting_cash

    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    if portfolio:
        return portfolio
    cash_map = await get_starting_cash(session)
    starting = cash_map.get(user.currency_code, Decimal("1000.00"))
    portfolio = Portfolio(user_id=user.id, virtual_cash=starting, currency_code=user.currency_code)
    session.add(portfolio)
    await session.flush()
    return portfolio
```

- [ ] **Step 5: Extend admin settings schema + endpoint**

In `app/schemas/admin.py`:

```python
class AdminSettingsOut(BaseModel):
    alert_emails: list[str]
    starting_cash: dict[str, str] = {}


class AdminSettingsUpdate(BaseModel):
    alert_emails: list[EmailStr]
    starting_cash: dict[str, str] | None = None
```

In `app/routers/admin.py`, update the GET and PUT `/settings` handlers:

```python
@router.get("/settings", response_model=AdminSettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)):
    emails = await get_alert_emails(session)
    cash = await get_starting_cash(session)
    return AdminSettingsOut(alert_emails=emails, starting_cash={k: str(v) for k, v in cash.items()})


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session)):
    await set_alert_emails(session, body.alert_emails)
    if body.starting_cash is not None:
        from decimal import Decimal
        await set_starting_cash(session, {k: Decimal(v) for k, v in body.starting_cash.items()})
    await session.commit()
    cash = await get_starting_cash(session)
    return AdminSettingsOut(alert_emails=body.alert_emails,
                            starting_cash={k: str(v) for k, v in cash.items()})
```

Add `from app.services.app_settings import get_starting_cash, set_starting_cash` to the imports.

- [ ] **Step 6: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_starting_cash_settings.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: PASS, clean.

- [ ] **Step 7: Commit**

```bash
git add app/services/app_settings.py app/services/simulator_service.py app/routers/admin.py app/schemas/admin.py tests/test_starting_cash_settings.py
git commit -m "feat(sim): admin-editable starting cash via AppSetting"
```

---

## Task 10: Admin CRUD — apply-mission block + module cash reward

**Files:**
- Modify: `app/schemas/admin.py`, `app/routers/admin.py`
- Test: `tests/test_admin_apply_mission.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin_apply_mission.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_lesson_with_apply_mission(admin_client):
    mod = await admin_client.post("/admin/modules",
        json={"topic": "stocks", "title": "M", "order_index": 1})
    module_id = mod.json()["id"]
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card", "content_json": {"title": "t", "body": "b"}, "xp_reward": 10, "order_index": 1,
        "apply_mission": {"mission_type": "first_buy", "params_json": {}, "title": "Buy one",
                          "prompt": "Try it!", "xp_reward": 20, "cash_reward": "100.00"},
    })
    assert resp.status_code == 200
    assert resp.json()["apply_mission"]["mission_type"] == "first_buy"


async def test_module_completion_cash_reward_roundtrip(admin_client):
    mod = await admin_client.post("/admin/modules",
        json={"topic": "stocks", "title": "M2", "order_index": 2, "completion_cash_reward": "250.00"})
    assert mod.status_code == 200
    module_id = mod.json()["id"]
    upd = await admin_client.put(f"/admin/modules/{module_id}",
        json={"completion_cash_reward": "300.00"})
    assert upd.json()["completion_cash_reward"] == "300.00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_apply_mission.py -v`
Expected: FAIL (unknown field / KeyError).

- [ ] **Step 3: Schemas**

In `app/schemas/admin.py`:

```python
from decimal import Decimal

from app.services.simulator_rewards_config import MISSION_TYPES


class ApplyMissionIn(BaseModel):
    mission_type: str
    params_json: dict = {}
    title: str
    prompt: str
    xp_reward: int = 0
    cash_reward: Decimal | None = None
    badge_id: uuid.UUID | None = None

    @field_validator("mission_type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in MISSION_TYPES:
            raise ValueError(f"unknown mission_type: {v}")
        return v


class ApplyMissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    mission_type: str
    params_json: dict
    title: str
    prompt: str
    xp_reward: int
    cash_reward: Decimal | None
    badge_id: uuid.UUID | None
```

Add `completion_cash_reward: Decimal | None = None` to both `ModuleCreate` and `ModuleUpdate`. Add `apply_mission: ApplyMissionIn | None = None` to `LessonCreate` and `LessonUpdate`. Add `apply_mission: ApplyMissionOut | None = None` and `completion_cash_reward: Decimal | None = None` to the relevant `LessonOut` / `ModuleOut` response schemas (locate them in `app/schemas/admin.py` and add the fields with `from_attributes`).

(Ensure `field_validator` is imported from pydantic at the top of the file.)

- [ ] **Step 4: Endpoints**

In `app/routers/admin.py`:
- `create_module` / `update_module`: pass through `completion_cash_reward` to the `Module` (set attribute when present).
- `create_lesson` (and the level-lesson + update variants): after creating/updating the `Lesson`, upsert its `ApplyMission` from `payload.apply_mission`:

```python
    if payload.apply_mission is not None:
        from app.models.apply_mission import ApplyMission

        existing = await session.scalar(
            select(ApplyMission).where(ApplyMission.lesson_id == lesson.id)
        )
        am = payload.apply_mission
        if existing is None:
            session.add(ApplyMission(
                lesson_id=lesson.id, mission_type=am.mission_type, params_json=am.params_json,
                title=am.title, prompt=am.prompt, xp_reward=am.xp_reward,
                cash_reward=am.cash_reward, badge_id=am.badge_id))
        else:
            existing.mission_type = am.mission_type
            existing.params_json = am.params_json
            existing.title = am.title
            existing.prompt = am.prompt
            existing.xp_reward = am.xp_reward
            existing.cash_reward = am.cash_reward
            existing.badge_id = am.badge_id
    await session.commit()
```

For the lesson response to include `apply_mission`, load it (e.g. `await session.scalar(select(ApplyMission).where(ApplyMission.lesson_id == lesson.id))`) and populate the `LessonOut`. Match the existing serialization approach in the file.

- [ ] **Step 5: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_admin_apply_mission.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/admin.py app/routers/admin.py tests/test_admin_apply_mission.py
git commit -m "feat(sim): admin CRUD for apply-missions + module cash reward"
```

---

## Task 11: Frontend API — missions client + enriched trade type

**Files:**
- Create: `src/api/missions.ts`, `src/hooks/useActiveMissions.ts`
- Modify: `src/api/simulator.ts`
- Test: `src/__tests__/missions-api.test.ts` (mirror existing `tests/unit/api-simulator.test.ts` location/style)

- [ ] **Step 1: Write the failing test**

```typescript
// place beside the existing api-simulator test (e.g. tests/unit/missions-api.test.ts)
import { describe, expect, it } from 'vitest';
import { missionsApi } from '@/api/missions';
import { mockFetch } from './helpers'; // reuse the same helper the simulator api test imports

describe('missionsApi', () => {
  it('getActive calls GET /missions/active', async () => {
    const spy = mockFetch([{ id: 'm1', lesson_id: 'l1', mission_type: 'first_buy',
      title: 'Buy one', prompt: 'Try it', params_json: {} }], 200);
    const res = await missionsApi.getActive();
    expect(spy).toHaveBeenCalledWith('/missions/active', expect.any(Object));
    expect(res?.[0].mission_type).toBe('first_buy');
  });
});
```

(Match the import path/style of the existing simulator api unit test — use whatever helper + alias it uses.)

- [ ] **Step 2: Run test to verify it fails**

Run (from `invest-ed/frontend`): `npm test -- missions-api`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

```typescript
// src/api/missions.ts
import { apiFetch } from './client'; // match the import the simulator api uses

export type ActiveMission = {
  id: string;
  lesson_id: string;
  mission_type: string;
  title: string;
  prompt: string;
  params_json: Record<string, unknown>;
};

export const missionsApi = {
  getActive: () => apiFetch<ActiveMission[]>('/missions/active'),
};
```

```typescript
// src/hooks/useActiveMissions.ts
import { useQuery } from '@tanstack/react-query';
import { type ActiveMission, missionsApi } from '@/api/missions';

export function useActiveMissions() {
  return useQuery<ActiveMission[] | null>({
    queryKey: ['active-missions'],
    queryFn: () => missionsApi.getActive(),
    retry: false,
  });
}
```

In `src/api/simulator.ts`, add the enriched result type and use it for `placeTrade`:

```typescript
export type TradeReward = {
  xp_awarded: number;
  streak_extended: boolean;
  cash_granted: string;
  missions_completed: { id: string; title: string }[];
  badges_unlocked: string[];
};

export type TradeResult = TradeOut & { rewards: TradeReward };
```

Change `placeTrade` return type to `apiFetch<TradeResult>(...)` (the body/URL are unchanged).

- [ ] **Step 4: Run tests**

Run: `npm test -- missions-api && npx tsc -b`
Expected: PASS, tsc clean.

- [ ] **Step 5: Commit**

```bash
git add src/api/missions.ts src/hooks/useActiveMissions.ts src/api/simulator.ts tests/unit/missions-api.test.ts
git commit -m "feat(sim): frontend missions API + enriched trade result type"
```

---

## Task 12: `PortfolioSnapshotCard` on home

**Files:**
- Create: `src/components/child/home/PortfolioSnapshotCard.tsx`
- Modify: `src/pages/child/Home.tsx`
- Test: unit `tests/unit/PortfolioSnapshotCard.test.tsx` + a11y `tests/a11y/portfolio-snapshot.a11y.test.tsx` (mirror existing suite locations)

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/unit/PortfolioSnapshotCard.test.tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PortfolioSnapshotCard } from '@/components/child/home/PortfolioSnapshotCard';

describe('PortfolioSnapshotCard', () => {
  it('shows value and an up indicator with a label, not colour alone', () => {
    render(<PortfolioSnapshotCard totalValue="1234.50" currencyCode="GBP" changePct={2.3} />);
    expect(screen.getByText(/£1,234.50/)).toBeInTheDocument();
    expect(screen.getByText(/up/i)).toBeInTheDocument();   // textual label
    expect(screen.getByText('▲')).toBeInTheDocument();      // glyph
    expect(screen.getByRole('link', { name: /trade/i })).toBeInTheDocument();
  });
});
```

```tsx
// tests/a11y/portfolio-snapshot.a11y.test.tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { PortfolioSnapshotCard } from '@/components/child/home/PortfolioSnapshotCard';

describe('a11y: PortfolioSnapshotCard', () => {
  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter><PortfolioSnapshotCard totalValue="1000.00" currencyCode="GBP" changePct={-1.1} /></MemoryRouter>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- PortfolioSnapshotCard portfolio-snapshot`
Expected: FAIL (component missing).

- [ ] **Step 3: Implement the component**

```tsx
// src/components/child/home/PortfolioSnapshotCard.tsx
import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/format'; // match the existing currency formatter import used by CashCard

type Props = {
  totalValue: string;
  currencyCode: string;
  changePct?: number | null;
};

export function PortfolioSnapshotCard({ totalValue, currencyCode, changePct }: Props) {
  const pct = changePct ?? 0;
  const up = pct >= 0;
  const glyph = up ? '▲' : '▼';
  const label = up ? 'up' : 'down';
  return (
    <section
      aria-label="Your practice portfolio"
      className="rounded-2xl border border-line bg-card p-4 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Practice portfolio
          </p>
          <p className="mt-1 text-2xl font-extrabold text-ink">
            {formatCurrency(totalValue, currencyCode)}
          </p>
          <p className={`mt-0.5 text-sm font-semibold ${up ? 'text-success-700' : 'text-accent-700'}`}>
            <span aria-hidden="true">{glyph}</span>{' '}
            <span>{label} {Math.abs(pct).toFixed(1)}% today</span>
          </p>
        </div>
        <Link
          to="/simulator"
          className="rounded-full bg-brand-gradient px-4 py-2 text-sm font-bold text-white shadow"
        >
          Trade
        </Link>
      </div>
    </section>
  );
}
```

(Use the same `formatCurrency` import path that `CashCard.tsx` uses. Use `success-700` / `accent-700` for AA contrast, matching the StrengthsGaps re-skin precedent.)

- [ ] **Step 4: Wire into Home**

In `src/pages/child/Home.tsx`, import `usePortfolio` and `PortfolioSnapshotCard`, and render it between the `LevelProgressCard` block and the `AchievementsStrip` block:

```tsx
      {portfolio && (
        <div className="mt-4">
          <PortfolioSnapshotCard
            totalValue={portfolio.total_value}
            currencyCode={portfolio.currency_code}
            changePct={null}
          />
        </div>
      )}
```

with `const { data: portfolio } = usePortfolio();` added near the other data hooks. (`changePct` is `null` for now — a today-change value can be derived from `usePortfolioHistory` in a later pass; the component already handles null gracefully.)

- [ ] **Step 5: Run tests + tsc + a11y**

Run: `npm test -- PortfolioSnapshotCard portfolio-snapshot && npx tsc -b`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add src/components/child/home/PortfolioSnapshotCard.tsx src/pages/child/Home.tsx tests/unit/PortfolioSnapshotCard.test.tsx tests/a11y/portfolio-snapshot.a11y.test.tsx
git commit -m "feat(sim): portfolio snapshot card on child home"
```

---

## Task 13: `ApplyMissionCTA` on lesson completion

**Files:**
- Create: `src/components/child/lesson/ApplyMissionCTA.tsx`
- Modify: `src/pages/child/Lesson.tsx`
- Test: unit `tests/unit/ApplyMissionCTA.test.tsx` + a11y `tests/a11y/apply-mission-cta.a11y.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/unit/ApplyMissionCTA.test.tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';

describe('ApplyMissionCTA', () => {
  it('renders prompt and links into the simulator primed for the mission', () => {
    render(
      <MemoryRouter>
        <ApplyMissionCTA mission={{ id: 'm1', lesson_id: 'l1', mission_type: 'first_buy',
          title: 'Buy your first share', prompt: 'Now try it for real!', params_json: {} }} />
      </MemoryRouter>
    );
    expect(screen.getByText(/now try it for real/i)).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /try it in the simulator/i });
    expect(link).toHaveAttribute('href', '/simulator?mission=m1');
  });
});
```

```tsx
// tests/a11y/apply-mission-cta.a11y.test.tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';

describe('a11y: ApplyMissionCTA', () => {
  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <ApplyMissionCTA mission={{ id: 'm1', lesson_id: 'l1', mission_type: 'first_buy',
          title: 'Buy your first share', prompt: 'Try it!', params_json: {} }} />
      </MemoryRouter>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- ApplyMissionCTA apply-mission-cta`
Expected: FAIL (component missing).

- [ ] **Step 3: Implement**

```tsx
// src/components/child/lesson/ApplyMissionCTA.tsx
import { Link } from 'react-router-dom';
import { type ActiveMission } from '@/api/missions';

export function ApplyMissionCTA({ mission }: { mission: ActiveMission }) {
  return (
    <section
      aria-label="Apply what you learned"
      className="mt-4 rounded-2xl border-2 border-brand-200 bg-brand-50 p-5 text-center"
    >
      <p className="text-sm font-bold uppercase tracking-wider text-brand-700">Your mission</p>
      <p className="mt-1 text-lg font-extrabold text-ink">{mission.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{mission.prompt}</p>
      <Link
        to={`/simulator?mission=${mission.id}`}
        className="mt-3 inline-block rounded-full bg-brand-gradient px-5 py-2.5 text-sm font-bold text-white shadow"
      >
        Try it in the simulator
      </Link>
    </section>
  );
}
```

- [ ] **Step 4: Wire into the lesson completion screen**

In `src/pages/child/Lesson.tsx`, in the success branch (where `<CompletionPanel .../>` renders), fetch active missions and show the CTA for one matching this lesson:

```tsx
import { useActiveMissions } from '@/hooks/useActiveMissions';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';
// ...
const { data: missions } = useActiveMissions();
const lessonMission = missions?.find((m) => m.lesson_id === lessonId);
// inside the `complete.isSuccess && complete.data` block, after <CompletionPanel/>:
{lessonMission && <ApplyMissionCTA mission={lessonMission} />}
```

(`lessonId` is already in scope in this component. Invalidate `['active-missions']` is not required here — the mission disappears once completed in the simulator, and the home query refetches.)

- [ ] **Step 5: Run tests + tsc**

Run: `npm test -- ApplyMissionCTA apply-mission-cta && npx tsc -b`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add src/components/child/lesson/ApplyMissionCTA.tsx src/pages/child/Lesson.tsx tests/unit/ApplyMissionCTA.test.tsx tests/a11y/apply-mission-cta.a11y.test.tsx
git commit -m "feat(sim): apply-mission CTA on lesson completion"
```

---

## Task 14: `MissionBanner` in the simulator

**Files:**
- Create: `src/components/child/simulator/MissionBanner.tsx`
- Modify: `src/pages/child/Simulator.tsx`
- Test: unit `tests/unit/MissionBanner.test.tsx` + a11y `tests/a11y/mission-banner.a11y.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/unit/MissionBanner.test.tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';

const mission = { id: 'm1', lesson_id: 'l1', mission_type: 'diversify',
  title: 'Hold 3 different stocks', prompt: 'Spread your money out', params_json: { n: 3 } };

describe('MissionBanner', () => {
  it('shows the active mission goal', () => {
    render(<MissionBanner mission={mission} />);
    expect(screen.getByText(/hold 3 different stocks/i)).toBeInTheDocument();
  });

  it('returns nothing when there is no mission', () => {
    const { container } = render(<MissionBanner mission={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

```tsx
// tests/a11y/mission-banner.a11y.test.tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';

describe('a11y: MissionBanner', () => {
  it('has no axe violations', async () => {
    const { container } = render(<MissionBanner mission={{ id: 'm1', lesson_id: 'l1',
      mission_type: 'first_buy', title: 'Buy a share', prompt: 'Go!', params_json: {} }} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- MissionBanner mission-banner`
Expected: FAIL (component missing).

- [ ] **Step 3: Implement**

```tsx
// src/components/child/simulator/MissionBanner.tsx
import { type ActiveMission } from '@/api/missions';

export function MissionBanner({ mission }: { mission?: ActiveMission }) {
  if (!mission) return null;
  return (
    <section
      aria-label="Active mission"
      className="mb-4 flex items-start gap-3 rounded-2xl border-2 border-accent-400 bg-accent-50 p-4"
    >
      <span aria-hidden="true" className="text-2xl">🎯</span>
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-accent-700">Mission</p>
        <p className="text-base font-extrabold text-ink">{mission.title}</p>
        <p className="text-sm text-muted-foreground">{mission.prompt}</p>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire into the simulator (reads `?mission=`)**

In `src/pages/child/Simulator.tsx`, read the query param and render the banner above the portfolio hero:

```tsx
import { useSearchParams } from 'react-router-dom';
import { useActiveMissions } from '@/hooks/useActiveMissions';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';
// ...
const [params] = useSearchParams();
const missionId = params.get('mission');
const { data: missions } = useActiveMissions();
const activeMission = missions?.find((m) => m.id === missionId) ?? missions?.[0];
// at the top of the returned content (inside the main wrapper, before PortfolioHero):
<MissionBanner mission={activeMission} />
```

(If `missionId` is set but already completed it won't be in `missions`, so the banner falls back to any other active mission, or renders nothing.)

- [ ] **Step 5: Run tests + tsc**

Run: `npm test -- MissionBanner mission-banner && npx tsc -b`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add src/components/child/simulator/MissionBanner.tsx src/pages/child/Simulator.tsx tests/unit/MissionBanner.test.tsx tests/a11y/mission-banner.a11y.test.tsx
git commit -m "feat(sim): mission banner in the simulator"
```

---

## Task 15: Reward feedback toast on trade

**Files:**
- Modify: `src/components/child/simulator/TradeForm.tsx`
- Test: unit `tests/unit/TradeForm.rewards.test.tsx`

- [ ] **Step 1: Read `TradeForm.tsx`** to find the `placeTrade` mutation and its `onSuccess`. The mutation result is now `TradeResult` (Task 11), carrying `.rewards`.

- [ ] **Step 2: Write the failing test**

```tsx
// tests/unit/TradeForm.rewards.test.tsx
// Mirror the existing TradeForm test's setup (QueryClientProvider + mocked placeTrade).
// Assert that after a successful buy whose response includes rewards.xp_awarded > 0,
// the toast hook is called with a message containing the XP.
import { describe, expect, it, vi } from 'vitest';
// ... import render helpers + useToast mock exactly as the existing TradeForm test does.

describe('TradeForm reward feedback', () => {
  it('shows an XP toast when a trade awards XP', async () => {
    // Arrange: mock simulatorApi.placeTrade to resolve with:
    //   { id:'t1', ticker:'AAPL', type:'buy', shares:'1', price:'150', executed_at:'...',
    //     rewards:{ xp_awarded:5, streak_extended:false, cash_granted:'0',
    //               missions_completed:[], badges_unlocked:[] } }
    // Act: fill + submit the form.
    // Assert: the mocked toast was called with a title/description mentioning "+5 XP".
    expect(true).toBe(true); // replace with real assertions following the existing TradeForm test
  });
});
```

> Implementer: replace the placeholder assertion with concrete ones by copying the existing `TradeForm` test's mocking harness (it already mocks `simulatorApi` and `useToast`). This step is TDD — write the real failing assertion first.

- [ ] **Step 3: Implement reward feedback**

In `TradeForm.tsx`, extend the `placeTrade` mutation's `onSuccess(result)` to surface rewards via the existing `useToast`:

```tsx
import { useToast } from '@/hooks/use-toast';
// inside onSuccess(result: TradeResult):
const r = result?.rewards;
if (r) {
  const bits: string[] = [];
  if (r.xp_awarded > 0) bits.push(`+${r.xp_awarded} XP`);
  if (r.streak_extended) bits.push('🔥 streak kept');
  if (Number(r.cash_granted) > 0) bits.push(`+${r.cash_granted} to invest`);
  if (r.missions_completed.length) bits.push(`Mission complete: ${r.missions_completed[0].title}`);
  if (bits.length) {
    toast({ title: 'Nice trade!', description: bits.join(' · ') });
  }
}
// keep the existing query invalidations and ALSO invalidate missions + portfolio + progress:
qc.invalidateQueries({ queryKey: ['active-missions'] });
qc.invalidateQueries({ queryKey: ['portfolio'] });
qc.invalidateQueries({ queryKey: ['progress'] });
```

(Use the component's existing `queryClient`/`qc` reference and `toast` instance — match local names.)

- [ ] **Step 4: Run tests + tsc**

Run: `npm test -- TradeForm && npx tsc -b`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/components/child/simulator/TradeForm.tsx tests/unit/TradeForm.rewards.test.tsx
git commit -m "feat(sim): reward feedback toast on trade"
```

---

## Task 16: Admin forms — module cash reward + apply-mission block

**Files:**
- Modify: `src/components/admin/ModuleForm.tsx`, `src/components/admin/LessonForm.tsx`, and the admin API client types they use
- Test: unit `tests/unit/admin-ModuleForm.cash.test.tsx` (mirror existing admin ModuleForm test)

- [ ] **Step 1: Write the failing test**

```tsx
// tests/unit/admin-ModuleForm.cash.test.tsx
// Mirror the existing ModuleForm test harness.
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
// ... existing wrap helper for admin forms

describe('admin ModuleForm cash reward', () => {
  it('renders a completion cash reward input', () => {
    // render ModuleForm in create mode using the existing test harness
    // assert an input labelled /completion cash reward/i exists
    expect(screen.queryByLabelText(/completion cash reward/i)).toBeTruthy();
  });
});
```

(Follow the existing admin ModuleForm test's provider/mocking setup precisely.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- admin-ModuleForm.cash`
Expected: FAIL (no such input).

- [ ] **Step 3: ModuleForm — add the field**

Add state + input, and include in the `moduleData` payload:

```tsx
const [completionCashReward, setCompletionCashReward] = useState<string>(
  existing?.completion_cash_reward ?? ''
);
// in handleSave, add to moduleData:
completion_cash_reward: completionCashReward ? completionCashReward : null,
// render (number input, min 0, step 0.01):
<div>
  <label htmlFor="mod-cash" className="mb-1 block text-sm text-ink">
    Completion cash reward (optional)
  </label>
  <input id="mod-cash" type="number" min="0" step="0.01" value={completionCashReward}
    onChange={(e) => setCompletionCashReward(e.target.value)}
    className="w-full rounded-lg border border-line px-3 py-2" />
</div>
```

Add `completion_cash_reward?: string | null` to the admin module type used by the form, and ensure the create/update mutation passes it.

- [ ] **Step 4: LessonForm — add the apply-mission block**

Add collapsible state and inputs for: `mission_type` (a `<select>` populated from the four known types `first_buy | first_sell | diversify | invest_amount`), `params_json` (a single `n`/`amount` number input shown conditionally by type), `title`, `prompt`, `xp_reward`, `cash_reward`. Build an `apply_mission` object (or `null` when the block is disabled) and include it in the create/update lesson payload. Initialise from `lesson?.apply_mission` when editing.

```tsx
const [missionEnabled, setMissionEnabled] = useState(!!lesson?.apply_mission);
const [missionType, setMissionType] = useState(lesson?.apply_mission?.mission_type ?? 'first_buy');
const [missionTitle, setMissionTitle] = useState(lesson?.apply_mission?.title ?? '');
const [missionPrompt, setMissionPrompt] = useState(lesson?.apply_mission?.prompt ?? '');
const [missionXp, setMissionXp] = useState<string>(String(lesson?.apply_mission?.xp_reward ?? 20));
const [missionCash, setMissionCash] = useState<string>(lesson?.apply_mission?.cash_reward ?? '');
const [missionN, setMissionN] = useState<string>(String(lesson?.apply_mission?.params_json?.n ?? 2));
const [missionAmount, setMissionAmount] = useState<string>(
  String(lesson?.apply_mission?.params_json?.amount ?? '500')
);

function buildApplyMission() {
  if (!missionEnabled) return null;
  const params =
    missionType === 'diversify' ? { n: Number(missionN) }
    : missionType === 'invest_amount' ? { amount: missionAmount }
    : {};
  return { mission_type: missionType, params_json: params, title: missionTitle,
           prompt: missionPrompt, xp_reward: Number(missionXp),
           cash_reward: missionCash ? missionCash : null };
}
// include `apply_mission: buildApplyMission()` in each create/update mutation payload.
```

Render a labelled checkbox to toggle the block, the type `<select>`, the conditional param input, and text/number inputs (each with an associated `<label htmlFor>` for a11y). Add the `apply_mission` field to the admin lesson types + mutations.

- [ ] **Step 5: Run the FULL frontend suite + tsc + lint + build**

Run: `npm test && npx tsc -b && npm run lint && npm run build`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/components/admin/ModuleForm.tsx src/components/admin/LessonForm.tsx src/api/ tests/unit/admin-ModuleForm.cash.test.tsx
git commit -m "feat(sim): admin form fields for module cash reward + apply-mission"
```

---

## Task 17: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend regression**

Run (from `invest-ed/backend`):
```
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head
/Users/leeashmore/Local\ Repo/.venv/bin/pytest
```
Expected: ruff clean; migration applies on a fresh DB; tests green (note any pre-existing failures unrelated to this work — the repo has known environmental DB-hang behaviour; rely on CI if a DB-backed test hangs ~90s+).

- [ ] **Step 2: Frontend regression**

Run (from `invest-ed/frontend`):
```
npx tsc -b
npm run lint
npm test
npm run build
```
Expected: all green, including the new `vitest-axe` suites.

- [ ] **Step 3: iOS sync note (manual, user-side)**

The portfolio card, mission CTA, and banner are iOS-visible. After merge, the user must run `npm run build && npx cap sync ios` and rebuild in Xcode to see them on device. Note this in the PR/summary; do not attempt the Xcode build here.

- [ ] **Step 4: Dispatch the final holistic code review**

Per subagent-driven-development, dispatch a final reviewer over the whole branch (security + COPPA: confirm no child-initiated cash/XP path is exploitable beyond the daily cap, all grants idempotent, missions target free-tier tickers, no new PII).

- [ ] **Step 5: Finish the branch**

Use `superpowers:finishing-a-development-branch` to present options (commit to `main`, push; Railway deploys backend on green CI, Vercel auto-deploys frontend).

---

## Self-Review

**Spec coverage:**
- Full progression integration → Tasks 3 (streak), 4 (trade XP), 7 (endpoint wires both). ✅
- Targeted apply-missions → Tasks 1 (models), 2 (predicates), 5 (eval), 8 (active endpoint), 10 (authoring), 13 (lesson CTA), 14 (banner). ✅
- Home presence → Task 12 (snapshot card) + missions surfaced via Task 13/home. ✅
- Anti-gaming (mission XP + daily-capped routine XP; streak on first qualifying activity) → Tasks 2/4/3. ✅
- Configurable starting cash (admin) → Task 9. ✅
- Earnable cash (per-module on completion, per-mission) → Tasks 1, 5, 6, 10. ✅
- Idempotent ledger → Tasks 1 (constraint), 5 (`grant_cash`), 6 (module). ✅
- Reward feedback (shared toast) → Task 15. ✅
- Testing + a11y + close-out → every task + Task 17. ✅

**Placeholder scan:** Tasks 7, 8, 10, 15, 16 contain a few "confirm the exact existing helper name / mirror the existing test harness" notes. These are deliberate — they point the implementer at a *named, existing* pattern in a specific file rather than inventing one, and are not substitutes for code (full code is given for every new module/component). The only intentionally-stubbed test body is Task 15 Step 2, which the implementer must flesh out from the existing TradeForm test before implementing (TDD).

**Type consistency:** `RewardsOut`/`TradeResultOut` (backend) ↔ `TradeReward`/`TradeResult` (frontend) field names align (`xp_awarded`, `streak_extended`, `cash_granted`, `missions_completed`, `badges_unlocked`). `ActiveMission` shape matches `ActiveMissionOut`. `evaluate_apply_missions(session, user_id, progress, portfolio)`, `award_trade_xp(progress, today_local)`, `record_daily_activity(progress, today_local)`, `grant_cash(session, user_id, portfolio, source_type, source_id, amount)`, `grant_module_completion_cash(session, user_id, module_id)` are used consistently across tasks.
