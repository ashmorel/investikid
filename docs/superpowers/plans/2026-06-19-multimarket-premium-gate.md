# Multi-Market Premium Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Limit free users to progress in one market (their first lesson-completed), with a hard server gate at lesson completion + proactive "Premium" marking in the market picker, while premium unlocks all markets and current GB users see no change.

**Architecture:** A nullable `users.started_market_code` (set on first completion, backfilled to each user's dominant market), one `market_locked_for(user, code)` predicate driving both enforcement and UI, a gate in `complete_lesson` (403 `premium_required`, no award), a `locked` flag on `GET /markets`, and picker Premium chips + a content unlock panel on the frontend.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres; React 18 + Vite + TS + TanStack Query + react-i18next.

**Spec:** `docs/superpowers/specs/2026-06-19-multimarket-premium-gate-design.md`
**Branch:** `testing`. Carries a prod DB migration → ask the snapshot question before prod.

---

## File Structure

- Modify `backend/app/models/user.py` — add `started_market_code`.
- Create `backend/alembic/versions/<rev>_started_market_code.py` — column + backfill.
- Modify `backend/app/services/entitlements.py` — `market_locked_for` predicate.
- Modify `backend/app/routers/content.py` — the completion gate + set-on-first.
- Modify `backend/app/routers/markets.py` — `locked` on `MarketOut`.
- Modify `frontend/src/api/market.ts` (`MarketSummary.locked`), `frontend/src/pages/child/Markets.tsx` (Premium chip), `frontend/src/pages/child/Home.tsx` (unlock panel), `frontend/src/locales/en/markets.json`.
- Tests under `backend/tests/` and `frontend/src/**/__tests__/`.

---

### Task 1: `users.started_market_code` + migration + backfill

**Files:**
- Modify: `backend/app/models/user.py`
- Create: `backend/alembic/versions/d3f6a9c0b1e2_started_market_code.py`
- Test: `backend/tests/test_started_market_code_migration.py`

- [ ] **Step 1: Model field**

In `backend/app/models/user.py`, add to `User` (near `active_market_code`):

```python
    started_market_code: Mapped[str | None] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=True
    )
```

(`String`, `ForeignKey` already imported in that file — verify.)

- [ ] **Step 2: Failing test**

Create `backend/tests/test_started_market_code_migration.py`:

```python
import pytest

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_started_market_code_defaults_null_and_settable(db_session, child_user_factory):
    # child_user_factory: use the repo's helper/inline registration to make a user.
    user = await child_user_factory()
    assert user.started_market_code is None
    user.started_market_code = "GB"
    await db_session.flush()
    fetched = await db_session.get(User, user.id)
    assert fetched.started_market_code == "GB"
```

> If there's no `child_user_factory`, register a user inline via the pattern in `backend/tests/test_market_enroll_reward.py` and read the `User` row. Adapt to the suite's real fixtures.

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_started_market_code_migration.py -v` → expect FAIL (no column).

- [ ] **Step 3: Migration**

Confirm head: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → `c2e5f8a9b0c1`. Verify the id is free: `grep -rl "d3f6a9c0b1e2" backend/alembic/versions/ || echo FREE`. Create `backend/alembic/versions/d3f6a9c0b1e2_started_market_code.py`:

```python
"""users.started_market_code (nullable) + backfill to dominant market

Revision ID: d3f6a9c0b1e2
Revises: c2e5f8a9b0c1
Create Date: 2026-06-19
"""
import sqlalchemy as sa
from alembic import op

revision = "d3f6a9c0b1e2"
down_revision = "c2e5f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("started_market_code", sa.String(length=2), nullable=True))
    op.create_foreign_key(
        "fk_users_started_market_code", "users", "markets", ["started_market_code"], ["code"]
    )
    # Backfill: each user's dominant market = the UserMarketProgress row with the
    # most XP (tie-break earliest created_at). Today this resolves to GB for all.
    op.execute(sa.text(
        "UPDATE users SET started_market_code = sub.market_code "
        "FROM ("
        "  SELECT DISTINCT ON (user_id) user_id, market_code "
        "  FROM user_market_progress "
        "  ORDER BY user_id, xp DESC, created_at ASC"
        ") sub "
        "WHERE users.id = sub.user_id AND users.started_market_code IS NULL"
    ))


def downgrade() -> None:
    op.drop_constraint("fk_users_started_market_code", "users", type_="foreignkey")
    op.drop_column("users", "started_market_code")
```

> Verify the real table/column names (`users`, `user_market_progress.user_id/market_code/xp/created_at`) by grepping the models before finalizing.

- [ ] **Step 4: Apply + test**

From `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head` then `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_started_market_code_migration.py -v` → PASS. Ruff the touched files. (Local DB hang >90s → defer apply to CI.)

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/models/user.py backend/alembic/versions/d3f6a9c0b1e2_started_market_code.py backend/tests/test_started_market_code_migration.py && git commit -m "feat(market): users.started_market_code + backfill to dominant market

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `market_locked_for` predicate

**Files:**
- Modify: `backend/app/services/entitlements.py`
- Test: `backend/tests/test_market_locked_for.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/test_market_locked_for.py` (pure — no DB; uses a lightweight fake user):

```python
from app.services.entitlements import market_locked_for


class FakeUser:
    def __init__(self, is_premium, started):
        self.is_premium = is_premium
        self.started_market_code = started


def test_premium_never_locked():
    assert market_locked_for(FakeUser(True, "GB"), "US") is False


def test_free_no_started_nothing_locked():
    assert market_locked_for(FakeUser(False, None), "US") is False


def test_free_started_other_market_locked():
    u = FakeUser(False, "GB")
    assert market_locked_for(u, "US") is True
    assert market_locked_for(u, "GB") is False
```

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_market_locked_for.py -v` → FAIL.

- [ ] **Step 2: Implement**

In `backend/app/services/entitlements.py`, add (uses the existing `is_premium`):

```python
def market_locked_for(user: User, market_code: str) -> bool:
    """A free user may progress in only their started market. Premium → never
    locked; free with no started market → nothing locked (first completion sets
    it); free with a started market → every OTHER market is locked."""
    if is_premium(user):
        return False
    if user.started_market_code is None:
        return False
    return market_code != user.started_market_code
```

Run → PASS. Ruff.

- [ ] **Step 3: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/entitlements.py backend/tests/test_market_locked_for.py && git commit -m "feat(market): market_locked_for premium-gate predicate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Hard gate at lesson completion

**Files:**
- Modify: `backend/app/routers/content.py`
- Test: `backend/tests/test_market_premium_gate.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/test_market_premium_gate.py`. Build markets/modules/lessons and register users (mirror `backend/tests/test_market_completion_reward.py`). Cover:
- A free user completing their FIRST lesson (GB) → 200, and their `started_market_code` becomes `"GB"`.
- That same free user, now started=GB, completing a lesson in a different market (create a US module+lesson, switch active to US) → **403** with `code == "premium_required"`, and **no `LessonCompletion` row / no XP** for that US lesson.
- A premium user completing a lesson in a second market → 200 (allowed).
- Same-market re-completion for the free user → allowed (no 403).

```python
# skeleton — fill in per the repo's fixtures
async def test_first_completion_sets_started_market(client, db_session, ...):
    r = await client.post(f"/lessons/{gb_lesson_id}/complete", json={"score": 1.0})
    assert r.status_code == 200
    user = await db_session.get(User, child_id)
    assert user.started_market_code == "GB"

async def test_free_second_market_completion_blocked(client, db_session, ...):
    # started=GB already; switch active to US; complete a US lesson
    r = await client.post(f"/lessons/{us_lesson_id}/complete", json={"score": 1.0})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "premium_required"
    # no completion row / no xp for the US lesson
```

> To put the US lesson behind the active market, set the user's `active_market_code="US"` (and ensure the US module/lesson exist + the user is allowed to fetch them — mirror how the completion test makes content accessible). For the premium case, set `is_premium=True`.

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_market_premium_gate.py -v` → FAIL.

- [ ] **Step 2: Implement the gate**

In `backend/app/routers/content.py` `complete_lesson`, after the module is resolved (`module = await _get_accessible_module(lesson.module_id, current_user, session)`) and BEFORE the award (`_award_completion`/the analytics/award block), insert:

```python
from app.services.entitlements import market_locked_for
from app.services.premium_config import premium_required_error
from app.models.market import Market
# (import at top of file if not already present)

    if current_user.started_market_code is None:
        current_user.started_market_code = module.market_code
    elif market_locked_for(current_user, module.market_code):
        market = await session.get(Market, module.market_code)
        raise premium_required_error("market", market.name if market else module.market_code)
```

This runs for every completion (repeat or not): the first-ever completion claims the market; a locked second-market completion 403s before any side effect. `module.market_code` equals the active market (content is gated to it), so this is the lesson's market.

- [ ] **Step 3: Run + ruff**

From `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_market_premium_gate.py -v` → PASS. Then run the existing completion/reward tests to confirm no regression (`test_market_completion_reward.py`, `test_market_enroll_reward.py`, content tests). `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/routers/content.py tests/test_market_premium_gate.py` → fix anything.

> Regression watch: existing tests that complete GB lessons must still pass — the first completion sets started=GB, subsequent GB completions are same-market (allowed). If any test completes lessons across markets for a free user, it will now correctly 403; update only genuinely-affected tests (and confirm the change is correct, not masking a real regression).

- [ ] **Step 4: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/content.py backend/tests/test_market_premium_gate.py && git commit -m "feat(market): premium gate — free users progress in one market

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `locked` flag on `GET /markets`

**Files:**
- Modify: `backend/app/routers/markets.py`
- Test: `backend/tests/test_markets_locked_flag.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/test_markets_locked_flag.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_free_started_market_locks_others(client, db_session, ...):
    # free user, started_market_code = "GB"
    r = await client.get("/markets")
    by = {m["code"]: m for m in r.json()}
    assert by["GB"]["locked"] is False
    assert by["US"]["locked"] is True


async def test_premium_user_nothing_locked(client, db_session, ...):
    # premium user, started_market_code = "GB"
    r = await client.get("/markets")
    assert all(m["locked"] is False for m in r.json())
```

> Set `started_market_code`/`is_premium` on the user via db_session after registration. Adapt fixtures.

Run → FAIL.

- [ ] **Step 2: Implement**

In `backend/app/routers/markets.py`: add `locked: bool = False` to `MarketOut`; import `market_locked_for`; in `list_markets`, set `locked=market_locked_for(current_user, m.code)` when building each `MarketOut`.

- [ ] **Step 3: Run + ruff + commit**

Run the new test → PASS; ruff.

```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/markets.py backend/tests/test_markets_locked_flag.py && git commit -m "feat(market): expose per-user locked flag on GET /markets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Frontend — picker Premium chip + content unlock panel

**Files:**
- Modify: `frontend/src/api/market.ts`, `frontend/src/pages/child/Markets.tsx`, `frontend/src/pages/child/Home.tsx`, `frontend/src/locales/en/markets.json`
- Test: `frontend/src/pages/child/__tests__/MarketsLocked.test.tsx`

- [ ] **Step 1: Failing test**

Create `frontend/src/pages/child/__tests__/MarketsLocked.test.tsx`: mock `useMarkets` to return a list where a non-selected market has `locked: true`, render `Markets`, assert a "Premium" chip shows on the locked market (and not on the unlocked/selected one).

```typescript
vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true, locked: false },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: true, enrolled: false, is_selected: false, locked: true },
  ] }),
  useSwitchMarket: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
// render Markets, assert getByText('picker.premium') is within the US card
```

Run `cd frontend && npx vitest run src/pages/child/__tests__/MarketsLocked.test.tsx` → FAIL.

- [ ] **Step 2: Types + picker chip**

In `frontend/src/api/market.ts`, add `locked: boolean` to `MarketSummary`. In `Markets.tsx`, render a **"Premium"** chip on cards where `m.locked` (alongside/instead of the "Coming soon" pill; locked takes visual priority). Add `picker.premium` = "Premium" to `markets.json`. Cards stay tappable (preview). Use the real sky-blue/muted tokens (grep the existing pill classes).

- [ ] **Step 3: Content unlock panel on Home**

In `Home.tsx`, derive the active market from `useMarkets()` (`is_selected`); if that market's `locked` is true, render a premium-unlock panel ("Unlock all markets with Premium") — reuse the existing premium-upsell component (grep `PremiumUpsellCard`/`usePremiumPaywall`) — above the lesson content. Add `unlock.title`/`unlock.body`/`unlock.cta` to `markets.json`. (Completing a locked lesson already 403s → the existing global `premium_required` handler opens the paywall; confirm that path exists — grep for `premium_required` handling in the frontend api/error layer — and rely on it.)

- [ ] **Step 4: Verify + commit**

`cd frontend && npx tsc -b && npm run lint && npx vitest run src/pages/child/__tests__/MarketsLocked.test.tsx` → clean + PASS. Run existing `Markets.test.tsx` + `Home.test.tsx` for no regression.

```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/market.ts frontend/src/pages/child/Markets.tsx frontend/src/pages/child/Home.tsx frontend/src/locales/en/markets.json frontend/src/pages/child/__tests__/MarketsLocked.test.tsx && git commit -m "feat(market): picker Premium chip + content unlock panel for locked markets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`. All green. Key regression: a default GB user's completion flow byte-identical (first completion sets started=GB; subsequent GB completions allowed; XP/level/streak unchanged).
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. All green; `no-literal-string` clean.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (picker chip + unlock panel are UI-visible).
- [ ] **Step 4: Push + green CI** — `git push origin testing`; watch all jobs green (Backend runs).
- [ ] **Step 5: Promote (snapshot question)** — carries a prod migration (`users.started_market_code` + backfill). **Ask whether to snapshot prod first.** Merge testing→staging→main on green CI (Railway applies `alembic upgrade head`), then the manual Vercel prod deploy. Verify `/health` 200. Inert for current GB users (started=GB, GB content fully accessible) — confirm a GB user's flow is unchanged.

---

## Self-Review

**Spec coverage:**
- Unit 1 `started_market_code` (set on first completion, backfilled) → Task 1 (column+backfill) + Task 3 (set-on-first). ✓
- Unit 2 `market_locked_for` predicate → Task 2. ✓
- Unit 3 hard completion gate → Task 3. ✓
- Unit 4 `locked` on `/markets` → Task 4. ✓
- Unit 5 content unlock panel (detect via `is_selected` market's `locked`) → Task 5 Step 3. ✓
- Unit 6 picker Premium chip + copy → Task 5 Step 2. ✓
- Unit 7 backfill migration → Task 1. ✓
- Non-goals respected: no within-market gating change, no simulator gating, no un-start. ✓
- Rollout: snapshot question + inert-for-GB + testing→staging→main + Vercel → Task 6. ✓

**Placeholder scan:** No TBDs. Migration/model/predicate/gate code complete; the frontend chip/panel + the cross-market test fixtures are precise read-then-mirror instructions against named patterns (the completion test for content creation; the existing premium-upsell + `premium_required` handler). The gate sets `started_market_code` on first completion (Task 3) which is the behavioral half of Unit 1 — called out so it isn't mistaken as belonging to Task 1's migration.

**Type/name consistency:** `started_market_code` (Task 1 model) read/written in Tasks 2, 3, 4. `market_locked_for` (Task 2) used in Tasks 3, 4. `MarketOut.locked` (Task 4) ↔ `MarketSummary.locked` (Task 5). `premium_required_error("market", …)` (Task 3) → frontend `code: "premium_required"` paywall (Task 5 Step 3). Migration `d3f6a9c0b1e2` chains `c2e5f8a9b0c1`.
