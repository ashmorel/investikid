# Live-Market Regeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an operator regenerate an already-live market's curriculum (UK/GB) via the curriculum engine without kids seeing half-built content — staged invisible, then atomically swapped live with the old modules soft-retired.

**Architecture:** Add a per-module `Module.published` flag (default true; all existing modules backfill true). Every child-facing module read path filters to published only; admin paths see all. `accept_proposal` creates staged modules `published=false`. A new `publish_market_curriculum` flips the staged modules live and soft-retires the previously-live ones in one transaction (guarded so a market can't go blank). The Market Content admin UI is un-gated so GB shows the Brief + Curriculum panel plus a "Publish curriculum (replaces live)" action.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres (backend); React 18 + Vite + TanStack Query + Tailwind v4 + i18next (frontend); pytest + vitest/vitest-axe.

## Global Constraints

- Repo root `/Users/leeashmore/investikid`; backend cmds from `backend/`, frontend from `frontend/`. venv at `/Users/leeashmore/Local Repo/.venv`.
- Backend test: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`; lint: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`.
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient`. A `seed_markets_once` session fixture already inserts the 10 markets incl. GB/US — do NOT re-insert `Market(code=...)` in tests; insert only the rows you need (briefs, modules).
- DB change = hand-written, chained Alembic migration; run `alembic heads` from `backend/` first. Current single head is `b2d4f6a8c0e1` — chain off it. **Ask the user before any production migration whether to snapshot first.**
- It's a kids' app: this feature ships **inert** — every existing module backfills `published=true`, so child-facing behaviour is byte-identical until an operator runs a regeneration. Do not change moderation/auth.
- Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Do NOT push (the controller promotes). Do NOT read/modify any `.env`.

---

### Task 1: `Module.published` column + migration + visibility predicate

**Files:**
- Modify: `backend/app/models/content.py` (add column to `Module`)
- Create: `backend/alembic/versions/<rev>_module_published.py`
- Modify: `backend/app/services/content_service.py` (add `is_module_visible`)
- Test: `backend/tests/test_module_visibility.py`

**Interfaces:**
- Produces: `Module.published: Mapped[bool]` (NOT NULL, default/server_default true); `content_service.is_module_visible(module: Module, active_market_code: str) -> bool` = `module.published and is_module_in_market(module.market_code, active_market_code)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_module_visibility.py
from types import SimpleNamespace

from app.services.content_service import is_module_visible


def _mod(market_code, published):
    return SimpleNamespace(market_code=market_code, published=published)


def test_published_in_market_is_visible():
    assert is_module_visible(_mod("GB", True), "GB") is True


def test_unpublished_is_hidden_even_in_market():
    assert is_module_visible(_mod("GB", False), "GB") is False


def test_published_wrong_market_is_hidden():
    assert is_module_visible(_mod("US", True), "GB") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_visibility.py -q`
Expected: FAIL (ImportError: cannot import name 'is_module_visible').

- [ ] **Step 3a: Add the model column**

In `backend/app/models/content.py`, inside `class Module`, after the `conversation_prompt` column (line ~44):

```python
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
```

(`Boolean` is already imported in that module.)

- [ ] **Step 3b: Add the predicate** to `backend/app/services/content_service.py`, right after `is_module_in_market`:

```python
def is_module_visible(module, active_market_code: str) -> bool:
    """Child-facing visibility: a module is shown only when it is published AND
    in the user's active market. Staged (unpublished) modules — built by the
    curriculum engine before an atomic publish — are invisible to children."""
    return bool(module.published) and is_module_in_market(module.market_code, active_market_code)
```

- [ ] **Step 3c: Write the chained migration**

Run `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` — confirm the single head is `b2d4f6a8c0e1`. Pick a fresh revision id (e.g. `c3e5a7b9d1f2`, verify it is not already used in `backend/alembic/versions/`).

```python
# backend/alembic/versions/c3e5a7b9d1f2_module_published.py
"""module published flag

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
"""
import sqlalchemy as sa
from alembic import op

revision = "c3e5a7b9d1f2"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "modules",
        sa.Column("published", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("modules", "published")
```

(`server_default="true"` backfills every existing module — the 15 GB + all others — to published, so behaviour is unchanged.)

- [ ] **Step 4: Apply + run tests**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_visibility.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: migration applies; 3 passed; single head `c3e5a7b9d1f2`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/content.py backend/app/services/content_service.py backend/alembic/versions/*module_published.py backend/tests/test_module_visibility.py
git commit -m "feat(content): Module.published flag + is_module_visible predicate + migration"
```

---

### Task 2: Child-feeder visibility sweep + coverage meta-test

**Files:**
- Modify: `backend/app/routers/content.py` (lines 70, 95/108)
- Modify: `backend/app/services/next_lesson_service.py` (line 34 / select at 32)
- Modify: `backend/app/services/recommendation_service.py` (lines 62, 236, 443, 450)
- Modify: `backend/app/services/coach_service.py` (line 237)
- Modify: `backend/app/services/revise_service.py` (line 121)
- Modify: `backend/app/services/market_progress_service.py` (`is_market_complete`, lines ~87, 96)
- Test: `backend/tests/test_module_visibility_feeders.py`

**Interfaces:**
- Consumes: `is_module_visible` (Task 1) and `Module.published`.
- Produces: every child-facing module read path excludes unpublished modules. (Admin paths — `admin.py`, `market_scaffold_service.py`, `market_module_suggester.py`, `market_curriculum/*`, `admin_content_generation_service.py`, and `analytics_service.py` admin metrics — are intentionally left unfiltered.)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_module_visibility_feeders.py
import inspect
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.user import User
from app.services import content_service, next_lesson_service, recommendation_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _gb_user(db_session, **over):
    from datetime import date
    u = User(username=f"vis_{id(over)}", password_hash="x", dob=date(2014, 1, 1),
             country_code="GB", currency_code="GBP", active_market_code="GB",
             home_market_code="GB", **over)
    db_session.add(u)
    await db_session.flush()
    return u


async def _gb_module(db_session, *, published, order_index, title="M"):
    m = Module(topic="saving", title=title, country_codes=[], market_code="GB",
               is_premium=False, order_index=order_index, icon="💷",
               min_age=10, max_age=14, published=published)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    db_session.add(Lesson(module_id=m.id, level_id=lvl.id, type="card", xp_reward=10,
                          order_index=0, content_json={"title": "t", "body": "b"}))
    await db_session.flush()
    return m


async def test_child_module_list_excludes_unpublished(db_session):
    user = await _gb_user(db_session)
    pub = await _gb_module(db_session, published=True, order_index=900, title="Visible")
    await _gb_module(db_session, published=False, order_index=901, title="Staged")
    # The child list endpoint query: published-only.
    rows = (await db_session.scalars(
        select(Module).where(Module.market_code == "GB", Module.published.is_(True))
    )).all()
    titles = {m.title for m in rows}
    assert "Visible" in titles and "Staged" not in titles


def test_feeder_coverage_meta():
    """Every child feeder module that filters by is_module_in_market must also
    consider published (via is_module_visible) OR filter Module.published in SQL.
    This guards against a new feeder silently skipping the published gate."""
    import app.routers.content as content_router
    for mod in (content_router, next_lesson_service, recommendation_service):
        src = inspect.getsource(mod)
        if "is_module_in_market" in src:
            assert "is_module_visible" in src, f"{mod.__name__} gates market but not published"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_visibility_feeders.py -q`
Expected: FAIL — `test_feeder_coverage_meta` fails (feeders still use `is_module_in_market` without `is_module_visible`).

- [ ] **Step 3: Apply the published gate at each child feeder**

In each file, swap the child market gate to the visibility predicate, or add the SQL filter. Exact edits:

**`backend/app/routers/content.py`** — import `is_module_visible` alongside `is_module_in_market` (line ~35); at line 70 (module detail) replace `if not is_module_in_market(module.market_code, current_user.active_market_code):` with `if not is_module_visible(module, current_user.active_market_code):`. In `list_modules` (line ~95) add the SQL filter and update the Python guard at 108:

```python
    result = await session.scalars(
        select(Module).where(Module.published.is_(True)).order_by(Module.order_index)
    )
```
and at line ~108 replace the guard with `if not is_module_visible(m, current_user.active_market_code):`.

**`backend/app/services/next_lesson_service.py`** — import `is_module_visible` (the file already imports `is_module_in_market` at line 18); at line 32 add `.where(Module.published.is_(True))` to the select; at line 34 replace the guard with `if not is_module_visible(m, user.active_market_code):`.

**`backend/app/services/recommendation_service.py`** — import `is_module_visible`; at lines 236 and 443 add `.where(Module.published.is_(True))` to those `select(Module)` queries (keep existing `.where(...)` / `.order_by(...)`); at lines 62 and 450 replace `is_module_in_market(...)` with `is_module_visible(module, user.active_market_code)` / `is_module_visible(m, user.active_market_code)`.

**`backend/app/services/coach_service.py`** — at line 237 change `select(Module)` to `select(Module).where(Module.published.is_(True))`.

**`backend/app/services/revise_service.py`** — at line 121 change `select(Module).where(Module.id.in_(comp_modules))` to `select(Module).where(Module.id.in_(comp_modules), Module.published.is_(True))` (retired content drops out of Revise).

**`backend/app/services/market_progress_service.py`** — in `is_market_complete`, add `Module.published.is_(True)` to the `.where(...)` clauses at lines ~87 and ~96, so retired modules don't block a market from ever counting complete.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_visibility_feeders.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app`
Expected: PASS (2 passed); ruff clean.

- [ ] **Step 5: Run the broader child-content + market regression suites**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content.py tests/test_next_lesson*.py tests/test_recommendation*.py tests/test_revise*.py tests/test_market*.py -q`
Expected: all PASS (existing modules are published=true, so behaviour unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/content.py backend/app/services/next_lesson_service.py backend/app/services/recommendation_service.py backend/app/services/coach_service.py backend/app/services/revise_service.py backend/app/services/market_progress_service.py backend/tests/test_module_visibility_feeders.py
git commit -m "feat(content): gate every child module feeder on Module.published"
```

---

### Task 3: `accept_proposal` stages modules invisibly + records module ids

**Files:**
- Modify: `backend/app/services/market_curriculum/proposal_service.py` (`accept_proposal`)
- Test: `backend/tests/test_curriculum_stage_on_accept.py`

**Interfaces:**
- Consumes: `Module.published` (Task 1).
- Produces: `accept_proposal` creates `Module(..., published=False)` and writes `tree["modules"][m_idx]["module_id"] = str(module.id)` for each created module (alongside the existing per-level `level_id` write-back).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_stage_on_accept.py
import pytest
from sqlalchemy import select

from app.models.content import Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.types import CurriculumProposal, ModuleNode, LevelNode, ValidationReport
from app.services.market_curriculum.proposal_service import save_proposal, accept_proposal

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REPORT = ValidationReport(ok=True, missing_backbone=[], tiers_present=[1, 2, 3],
                           spans_all_tiers=True, regressions=[])


def _proposal():
    lvl = LevelNode(title="L0", order_index=0, complexity_tier=1,
                    learning_objective="o", concepts=["a"], backbone_keys=["saving_goals"])
    mod = ModuleNode(topic="money", title="Money", icon="💵", min_age=10, max_age=14,
                     order_index=0, levels=[lvl])
    return CurriculumProposal(market_code="GB", modules=[mod])


async def test_accept_creates_unpublished_modules_and_records_ids(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    await accept_proposal(db_session, row)
    mods = (await db_session.scalars(
        select(Module).where(Module.market_code == "GB", Module.title == "Money")
    )).all()
    assert len(mods) == 1
    assert mods[0].published is False  # staged, invisible to kids
    node = row.proposal_json["modules"][0]
    assert node["module_id"] == str(mods[0].id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_stage_on_accept.py -q`
Expected: FAIL (module created published=true by default; `module_id` not in node).

- [ ] **Step 3: Modify `accept_proposal`**

In `backend/app/services/market_curriculum/proposal_service.py`, in the materialise loop: create the module with `published=False`, and record its id on the tree node. The relevant lines become:

```python
        module = Module(
            topic=mod_node.topic[:30], title=mod_node.title, country_codes=[],
            market_code=proposal.market_code, is_premium=False,
            order_index=mod_node.order_index, icon=mod_node.icon,
            min_age=mod_node.min_age, max_age=mod_node.max_age,
            published=False,  # staged — invisible until publish_market_curriculum swaps it live
        )
        session.add(module)
        await session.flush()
        n_modules += 1
        tree["modules"][m_idx]["module_id"] = str(module.id)
```

(The `tree["modules"]` list is already sorted by `order_index` earlier in the function, so `m_idx` aligns.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_stage_on_accept.py tests/test_curriculum_proposal_service.py -q`
Expected: PASS (new test + existing proposal-service tests still green).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_curriculum/proposal_service.py backend/tests/test_curriculum_stage_on_accept.py
git commit -m "feat(curriculum): accept stages modules unpublished + records module ids"
```

---

### Task 4: `publish_market_curriculum` atomic swap + endpoint

**Files:**
- Create: `backend/app/services/market_curriculum/curriculum_publish_service.py`
- Modify: `backend/app/routers/admin.py` (new endpoint + import)
- Test: `backend/tests/test_curriculum_publish.py`

**Interfaces:**
- Consumes: `MarketCurriculumProposal` (status `accepted`, `proposal_json` with `module_id` per node from Task 3), `Module.published`, `get_active_proposal`.
- Produces:
  - `async publish_market_curriculum(session, market_code: str) -> dict` returning `{"published": int, "retired": int}`. Raises `ValueError` if no accepted proposal, or if any staged module has zero published `Lesson` rows.
  - `POST /admin/markets/{market_code}/curriculum/publish` → that dict; 409 on `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_publish.py
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.curriculum_publish_service import publish_market_curriculum

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session, *, published, order_index, title, with_lesson):
    m = Module(topic="money", title=title, country_codes=[], market_code="GB",
               is_premium=False, order_index=order_index, icon="💷",
               min_age=10, max_age=14, published=published)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    if with_lesson:
        db_session.add(Lesson(module_id=m.id, level_id=lvl.id, type="card", xp_reward=0,
                              order_index=0, content_json={"title": "t", "body": "b"}))
        await db_session.flush()
    return m


async def _accepted_proposal(db_session, staged_module_ids):
    row = MarketCurriculumProposal(
        market_code="GB", status="accepted",
        proposal_json={"market_code": "GB", "modules": [
            {"topic": "money", "title": "New", "icon": "💷", "min_age": 10, "max_age": 14,
             "order_index": 0, "module_id": str(mid), "levels": []} for mid in staged_module_ids]},
        coverage_json={"ok": True})
    db_session.add(row)
    await db_session.flush()
    return row


async def test_publish_swaps_live_and_retires_old(db_session):
    old = await _module(db_session, published=True, order_index=0, title="OldLive", with_lesson=True)
    staged = await _module(db_session, published=False, order_index=1, title="NewStaged", with_lesson=True)
    await _accepted_proposal(db_session, [staged.id])

    result = await publish_market_curriculum(db_session, "GB")
    assert result == {"published": 1, "retired": 1}
    await db_session.refresh(old)
    await db_session.refresh(staged)
    assert staged.published is True and old.published is False


async def test_publish_blocked_when_staged_module_has_no_lessons(db_session):
    staged = await _module(db_session, published=False, order_index=0, title="Empty", with_lesson=False)
    await _accepted_proposal(db_session, [staged.id])
    with pytest.raises(ValueError):
        await publish_market_curriculum(db_session, "GB")
    await db_session.refresh(staged)
    assert staged.published is False  # nothing changed


async def test_publish_no_accepted_proposal_raises(db_session):
    with pytest.raises(ValueError):
        await publish_market_curriculum(db_session, "ZZ")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_publish.py -q`
Expected: FAIL (module not found / import error).

- [ ] **Step 3: Write the service**

```python
# backend/app/services/market_curriculum/curriculum_publish_service.py
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Module
from app.models.market import Market
from app.services.market_curriculum.proposal_service import get_active_proposal


async def publish_market_curriculum(session: AsyncSession, market_code: str) -> dict:
    """Atomically swap a market's accepted-but-staged curriculum live: publish the
    staged modules, soft-retire the previously-published ones, flip has_content.
    Reversible (retire is a flag flip; rows are kept). Raises ValueError if there
    is no accepted proposal or a staged module has no published lessons."""
    row = await get_active_proposal(session, market_code)
    if row is None or row.status != "accepted":
        raise ValueError("no accepted curriculum to publish")

    staged_ids = [
        uuid.UUID(n["module_id"])
        for n in row.proposal_json.get("modules", [])
        if n.get("module_id")
    ]
    if not staged_ids:
        raise ValueError("accepted curriculum has no materialised modules")

    # Guard: every staged module must have at least one published lesson.
    for mid in staged_ids:
        n_lessons = await session.scalar(
            select(func.count(Lesson.id)).where(Lesson.module_id == mid)
        )
        if not n_lessons:
            raise ValueError("review and approve lessons before publishing")

    # Retire the currently-live modules for this market (excluding the staged set).
    retired = (await session.execute(
        update(Module)
        .where(Module.market_code == market_code, Module.published.is_(True),
               Module.id.notin_(staged_ids))
        .values(published=False)
    )).rowcount or 0

    # Publish the staged modules.
    await session.execute(
        update(Module).where(Module.id.in_(staged_ids)).values(published=True)
    )

    market = await session.get(Market, market_code)
    if market is not None:
        market.has_content = True
    row.status = "published"
    await session.flush()
    return {"published": len(staged_ids), "retired": retired}
```

- [ ] **Step 4: Add the endpoint** to `backend/app/routers/admin.py`

Import near the other `market_curriculum` imports:
```python
from app.services.market_curriculum.curriculum_publish_service import publish_market_curriculum
```
Endpoint (place beside the other `/markets/{market_code}/curriculum/*` routes):
```python
@router.post("/markets/{market_code}/curriculum/publish")
async def publish_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await publish_market_curriculum(session, market_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await session.commit()
    return result
```

- [ ] **Step 5: Run tests + lint**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_publish.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/market_curriculum/curriculum_publish_service.py app/routers/admin.py`
Expected: PASS (3 passed); ruff clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/market_curriculum/curriculum_publish_service.py backend/app/routers/admin.py backend/tests/test_curriculum_publish.py
git commit -m "feat(curriculum): publish_market_curriculum atomic swap + endpoint"
```

---

### Task 5: Frontend — un-gate live markets + publish-curriculum action

**Files:**
- Modify: `frontend/src/api/admin.ts` (add `usePublishCurriculum`)
- Modify: `frontend/src/components/admin/MarketContent.tsx` (un-gate Brief + CurriculumPanel for all markets; keep scaffold/suggestions non-GB; add publish-curriculum button + confirm)
- Modify: `frontend/src/locales/en/admin.json` (`marketContent.publishCurriculum.*`)
- Test: `frontend/src/components/admin/__tests__/MarketContent.test.tsx`

**Interfaces:**
- Consumes: `POST /admin/markets/{code}/curriculum/publish` (Task 4).
- Produces: `usePublishCurriculum(marketCode)` mutation hook (invalidates `['admin','curriculum',marketCode]`, `['admin','modules']`, `['admin','levels']`); GB now renders the Brief + CurriculumPanel; a "Publish curriculum (replaces live)" control with a confirm dialog.

- [ ] **Step 1: Write/extend the failing test**

In `MarketContent.test.tsx`, add a test that selecting GB renders the curriculum panel (not just the source note). The component currently shows `gbNote` for GB; after the change GB must render `<CurriculumPanel>` (mockable) and the Brief heading. Use the existing render helpers; mirror the existing market-selection tests. Assert: when `code === 'GB'` is selected, the Brief heading (`marketContent.brief.heading`) and the curriculum panel are present, and the scaffold heading (`marketContent.scaffold.heading`) is NOT.

```tsx
it('renders the Brief + Curriculum panel for GB (no longer a source-only wall)', async () => {
  // select GB in the market picker, then:
  // expect(screen.getByText(<brief heading>)).toBeInTheDocument();
  // expect(screen.getByTestId('curriculum-panel')).toBeInTheDocument();  // stub CurriculumPanel
  // expect(screen.queryByText(<scaffold heading>)).not.toBeInTheDocument();
});
```

(If `CurriculumPanel` is heavy to render, `vi.mock` it to a stub that renders `data-testid="curriculum-panel"`, matching how Task 9 stubbed `LessonDraftReview`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/MarketContent.test.tsx`
Expected: FAIL (GB renders only `gbNote`).

- [ ] **Step 3a: Add the API hook** to `frontend/src/api/admin.ts` (follow the `useAcceptCurriculum` pattern):

```ts
export function usePublishCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<{ published: number; retired: number }>(
      `/admin/markets/${marketCode}/curriculum/publish`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    },
  });
}
```

- [ ] **Step 3b: Restructure the render gate** in `MarketContent.tsx`

Currently (lines ~175–181): GB shows only `gbNote`; everything (Brief + `CurriculumPanel` + scaffold + suggestions) is inside `{code && code !== 'GB' && (...)}`. Change to:
- Render the **Brief section** and **`<CurriculumPanel marketCode={code} />`** for **any** selected `code` (GB included).
- Keep the **scaffold** step and the **suggestions** section inside a `code !== 'GB'` sub-block (meaningless for the source market).
- Remove the `gbNote`-only wall; optionally keep a one-line note for GB explaining it's the live market being regenerated.
- Add the **publish-curriculum** control (button → `ConfirmDialog` → `usePublishCurriculum(code).mutate()`), shown for any market with an accepted curriculum. The confirm copy: `marketContent.publishCurriculum.confirmMessage`. After success show `marketContent.publishCurriculum.result` ("{{published}} live, {{retired}} retired") in a `role="status"` line.

Reuse the existing `ConfirmDialog` component (already imported elsewhere in the admin tree) and the existing token classes.

- [ ] **Step 3c: Add i18n** keys under `marketContent.publishCurriculum` in `frontend/src/locales/en/admin.json`:
```
"publishCurriculum": {
  "action": "Publish curriculum (replaces live)",
  "confirmTitle": "Publish new curriculum?",
  "confirmMessage": "This makes the newly generated modules live and retires the market's current modules. Existing learners keep their XP, coins, level and streak but start the new curriculum fresh. This can't be auto-undone.",
  "publishing": "Publishing…",
  "result": "{{published}} module(s) live, {{retired}} retired."
}
```

- [ ] **Step 4: Run the frontend gates**

Run: `cd frontend && npx vitest run src/components/admin && npx tsc -b && npm run lint`
Expected: PASS (incl. the new GB test); tsc clean; lint 0 errors (pre-existing react-refresh warnings OK).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/components/admin/MarketContent.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/MarketContent.test.tsx
git commit -m "feat(curriculum): un-gate GB Market Content + publish-curriculum swap action"
```

---

### Task 6: Full verification + promote + operator UK regeneration

**Files:**
- Modify: `docs/superpowers/PROGRESS.md` (record the capability, live state)

- [ ] **Step 1: Backend full slice + lint**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_visibility.py tests/test_module_visibility_feeders.py tests/test_curriculum_stage_on_accept.py tests/test_curriculum_publish.py tests/test_curriculum_proposal_service.py tests/test_curriculum_native_batch.py tests/test_curriculum_endpoints.py tests/test_content.py tests/test_market*.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: all PASS; ruff clean.

- [ ] **Step 2: Frontend full gates**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: tsc clean; lint 0 errors; tests pass; build OK. (Admin-web only — no `cap sync ios`.)

- [ ] **Step 3: Promote** `testing → staging → main` per the standing flow. This includes the **`Module.published` migration** — ask the user before the production migration whether to snapshot first. Vercel prod deploy + alias `app.investikid.ai`. Confirm prod `alembic_version` advanced and `/health` 200.

- [ ] **Step 4: Update `PROGRESS.md`** (standing rule) with the live-market-regeneration capability + migration id; commit and sync to `main`.

- [ ] **Step 5: Operator UK regeneration (with the user)** — in Market Content → GB: generate + verify a **GB brief** → Design curriculum → review coverage → Accept (stages invisibly) → Generate all → review drafts inline → approve → **Publish curriculum (replaces live)**. Then verify in the child app that GB shows the new curriculum and the old 15 modules are retired, with global XP/streak intact.

---

## Self-Review notes

- **Spec coverage:** `Module.published` + predicate (T1); child-feeder sweep + meta-test (T2); stage-on-accept + module-id recording (T3); atomic swap + guard + endpoint (T4); UI un-gate + publish action (T5); verify/promote/operator-regen (T6). Every spec section maps to a task.
- **Type/name consistency:** `is_module_visible(module, active_market_code)` defined in T1, used in T2; `Module.published` consistent throughout; `publish_market_curriculum(session, market_code) -> {published, retired}` defined T4, consumed by `usePublishCurriculum` T5; `module_id` written on proposal nodes in T3 and read in T4.
- **Migration:** single new column, chained off `b2d4f6a8c0e1` (T1); flagged for snapshot before prod (T6).
- **Inert on ship:** server_default true backfills all modules → child behaviour byte-identical until an operator publishes a regenerated curriculum.
