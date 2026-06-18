# Market Foundation Implementation Plan (Sub-project C1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a first-class `Market`, associate every module with a market, migrate all existing content + users to a `GB` (UK) market, and filter content by the user's `home_market_code` — with zero behavior change.

**Architecture:** A new `markets` table keyed by ISO-3166 alpha-2 code, seeded with 10 markets (only `GB` has content). `Module` gains `market_code` and `User` gains `home_market_code`, both defaulting to `GB`. The content router's region/`country_codes` gate is replaced by a market gate; the premium and age gates are unchanged. A single additive, backfilled Alembic migration carries it to prod.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest.

**Spec:** `docs/superpowers/specs/2026-06-18-market-foundation-design.md`
**Branch:** `testing`. Current Alembic head: `b0c1d2e3f4a5`.

---

## File Structure

- Create `backend/app/models/market.py` — `Market` model.
- Modify `backend/app/models/content.py` — add `Module.market_code`.
- Modify `backend/app/models/user.py` — add `User.home_market_code`.
- Create `backend/app/seed/markets.py` — `MARKETS` data + idempotent `seed_markets(session)`.
- Modify `backend/app/seed/run.py` — call `seed_markets`.
- Create `backend/alembic/versions/<rev>_market_foundation.py` — table + seed + 2 columns.
- Modify `backend/app/services/content_service.py` — add `is_module_in_market` + `is_module_premium_ok`.
- Modify `backend/app/routers/content.py` — swap region gate → market gate.
- Modify `backend/app/services/analytics_service.py` — market filter.
- Modify `backend/app/schemas/user.py` — `home_market_code` on `UserProfile`.
- Tests: `backend/tests/test_markets.py`, `backend/tests/test_market_content_filter.py`, plus an assertion in the migration/model tests.

> **Model registration:** the test DB schema is created from `Base.metadata` (SQLAlchemy `create_all` in the test fixtures), so a new model must be imported where the app imports its models (check `app/models/__init__.py` — if it explicitly imports each model module, add `market`). Confirm `Market` is reachable from `Base.metadata` before writing model tests.

---

### Task 1: `Market` model + columns + seed

**Files:**
- Create: `backend/app/models/market.py`
- Modify: `backend/app/models/content.py` (Module), `backend/app/models/user.py` (User), `backend/app/models/__init__.py` (if it lists models)
- Create: `backend/app/seed/markets.py`
- Modify: `backend/app/seed/run.py`
- Test: `backend/tests/test_markets.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_markets.py`:

```python
import pytest

from app.seed.markets import MARKETS, seed_markets
from app.models.market import Market

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_market_catalog_has_ten_iso_coded_markets():
    codes = {m["code"] for m in MARKETS}
    assert codes == {"GB", "US", "AU", "CA", "IE", "ES", "FR", "DE", "HK", "SG"}
    by_code = {m["code"]: m for m in MARKETS}
    assert by_code["GB"]["currency_code"] == "GBP"
    assert by_code["GB"]["default_language"] == "en"
    assert by_code["GB"]["has_content"] is True
    assert by_code["ES"]["default_language"] == "es"
    assert by_code["HK"]["currency_code"] == "HKD"
    # GB is the only market with content at C1
    assert {m["code"] for m in MARKETS if m["has_content"]} == {"GB"}


async def test_seed_markets_is_idempotent(db_session):
    await seed_markets(db_session)
    await seed_markets(db_session)  # second run must not duplicate or error
    rows = (await db_session.scalars(__import__("sqlalchemy").select(Market))).all()
    assert len(rows) == 10
    gb = await db_session.get(Market, "GB")
    assert gb.name == "United Kingdom"
    assert gb.currency_code == "GBP"
    assert gb.has_content is True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_markets.py -q`
Expected: FAIL (`ModuleNotFoundError: app.models.market` / `app.seed.markets`).

- [ ] **Step 3: Create the `Market` model**

Create `backend/app/models/market.py`:

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Market(Base):
    """A country financial-education market (the 'money' axis). Content and users
    are scoped to a market. Keyed by ISO-3166 alpha-2 code to align with
    users.country_code / modules.country_codes."""
    __tablename__ = "markets"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    default_language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
    has_content: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
```

If `backend/app/models/__init__.py` imports model modules explicitly, add `from app.models import market  # noqa` (or the matching style) so `Base.metadata` includes `markets`.

- [ ] **Step 4: Add the FK columns to Module and User**

In `backend/app/models/content.py`, add to `Module` (after `country_codes`):

```python
    market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=False, server_default="GB", index=True
    )
```
(`String` and `ForeignKey` are already imported in content.py.)

In `backend/app/models/user.py`, add to `User` (after `currency_code` / near `language`):

```python
    home_market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=False, server_default="GB"
    )
```
(`String` and `ForeignKey` are already imported in user.py.)

- [ ] **Step 5: Create the seed module**

Create `backend/app/seed/markets.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Market

# The 10 target markets. has_content=True only for GB at C1 (the migrated UK
# curriculum); other markets are seeded-but-empty until Sub-project E authors
# their content. default_language uses BCP-47 codes matching app/core/languages.py.
MARKETS: list[dict] = [
    {"code": "GB", "name": "United Kingdom", "currency_code": "GBP", "default_language": "en", "has_content": True},
    {"code": "US", "name": "United States", "currency_code": "USD", "default_language": "en", "has_content": False},
    {"code": "AU", "name": "Australia", "currency_code": "AUD", "default_language": "en", "has_content": False},
    {"code": "CA", "name": "Canada", "currency_code": "CAD", "default_language": "en", "has_content": False},
    {"code": "IE", "name": "Ireland", "currency_code": "EUR", "default_language": "en", "has_content": False},
    {"code": "ES", "name": "Spain", "currency_code": "EUR", "default_language": "es", "has_content": False},
    {"code": "FR", "name": "France", "currency_code": "EUR", "default_language": "fr", "has_content": False},
    {"code": "DE", "name": "Germany", "currency_code": "EUR", "default_language": "de", "has_content": False},
    {"code": "HK", "name": "Hong Kong", "currency_code": "HKD", "default_language": "en", "has_content": False},
    {"code": "SG", "name": "Singapore", "currency_code": "SGD", "default_language": "en", "has_content": False},
]


async def seed_markets(session: AsyncSession) -> None:
    """Idempotent upsert of the market catalog. Safe to run repeatedly."""
    existing = {c for c in (await session.scalars(select(Market.code))).all()}
    for m in MARKETS:
        if m["code"] in existing:
            row = await session.get(Market, m["code"])
            row.name = m["name"]
            row.currency_code = m["currency_code"]
            row.default_language = m["default_language"]
            row.has_content = m["has_content"]
        else:
            session.add(Market(**m, is_active=True))
    await session.flush()
```

- [ ] **Step 6: Register the seed in the runner**

In `backend/app/seed/run.py`, import and call `seed_markets(session)` BEFORE any content seeding (markets must exist before modules reference them). Read the file to match its session/ordering style; add `from app.seed.markets import seed_markets` and call it first in the seed sequence.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_markets.py -q && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/models/market.py app/seed/markets.py`
Expected: PASS (2 passed); ruff clean.

- [ ] **Step 8: Commit**

```bash
cd "/Users/leeashmore/investikid" && git add backend/app/models/market.py backend/app/models/content.py backend/app/models/user.py backend/app/models/__init__.py backend/app/seed/markets.py backend/app/seed/run.py backend/tests/test_markets.py && git commit -m "feat(market): Market model + 10-market seed + module/user market columns

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Migration (table + seed + columns, backfill GB)

**Files:**
- Create: `backend/alembic/versions/c1d2e3f4a5b6_market_foundation.py`
- Test: `backend/tests/test_markets.py` (append a migration-shape assertion) — optional; the migration is primarily verified by `alembic upgrade head` + the existing suite running against the schema.

- [ ] **Step 1: Confirm the current head**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/alembic" heads`
Expected: single head `b0c1d2e3f4a5`. Use it as `down_revision` (if different, use the real head).

- [ ] **Step 2: Write the migration**

Create `backend/alembic/versions/c1d2e3f4a5b6_market_foundation.py`:

```python
"""market foundation: markets table + module/user market codes (C1)

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-06-18 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MARKETS = [
    {"code": "GB", "name": "United Kingdom", "currency_code": "GBP", "default_language": "en", "has_content": True, "is_active": True},
    {"code": "US", "name": "United States", "currency_code": "USD", "default_language": "en", "has_content": False, "is_active": True},
    {"code": "AU", "name": "Australia", "currency_code": "AUD", "default_language": "en", "has_content": False, "is_active": True},
    {"code": "CA", "name": "Canada", "currency_code": "CAD", "default_language": "en", "has_content": False, "is_active": True},
    {"code": "IE", "name": "Ireland", "currency_code": "EUR", "default_language": "en", "has_content": False, "is_active": True},
    {"code": "ES", "name": "Spain", "currency_code": "EUR", "default_language": "es", "has_content": False, "is_active": True},
    {"code": "FR", "name": "France", "currency_code": "EUR", "default_language": "fr", "has_content": False, "is_active": True},
    {"code": "DE", "name": "Germany", "currency_code": "EUR", "default_language": "de", "has_content": False, "is_active": True},
    {"code": "HK", "name": "Hong Kong", "currency_code": "HKD", "default_language": "en", "has_content": False, "is_active": True},
    {"code": "SG", "name": "Singapore", "currency_code": "SGD", "default_language": "en", "has_content": False, "is_active": True},
]


def upgrade() -> None:
    markets = op.create_table(
        "markets",
        sa.Column("code", sa.String(length=2), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("default_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("has_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.bulk_insert(markets, _MARKETS)

    # All existing content + users belong to the GB (UK) market.
    op.add_column(
        "modules",
        sa.Column("market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_modules_market", "modules", "markets", ["market_code"], ["code"])
    op.create_index("ix_modules_market_code", "modules", ["market_code"])

    op.add_column(
        "users",
        sa.Column("home_market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_users_home_market", "users", "markets", ["home_market_code"], ["code"])


def downgrade() -> None:
    op.drop_constraint("fk_users_home_market", "users", type_="foreignkey")
    op.drop_column("users", "home_market_code")
    op.drop_index("ix_modules_market_code", table_name="modules")
    op.drop_constraint("fk_modules_market", "modules", type_="foreignkey")
    op.drop_column("modules", "market_code")
    op.drop_table("markets")
```

- [ ] **Step 3: Apply the migration locally**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/alembic" upgrade head`
Expected: `Running upgrade b0c1d2e3f4a5 -> c1d2e3f4a5b6`. Then `alembic heads` shows a single head `c1d2e3f4a5b6`.

- [ ] **Step 4: Verify downgrade/upgrade round-trips**

Run: `"/Users/leeashmore/Local Repo/.venv/bin/alembic" downgrade -1 && "/Users/leeashmore/Local Repo/.venv/bin/alembic" upgrade head`
Expected: both succeed with no error (clean down + re-up).

- [ ] **Step 5: Confirm the seed module matches the migration**

The `_MARKETS` in the migration and `MARKETS` in `app/seed/markets.py` must be identical in code/currency/language/has_content. Eyeball both; they must agree (a divergence would mean migrated prod ≠ freshly-seeded dev).

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/investikid" && git add backend/alembic/versions/c1d2e3f4a5b6_market_foundation.py && git commit -m "feat(market): migration — markets table + seed + module/user market_code (backfill GB)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Market-based content filtering + profile field

**Files:**
- Modify: `backend/app/services/content_service.py` (add helpers)
- Modify: `backend/app/routers/content.py` (swap gate in `_get_accessible_module` + `list_modules`)
- Modify: `backend/app/services/analytics_service.py` (market filter)
- Modify: `backend/app/schemas/user.py` (`UserProfile.home_market_code`)
- Test: `backend/tests/test_market_content_filter.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_market_content_filter.py`:

```python
import pytest

from app.services.content_service import is_module_in_market, is_module_premium_ok

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_is_module_in_market():
    assert is_module_in_market("GB", "GB") is True
    assert is_module_in_market("US", "GB") is False


def test_is_module_premium_ok():
    assert is_module_premium_ok(module_is_premium=False, is_premium_user=False) is True
    assert is_module_premium_ok(module_is_premium=True, is_premium_user=False) is False
    assert is_module_premium_ok(module_is_premium=True, is_premium_user=True) is True


async def test_gb_user_sees_gb_modules_not_us(client, db_session):
    # The authenticated `client` user defaults to home_market_code 'GB'.
    from app.models.content import Module

    db_session.add(Module(
        topic="savings", title="GB Module", country_codes=[], is_premium=False,
        order_index=900, icon="💷", market_code="GB",
    ))
    db_session.add(Module(
        topic="savings", title="US Module", country_codes=[], is_premium=False,
        order_index=901, icon="💵", market_code="US",
    ))
    await db_session.flush()

    titles = [m["title"] for m in (await client.get("/content/modules")).json()]
    assert "GB Module" in titles
    assert "US Module" not in titles
```

> Adapt fixtures to the project's real ones (the authenticated `client`, `db_session`). Confirm the `/content/modules` route prefix (it may be `/content/modules` or `/modules` — check the router prefix) and that a freshly-registered `client` user has `home_market_code == "GB"` (column default).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_market_content_filter.py -q`
Expected: FAIL (`ImportError: is_module_in_market`).

- [ ] **Step 3: Add the helpers**

In `backend/app/services/content_service.py`, add:

```python
def is_module_in_market(module_market_code: str, home_market_code: str) -> bool:
    """C1 single-market gate: a module is in scope when it belongs to the user's
    home market. (Multi-market enrollment arrives in Sub-project C2.)"""
    return module_market_code == home_market_code


def is_module_premium_ok(*, module_is_premium: bool, is_premium_user: bool) -> bool:
    """Premium gate, decoupled from the (now market-based) region gate."""
    return (not module_is_premium) or is_premium_user
```

(Leave `is_module_accessible` and `content_region_for` defined — other callers/tests may reference them; they're simply no longer used for the content-list/detail gate.)

- [ ] **Step 4: Swap the gate in the content router**

In `backend/app/routers/content.py`:

In `_get_accessible_module`, replace:
```python
    country_ok = not module.country_codes or content_region_for(current_user) in module.country_codes
    if not country_ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
```
with:
```python
    if not is_module_in_market(module.market_code, current_user.home_market_code):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
```
and replace the premium check:
```python
    if not is_module_accessible(
        content_region_for(current_user), is_premium(current_user),
        module.country_codes, module.is_premium,
    ):
        raise premium_required_error("module", module.title)
```
with:
```python
    if not is_module_premium_ok(module_is_premium=module.is_premium, is_premium_user=is_premium(current_user)):
        raise premium_required_error("module", module.title)
```

In `list_modules`, replace:
```python
        country_ok = not m.country_codes or content_region_for(current_user) in m.country_codes
        if not country_ok:
            continue
```
with:
```python
        if not is_module_in_market(m.market_code, current_user.home_market_code):
            continue
```
and replace:
```python
        accessible = is_module_accessible(
            content_region_for(current_user), is_premium(current_user),
            m.country_codes, m.is_premium,
        )
```
with:
```python
        accessible = is_module_premium_ok(module_is_premium=m.is_premium, is_premium_user=is_premium(current_user))
```

Update the imports in `content.py`: add `is_module_in_market, is_module_premium_ok` to the `content_service` import; drop `content_region_for`/`is_module_accessible` only if no longer referenced in the file (grep the file first — keep imports that are still used elsewhere).

- [ ] **Step 5: Apply the market filter in analytics**

In `backend/app/services/analytics_service.py`, the module query uses `Module.country_codes.any(country_code) | (Module.country_codes == [])`. Replace that region filter with `Module.market_code == <the market being reported>`. Read the surrounding function to determine the correct market value (it should reflect the user/report market; if the function reports globally across content, filter by the relevant market parameter or default `"GB"`). Keep the rest of the query intact. If the analytics function has no user/market in scope, default to `Module.market_code == "GB"` (the only market with content) and leave a comment.

- [ ] **Step 6: Add `home_market_code` to the profile schema**

In `backend/app/schemas/user.py`, add to `UserProfile` (after `language`):
```python
    home_market_code: str = "GB"
```

- [ ] **Step 7: Run the tests**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_market_content_filter.py tests/test_markets.py -q`
Expected: PASS. Then run the existing content + users test modules to confirm no regression:
`"/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_content.py tests/test_users.py -q` (use the real content-test filename; grep `tests` for `/content/modules` or `list_modules`).

- [ ] **Step 8: Run ruff**

Run: `"/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/services/content_service.py app/routers/content.py app/services/analytics_service.py app/schemas/user.py`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
cd "/Users/leeashmore/investikid" && git add backend/app/services/content_service.py backend/app/routers/content.py backend/app/services/analytics_service.py backend/app/schemas/user.py backend/tests/test_market_content_filter.py && git commit -m "feat(market): gate content by home market (replaces country_codes region gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full verification + promote

- [ ] **Step 1: Seed parity + full suite**

Run: `cd "/Users/leeashmore/investikid/backend" && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check . && "/Users/leeashmore/Local Repo/.venv/bin/pytest" -q`
Expected: ruff clean; full suite green. (If `tests/test_users.py::test_get_progress_reflects_lesson_completion` fails ONLY with a date like `2026-06-18 == 2026-06-19`, that's the known pre-existing UTC-vs-local midnight flake — it passes on CI's UTC runners; ignore it. Any other failure must be fixed.)

- [ ] **Step 2: Regression sanity — content unchanged for a GB user**

Confirm (via the test in Task 3 + a manual reasoning pass) that the seeded GB curriculum is returned identically to pre-C1 for a default (GB) user. The only content-visibility change is that a module on a non-GB market is hidden.

- [ ] **Step 3: Push to testing + green CI**

```bash
git push origin testing
```
Watch all 6 CI jobs green (backend job runs the migration + full suite).

- [ ] **Step 4: Promote testing → staging → main**

Merge testing → staging (watch CI green), then staging → main (watch CI green; Railway deploys backend + runs the migration on prod). **This migration adds the `markets` table and columns on `modules` + `users` in prod — before it reaches prod, ASK THE USER whether to snapshot the prod DB first** (standing rule). After deploy, confirm prod `/health` 200 and that `/users/me` returns `home_market_code: "GB"`.

---

## Self-Review

**Spec coverage:**
- Unit 1 Market model + seed (10 markets, GB-only content) → Task 1. ✓
- Unit 2 Module.market_code (backfill GB) → Task 1 (column) + Task 2 (migration). ✓
- Unit 3 User.home_market_code (backfill GB) + on profile → Task 1 (column), Task 2 (migration), Task 3 Step 6 (profile). ✓
- Unit 4 market-based filtering (router + analytics; premium/age preserved) → Task 3. ✓
- Unit 5 migration (create+seed markets, add 2 cols, clean downgrade) → Task 2. ✓
- Non-goals respected: no per-market progress/enrollment, no translation storage, no frontend, no currency change, `country_codes` left vestigial. ✓
- Testing: model/seed idempotency, migration round-trip, **filtering regression (GB sees GB, not US)**, profile field → Tasks 1–3. ✓
- Rollout: snapshot prompt at prod promotion → Task 4 Step 4. ✓

**Placeholder scan:** none — full code in every code step; migration + seed given verbatim. The two adapt-to-real-fixtures notes (analytics market value, real test filenames) are explicit instructions, not deferred work.

**Type/name consistency:** `Market.code` (PK str) referenced by `Module.market_code` + `User.home_market_code` FKs; `is_module_in_market(module_market_code, home_market_code)` and `is_module_premium_ok(*, module_is_premium, is_premium_user)` defined in Task 3 Step 3 and used in Step 4; `MARKETS`/`_MARKETS` lists identical across seed (Task 1) and migration (Task 2); `home_market_code` column (Task 1) → migration (Task 2) → profile schema (Task 3). Consistent.
