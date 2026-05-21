# Tier System + Test Accounts Implementation Plan (Sub-project 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the free/premium tier real, grantable without Stripe (parent toggle + ops CLI), observable (sample premium content + UI), and testable end-to-end (seeded per-tier accounts), all behind a single entitlement seam.

**Architecture:** One `app/services/entitlements.py` module is the sole read (`is_premium`) and write (`set_premium`) seam for premium status. ~5 user-entitlement call sites are refactored to read through it (pure indirection — suite must stay green). A parent endpoint and an ops CLI both mutate via `set_premium` (audited). Sample premium seed fixtures + prod-guarded tier test accounts make tiers exercisable; the frontend shows a tier badge, graceful locked-state affordances, and a parent upgrade/downgrade toggle.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic (no migration needed — no schema change), pytest (`asyncio_mode=auto`, **session-scoped** `db_session`/`client` fixtures → async tests need `loop_scope="session"`), ruff (E/F/I/UP, 120 cols), React/TS + Vite, TanStack Query.

**Conventions (read before starting):**
- Backend cmds from `/Users/leeashmore/Local Repo/invest-ed/backend`; frontend from `invest-ed/frontend`; git from repo root `/Users/leeashmore/Local Repo` using `invest-ed/...` paths.
- Async test using `db_session`/`client`: if the test file already has module-level `pytestmark = pytest.mark.asyncio(loop_scope="session")`, append and inherit it. New test file → add that file-level `pytestmark` + `import pytest`. A single async test added to an all-sync file → decorate ONLY that function `@pytest.mark.asyncio(loop_scope="session")` (do NOT add a file-level mark to an all-sync file).
- A `security_reminder` PreToolUse hook blocks writing literal dangerous-API tokens even in docs — not relevant to this sub-project's code, but if a doc trips it, reword without the literal substring.
- `ruff check` changed files and fix before every commit. Commit trailer: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`.
- Full backend suite (currently 234) must stay green after every task. Delivery: controller commits to `main`; the `claude/lucid-cray-03eff5` branch (PR #7) is synced separately by the controller — implementers just commit to the working tree on `main`.

**Grounding facts (verified against the real code):**
- `User.is_premium: Mapped[bool]` exists (default `False`, `nullable=False`). No schema/migration change anywhere in this sub-project.
- `AuditLog` columns: `id, user_id (nullable), event_type (str50), ip_address (str45 nullable), metadata_json (JSON nullable), created_at`. Record actor in `metadata_json`.
- `app/schemas/user.py UserProfile` **already** has `is_premium: bool` → `/users/me` already exposes it. Frontend `src/api/auth.ts` `Me` type **already** has `is_premium: boolean`. No change needed for child-side plumbing.
- `app/routers/content.py`: `get_module` already raises `403 "Module requires premium"` for a free user on a premium module (clean, not 500); `list_modules` already returns `locked: not accessible` per `ModuleOut`. Premium gate logic is `is_module_accessible(country_code, is_premium_user, country_codes, module_is_premium)` in `app/services/content_service.py`.
- User-entitlement read sites to refactor: `app/routers/ai.py` two sites (`premium=current_user.is_premium`), `app/routers/simulator.py:617` (`not current_user.is_premium`), `app/routers/content.py` two sites (the `current_user.is_premium` arg to `is_module_accessible`, in `get_module` ~L50 and `list_modules` ~L70). **`app/routers/gamification.py`'s `is_premium=c.is_premium` is the Challenge model's own attribute, NOT user entitlement — DO NOT refactor it.**
- Parent routes pattern (`app/routers/parent.py`): `_get_owned_child(session, parent_email, user_id)` (404 if not owned, `include_deleted=True`), `freeze_child` mirrors the shape we need (410 if `child.deleted_at`, `await session.commit()`, return dict). Parent schemas in `app/schemas/parent.py` (`ChildOut`, `FreezeRequest`).
- Seed pattern to mirror: `app/seed/compliance_accounts.py` (`_ensure` helper, `if settings.environment == "production": return`, `_PASSWORD = "TestPassword1234!"`, commits internally). `app/seed/run.py` calls `seed_modules_and_lessons` + `seed_badges_and_challenges` then commits. `app/cli.py` currently dispatches only `purge-accounts` via `run(argv)`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/services/entitlements.py` | Create | `is_premium(user)`, `set_premium(session, child, *, value, actor)` — the only entitlement seam |
| `backend/app/routers/ai.py` | Modify | 2 sites read via `is_premium()` |
| `backend/app/routers/simulator.py` | Modify | L617 reads via `is_premium()` |
| `backend/app/routers/content.py` | Modify | 2 sites pass `is_premium(current_user)` to `is_module_accessible` |
| `backend/app/schemas/parent.py` | Modify | `PremiumToggleRequest`; `ChildOut` gains `is_premium` |
| `backend/app/routers/parent.py` | Modify | `POST /parent/children/{id}/premium`; `list_children` returns `is_premium` |
| `backend/app/cli.py` | Modify | `grant-premium <ident> [--revoke]` command |
| `backend/app/seed/content.py` | Modify | mark 2 module specs `is_premium=True` (sample fixtures) |
| `backend/app/seed/gamification.py` | Modify | mark 1 challenge spec `is_premium=True` (sample fixture) |
| `backend/app/seed/tier_accounts.py` | Create | `seed_tier_accounts` (prod-guarded, idempotent) |
| `backend/app/seed/run.py` | Modify | wire `seed_tier_accounts` |
| `docs/testing/test-accounts.md` | Create | test-account/tier matrix |
| `frontend/src/api/parent.ts` | Modify | `Child` gains `is_premium`; `setChildPremium` |
| `frontend/src/components/ChildCard.tsx` | Modify | premium toggle (mirror freeze mutation) |
| `frontend/src/components/child/TierBadge.tsx` | Create | small Free/Premium badge |
| `frontend/src/components/child/Shell.tsx` | Modify | render `TierBadge` from session |
| `frontend/src/components/child/ModuleCard.tsx` | Modify | graceful locked-state affordance |
| `backend/tests/test_entitlements.py` | Create | seam unit tests |
| `backend/tests/test_parent_dashboard.py` | Modify | premium-toggle integration |
| `backend/tests/test_cli.py` | Create | `grant-premium` CLI test |
| `backend/tests/test_seed.py` | Modify | tier-account seed test |
| `backend/tests/test_content.py` | Modify | content-gate free vs premium |

---

### Task 1: Entitlement service (the seam)

**Files:**
- Create: `backend/app/services/entitlements.py`
- Test: `backend/tests/test_entitlements.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_entitlements.py`:

```python
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.user import User
from app.services.entitlements import is_premium, set_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk(session, premium=False):
    u = User(
        email=f"ent-{uuid.uuid4().hex[:8]}@example.com",
        username=f"ent{uuid.uuid4().hex[:8]}",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=premium,
    )
    session.add(u)
    await session.flush()
    return u


async def test_is_premium_reads_column(db_session):
    free = await _mk(db_session, premium=False)
    paid = await _mk(db_session, premium=True)
    assert is_premium(free) is False
    assert is_premium(paid) is True


async def test_set_premium_grants_and_audits(db_session):
    u = await _mk(db_session, premium=False)
    changed = await set_premium(db_session, u, value=True, actor="parent@test")
    assert changed is True
    assert u.is_premium is True
    rows = (await db_session.scalars(
        select(AuditLog).where(AuditLog.user_id == u.id)
    )).all()
    grant = [r for r in rows if r.event_type == "premium_grant"]
    assert len(grant) == 1
    assert grant[0].metadata_json == {"actor": "parent@test", "old": False, "new": True}


async def test_set_premium_idempotent_noop(db_session):
    u = await _mk(db_session, premium=True)
    changed = await set_premium(db_session, u, value=True, actor="cli")
    assert changed is False
    rows = (await db_session.scalars(
        select(AuditLog).where(AuditLog.user_id == u.id)
    )).all()
    assert rows == []


async def test_set_premium_revoke_audits(db_session):
    u = await _mk(db_session, premium=True)
    changed = await set_premium(db_session, u, value=False, actor="cli")
    assert changed is True
    assert u.is_premium is False
    rows = (await db_session.scalars(
        select(AuditLog).where(
            AuditLog.user_id == u.id, AuditLog.event_type == "premium_revoke"
        )
    )).all()
    assert len(rows) == 1
    assert rows[0].metadata_json == {"actor": "cli", "old": True, "new": False}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_entitlements.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.entitlements'`.

- [ ] **Step 3: Implement the seam**

Create `backend/app/services/entitlements.py`:

```python
from __future__ import annotations

from app.models.audit import AuditLog
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


def is_premium(user: User) -> bool:
    """Single read seam for premium entitlement.

    Today this is the per-child `is_premium` column. A future family or
    Stripe-backed model changes ONLY this function's internals — callers
    must never read `user.is_premium` directly.
    """
    return user.is_premium


async def set_premium(
    session: AsyncSession, child: User, *, value: bool, actor: str
) -> bool:
    """Single write seam for premium entitlement.

    Idempotent: no-op (returns False, no audit row) when already at `value`.
    On change: flips the column and writes one AuditLog row attributing the
    change to `actor`. Does NOT commit — the caller owns the transaction
    (consistent with other service-layer writers).
    """
    old = child.is_premium
    if old == value:
        return False
    child.is_premium = value
    session.add(AuditLog(
        user_id=child.id,
        event_type="premium_grant" if value else "premium_revoke",
        metadata_json={"actor": actor, "old": old, "new": value},
    ))
    await session.flush()
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_entitlements.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/services/entitlements.py invest-ed/backend/tests/test_entitlements.py
git commit -m "$(printf 'feat(tier): entitlement service seam (is_premium/set_premium)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 2: Refactor read sites to the seam (pure indirection)

**Files:**
- Modify: `backend/app/routers/ai.py`, `backend/app/routers/simulator.py`, `backend/app/routers/content.py`

- [ ] **Step 1: Confirm the exact sites**

Run: `cd invest-ed/backend && grep -n "current_user.is_premium" app/routers/ai.py app/routers/simulator.py app/routers/content.py`
Expected: 2 hits in `ai.py`, 1 in `simulator.py` (the `place_trade` gate at ~L617), 2 in `content.py` (`get_module` ~L50, `list_modules` ~L70). (`gamification.py` will NOT appear — `c.is_premium` there is the Challenge attribute; do not touch it.)

- [ ] **Step 2: Refactor `ai.py`**

In `app/routers/ai.py` add to imports (with the other `from app.services...` imports): `from app.services.entitlements import is_premium`. Replace both occurrences of `premium=current_user.is_premium` with `premium=is_premium(current_user)`.

- [ ] **Step 3: Refactor `simulator.py`**

In `app/routers/simulator.py` add `from app.services.entitlements import is_premium` (with the other `from app.services...` imports). Change line ~617 from:
```python
    if not current_user.is_premium and not provider.is_free_tier(payload.ticker, payload.exchange):
```
to:
```python
    if not is_premium(current_user) and not provider.is_free_tier(payload.ticker, payload.exchange):
```

- [ ] **Step 4: Refactor `content.py`**

In `app/routers/content.py` add `from app.services.entitlements import is_premium` (with other service imports). In BOTH `is_module_accessible(...)` calls, replace the `current_user.is_premium` argument with `is_premium(current_user)`. (The call shape is `is_module_accessible(current_user.country_code, current_user.is_premium, ...code/flag...)` → `is_module_accessible(current_user.country_code, is_premium(current_user), ...)`. Do not change argument order or anything else.)

- [ ] **Step 5: Verify pure indirection — full suite green**

Run: `python -m pytest -q`
Expected: 234 passed, 0 failed (behaviour is byte-identical; any failure means the refactor changed behaviour — fix the refactor, NOT the test). Then `ruff check app/routers/ai.py app/routers/simulator.py app/routers/content.py` → clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/routers/ai.py invest-ed/backend/app/routers/simulator.py invest-ed/backend/app/routers/content.py
git commit -m "$(printf 'refactor(tier): route entitlement reads through is_premium() seam\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 3: Parent premium-toggle endpoint

**Files:**
- Modify: `backend/app/schemas/parent.py`, `backend/app/routers/parent.py`
- Test: `backend/tests/test_parent_dashboard.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_parent_dashboard.py` (file already has the parent-auth helper used by freeze/erasure/export tests — reuse the SAME helper/pattern those tests use to obtain an authenticated parent session; inspect the file first and mirror it. The skeleton below names it `_setup` — replace with the file's actual helper):

```python
async def test_parent_can_toggle_child_premium(client, db_session):
    from sqlalchemy import select
    from app.models.user import User
    from app.models.audit import AuditLog

    await client.post("/auth/register", json={
        "username": "ptierkid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "ptierparent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    child = await db_session.scalar(select(User).where(User.username == "ptierkid"))
    cookies = await _setup(client, db_session, "ptierparent@example.com")

    up = await client.post(
        f"/parent/children/{child.id}/premium", json={"premium": True}, cookies=cookies)
    assert up.status_code == 200
    assert up.json() == {"status": "ok", "premium": True}
    await db_session.refresh(child)
    assert child.is_premium is True
    aud = (await db_session.scalars(select(AuditLog).where(
        AuditLog.user_id == child.id, AuditLog.event_type == "premium_grant"))).all()
    assert len(aud) == 1

    down = await client.post(
        f"/parent/children/{child.id}/premium", json={"premium": False}, cookies=cookies)
    assert down.status_code == 200
    assert down.json() == {"status": "ok", "premium": False}
    await db_session.refresh(child)
    assert child.is_premium is False


async def test_parent_premium_toggle_not_owned_404(client, db_session):
    import uuid
    cookies = await _setup(client, db_session, "ptierstranger@example.com")
    resp = await client.post(
        f"/parent/children/{uuid.uuid4()}/premium", json={"premium": True}, cookies=cookies)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parent_dashboard.py -k "toggle_child_premium or premium_toggle_not_owned" -v`
Expected: FAIL (endpoint 404 / not implemented).

- [ ] **Step 3: Add the request schema + ChildOut field**

In `backend/app/schemas/parent.py`: add a class
```python
class PremiumToggleRequest(BaseModel):
    premium: bool
```
and add `is_premium: bool` to `ChildOut` (after `is_active: bool`).

- [ ] **Step 4: Implement the endpoint + expose is_premium in list_children**

In `backend/app/routers/parent.py`:
- Imports: extend `from app.schemas.parent import ChildOut, FreezeRequest` to also import `PremiumToggleRequest`; add `from app.services.entitlements import set_premium`.
- In `list_children`, add `is_premium=r.is_premium,` to the `ChildOut(...)` construction (alongside `is_active=r.is_active,`).
- Add this endpoint (mirror `freeze_child`'s shape) after `freeze_child`:

```python
@router.post("/children/{user_id}/premium")
async def set_child_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    await set_premium(session, child, value=payload.premium, actor=parent_email)
    await session.commit()
    return {"status": "ok", "premium": payload.premium}
```

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_parent_dashboard.py -q` then full `python -m pytest -q`.
Expected: all pass (new 2 + existing parent tests + 234 baseline incl. the new entitlement tests). `ruff check app/routers/parent.py app/schemas/parent.py` → clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/routers/parent.py invest-ed/backend/app/schemas/parent.py invest-ed/backend/tests/test_parent_dashboard.py
git commit -m "$(printf 'feat(tier): parent premium upgrade/downgrade endpoint (audited, IDOR-safe)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 4: Ops CLI `grant-premium`

**Files:**
- Modify: `backend/app/cli.py`
- Test: `backend/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_cli.py`:

```python
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app import cli
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk(session, username, email):
    u = User(
        email=email, username=username, password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
        is_premium=False,
    )
    session.add(u)
    await session.flush()
    return u


async def test_grant_premium_by_username_then_revoke(db_session, monkeypatch):
    u = await _mk(db_session, "cliuser1", "cliuser1@example.com")
    uid = u.id

    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)

    code = await cli.run(["grant-premium", "cliuser1"])
    assert code == 0
    refreshed = await db_session.scalar(select(User).where(User.id == uid))
    assert refreshed.is_premium is True

    code = await cli.run(["grant-premium", "cliuser1", "--revoke"])
    assert code == 0
    refreshed = await db_session.scalar(select(User).where(User.id == uid))
    assert refreshed.is_premium is False


async def test_grant_premium_by_email(db_session, monkeypatch):
    await _mk(db_session, "cliuser2", "cliuser2@example.com")

    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)

    code = await cli.run(["grant-premium", "cliuser2@example.com"])
    assert code == 0
    u = await db_session.scalar(select(User).where(User.username == "cliuser2"))
    assert u.is_premium is True


async def test_grant_premium_unknown_user_exit_2(db_session, monkeypatch):
    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)
    code = await cli.run(["grant-premium", "nobody@example.com"])
    assert code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL (`grant-premium` unknown → usage/return 2, or AttributeError).

- [ ] **Step 3: Implement the command**

Rewrite `backend/app/cli.py`'s `run()` to dispatch both commands (keep `purge-accounts` behaviour identical; add `grant-premium`). Full file:

```python
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from datetime import date

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.user import User
from app.services.entitlements import set_premium
from app.services.retention import purge_expired_accounts


async def _session_scope() -> AsyncIterator:
    async with async_session_factory() as session:
        yield session


async def _purge() -> int:
    gen = _session_scope()
    session = await gen.__anext__()
    try:
        n = await purge_expired_accounts(session, date.today())
        print(f"purged {n} account(s)")
        return 0
    finally:
        await gen.aclose()


async def _grant_premium(argv: list[str]) -> int:
    args = [a for a in argv if a != "--revoke"]
    revoke = "--revoke" in argv
    if len(args) != 1:
        print("usage: python -m app.cli grant-premium <email|username> [--revoke]",
              file=sys.stderr)
        return 2
    ident = args[0].lower().strip()
    gen = _session_scope()
    session = await gen.__anext__()
    try:
        user = await session.scalar(
            select(User).where((User.email == ident) | (User.username == ident))
        )
        if user is None:
            print(f"user not found: {ident}", file=sys.stderr)
            return 2
        changed = await set_premium(
            session, user, value=not revoke, actor="cli"
        )
        await session.commit()
        verb = "revoked" if revoke else "granted"
        print(f"{verb} premium for {user.username}" if changed
              else f"no-op ({user.username} already {'free' if revoke else 'premium'})")
        return 0
    finally:
        await gen.aclose()


async def run(argv: list[str]) -> int:
    if argv and argv[0] == "purge-accounts":
        return await _purge()
    if argv and argv[0] == "grant-premium":
        return await _grant_premium(argv[1:])
    print("usage: python -m app.cli {purge-accounts | grant-premium <id> [--revoke]}",
          file=sys.stderr)
    return 2


def main() -> None:
    raise SystemExit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py tests/test_retention.py -v`
Expected: all pass (new CLI tests + the existing retention CLI test still green — `purge-accounts` behaviour unchanged). `ruff check app/cli.py tests/test_cli.py` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/cli.py invest-ed/backend/tests/test_cli.py
git commit -m "$(printf 'feat(tier): ops CLI grant-premium command (audited via set_premium)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 5: Sample premium content fixtures

**Files:**
- Modify: `backend/app/seed/content.py`, `backend/app/seed/gamification.py`
- Test: `backend/tests/test_content.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content.py` (inspect the file's existing fixtures/login helper and reuse them; it already exercises `/modules` and module access — mirror its style. Skeleton — adapt the helper/fixture names to the file's real ones):

```python
async def test_premium_module_gated_for_free_user(client, db_session):
    # Seed real content (includes the 2 sample-premium modules).
    from app.seed.content import seed_modules_and_lessons
    from app.seed.gamification import seed_badges_and_challenges
    from sqlalchemy import select
    from app.models.content import Module
    await seed_modules_and_lessons(db_session)
    await seed_badges_and_challenges(db_session)
    await db_session.commit()

    premium_mod = await db_session.scalar(
        select(Module).where(Module.is_premium.is_(True)).limit(1))
    assert premium_mod is not None, "expected at least one seeded premium module"

    # Free user (default is_premium=False).
    await _login_child(client, "freecontent@example.com", "freecontentkid")
    detail = await client.get(f"/modules/{premium_mod.id}")
    assert detail.status_code == 403  # "Module requires premium"

    lst = await client.get("/modules")
    assert lst.status_code == 200
    locked = [m for m in lst.json() if m["id"] == str(premium_mod.id)]
    assert locked and locked[0]["locked"] is True
```

(Replace `_login_child` with the real helper that registers+logs in a non-premium child in `tests/test_content.py`. If the file uses fixtures instead, follow that.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_content.py -k premium_module_gated_for_free_user -v`
Expected: FAIL — `assert premium_mod is not None` (no seeded module is premium yet).

- [ ] **Step 3: Mark sample fixtures premium**

In `backend/app/seed/content.py`: the module specs are dicts with an `is_premium` key. Set `is_premium` to `True` for exactly TWO specs — the crypto module (the one with `"icon": "₿"`, `order_index 6`) and the analytics/advanced module (the one with `"icon": "📊"`, `order_index 10`). Add an inline comment on each changed line: `# SAMPLE premium gating fixture — real premium curriculum is sub-project #4`. Change nothing else.

In `backend/app/seed/gamification.py`: the challenge specs have `"is_premium": False`. Set exactly ONE challenge spec to `"is_premium": True` (the second challenge spec). Add the same inline comment. Change nothing else.

- [ ] **Step 4: Run test to verify it passes + full suite**

Run: `python -m pytest tests/test_content.py -q` then `python -m pytest -q`.
Expected: new test passes; full suite 234+ green (existing content/seed tests must still pass — if a seed test asserts an exact count of free modules or "no premium modules", that assertion encoded the old all-free state and is now contradicted by the spec decision: update ONLY that directly-contradicted assertion minimally and report it; do NOT weaken unrelated tests). `ruff check app/seed/content.py app/seed/gamification.py` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/seed/content.py invest-ed/backend/app/seed/gamification.py invest-ed/backend/tests/test_content.py
git commit -m "$(printf 'feat(tier): seed sample premium modules + challenge (gating fixtures)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 6: Tier test accounts seed

**Files:**
- Create: `backend/app/seed/tier_accounts.py`
- Modify: `backend/app/seed/run.py`
- Test: `backend/tests/test_seed.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_seed.py` (it already has `test_compliance_accounts_seed_idempotent` — mirror it exactly; file already has the right pytestmark since that test is async):

```python
async def test_tier_accounts_seed_idempotent(db_session):
    from sqlalchemy import func, select
    from app.models.user import User
    from app.seed.tier_accounts import seed_tier_accounts

    await seed_tier_accounts(db_session)
    await seed_tier_accounts(db_session)
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_(["tier_parent", "premium_child", "free_child"])
        )
    )
    assert count == 3
    premium = await db_session.scalar(
        select(User).where(User.username == "premium_child"))
    free = await db_session.scalar(
        select(User).where(User.username == "free_child"))
    assert premium.is_premium is True
    assert free.is_premium is False
    assert premium.parent_email == "tier-parent@test.invest-ed"
    assert free.parent_email == "tier-parent@test.invest-ed"


async def test_tier_accounts_seed_prod_guarded(db_session, monkeypatch):
    from sqlalchemy import func, select
    from app.core.config import settings
    from app.models.user import User
    from app.seed.tier_accounts import seed_tier_accounts

    monkeypatch.setattr(settings, "environment", "production")
    await seed_tier_accounts(db_session)
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_(["tier_parent", "premium_child", "free_child"])
        )
    )
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_seed.py -k tier_accounts -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.seed.tier_accounts'`.

- [ ] **Step 3: Implement the seeder**

Create `backend/app/seed/tier_accounts.py` (mirror `compliance_accounts.py` exactly — own `_ensure`, prod guard, `_PASSWORD`, internal commit):

```python
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserProgress

_PASSWORD = "TestPassword1234!"


async def _ensure(session: AsyncSession, **kwargs) -> bool:
    existing = await session.scalar(
        select(User).where(User.username == kwargs["username"])
    )
    if existing:
        return False
    user = User(password_hash=hash_password(_PASSWORD), **kwargs)
    session.add(user)
    await session.flush()
    session.add(UserProgress(user_id=user.id))
    return True


async def seed_tier_accounts(session: AsyncSession) -> None:
    if settings.environment == "production":
        return
    now = datetime.now(UTC)
    # Parent who "owns" the two child accounts (also a self-login adult).
    await _ensure(
        session,
        email="tier-parent@test.invest-ed",
        username="tier_parent",
        dob=date(1990, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
        email_verified_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="premium-child@test.invest-ed",
        username="premium_child",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="tier-parent@test.invest-ed",
        is_active=True,
        is_premium=True,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="free-child@test.invest-ed",
        username="free_child",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="tier-parent@test.invest-ed",
        is_active=True,
        is_premium=False,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await session.commit()
```

(Before writing, open `app/models/user.py` and confirm every kwarg above is a real `User` column — `email, username, dob, country_code, currency_code, parent_email, is_active, is_premium, parent_consent_given_at, email_verified_at, policy_version_accepted, policy_accepted_at` all exist per sub-projects 1–2. If any name differs, adapt and report.)

- [ ] **Step 4: Wire into run.py**

In `backend/app/seed/run.py` add `from app.seed.tier_accounts import seed_tier_accounts` and call `await seed_tier_accounts(session)` inside `main()` after `seed_badges_and_challenges(session)` and before the final `await session.commit()` (it also commits internally — harmless; mirrors how `seed_compliance_accounts` self-commits). Also import + call `seed_compliance_accounts` is NOT in scope — leave run.py's existing content/gamification calls intact, only add the tier one.

- [ ] **Step 5: Run tests to verify they pass + full suite**

Run: `python -m pytest tests/test_seed.py -q` then `python -m pytest -q`.
Expected: all pass (3 accounts, idempotent, prod-guarded; 234+ baseline green). `ruff check app/seed/tier_accounts.py app/seed/run.py tests/test_seed.py` → clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/backend/app/seed/tier_accounts.py invest-ed/backend/app/seed/run.py invest-ed/backend/tests/test_seed.py
git commit -m "$(printf 'feat(tier): prod-guarded idempotent tier test accounts seed\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 7: Test-account matrix doc

**Files:**
- Create: `docs/testing/test-accounts.md`

- [ ] **Step 1: Write the doc**

Create `invest-ed/docs/testing/test-accounts.md` documenting every seeded dev/test account, all with password `TestPassword1234!`, all skipped when `environment == "production"`. Include a table with columns: Username | Email | Tier/Role | Parent | Purpose / what to test. Rows (from `seed_tier_accounts` + `seed_compliance_accounts`):

- `tier_parent` — `tier-parent@test.invest-ed` — Parent (adult self-login) — — — parent dashboard; owns premium_child & free_child; test the premium upgrade/downgrade toggle.
- `premium_child` — `premium-child@test.invest-ed` — Premium child — tier-parent — premium tier: premium modules unlocked, higher tutor limit, premium stock tickers, premium LLM tier, Premium badge.
- `free_child` — `free-child@test.invest-ed` — Free child — tier-parent — free tier: premium modules show locked-state, lower tutor limit, free stock tickers only.
- `consented_kid` — (no email) — Free child, parental consent given — parent@test.invest-ed — compliance: active under-threshold account.
- `pending_consent_kid` — (no email) — Free child, awaiting consent (inactive) — parent@test.invest-ed — compliance: pending-consent gate.
- `selfteen` — `selfteen@test.invest-ed` — Free teen (self, email unverified) — — — compliance: email-verification flow.

Add a short "How to seed" note: `cd invest-ed/backend && python -m app.seed.run` (idempotent; auto-skipped in production), and "How to grant premium ad hoc": `python -m app.cli grant-premium <email|username> [--revoke]`. State the security note: these accounts and the seeders are guarded by `settings.environment == "production"` and must never exist in prod.

- [ ] **Step 2: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/docs/testing/test-accounts.md
git commit -m "$(printf 'docs(tier): test-account / tier matrix\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 8: Frontend — tier badge

**Files:**
- Create: `frontend/src/components/child/TierBadge.tsx`
- Modify: `frontend/src/components/child/Shell.tsx`

- [ ] **Step 1: Inspect**

Read `frontend/src/components/child/Shell.tsx` (it renders `TopNav username={session.data.username}` and `VerifyEmailBanner profile={session.data}`; `session.data` is the `Me` object which already has `is_premium: boolean`). Read an existing small badge/chip for styling conventions (e.g. the status chips in `ChildCard.tsx` or any existing badge) to match Tailwind classes.

- [ ] **Step 2: Create the badge**

Create `frontend/src/components/child/TierBadge.tsx`:

```tsx
type Props = { premium: boolean };

export function TierBadge({ premium }: Props) {
  return (
    <span
      data-testid="tier-badge"
      className={
        premium
          ? 'rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900'
          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600'
      }
    >
      {premium ? 'Premium ✨' : 'Free'}
    </span>
  );
}
```

- [ ] **Step 3: Render it in Shell**

In `frontend/src/components/child/Shell.tsx`, import `TierBadge` and render `<TierBadge premium={session.data.is_premium} />` adjacent to where the username/TopNav is shown (place it where it reads naturally next to the user identity; do not restructure the layout — a single element addition). Keep the `!session.data` / `isLoading` guards intact (badge only renders when `session.data` exists).

- [ ] **Step 4: Verify build/type**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npm run build`
Expected: both clean/success. (No unit test required — render is exercised via the existing Shell tests; if `tests/unit` has a Shell test, run `npm test -- Shell` and confirm still green.)

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/frontend/src/components/child/TierBadge.tsx invest-ed/frontend/src/components/child/Shell.tsx
git commit -m "$(printf 'feat(tier): child tier badge in Shell\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 9: Frontend — graceful locked-state on premium modules

**Files:**
- Modify: `frontend/src/components/child/ModuleCard.tsx`
- Test: `frontend/tests/unit/` (add a focused render test if a sibling pattern exists; otherwise tsc/build is the gate — state which)

- [ ] **Step 1: Inspect**

Read `frontend/src/components/child/ModuleCard.tsx` and how it receives a module (the API `ModuleOut` includes `locked: boolean` and `is_premium: boolean`). Identify how a locked module currently renders (it likely still links/navigates). Read a sibling test in `frontend/tests/unit/` to learn the render-test convention (e.g. `child-Market.test.tsx`).

- [ ] **Step 2: Write a failing render test (if the unit harness supports it)**

If `frontend/tests/unit/` has component render tests, add `frontend/tests/unit/child-ModuleCard.test.tsx` asserting: given a module `{ locked: true, is_premium: true }`, the card shows a "Premium" lock affordance (text matched by `/premium/i` + a lock indicator) and does NOT render an enabled navigation link into the module; given `{ locked: false }` it renders the normal link. Mirror the sibling test's imports/render setup. Run it → it FAILS (current card navigates regardless of `locked`). If there is genuinely no component-test harness pattern to follow, skip the test and state in the report that tsc/build + manual reasoning is the gate (do not invent a bespoke harness).

- [ ] **Step 3: Implement the locked affordance**

In `ModuleCard.tsx`, when the module is `locked` (premium-gated for this free user), render a non-navigating card variant: dim/disabled styling, a small lock glyph, the module title, and one friendly line: `"Premium — ask a grown-up to unlock. Billing coming soon."` Do NOT render the `<Link>`/clickable navigation for a locked module (replace it with a static `<div>` so a free child cannot route into a 403). When not locked, behaviour is unchanged. Keep the change minimal and within this component; match existing Tailwind styling.

- [ ] **Step 4: Verify**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npm run build` and (if a test was added) `npm test -- ModuleCard`.
Expected: clean/success; the new test (if added) passes; existing module/lessons tests still green (`npm test 2>&1 | tail -5` — confirm no new failures beyond the suite's known state).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/frontend/src/components/child/ModuleCard.tsx invest-ed/frontend/tests/unit/child-ModuleCard.test.tsx
git commit -m "$(printf 'feat(tier): graceful premium locked-state on module cards\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```
(Omit the test path from `git add` if no test was added — say so in the report.)

---

### Task 10: Frontend — parent premium toggle on ChildCard

**Files:**
- Modify: `frontend/src/api/parent.ts`, `frontend/src/components/ChildCard.tsx`

- [ ] **Step 1: Inspect**

Read `frontend/src/api/parent.ts` (`Child` type ~L3, `parentApi` with `freezeChild`/`eraseChild` calling `apiFetch`) and `frontend/src/components/ChildCard.tsx` (the `freeze` `useMutation` with optimistic `onMutate`/`onError`/`onSettled` on query key `['children']`). The premium toggle mirrors `freeze` exactly.

- [ ] **Step 2: Extend the API client**

In `frontend/src/api/parent.ts`:
- Add `is_premium: boolean;` to the `Child` type (after `is_active`).
- Add to `parentApi`:
```ts
  setChildPremium: (userId: string, premium: boolean) =>
    apiFetch<{ status: string; premium: boolean }>(
      `/parent/children/${userId}/premium`,
      { method: 'POST', body: JSON.stringify({ premium }) },
    ),
```
(match the exact `apiFetch` call style used by `freezeChild` — same options shape.)

- [ ] **Step 3: Add the toggle to ChildCard**

In `frontend/src/components/ChildCard.tsx`, add a `premium` mutation mirroring the existing `freeze` mutation (same optimistic `onMutate` updating `qc.setQueryData<Child[]>(['children'], ...)` to flip `is_premium` for `child.user_id`, same `onError` rollback+toast, same `onSettled` invalidate). Render a control near the freeze control: when `child.is_premium` show `Premium ✨` + a "Downgrade" button; else an "Upgrade to Premium" button. Disable it when the child is deleted (reuse the existing `isDeleted` guard). Add a one-line helper text: `"Billing isn't set up yet — this grants Premium for testing."` No checkout UI. Match existing button/`cn` styling.

- [ ] **Step 4: Verify**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npm run build`
Expected: clean/success. If `tests/unit` has a ChildCard test, `npm test -- ChildCard` stays green; otherwise note tsc/build is the gate.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/Local\ Repo
git add invest-ed/frontend/src/api/parent.ts invest-ed/frontend/src/components/ChildCard.tsx
git commit -m "$(printf 'feat(tier): parent premium upgrade/downgrade toggle on ChildCard\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 11: Full regression + verification

**Files:** none (verification)

- [ ] **Step 1: Backend suite + lint**

Run: `cd invest-ed/backend && python -m pytest -q` → expect ≥234 + the new tests (entitlements 4, parent premium 2, cli 3, content gate 1, tier seed 2) all green, 0 failed. `ruff check .` → clean. `alembic heads` → single head (no migration was added; confirm unchanged).

- [ ] **Step 2: Frontend gates**

Run: `cd invest-ed/frontend && npx tsc --noEmit && npm run build && npm test 2>&1 | tail -5`
Expected: tsc clean, build success, `npm test` shows no NEW failures vs the known-green baseline (the 8 historically-broken tests were fixed earlier — suite should be fully green; any new failure attributable to Tasks 8–10 must be fixed, not ignored).

- [ ] **Step 3: Entitlement-seam completeness check**

Run: `cd invest-ed/backend && grep -rn "\.is_premium" app/routers app/services | grep -v "entitlements.py" | grep -v "c\.is_premium\|challenge\|Challenge\|module\.is_premium\|m\.is_premium\|r\.is_premium\|ModuleOut\|ChildOut\|payload\.premium"`
Expected: NO results that are a *user* entitlement read outside the seam. (Allowed/expected remaining: the seam itself; `module.is_premium`/`m.is_premium` content attributes; `c.is_premium` challenge attribute; `r.is_premium` in `list_children` building `ChildOut`; schema fields.) If a genuine `current_user.is_premium`/`user.is_premium` read remains in a router/service, refactor it through `is_premium()` (Fix-Loop: add test if behaviour-bearing, refactor, suite green, commit) and report it.

- [ ] **Step 4: Commit any verification fixes**

```bash
cd /Users/leeashmore/Local\ Repo
git add -A invest-ed
git commit -m "$(printf 'chore(tier): regression + seam-completeness fixes\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```
(Skip if nothing changed; say so.)

---

## Self-Review

**1. Spec coverage:**
- §1 Entitlement service → Task 1; refactor consumers → Task 2. ✓
- §2 Parent toggle (endpoint + IDOR + 410 + audit + frontend) → Task 3 (backend) + Task 10 (frontend). ✓
- §3 Ops CLI → Task 4. ✓
- §4 Demonstrable premium content (2 modules + 1 challenge; verify clean 403/locked, not 500) → Task 5 (grounding confirmed content.py already 403s + returns `locked`, so "fix 500" sub-clause is N/A — noted). ✓
- §5 Tier test accounts (prod-guarded, idempotent, 3 accounts, wired to run.py) → Task 6; matrix doc → Task 7. ✓
- §6 Frontend (is_premium already in /users/me & Me type — no plumbing task needed, correctly omitted; badge → Task 8; locked-state → Task 9; parent toggle → Task 10; parent children list `is_premium` → Task 3 Step 4). ✓
- §7 Testing → embedded per task + Task 11 regression + seam-completeness grep. ✓
- Out-of-scope (Stripe/family/#4/LLM-03) respected — no task touches them. ✓

**2. Placeholder scan:** No TBD/"figure out later". Test skeletons that say "reuse the file's real auth/login helper" (Tasks 3, 5) are explicit instructions to mirror an existing, named pattern in that exact file — not vague placeholders; the helper genuinely varies per test file and must be read, not guessed. Task 9's "add a render test if the harness pattern exists, else tsc/build is the gate" is a deliberate, bounded conditional (frontend has component tests in `tests/unit/` per earlier work, so the test path is expected) — acceptable and explicit.

**3. Type/consistency:** `is_premium(user)` / `set_premium(session, child, *, value, actor) -> bool` signatures identical across Tasks 1, 2, 3, 4. `PremiumToggleRequest{premium: bool}` consistent (Task 3 schema ↔ test ↔ frontend `setChildPremium` body `{premium}`). `AuditLog(event_type="premium_grant"/"premium_revoke", metadata_json={"actor","old","new"})` consistent (Task 1 impl ↔ Task 1 test ↔ Task 3 test assertion). Seed usernames `tier_parent`/`premium_child`/`free_child` + emails `tier-parent@/premium-child@/free-child@test.invest-ed` consistent (Task 6 impl ↔ Task 6 test ↔ Task 7 doc). `ChildOut.is_premium` ↔ frontend `Child.is_premium` ↔ `list_children` populate consistent (Tasks 3, 10). No drift.

No gaps requiring a new task. Note: Task 5 may need to minimally update one pre-existing seed/content test if it hard-coded "all modules free" — flagged inline as report-required, not silent.
