# Leveling + Premium-Tier Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a level's premium status derive automatically from its position — Levels 1–2 (order_index 0–1) free, Level 3+ (order_index ≥ 2) premium — enforced on every write, with a one-time backfill.

**Architecture:** A single pure helper `premium_for_position(order_index)`; admin create/update/seed route `is_premium` through it (client-supplied `is_premium` is ignored); a chained Alembic **data migration** normalises existing rows. The premium gate itself (`derive_level_states` → `locked_reason="premium"` → `LevelCard` paywall) is unchanged. Backend-only.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic; pytest.

**Conventions:** TDD. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated working-tree `.gitignore` + uncommitted iOS files alone. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify (from `backend/`): `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head && /Users/leeashmore/Local Repo/.venv/bin/pytest`. Work on `testing`; do NOT promote. **STANDING RULE:** this adds a data migration — at prod promotion, ask about a snapshot first.

**Verified facts:**
- `app/services/level_service.py`: `derive_level_states` reads `LevelStateInput.is_premium`; premium level + non-premium user → `locked_reason="premium"`.
- `app/routers/admin.py`: `admin_create_level` builds `Level(... is_premium=payload.is_premium ...)`; `admin_update_level` does `data = payload.model_dump(exclude_unset=True); for k,val in data.items(): setattr(level, k, val)`. `_level_out` returns `is_premium`.
- `app/schemas/admin.py`: `AdminLevelCreate(title, order_index, is_premium=False, pass_threshold=0.7, icon)`, `AdminLevelUpdate(title?, order_index?, is_premium?, pass_threshold?, icon?)`.
- `app/routers/content.py` `list_levels` (~l.149-198): `LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold)` and `LevelOut(... is_premium=lv.is_premium ...)`. (Read path stays as-is; enforce-on-write keeps stored `is_premium` correct.)
- `app/seed/content.py` (~l.825-833): creates one `Level(title="Level 1", order_index=0, is_premium=False, ...)` per module.
- Alembic head: **`b6c7d8e9f0a1`**. Confirm with `alembic heads` before writing the migration.
- `Level` model `__tablename__` — confirm (expected `levels`) before writing raw SQL.

---

## File Structure
- **Modify** `backend/app/services/level_service.py` — add `premium_for_position`.
- **Modify** `backend/app/routers/admin.py` — derive `is_premium` on create + update.
- **Modify** `backend/app/seed/content.py` — route the seeded level's `is_premium` through the helper.
- **Create** `backend/alembic/versions/<rev>_normalise_level_is_premium.py` — backfill data migration.
- **Create/Modify** `backend/tests/test_level_premium_model.py` — helper + admin-enforcement + endpoint gating tests.

---

## Task 1: `premium_for_position` helper + enforce on write (admin + seed)

**Files:** Modify `app/services/level_service.py`, `app/routers/admin.py`, `app/seed/content.py`; Create `backend/tests/test_level_premium_model.py`.

- [ ] **Step 1: Write failing tests** — Create `backend/tests/test_level_premium_model.py`:

```python
from app.services.level_service import premium_for_position


def test_premium_for_position():
    assert premium_for_position(0) is False
    assert premium_for_position(1) is False
    assert premium_for_position(2) is True
    assert premium_for_position(5) is True
```

Then add admin-enforcement tests mirroring the existing admin test client/auth (copy the admin-auth fixture + a module-creation helper from `tests/test_admin_content.py` or whichever admin test file exists — find it first). Assert:
- `POST /admin/modules/{id}/levels` with `order_index=0, is_premium=True` (client lies) → response `is_premium is False`.
- same with `order_index=2, is_premium=False` → response `is_premium is True`.
- `PUT /admin/levels/{id}` moving a level from `order_index=1` to `2` → `is_premium True`; moving `2`→`0` → `is_premium False`.

(Use the real admin auth pattern — do not bypass it. If unsure which fixture, grep `tests/` for `admin_client`/`_admin_login`/`X-Admin`.)

- [ ] **Step 2: Run to verify it fails** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_level_premium_model.py -q` → FAIL (no `premium_for_position`; enforcement not applied).

- [ ] **Step 3: Add the helper** — in `app/services/level_service.py` (module scope):

```python
def premium_for_position(order_index: int) -> bool:
    """Levels 1-2 (order_index 0-1) are free; Level 3+ (order_index >= 2) is premium."""
    return order_index >= 2
```

- [ ] **Step 4: Enforce on admin create/update** — in `app/routers/admin.py`, add `from app.services.level_service import premium_for_position` (with the other service imports).
  - `admin_create_level`: build the `Level` with `is_premium=premium_for_position(payload.order_index)` (do NOT use `payload.is_premium`).
  - `admin_update_level`: after the `for k, val in data.items(): setattr(...)` loop, drop any client `is_premium` and recompute from the (possibly updated) order_index:

```python
    data = payload.model_dump(exclude_unset=True)
    data.pop("is_premium", None)  # derived from position, never client-set
    for k, val in data.items():
        setattr(level, k, val)
    level.is_premium = premium_for_position(level.order_index)
```

(Leave `AdminLevelCreate`/`AdminLevelUpdate` schemas as-is for backward compatibility — the field is simply ignored now. A follow-up can make the admin form show it read-only; out of scope here.)

- [ ] **Step 5: Route seed through the helper** — in `app/seed/content.py`, where the level is created, set `is_premium=premium_for_position(<order_index>)` instead of the hardcoded `False` (functionally unchanged for the order_index=0 "Level 1", but keeps the invariant if seed ever adds more levels). Import the helper.

- [ ] **Step 6: Run to verify it passes** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_level_premium_model.py -q` → PASS. If a DB-backed admin test hangs ~90s it's the local Postgres (CLAUDE.md) — note it, rely on CI.

- [ ] **Step 7: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check app/services/level_service.py app/routers/admin.py app/seed/content.py tests/test_level_premium_model.py
cd /Users/leeashmore/investikid
git add backend/app/services/level_service.py backend/app/routers/admin.py backend/app/seed/content.py backend/tests/test_level_premium_model.py
git commit -m "$(cat <<'EOF'
feat(content): derive level is_premium from position (L1-2 free, L3+ premium)

premium_for_position(order_index)=order_index>=2, enforced on admin
create/update and seed; client-supplied is_premium is ignored. Gate itself
(derive_level_states/paywall) unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Backfill data migration + end-to-end gating test

**Files:** Create `backend/alembic/versions/<rev>_normalise_level_is_premium.py`; extend `backend/tests/test_level_premium_model.py`.

- [ ] **Step 1: Confirm head + table name** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/alembic heads` (expect `b6c7d8e9f0a1`); confirm `Level.__tablename__` in `app/models/content.py` (expected `levels`).

- [ ] **Step 2: Create the migration** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/alembic revision -m "normalise level is_premium by position"`. Edit the generated file so `down_revision = "b6c7d8e9f0a1"` (the confirmed head) and:

```python
def upgrade() -> None:
    # Levels 1-2 free, Level 3+ premium — align existing rows with the position rule.
    op.execute("UPDATE levels SET is_premium = (order_index >= 2)")


def downgrade() -> None:
    # Data normalisation has no meaningful inverse.
    pass
```

(Use the real table name if not `levels`. Idempotent by construction — safe to re-run.)

- [ ] **Step 3: Apply + verify** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head` → succeeds. `alembic heads` shows the new single head.

- [ ] **Step 4: Add an end-to-end gating test** — extend `tests/test_level_premium_model.py`: via the admin client create a module + a Level at `order_index=2` (→ premium by Task 1). Then:
  - a **non-premium** child calling `GET /modules/{id}/levels` sees that level with `is_premium True`, `state="locked"`, `locked_reason="premium"`;
  - a **premium** child sees it not premium-locked (state gated only by progression — likely `"locked"` with `locked_reason="progression"` if earlier levels are incomplete, or `in_progress` if it's reachable). Assert `locked_reason != "premium"` for the premium user.

(Reuse the existing premium/non-premium user fixtures — grep `tests/` for how `is_premium` users are built, e.g. an existing levels-endpoint or premium test. Mirror that exactly.)

- [ ] **Step 5: Run** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_level_premium_model.py -q` → PASS.

- [ ] **Step 6: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .
cd /Users/leeashmore/investikid
git add backend/alembic/versions/ backend/tests/test_level_premium_model.py
git commit -m "$(cat <<'EOF'
feat(content): backfill level is_premium by position (data migration)

Chained data migration normalising existing levels to the position rule, plus
an end-to-end test that a Level 3 is premium-locked for free users and not for
premium users.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Backend gate** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head && /Users/leeashmore/Local Repo/.venv/bin/pytest -q` (note any local-Postgres hang as environmental).
- [ ] **Step 2: Push + report** — `cd /Users/leeashmore/investikid && git push origin testing`; report CI status (all jobs, incl. backend + the migration applying on the testing DB). Do NOT promote. Leave unrelated working-tree files alone.

---

## Self-Review

**1. Spec coverage:** "premium by position" → Task 1 helper + enforce-on-write (create/update/seed). "Backfill existing rows" → Task 2 data migration. "Gate already wired, no FE change" → confirmed (read path + LevelCard untouched). End-to-end premium gating validated → Task 2 Step 4. Standing migration/snapshot rule → noted in header + Task 3. ✓

**2. Placeholder scan:** Helper + endpoint edits + migration body are concrete. The two "find the real fixture" notes (admin auth, premium-user) point at existing test files to mirror, not vague gaps. ✓

**3. Type consistency:** `premium_for_position(order_index: int) -> bool` used identically in admin create/update + seed; `is_premium` derivation never reads client input after this. Read path (`list_levels`, `derive_level_states`) unchanged — still reads the now-guaranteed-correct stored `is_premium`. ✓
