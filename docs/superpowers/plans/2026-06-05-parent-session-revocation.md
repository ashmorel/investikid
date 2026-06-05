# Parent Session — Logout & Revocation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the parent session reliably clearable on logout and revocable server-side, by introducing a DB-backed `ParentSession` (jti + revoked_at) mirroring the existing child `RefreshToken`.

**Architecture:** The parent-session JWT gains a `jti` backed by a `parent_sessions` row. `get_current_parent` validates the `jti` against the DB (rejecting missing/revoked/expired) and `logout` revokes the row plus clears the cookie with attributes matching how it was set. Backend-only; no frontend or iOS change.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, python-jose (JWT), pytest (`loop_scope="session"`), Postgres.

**Spec:** `docs/superpowers/specs/2026-06-05-parent-session-revocation-design.md`

**Working dir:** `/Users/leeashmore/Local Repo/invest-ed/backend` unless noted. Git from repo root `/Users/leeashmore/Local Repo`, commit to `main`, end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Commands:**
- Tests: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`
- Lint: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
- Alembic head check: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` (current head = `e1f2a3b4c5d6`)

**Notes for the implementer:**
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`db_session` fixtures from `tests/conftest.py`. Never construct a raw `AsyncClient` on the app engine.
- The local test Postgres can wedge after a killed pytest run; if a DB-backed test hangs ~90s+ it's environmental — rely on CI.
- `tests/conftest.py` builds tables from `Base.metadata` (it imports `app.models`), so a new model MUST be exported from `app/models/__init__.py` or its table won't exist in tests.
- Railway deploys backend only on green CI (6 jobs). No `.env` access.

## File Structure

- **Create** `app/models/parent_session.py` — the `ParentSession` ORM model.
- **Create** `alembic/versions/f0a1b2c3d4e5_add_parent_sessions.py` — migration creating `parent_sessions`.
- **Modify** `app/models/__init__.py` — export `ParentSession` (so metadata/tests see it).
- **Modify** `app/services/tokens.py` — `issue_parent_session` async + persists row + `jti`; `decode_parent_session` returns `(email, jti)`; add `revoke_parent_session`.
- **Modify** `app/routers/parent_auth.py` — async `_set_parent_cookies`; await in `magic_callback`/`oauth_sign_in`; `logout` revokes + clears with matching attrs; `get_current_parent` DB-validates the `jti`.
- **Modify** `tests/test_token_service.py`, `tests/test_token_audience_confusion.py`, `tests/test_parent_oauth.py` — migrate call sites of the now-async `issue_parent_session` / tuple-returning `decode_parent_session`.
- **Create** `tests/test_parent_session_revocation.py` — new behaviour tests.

---

### Task 1: `ParentSession` model + migration

**Files:**
- Create: `app/models/parent_session.py`
- Create: `alembic/versions/f0a1b2c3d4e5_add_parent_sessions.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_parent_session_revocation.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_parent_session_revocation.py`:

```python
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_parent_session_row_roundtrips(db_session):
    from app.models.parent_session import ParentSession

    jti = uuid.uuid4()
    db_session.add(ParentSession(
        jti=jti,
        parent_email="dad@example.com",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    ))
    await db_session.flush()

    row = await db_session.scalar(select(ParentSession).where(ParentSession.jti == jti))
    assert row is not None
    assert row.parent_email == "dad@example.com"
    assert row.revoked_at is None
    assert row.id is not None
    assert row.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py::test_parent_session_row_roundtrips -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.parent_session'`.

- [ ] **Step 3: Create the model** — `app/models/parent_session.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParentSession(Base):
    __tablename__ = "parent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    jti: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    parent_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
```

- [ ] **Step 4: Export the model** — add to `app/models/__init__.py` (alongside the existing `parent_identity` import, keep alphabetical-ish grouping):

```python
from app.models.parent_session import ParentSession  # noqa: F401
```

- [ ] **Step 5: Write the migration** — `alembic/versions/f0a1b2c3d4e5_add_parent_sessions.py`:

```python
"""add parent_sessions table

Revision ID: f0a1b2c3d4e5
Revises: e1f2a3b4c5d6
Create Date: 2026-06-05 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parent_sessions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("jti", UUID(as_uuid=True), nullable=False),
        sa.Column("parent_email", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parent_sessions_jti", "parent_sessions", ["jti"], unique=True)
    op.create_index(
        "ix_parent_sessions_parent_email", "parent_sessions", ["parent_email"]
    )


def downgrade() -> None:
    op.drop_index("ix_parent_sessions_parent_email", table_name="parent_sessions")
    op.drop_index("ix_parent_sessions_jti", table_name="parent_sessions")
    op.drop_table("parent_sessions")
```

- [ ] **Step 6: Verify head chains correctly**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: a single head `f0a1b2c3d4e5 (head)`. If it shows two heads, the `down_revision` is wrong — fix it to the actual prior head.

- [ ] **Step 7: Run the test to verify it passes**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py::test_parent_session_row_roundtrips -v`
Expected: PASS. (If it hangs ~90s+, it's the environmental Postgres wedge — rely on CI.)

- [ ] **Step 8: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend"
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/parent_session.py invest-ed/backend/app/models/__init__.py invest-ed/backend/alembic/versions/f0a1b2c3d4e5_add_parent_sessions.py invest-ed/backend/tests/test_parent_session_revocation.py
git commit -m "feat: add ParentSession model + migration for revocable parent sessions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Token service — async issue, jti, revoke; migrate unit-test call sites

This is the atomic core change: `issue_parent_session` becomes async (so callers must `await`). To keep the suite green at this commit, update its direct call sites in `parent_auth.py` (to `await`) and in the three test files. Behavioural enforcement (the DB check in `get_current_parent`, logout revoke) lands in Task 3.

**Files:**
- Modify: `app/services/tokens.py`
- Modify: `app/routers/parent_auth.py` (call sites only, this task)
- Modify: `tests/test_token_service.py`
- Modify: `tests/test_token_audience_confusion.py`
- Modify: `tests/test_parent_oauth.py`
- Test: `tests/test_parent_session_revocation.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_parent_session_revocation.py`:

```python
async def test_issue_parent_session_persists_row_and_jti(db_session):
    import uuid as _uuid

    from app.models.parent_session import ParentSession
    from app.services.tokens import decode_parent_session, issue_parent_session

    token = await issue_parent_session(db_session, "mum@example.com")
    await db_session.flush()

    email, jti = decode_parent_session(token)
    assert email == "mum@example.com"
    assert isinstance(jti, _uuid.UUID)

    row = await db_session.scalar(
        select(ParentSession).where(ParentSession.jti == jti)
    )
    assert row is not None
    assert row.parent_email == "mum@example.com"
    assert row.revoked_at is None


async def test_revoke_parent_session_sets_revoked_at(db_session):
    from app.models.parent_session import ParentSession
    from app.services.tokens import (
        decode_parent_session,
        issue_parent_session,
        revoke_parent_session,
    )

    token = await issue_parent_session(db_session, "mum@example.com")
    await db_session.flush()
    _email, jti = decode_parent_session(token)

    await revoke_parent_session(db_session, jti)
    await db_session.flush()

    row = await db_session.scalar(
        select(ParentSession).where(ParentSession.jti == jti)
    )
    assert row.revoked_at is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py -v -k "persists_row or revoke_parent_session"`
Expected: FAIL — `issue_parent_session` is not async / takes no session, and `revoke_parent_session` doesn't exist.

- [ ] **Step 3: Rewrite the parent-session functions in `app/services/tokens.py`**

Add `ParentSession` + `select` to the imports at the top (the module already imports `update` from sqlalchemy and `AsyncSession`):

```python
from sqlalchemy import select, update
```
```python
from app.models.parent_session import ParentSession
```

Replace the existing `issue_parent_session` and `decode_parent_session` with:

```python
async def issue_parent_session(session: AsyncSession, email: str) -> str:
    jti = uuid.uuid4()
    now = datetime.now(UTC)
    expires_at = now + PARENT_SESSION_EXPIRY
    session.add(ParentSession(jti=jti, parent_email=email, expires_at=expires_at))
    await session.flush()
    payload = {
        "sub": email,
        "aud": PARENT_SESSION_AUDIENCE,
        "jti": str(jti),
        "exp": expires_at,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_parent_session(token: str) -> tuple[str, uuid.UUID]:
    """Returns (parent_email, jti) or raises TokenInvalid."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=PARENT_SESSION_AUDIENCE,
        )
    except JWTError as exc:
        raise TokenInvalid(str(exc)) from exc
    email = payload.get("sub")
    if not email:
        raise TokenInvalid("missing sub")
    try:
        jti = uuid.UUID(payload["jti"])
    except (KeyError, ValueError, TypeError) as exc:
        raise TokenInvalid("missing jti") from exc
    return email, jti


async def revoke_parent_session(session: AsyncSession, jti: uuid.UUID) -> None:
    """Mark the matching live parent session revoked (idempotent; no-op if absent)."""
    await session.execute(
        update(ParentSession)
        .where(ParentSession.jti == jti, ParentSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
```

- [ ] **Step 4: Update the `parent_auth.py` call sites to await (keep app importable/runnable)**

In `app/routers/parent_auth.py`:

`_set_parent_cookies` → make async and pass the session:

```python
async def _set_parent_cookies(
    session: AsyncSession, response: Response, email: str
) -> None:
    secure = settings.environment != "development"
    token = await issue_parent_session(session, email)
    response.set_cookie(
        _PARENT_COOKIE, token,
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)
```

In `oauth_sign_in`, change the call to:

```python
    await _set_parent_cookies(session, response, parent_email)
```

In `magic_callback`, replace the consume/issue/commit block so the row and the consumed-token commit land together:

```python
    try:
        record = await consume_one_time_token(session, token, PARENT_MAGIC_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired")

    parent_session_token = await issue_parent_session(session, record.email)
    await session.commit()

    secure = settings.environment != "development"
    response.set_cookie(
        _PARENT_COOKIE, parent_session_token,
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)
    return {"status": "signed_in", "email": record.email}
```

(`get_current_parent` and `logout` are updated in Task 3 — leave them for now; the app still runs because the cookie still decodes, even though the tuple return from `decode_parent_session` means `get_current_parent`'s current `return decode_parent_session(token)` would return a tuple. To avoid breaking auth between tasks, also apply this minimal interim fix to `get_current_parent` now:)

```python
async def get_current_parent(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> str:
    token = request.cookies.get(_PARENT_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        email, _jti = decode_parent_session(token)
    except TokenInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return email
```

- [ ] **Step 5: Migrate the unit-test call sites**

In `tests/test_token_service.py`, replace `test_parent_session_roundtrip` (currently sync) with an async version that uses `db_session` and unpacks the tuple:

```python
async def test_parent_session_roundtrip(db_session):
    token = await issue_parent_session(db_session, "p@example.com")
    email, jti = decode_parent_session(token)
    assert email == "p@example.com"
    assert jti is not None
```

(Leave `test_parent_session_invalid_rejected` as-is — `decode_parent_session("garbage")` still raises `TokenInvalid`.)

In `tests/test_token_audience_confusion.py`, line ~55, change:

```python
    parent_token = await issue_parent_session(db_session, "victim_parent@example.com")
```
(The surrounding test is already `async def ... (client, db_session)`, so just add `await` + the `db_session` arg.)

In `tests/test_parent_oauth.py`, make the auth helper async and DB-backed. Replace the helper:

```python
async def _auth_headers(db_session, parent_email: str) -> dict:
    """Return headers that carry a valid (persisted) parent session and bypass CSRF."""
    token = await issue_parent_session(db_session, parent_email)
    await db_session.commit()
    return {
        "Origin": "https://localhost",
        "Cookie": f"parent_session={token}",
    }
```

Then update each of the 6 call sites (lines ~121, 148, 186, 215, 240) from `_auth_headers(<email>)` to `await _auth_headers(db_session, <email>)`. Ensure each of those test functions has `db_session` in its signature (add it where missing).

- [ ] **Step 6: Run the affected tests**

Run:
```
/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py tests/test_token_service.py tests/test_token_audience_confusion.py tests/test_parent_oauth.py -v
```
Expected: PASS (all). If the DB wedges, rely on CI.

- [ ] **Step 7: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend"
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/tokens.py invest-ed/backend/app/routers/parent_auth.py invest-ed/backend/tests/
git commit -m "feat: persist + revoke parent sessions in token service (jti-backed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Enforce revocation in `get_current_parent` + fix logout

**Files:**
- Modify: `app/routers/parent_auth.py`
- Test: `tests/test_parent_session_revocation.py`, `tests/test_parent_auth.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_parent_session_revocation.py`:

```python
async def _sign_in_parent(client, db_session, parent_email="dad@example.com"):
    """Register a kid (so the parent email is known) and sign the parent in via magic link.
    Returns the csrf token for CSRF-protected POSTs."""
    from datetime import timedelta

    from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "kid_rev@example.com", "username": "kid_rev", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    return client.cookies.get("csrf_token")


async def test_logout_revokes_session_server_side(client, db_session):
    csrf = await _sign_in_parent(client, db_session)
    # Authenticated route works before logout
    r = await client.get("/parent/children")
    assert r.status_code == 200

    # Capture the cookie, log out, then replay the SAME cookie
    cookie = client.cookies.get("parent_session")
    r = await client.post("/parent/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200

    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={cookie}"})
    assert r.status_code == 401, "a logged-out (revoked) parent cookie must not authenticate"


async def test_logout_emits_cookie_clear(client, db_session):
    csrf = await _sign_in_parent(client, db_session)
    r = await client.post("/parent/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert "parent_session=" in set_cookie
    assert "path=/" in set_cookie.lower()
    # A real clear sets an immediate expiry / Max-Age=0
    assert ("max-age=0" in set_cookie.lower()) or ("expires=" in set_cookie.lower())


async def test_revoked_row_rejected(client, db_session):
    from app.models.parent_session import ParentSession
    from app.services.tokens import decode_parent_session, revoke_parent_session

    await _sign_in_parent(client, db_session)
    cookie = client.cookies.get("parent_session")
    _email, jti = decode_parent_session(cookie)
    await revoke_parent_session(db_session, jti)
    await db_session.commit()

    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={cookie}"})
    assert r.status_code == 401


async def test_unknown_jti_rejected(client, db_session):
    # A validly-signed parent JWT whose jti has no row must be rejected.
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings
    from app.services.tokens import PARENT_SESSION_AUDIENCE

    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": "ghost@example.com",
            "aud": PARENT_SESSION_AUDIENCE,
            "jti": str(_uuid.uuid4()),
            "exp": now + timedelta(days=7),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={forged}"})
    assert r.status_code == 401


async def test_expired_row_rejected(client, db_session):
    # JWT exp is valid but the DB row is expired -> defence-in-depth 401.
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings
    from app.models.parent_session import ParentSession
    from app.services.tokens import PARENT_SESSION_AUDIENCE

    jti = _uuid.uuid4()
    db_session.add(ParentSession(
        jti=jti,
        parent_email="stale@example.com",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    ))
    await db_session.commit()

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "stale@example.com",
            "aud": PARENT_SESSION_AUDIENCE,
            "jti": str(jti),
            "exp": now + timedelta(days=7),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={token}"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run to verify they fail**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py -v -k "logout_revokes or emits_cookie or revoked_row or unknown_jti or expired_row"`
Expected: FAIL — `get_current_parent` does not yet check the DB (revoked/unknown/expired all still 200), and `logout` does not revoke.

- [ ] **Step 3: Implement the DB check in `get_current_parent`** — replace the interim version from Task 2 with:

```python
async def get_current_parent(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> str:
    """Returns the parent email from a valid, non-revoked, unexpired session cookie."""
    token = request.cookies.get(_PARENT_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        email, jti = decode_parent_session(token)
    except TokenInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    row = await session.scalar(
        select(ParentSession).where(ParentSession.jti == jti).limit(1)
    )
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return email
```

Add the needed imports near the top of `app/routers/parent_auth.py` (the module already imports `datetime` and `UTC` from `datetime`, `select` from sqlalchemy, and `status`):

```python
from app.models.parent_session import ParentSession
from app.services.tokens import revoke_parent_session  # add to the existing tokens import block
```

- [ ] **Step 4: Implement the logout revoke + matching cookie clear** — replace the existing `logout` with:

```python
@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(_PARENT_COOKIE)
    if token:
        try:
            _email, jti = decode_parent_session(token)
        except TokenInvalid:
            jti = None
        if jti is not None:
            await revoke_parent_session(session, jti)
            await session.commit()
    secure = settings.environment != "development"
    response.delete_cookie(
        _PARENT_COOKIE,
        samesite=_cookie_samesite(),
        secure=secure,
        httponly=True,
        path="/",
    )
    return {"status": "ok"}
```

- [ ] **Step 5: Run the new tests + the existing parent-auth tests**

Run:
```
/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_session_revocation.py tests/test_parent_auth.py -v
```
Expected: PASS (all), including the pre-existing `test_logout_clears_cookie`.

- [ ] **Step 6: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend"
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/parent_auth.py invest-ed/backend/tests/test_parent_session_revocation.py
git commit -m "feat: enforce parent-session revocation + fix logout cookie clear (audit H1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full regression + push

**Files:** none (verification only).

- [ ] **Step 1: Run the full backend suite**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: all pass (modulo any documented pre-existing failures). If a DB-backed test hangs ~90s+, that's the environmental Postgres wedge — note it and rely on CI.

- [ ] **Step 2: Lint**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: no errors.

- [ ] **Step 3: Confirm a single Alembic head**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: single head `f0a1b2c3d4e5 (head)`.

- [ ] **Step 4: Push**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```

- [ ] **Step 5: Report** — summarise commits and remind that Railway deploys only on green CI (6 jobs); the one-time effect is that any parent currently signed in must log in again after deploy.

---

## Self-Review

**Spec coverage:**
- Component A (model + migration) → Task 1. ✓
- Component B (`issue_parent_session` async + row + jti; `decode` returns `(email, jti)`; `revoke_parent_session`) → Task 2. ✓
- Component C (`_set_parent_cookies` async; `magic_callback`/`oauth_sign_in` await; `logout` revoke + matching clear; `get_current_parent` DB check) → Tasks 2 (call sites) + 3 (enforcement/logout). ✓
- Testing items 1–8 → Task 1 (row roundtrip), Task 2 (persist row, revoke), Task 3 (logout revoke, cookie-clear, revoked/unknown/expired → 401), Task 4 (full regression). The spec's "sign-in persists a row" is covered by `test_issue_parent_session_persists_row_and_jti` (Task 2) and exercised end-to-end via `_sign_in_parent` in Task 3. ✓
- Edge cases (in-flight tokens 401 once; logout with malformed cookie; multi-device) → handled by the `get_current_parent` DB check + logout `try/except` (Task 3). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**Type consistency:** `issue_parent_session(session, email) -> str` (async) and `decode_parent_session(token) -> tuple[str, uuid.UUID]` and `revoke_parent_session(session, jti)` are used identically across Tasks 2–3 and all migrated test call sites. `_set_parent_cookies(session, response, email)` arg order is consistent between definition and the `oauth_sign_in` call. ✓
