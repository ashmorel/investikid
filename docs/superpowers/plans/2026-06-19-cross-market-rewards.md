# Cross-Market Rewards Implementation Plan (Sub-project D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reward learners with coins for adding a non-home market (one-time) and coins + a collectible "Market Mastered" badge for completing a market, with admin-tunable amounts, in-app feedback, and zero change to global XP/level/streak.

**Architecture:** A new reward seam in `market_progress_service` (enroll grant on the switch path; completion grant on the lesson-completion path), idempotency tracked by three timestamps on `UserMarketProgress`, a per-market `Badge.market_code` extension with 10 seeded badges, two admin-tunable coin settings, and a `RewardGrant` surfaced through the switch + lesson-completion responses to drive existing toasts. One additive, backfilled Alembic migration.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres (backend); React 18 + Vite + TS + TanStack Query + react-i18next (frontend).

**Spec:** `docs/superpowers/specs/2026-06-19-cross-market-rewards-design.md`
**Branch:** `testing`. Carries a prod DB migration → ask the snapshot question before applying to prod.

---

## File Structure

- Modify `backend/app/models/market_progress.py` — add `enroll_rewarded_at`, `completed_at`, `completion_rewarded_at`.
- Modify `backend/app/models/gamification.py` — add `Badge.market_code`.
- Create `backend/alembic/versions/<rev>_market_rewards.py` — columns + seed badges + GB backfill.
- Modify `backend/app/seed/gamification.py` — seed the 10 market badges (idempotent, shared by app seed + migration).
- Modify `backend/app/services/app_settings.py` — two coin-bonus getters/setters.
- Modify `backend/app/services/market_progress_service.py` — `RewardGrant`, `grant_enroll_reward`, `is_market_complete`, `grant_market_completion_reward`.
- Modify `backend/app/routers/markets.py` — enroll grant on switch; `reward` on `ActiveMarketResponse`.
- Modify `backend/app/routers/content.py` — completion grant in `complete_lesson`; `reward` on result.
- Modify `backend/app/schemas/content.py` — `RewardGrant` + `reward` field on `LessonCompletionResult`.
- Modify `backend/app/schemas/admin.py` + `backend/app/routers/admin.py` — two coin settings in `/settings`.
- Modify `frontend/src/api/market.ts`, `frontend/src/hooks/useMarkets.ts`, `frontend/src/api/content.ts` (or lesson api), `frontend/src/pages/child/Markets.tsx`, `frontend/src/pages/child/Lesson.tsx`, `frontend/src/api/admin.ts` + admin settings page, `frontend/src/locales/en/markets.json` — reward types + toasts + admin field.
- Tests under `backend/tests/` and `frontend/src/**/__tests__/`.

---

### Task 1: Migration + models — reward-state columns, `Badge.market_code`, market-badge seed, GB backfill

**Files:**
- Modify: `backend/app/models/market_progress.py`, `backend/app/models/gamification.py`, `backend/app/seed/gamification.py`
- Create: `backend/alembic/versions/<rev>_market_rewards.py`
- Test: `backend/tests/test_market_rewards_migration.py`

- [ ] **Step 1: Add model columns**

In `backend/app/models/market_progress.py`, add to `UserMarketProgress` (after `created_at`):

```python
    enroll_rewarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_rewarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

In `backend/app/models/gamification.py`, add to `Badge` (after `condition_value`):

```python
    market_code: Mapped[str | None] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=True
    )
```

(`String` and `ForeignKey` are already imported in that file.)

- [ ] **Step 2: Define the market-badge seed (shared)**

In `backend/app/seed/gamification.py`, add a module-level list and an idempotent seeder. The 10 markets + names mirror the `markets` seed (GB/US/AU/CA/IE/ES/FR/DE/HK/SG):

```python
_MARKET_BADGES = [
    ("GB", "United Kingdom", "🇬🇧"), ("US", "United States", "🇺🇸"),
    ("AU", "Australia", "🇦🇺"), ("CA", "Canada", "🇨🇦"),
    ("IE", "Ireland", "🇮🇪"), ("ES", "Spain", "🇪🇸"),
    ("FR", "France", "🇫🇷"), ("DE", "Germany", "🇩🇪"),
    ("HK", "Hong Kong", "🇭🇰"), ("SG", "Singapore", "🇸🇬"),
]


async def seed_market_badges(session: AsyncSession) -> None:
    """Idempotent. One 'Market Mastered: <name>' badge per market, keyed by name."""
    for code, name, flag in _MARKET_BADGES:
        badge_name = f"Market Mastered: {name}"
        existing = await session.scalar(select(Badge).where(Badge.name == badge_name))
        if existing is None:
            session.add(Badge(
                name=badge_name,
                description=f"Finish all the {name} money lessons",
                icon_url=flag,
                condition_type="market_completed",
                condition_value=0,
                market_code=code,
            ))
        elif existing.market_code != code:
            existing.market_code = code
```

Call `await seed_market_badges(session)` from the existing app-seed entrypoint right after `seed_badges_and_challenges(session)` (find where that's invoked — `backend/app/seed/__init__.py` or wherever the seeders are run — and add the call there).

- [ ] **Step 3: Write the failing migration test**

Create `backend/tests/test_market_rewards_migration.py`. This is a model/seed-level test (the actual Alembic upgrade is exercised by CI's `alembic upgrade head`); it asserts the seed + completion-detection backfill helper behave. Use the async fixtures:

```python
import pytest
from sqlalchemy import select

from app.models.gamification import Badge, UserBadge
from app.models.market_progress import UserMarketProgress
from app.seed.gamification import seed_market_badges

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_market_badges_idempotent(db_session):
    await seed_market_badges(db_session)
    await seed_market_badges(db_session)
    await db_session.flush()
    badges = (await db_session.scalars(
        select(Badge).where(Badge.condition_type == "market_completed")
    )).all()
    assert len(badges) == 10
    gb = next(b for b in badges if b.market_code == "GB")
    assert gb.name == "Market Mastered: United Kingdom"
    assert gb.icon_url == "🇬🇧"
```

- [ ] **Step 4: Run it — expect FAIL** (no `seed_market_badges` / no `market_code` column)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_rewards_migration.py -v`
Expected: FAIL (import error / unknown column).

- [ ] **Step 5: Write the migration**

Confirm the head and pick a free revision id:

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → expect `a9b0c1d2e3f4 (head)`.
Run: `grep -rl "b1d4e5f6a7c8" backend/alembic/versions/ || echo FREE` → expect `FREE` (if taken, pick another and grep again).

Create `backend/alembic/versions/b1d4e5f6a7c8_market_rewards.py`:

```python
"""market rewards: reward-state columns, badge.market_code, market badges + GB backfill

Revision ID: b1d4e5f6a7c8
Revises: a9b0c1d2e3f4
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "b1d4e5f6a7c8"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None

_MARKET_BADGES = [
    ("GB", "United Kingdom", "🇬🇧"), ("US", "United States", "🇺🇸"),
    ("AU", "Australia", "🇦🇺"), ("CA", "Canada", "🇨🇦"),
    ("IE", "Ireland", "🇮🇪"), ("ES", "Spain", "🇪🇸"),
    ("FR", "France", "🇫🇷"), ("DE", "Germany", "🇩🇪"),
    ("HK", "Hong Kong", "🇭🇰"), ("SG", "Singapore", "🇸🇬"),
]


def upgrade() -> None:
    op.add_column("user_market_progress", sa.Column("enroll_rewarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_market_progress", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_market_progress", sa.Column("completion_rewarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("badges", sa.Column("market_code", sa.String(length=2), nullable=True))
    op.create_foreign_key("fk_badges_market_code", "badges", "markets", ["market_code"], ["code"])

    conn = op.get_bind()
    # Seed the 10 market badges (idempotent by name).
    for code, name, flag in _MARKET_BADGES:
        badge_name = f"Market Mastered: {name}"
        exists = conn.execute(sa.text("SELECT id FROM badges WHERE name = :n"), {"n": badge_name}).first()
        if exists is None:
            conn.execute(sa.text(
                "INSERT INTO badges (id, name, description, icon_url, condition_type, condition_value, market_code) "
                "VALUES (gen_random_uuid(), :n, :d, :i, 'market_completed', 0, :c)"
            ), {"n": badge_name, "d": f"Finish all the {name} money lessons", "i": flag, "c": code})

    # Backfill: GB completers get the GB badge (NO coins) + stamps. A user has
    # "completed GB" iff GB has >=1 lesson and they completed every GB lesson.
    gb_badge = conn.execute(sa.text(
        "SELECT id FROM badges WHERE name = 'Market Mastered: United Kingdom'"
    )).scalar()
    gb_total = conn.execute(sa.text(
        "SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id = l.module_id WHERE m.market_code = 'GB'"
    )).scalar() or 0
    if gb_badge is not None and gb_total > 0:
        # users who completed all GB lessons
        rows = conn.execute(sa.text(
            "SELECT lc.user_id "
            "FROM lesson_completions lc "
            "JOIN lessons l ON l.id = lc.lesson_id "
            "JOIN modules m ON m.id = l.module_id "
            "WHERE m.market_code = 'GB' "
            "GROUP BY lc.user_id "
            "HAVING COUNT(DISTINCT lc.lesson_id) >= :total"
        ), {"total": gb_total}).fetchall()
        for (user_id,) in rows:
            # badge (skip if already owned)
            owned = conn.execute(sa.text(
                "SELECT 1 FROM user_badges WHERE user_id = :u AND badge_id = :b"
            ), {"u": user_id, "b": gb_badge}).first()
            if owned is None:
                conn.execute(sa.text(
                    "INSERT INTO user_badges (user_id, badge_id, earned_at) VALUES (:u, :b, NOW())"
                ), {"u": user_id, "b": gb_badge})
            # stamp the GB market-progress row if present (no coins)
            conn.execute(sa.text(
                "UPDATE user_market_progress SET completed_at = NOW(), completion_rewarded_at = NOW() "
                "WHERE user_id = :u AND market_code = 'GB'"
            ), {"u": user_id})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM user_badges WHERE badge_id IN (SELECT id FROM badges WHERE condition_type = 'market_completed')"))
    conn.execute(sa.text("DELETE FROM badges WHERE condition_type = 'market_completed'"))
    op.drop_constraint("fk_badges_market_code", "badges", type_="foreignkey")
    op.drop_column("badges", "market_code")
    op.drop_column("user_market_progress", "completion_rewarded_at")
    op.drop_column("user_market_progress", "completed_at")
    op.drop_column("user_market_progress", "enroll_rewarded_at")
```

> Confirm the actual table/column names by grepping (`lesson_completions`, `lessons`, `modules`, `user_badges`, `badges`, `user_market_progress`) — they match the models above, but verify (`\d+` names) before finalizing. `gen_random_uuid()` requires pgcrypto/pg13+ (already used elsewhere in this codebase — confirm with `grep -rn gen_random_uuid backend/alembic`; if absent, use `uuid_generate_v4()` or generate in Python).

- [ ] **Step 6: Apply the migration locally + run the test**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head`
Expected: applies cleanly to `b1d4e5f6a7c8`.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_rewards_migration.py -v`
Expected: PASS.

> If the local test Postgres hangs >90s (a known environmental issue per CLAUDE.md), rely on CI for the migration apply; don't thrash.

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/models/market_progress.py backend/app/models/gamification.py backend/app/seed/gamification.py backend/alembic/versions/b1d4e5f6a7c8_market_rewards.py backend/tests/test_market_rewards_migration.py && git commit -m "feat(market): reward-state columns + market badges + GB backfill migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Admin-tunable coin-bonus settings

**Files:**
- Modify: `backend/app/services/app_settings.py`
- Test: `backend/tests/test_market_reward_settings.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_reward_settings.py`:

```python
import pytest

from app.services.app_settings import (
    get_market_completion_bonus_coins,
    get_market_enroll_bonus_coins,
    set_market_completion_bonus_coins,
    set_market_enroll_bonus_coins,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_enroll_bonus_defaults_then_settable(db_session):
    assert await get_market_enroll_bonus_coins(db_session) == 25
    await set_market_enroll_bonus_coins(db_session, 40)
    assert await get_market_enroll_bonus_coins(db_session) == 40


async def test_completion_bonus_defaults_then_settable(db_session):
    assert await get_market_completion_bonus_coins(db_session) == 250
    await set_market_completion_bonus_coins(db_session, 500)
    assert await get_market_completion_bonus_coins(db_session) == 500


async def test_negative_rejected(db_session):
    with pytest.raises(ValueError):
        await set_market_enroll_bonus_coins(db_session, -1)
```

- [ ] **Step 2: Run it — expect FAIL** (no such functions)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_reward_settings.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement the getters/setters**

In `backend/app/services/app_settings.py`, add near the other keys/getters (mirror `get_trade_commission_pct` shape):

```python
_MARKET_ENROLL_BONUS_KEY = "market.enroll_bonus_coins"
_MARKET_COMPLETION_BONUS_KEY = "market.completion_bonus_coins"
_DEFAULT_MARKET_ENROLL_BONUS = 25
_DEFAULT_MARKET_COMPLETION_BONUS = 250


async def _get_int_setting(session: AsyncSession, key: str, default: int) -> int:
    raw = await get_setting(session, key)
    if raw is not None:
        try:
            val = int(raw)
            if val >= 0:
                return val
        except (TypeError, ValueError):
            pass
    return default


async def get_market_enroll_bonus_coins(session: AsyncSession) -> int:
    return await _get_int_setting(session, _MARKET_ENROLL_BONUS_KEY, _DEFAULT_MARKET_ENROLL_BONUS)


async def set_market_enroll_bonus_coins(session: AsyncSession, coins: int) -> None:
    if coins < 0:
        raise ValueError("enroll bonus coins must be >= 0")
    await set_setting(session, _MARKET_ENROLL_BONUS_KEY, str(coins))


async def get_market_completion_bonus_coins(session: AsyncSession) -> int:
    return await _get_int_setting(session, _MARKET_COMPLETION_BONUS_KEY, _DEFAULT_MARKET_COMPLETION_BONUS)


async def set_market_completion_bonus_coins(session: AsyncSession, coins: int) -> None:
    if coins < 0:
        raise ValueError("completion bonus coins must be >= 0")
    await set_setting(session, _MARKET_COMPLETION_BONUS_KEY, str(coins))
```

- [ ] **Step 4: Run it — expect PASS**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_reward_settings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/app_settings.py backend/tests/test_market_reward_settings.py && git commit -m "feat(market): admin-tunable enroll/completion coin-bonus settings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Enroll-reward seam + switch endpoint

**Files:**
- Modify: `backend/app/services/market_progress_service.py`, `backend/app/routers/markets.py`
- Test: `backend/tests/test_market_enroll_reward.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_enroll_reward.py` (uses the `client` fixture authed as a child; adapt fixture names to the repo's conventions — check an existing `backend/tests/test_markets*.py`):

```python
import pytest
from sqlalchemy import select

from app.models.market_progress import UserMarketProgress
from app.models.user import UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_switch_to_new_nonhome_market_grants_enroll_coins_once(client, db_session, child_user):
    prog = await db_session.get(UserProgress, child_user.id)
    start = prog.virtual_coins or 0

    r1 = await client.post("/me/active-market", json={"market_code": "US"})
    assert r1.status_code == 200
    assert r1.json()["reward"]["coins"] == 25

    await db_session.refresh(prog)
    assert (prog.virtual_coins or 0) == start + 25
    row = await db_session.get(UserMarketProgress, (child_user.id, "US"))
    assert row.enroll_rewarded_at is not None

    # second switch to US grants nothing
    r2 = await client.post("/me/active-market", json={"market_code": "US"})
    assert r2.json()["reward"]["coins"] == 0


async def test_switch_to_home_market_grants_nothing(client, db_session, child_user):
    # child_user.home_market_code defaults to GB
    r = await client.post("/me/active-market", json={"market_code": "GB"})
    assert r.json()["reward"]["coins"] == 0
```

> Use whatever authed-child fixtures the suite provides (`client`/`child_user`/`db_session`). If there's no `child_user` fixture, follow an existing markets test's setup to create + authenticate a child and read its id.

- [ ] **Step 2: Run it — expect FAIL** (no `reward` in response)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_enroll_reward.py -v`
Expected: FAIL (KeyError 'reward').

- [ ] **Step 3: Add `RewardGrant` + the enroll-grant service**

In `backend/app/services/market_progress_service.py`, add at the top (after imports):

```python
from dataclasses import dataclass


@dataclass
class RewardGrant:
    coins: int = 0
    badge_name: str | None = None
    badge_icon: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.coins == 0 and self.badge_name is None
```

Add the enroll-grant function (it must run AFTER the row is ensured; it reads `home_market_code`):

```python
async def grant_enroll_reward(
    session: AsyncSession, user: User, market_code: str
) -> RewardGrant:
    """One-time coin bonus the first time a user enrolls in a NON-home market.
    Idempotent via enroll_rewarded_at; the home market never qualifies."""
    if market_code == user.home_market_code:
        return RewardGrant()
    row = await session.get(UserMarketProgress, (user.id, market_code))
    if row is None or row.enroll_rewarded_at is not None:
        return RewardGrant()
    from datetime import UTC, datetime

    from app.services.app_settings import get_market_enroll_bonus_coins
    coins = await get_market_enroll_bonus_coins(session)
    progress = await session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id)
        session.add(progress)
        await session.flush()
    progress.virtual_coins = (progress.virtual_coins or 0) + coins
    row.enroll_rewarded_at = datetime.now(UTC)
    return RewardGrant(coins=coins)
```

- [ ] **Step 4: Wire it into the switch endpoint**

In `backend/app/routers/markets.py`: extend `ActiveMarketResponse` and call the grant after `ensure_enrolled`, before commit:

```python
from app.services.market_progress_service import RewardGrant, ensure_enrolled, grant_enroll_reward


class RewardGrantOut(BaseModel):
    coins: int = 0
    badge_name: str | None = None
    badge_icon: str | None = None


class ActiveMarketResponse(BaseModel):
    active_market_code: str
    reward: RewardGrantOut = RewardGrantOut()
```

In `switch_active_market`, replace the body after the 422 check with:

```python
    current_user.active_market_code = payload.market_code
    await ensure_enrolled(session, current_user.id, payload.market_code)
    grant = await grant_enroll_reward(session, current_user, payload.market_code)
    await session.commit()
    return ActiveMarketResponse(
        active_market_code=current_user.active_market_code,
        reward=RewardGrantOut(coins=grant.coins, badge_name=grant.badge_name, badge_icon=grant.badge_icon),
    )
```

- [ ] **Step 5: Run it — expect PASS**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_enroll_reward.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/market_progress_service.py backend/app/routers/markets.py backend/tests/test_market_enroll_reward.py && git commit -m "feat(market): enroll coin reward on first non-home market switch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Completion-reward seam + lesson-completion endpoint

**Files:**
- Modify: `backend/app/services/market_progress_service.py`, `backend/app/routers/content.py`, `backend/app/schemas/content.py`
- Test: `backend/tests/test_market_completion_reward.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_completion_reward.py`. It builds a tiny GB market with one module + one lesson, completes it, and asserts the completion reward fires once. Mirror an existing content/completion test for the module/lesson factory helpers:

```python
import pytest

from app.models.gamification import UserBadge
from app.models.market_progress import UserMarketProgress
from app.models.user import UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_completing_only_gb_lesson_grants_completion_reward_once(
    client, db_session, child_user, gb_single_lesson
):
    # gb_single_lesson: fixture/factory that creates a GB module with exactly one
    # lesson and returns the lesson id. Build inline if no such fixture exists.
    lesson_id = gb_single_lesson
    prog = await db_session.get(UserProgress, child_user.id)
    start = prog.virtual_coins or 0

    r = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 1.0})
    assert r.status_code == 200
    assert r.json()["reward"]["coins"] == 250
    assert r.json()["reward"]["badge_name"] == "Market Mastered: United Kingdom"

    await db_session.refresh(prog)
    assert (prog.virtual_coins or 0) == start + 250
    row = await db_session.get(UserMarketProgress, (child_user.id, "GB"))
    assert row.completion_rewarded_at is not None
    badge = await db_session.scalar(
        select(UserBadge).where(UserBadge.user_id == child_user.id)  # add: import select
    )
    assert badge is not None

    # re-complete: no second coin grant
    r2 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 1.0})
    assert r2.json()["reward"]["coins"] == 0
```

> If building a one-lesson GB market inline is simpler than a fixture, create the `Module(market_code="GB", ...)` + `Lesson(...)` rows in the test using the repo's existing content factories (grep `backend/tests` for how modules/lessons are created). Add `from sqlalchemy import select` to the test imports.

- [ ] **Step 2: Run it — expect FAIL** (no `reward` on completion result)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_completion_reward.py -v`
Expected: FAIL.

- [ ] **Step 3: Add `is_market_complete` + `grant_market_completion_reward`**

In `backend/app/services/market_progress_service.py`:

```python
async def is_market_complete(session: AsyncSession, user_id: uuid.UUID, market_code: str) -> bool:
    """True iff the market has >=1 lesson AND the user completed every lesson in
    every module of that market. Empty markets are never complete."""
    from sqlalchemy import func
    from app.models.content import Lesson, LessonCompletion, Module

    total = await session.scalar(
        select(func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == market_code)
    ) or 0
    if total == 0:
        return False
    done = await session.scalar(
        select(func.count(func.distinct(LessonCompletion.lesson_id)))
        .select_from(LessonCompletion)
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == market_code, LessonCompletion.user_id == user_id)
    ) or 0
    return done >= total


async def grant_market_completion_reward(
    session: AsyncSession, user: User, market_code: str
) -> RewardGrant:
    """If the (active) market is now complete and not yet rewarded, grant coins +
    the 'Market Mastered' badge. One-time via completion_rewarded_at."""
    row = await session.get(UserMarketProgress, (user.id, market_code))
    if row is None or row.completion_rewarded_at is not None:
        return RewardGrant()
    if not await is_market_complete(session, user.id, market_code):
        return RewardGrant()
    from datetime import UTC, datetime
    from app.models.gamification import Badge, UserBadge
    from app.services.app_settings import get_market_completion_bonus_coins

    coins = await get_market_completion_bonus_coins(session)
    progress = await session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id)
        session.add(progress)
        await session.flush()
    progress.virtual_coins = (progress.virtual_coins or 0) + coins

    badge = await session.scalar(
        select(Badge).where(Badge.market_code == market_code, Badge.condition_type == "market_completed")
    )
    badge_name = badge_icon = None
    if badge is not None:
        owned = await session.get(UserBadge, (user.id, badge.id))
        if owned is None:
            session.add(UserBadge(user_id=user.id, badge_id=badge.id))
        badge_name, badge_icon = badge.name, badge.icon_url

    now = datetime.now(UTC)
    if row.completed_at is None:
        row.completed_at = now
    row.completion_rewarded_at = now
    return RewardGrant(coins=coins, badge_name=badge_name, badge_icon=badge_icon)
```

- [ ] **Step 4: Surface it on the completion result**

In `backend/app/schemas/content.py`, add a `RewardGrant` schema and a field on `LessonCompletionResult`:

```python
class RewardGrantOut(BaseModel):
    coins: int = 0
    badge_name: str | None = None
    badge_icon: str | None = None
```

Add to `LessonCompletionResult`:

```python
    reward: RewardGrantOut = RewardGrantOut()
```

- [ ] **Step 5: Wire it into `complete_lesson`**

In `backend/app/routers/content.py`, import the seam and call it where the other completion side-effects run (inside the `if not already:` region, after `grant_module_completion_cash`, BEFORE `await session.commit()`):

```python
from app.services.market_progress_service import (
    award_xp, grant_market_completion_reward,
)
from app.schemas.content import RewardGrantOut
```

Replace the cash-grant + commit region with:

```python
    await grant_module_completion_cash(session, current_user.id, lesson.module_id)

    reward = RewardGrantOut()
    if not already:
        grant = await grant_market_completion_reward(
            session, current_user, current_user.active_market_code
        )
        reward = RewardGrantOut(coins=grant.coins, badge_name=grant.badge_name, badge_icon=grant.badge_icon)

    await session.commit()
    await session.refresh(progress)
```

And add `reward=reward` to the returned `LessonCompletionResult(...)`.

- [ ] **Step 6: Run it — expect PASS**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_market_completion_reward.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/market_progress_service.py backend/app/routers/content.py backend/app/schemas/content.py backend/tests/test_market_completion_reward.py && git commit -m "feat(market): completion coin + badge reward on finishing a market

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Admin settings — expose + edit the two coin amounts

**Files:**
- Modify: `backend/app/schemas/admin.py`, `backend/app/routers/admin.py`, `frontend/src/api/admin.ts` + the admin settings page
- Test: `backend/tests/test_admin_market_reward_settings.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_admin_market_reward_settings.py` (uses `admin_client`):

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_admin_settings_roundtrip_market_bonuses(admin_client):
    r = await admin_client.get("/admin/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["market_enroll_bonus_coins"] == 25
    assert body["market_completion_bonus_coins"] == 250

    upd = await admin_client.put("/admin/settings", json={
        "alert_emails": body["alert_emails"],
        "market_enroll_bonus_coins": 40,
        "market_completion_bonus_coins": 500,
    })
    assert upd.status_code == 200
    assert upd.json()["market_enroll_bonus_coins"] == 40
    assert upd.json()["market_completion_bonus_coins"] == 500
```

- [ ] **Step 2: Run it — expect FAIL** (fields absent)

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_admin_market_reward_settings.py -v`
Expected: FAIL (KeyError).

- [ ] **Step 3: Schema fields**

In `backend/app/schemas/admin.py`, add to `AdminSettingsOut`:

```python
    market_enroll_bonus_coins: int = 25
    market_completion_bonus_coins: int = 250
```

and to `AdminSettingsUpdate`:

```python
    market_enroll_bonus_coins: int | None = None
    market_completion_bonus_coins: int | None = None
```

Add a validator rejecting negatives (mirror the existing `trade_commission_pct` validator):

```python
    @field_validator("market_enroll_bonus_coins", "market_completion_bonus_coins")
    @classmethod
    def _non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("coin bonus must be >= 0")
        return v
```

- [ ] **Step 4: Route wiring**

In `backend/app/routers/admin.py`, import the new getters/setters and wire them into GET + PUT `/settings`:

```python
from app.services.app_settings import (
    get_market_enroll_bonus_coins, get_market_completion_bonus_coins,
    set_market_enroll_bonus_coins, set_market_completion_bonus_coins,
)
```

In `get_settings`, include in the returned `AdminSettingsOut`:

```python
        market_enroll_bonus_coins=await get_market_enroll_bonus_coins(session),
        market_completion_bonus_coins=await get_market_completion_bonus_coins(session),
```

In `update_settings`, before the final re-read/commit:

```python
    if body.market_enroll_bonus_coins is not None:
        await set_market_enroll_bonus_coins(session, body.market_enroll_bonus_coins)
    if body.market_completion_bonus_coins is not None:
        await set_market_completion_bonus_coins(session, body.market_completion_bonus_coins)
```

and include both in the returned `AdminSettingsOut` (read them back like `cash`/`pct`).

- [ ] **Step 5: Run it — expect PASS**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest backend/tests/test_admin_market_reward_settings.py -v`
Expected: PASS.

- [ ] **Step 6: Frontend admin field**

In `frontend/src/api/admin.ts`, add `market_enroll_bonus_coins: number` and `market_completion_bonus_coins: number` to the admin-settings types (Out + Update). In the admin settings page (grep `frontend/src/pages` for the component rendering `trade_commission_pct` / starting cash), add two number inputs bound to these fields, labelled via i18n (admin namespace; add keys like `settings.marketEnrollBonus` / `settings.marketCompletionBonus`). Mirror the existing commission-input markup exactly (same wrapper, label, ≥16px input, save handler).

- [ ] **Step 7: Verify FE + commit**

Run: `cd frontend && npx tsc -b && npm run lint`
Expected: clean.

```bash
cd /Users/leeashmore/investikid && git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/test_admin_market_reward_settings.py frontend/src/api/admin.ts frontend/src/pages frontend/src/locales/en/admin.json && git commit -m "feat(market): admin settings for enroll/completion coin bonuses

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Frontend reward feedback (toasts) + i18n

**Files:**
- Modify: `frontend/src/api/market.ts`, `frontend/src/hooks/useMarkets.ts`, `frontend/src/pages/child/Markets.tsx`, the lesson-complete consumer (`frontend/src/pages/child/Lesson.tsx` + its api type), `frontend/src/locales/en/markets.json`
- Test: `frontend/src/pages/child/__tests__/MarketRewardToast.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/child/__tests__/MarketRewardToast.test.tsx`. Mock the switch mutation to resolve with a reward and assert the toast text is requested. Adapt to the repo's `use-toast` testing approach (grep an existing test that asserts a toast):

```typescript
import { describe, expect, it, vi } from 'vitest';
import { formatRewardToast } from '../../../lib/marketReward';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => `${k} ${JSON.stringify(o ?? {})}` }) }));

describe('formatRewardToast', () => {
  it('returns coin copy for an enroll grant', () => {
    const t = (k: string, o?: Record<string, unknown>) => `${k} ${JSON.stringify(o ?? {})}`;
    const msg = formatRewardToast(t as never, { coins: 25, badge_name: null, badge_icon: null }, 'France');
    expect(msg).toContain('reward.enroll');
    expect(msg).toContain('25');
  });
  it('returns null when nothing granted', () => {
    const t = (k: string) => k;
    expect(formatRewardToast(t as never, { coins: 0, badge_name: null, badge_icon: null }, 'France')).toBeNull();
  });
});
```

- [ ] **Step 2: Run it — expect FAIL** (no `marketReward` helper)

Run: `cd frontend && npx vitest run src/pages/child/__tests__/MarketRewardToast.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Add the reward type + helper**

In `frontend/src/api/market.ts`, add:

```typescript
export type RewardGrant = {
  coins: number;
  badge_name: string | null;
  badge_icon: string | null;
};
```

and change `marketApi.switch`'s return type to `{ active_market_code: string; reward: RewardGrant }`.

Create `frontend/src/lib/marketReward.ts`:

```typescript
import type { TFunction } from 'i18next';
import type { RewardGrant } from '../api/market';

/** Build a celebratory toast string for a reward grant, or null if nothing was granted. */
export function formatRewardToast(t: TFunction, reward: RewardGrant | undefined, marketName: string): string | null {
  if (!reward || (reward.coins === 0 && !reward.badge_name)) return null;
  if (reward.badge_name) {
    return t('reward.completion', { coins: reward.coins, market: marketName });
  }
  return t('reward.enroll', { coins: reward.coins, market: marketName });
}
```

- [ ] **Step 4: Run it — expect PASS**

Run: `cd frontend && npx vitest run src/pages/child/__tests__/MarketRewardToast.test.tsx`
Expected: PASS.

- [ ] **Step 5: Fire the toasts + i18n**

Add to `frontend/src/locales/en/markets.json`:

```json
  "reward": {
    "enroll": "🎉 +{{coins}} coins for exploring {{market}}!",
    "completion": "🏆 Market mastered! +{{coins}} coins for finishing {{market}}!"
  }
```

In `Markets.tsx` (the switch handler), after a successful switch, call `formatRewardToast(t, data.reward, marketName)` and, if non-null, show it via the existing `use-toast` (grep `Shop.tsx`/`Lesson.tsx` for the toast call pattern). The switch mutation's `onSuccess` already navigates home; surface the toast there (or pass the reward through and toast on Home — keep it simple: toast in the picker's success handler before navigating).

In `Lesson.tsx`, the completion result (`complete.data`) now has `.reward`; after a successful non-repeat completion, if `reward.coins > 0 || reward.badge_name`, show the completion toast via `formatRewardToast`. Add the `reward` field to the lesson-completion result TS type (grep where `LessonCompletionResult` / `xp_awarded` is typed on the FE and add `reward: RewardGrant`).

- [ ] **Step 6: Verify FE + commit**

Run: `cd frontend && npx tsc -b && npm run lint && npx vitest run src/pages/child/__tests__/MarketRewardToast.test.tsx`
Expected: clean + PASS.

```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/market.ts frontend/src/lib/marketReward.ts frontend/src/hooks/useMarkets.ts frontend/src/pages/child/Markets.tsx frontend/src/pages/child/Lesson.tsx frontend/src/locales/en/markets.json frontend/src/pages/child/__tests__/MarketRewardToast.test.tsx && git commit -m "feat(market): reward toasts for enroll + completion grants

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full verification + promote

- [ ] **Step 1: Backend full suite + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest backend -q`
Expected: ruff clean; all tests pass. Fix any failure before proceeding (esp. the invariant: `sum(per-market xp) == UserProgress.xp` is unaffected — coins are separate from XP; if an existing xp/streak/badge test broke, investigate).

- [ ] **Step 2: Frontend full verification**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green; `no-literal-string` passes (all new strings in catalogs).

- [ ] **Step 3: Regression sanity**

Confirm a default GB user with no new market activity sees no behavior change: switching to GB grants nothing; XP/level/streak identical; existing badge/xp tests green. Existing GB completers (if any in test data) carry the GB badge from the backfill.

- [ ] **Step 4: iOS sync (UI-visible)**

Run: `cd frontend && npm run build && npx cap sync ios`
(The reward toasts are UI-visible; a device rebuild picks them up.)

- [ ] **Step 5: Push + green CI**

```bash
cd /Users/leeashmore/investikid && git push origin testing
```
Watch all CI jobs green (Backend now runs — there are backend changes).

- [ ] **Step 6: Promote (with the snapshot question)**

This carries a **prod DB migration** (3 columns + `badges.market_code` + seed + GB backfill). **Per the standing rule, ASK whether to snapshot the prod DB before applying.** Then merge testing → staging (CI green) → main (CI green; Railway applies `alembic upgrade head`), then the manual Vercel prod web deploy for the toasts. Verify `/health` 200 and a switch grants the enroll reward in prod.

---

## Self-Review

**Spec coverage:**
- Unit 1 reward-state columns → Task 1. ✓
- Unit 2 per-market badges (`Badge.market_code` + 10 seeded, direct award, inert in evaluator) → Task 1 (seed/migration) + Task 4 (direct award). ✓
- Unit 3 admin-tunable amounts → Task 2 (settings) + Task 5 (admin API/UI). ✓
- Unit 4 enroll-reward hook (non-home, one-time) → Task 3. ✓
- Unit 5 completion-reward hook (`is_market_complete`, coins + badge, one-time) → Task 4. ✓
- Unit 6 reward feedback (RewardGrant on switch + completion responses; toasts) → Tasks 3, 4 (API) + Task 6 (UI). ✓
- Unit 7 GB backfill (badge only, no coins) → Task 1 migration. ✓
- Unit 8 migration (additive + backfill + clean downgrade) → Task 1. ✓
- Non-goals respected: no un-enroll, no per-market amounts, no XP/level/streak change (coins only), no partial-progress rewards. ✓
- Rollout: snapshot question + testing→staging→main + Vercel → Task 7. ✓

**Placeholder scan:** No TBD/TODO. Full code for models, migration, settings, both reward seams, schemas, route wiring, and the FE helper. The admin-page input and the two FE toast call-sites are precise read-then-mirror instructions against named existing patterns (commission input; `use-toast` calls) — consistent with how this codebase's plans integrate into existing screens.

**Type/name consistency:** `RewardGrant` (dataclass, service) ↔ `RewardGrantOut` (pydantic, both routers/schemas) ↔ `RewardGrant` (TS) carry the same fields (`coins`, `badge_name`, `badge_icon`). `grant_enroll_reward`/`grant_market_completion_reward`/`is_market_complete` (Task 3/4) are defined once and wired once. Settings getters/setters (`get/set_market_enroll_bonus_coins`, `get/set_market_completion_bonus_coins`) defined in Task 2 and consumed in Tasks 3/4/5. `market_code` on `Badge` (Task 1) queried in Task 4. Migration revision `b1d4e5f6a7c8` chains `a9b0c1d2e3f4`. Consistent.
