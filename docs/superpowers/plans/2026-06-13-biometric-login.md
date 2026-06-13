# Biometric Quick-Login (SP-Bio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [x]`) syntax. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Face ID / Touch ID / Android-biometric quick-login for parents and children per `docs/superpowers/specs/2026-06-13-biometric-login-design.md` — lock-screen on launch + silent session re-mint, opaque revocable credential, hybrid parent-gated consent for kids.

**Architecture:** One backend service (`biometric_service`) over a new `biometric_credentials` table issues/verifies/rotates opaque secrets; child + parent enroll/exchange/unenroll endpoints reuse existing cookie/session issuance; a frontend `biometric.ts` plugin wrapper + `<BiometricGate>` state machine drive the lock screen; consent is a parent master switch (`users.biometric_allowed`) plus a per-device child/parent enroll toggle.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic; React 18 + TS + Capacitor 8 (`capacitor-native-biometric`, `@capacitor/app`). Backend tests `/Users/leeashmore/Local Repo/.venv/bin/pytest` from `backend/`; frontend `npx vitest run`. Branch `testing`. Commits end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Always check `pytest`/`vitest` exit codes directly (don't pipe through grep). Validate the migration with a scratch-Postgres full-chain replay before any push.

### File structure
- Create `backend/app/models/biometric.py` — `BiometricCredential`.
- Create `backend/app/services/biometric_service.py` — issue/verify_and_rotate/revoke.
- Create `backend/alembic/versions/e2f3a4b5c6d7_biometric_credentials.py`.
- Modify `backend/app/models/user.py` (+`biometric_allowed`), `app/models/__init__.py`.
- Modify `backend/app/routers/auth.py` (child enroll/exchange/unenroll), `app/routers/parent_auth.py` (parent equivalents), `app/routers/parent.py` (master toggle), `app/schemas/user.py`/`app/schemas/parent.py`.
- Modify `backend/app/services/account_deletion_service.py` (revoke on delete).
- Create `frontend/src/lib/biometric.ts`, `frontend/src/components/auth/BiometricGate.tsx`.
- Modify `frontend/src/api/auth.ts`, `frontend/src/api/parent.ts`, `frontend/src/App.tsx` (mount gate), `ProfileMenu.tsx`, `ChildCard.tsx`, parent settings.
- Modify `frontend/ios/App/App/Info.plist` (+`NSFaceIDUsageDescription`), `docs/compliance/privacy-notice.md`.

---

### Task 1: Migration + model + biometric_service

**Files:**
- Create: `backend/app/models/biometric.py`, `backend/app/services/biometric_service.py`, `backend/alembic/versions/e2f3a4b5c6d7_biometric_credentials.py`
- Modify: `backend/app/models/user.py`, `backend/app/models/__init__.py`
- Test: `backend/tests/test_biometric_service.py`

- [x] **Step 1: Write the failing test**

```python
# backend/tests/test_biometric_service.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.biometric import BiometricCredential
from app.models.user import User
from app.services import biometric_service as bio

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session) -> User:
    s = uuid.uuid4().hex[:8]
    u = User(username=f"b{s}", email=f"b{s}@example.com", password_hash="x",
             dob=datetime(2014, 1, 1).date(), country_code="GB", currency_code="GBP",
             parent_email="p@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


async def test_issue_then_verify_rotates_secret(db_session):
    child = await _child(db_session)
    secret = await bio.issue(
        db_session, subject_kind="child", user_id=child.id, parent_email=None,
        device_id="dev-1", label=child.username,
    )
    assert secret and len(secret) >= 32
    await db_session.flush()

    row = await bio.verify_and_rotate(db_session, device_id="dev-1", secret=secret)
    assert row is not None and row.user_id == child.id
    # secret rotated: the old one no longer verifies, the new one does
    assert await bio.verify_and_rotate(db_session, device_id="dev-1", secret=secret) is None
    assert await bio.verify_and_rotate(db_session, device_id="dev-1", secret=row.last_secret) is not None


async def test_reenroll_same_device_replaces(db_session):
    child = await _child(db_session)
    await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-2", label="a")
    await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-2", label="a")
    await db_session.flush()
    rows = (await db_session.execute(
        BiometricCredential.__table__.select().where(BiometricCredential.device_id == "dev-2")
    )).all()
    assert len(rows) == 1


async def test_revoked_and_expired_do_not_verify(db_session):
    child = await _child(db_session)
    secret = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-3", label="a")
    await db_session.flush()
    await bio.revoke_subject(db_session, subject_key=f"child:{child.id}")
    assert await bio.verify_and_rotate(db_session, device_id="dev-3", secret=secret) is None

    secret2 = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-4", label="a")
    await db_session.flush()
    cred = await db_session.scalar(
        BiometricCredential.__table__.select().where(BiometricCredential.device_id == "dev-4")
    )
    # force-expire
    from sqlalchemy import update
    await db_session.execute(
        update(BiometricCredential).where(BiometricCredential.device_id == "dev-4")
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    assert await bio.verify_and_rotate(db_session, device_id="dev-4", secret=secret2) is None


async def test_parent_subject(db_session):
    secret = await bio.issue(db_session, subject_kind="parent", user_id=None, parent_email="P@Example.com", device_id="dev-5", label="Parent")
    await db_session.flush()
    row = await bio.verify_and_rotate(db_session, device_id="dev-5", secret=secret)
    assert row is not None and row.parent_email == "p@example.com" and row.subject_kind == "parent"
```

- [x] **Step 2: Run to verify it fails** — `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_biometric_service.py -q` (module not found).

- [x] **Step 3: Model** — `backend/app/models/biometric.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BiometricCredential(Base):
    """Opaque, device-bound, revocable credential gated behind the OS biometric
    keychain (SP-Bio). Covers both account types via subject_key (NULL-free)."""

    __tablename__ = "biometric_credentials"
    __table_args__ = (
        UniqueConstraint("device_id", "subject_key", name="uq_biometric_device_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_kind: Mapped[str] = mapped_column(String(10), nullable=False)  # 'child'|'parent'
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    parent_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subject_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Register in `app/models/__init__.py` (alphabetical, before `from app.models.cash_grant`):
```python
from app.models.biometric import BiometricCredential  # noqa: F401
```
Add to `app/models/user.py` `User` (next to `push_enabled`):
```python
    biometric_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
```

- [x] **Step 4: Service** — `backend/app/services/biometric_service.py`:

```python
"""Opaque biometric credential issuance/verification (SP-Bio).

The ONLY module that touches biometric_credentials. Secret = 256-bit random,
stored as SHA-256 (high-entropy → no bcrypt), rotated on each successful verify,
device-bound and revocable.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from app.models.biometric import BiometricCredential

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

CREDENTIAL_TTL = timedelta(days=90)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _subject_key(subject_kind: str, user_id, parent_email: str | None) -> str:
    if subject_kind == "child":
        return f"child:{user_id}"
    return f"parent:{(parent_email or '').lower()}"


async def issue(
    session: AsyncSession,
    *,
    subject_kind: str,
    user_id: "uuid.UUID | None",
    parent_email: str | None,
    device_id: str,
    label: str,
) -> str:
    """Create (replacing any existing for this device+subject) and return a fresh
    plaintext secret. The caller stores it in the biometric keychain."""
    email = parent_email.lower() if parent_email else None
    key = _subject_key(subject_kind, user_id, email)
    await session.execute(
        delete(BiometricCredential).where(
            BiometricCredential.device_id == device_id,
            BiometricCredential.subject_key == key,
        )
    )
    secret = secrets.token_urlsafe(32)
    session.add(BiometricCredential(
        subject_kind=subject_kind, user_id=user_id, parent_email=email,
        subject_key=key, device_id=device_id, label=label[:60],
        secret_hash=_hash(secret),
        expires_at=datetime.now(UTC) + CREDENTIAL_TTL,
    ))
    return secret


async def verify_and_rotate(
    session: AsyncSession, *, device_id: str, secret: str
) -> BiometricCredential | None:
    """Validate a presented secret for a device; on success rotate it and stamp
    last_used_at. Returns the row (with a transient ``last_secret`` attribute =
    the new plaintext) or None. NEVER raises for a bad secret."""
    now = datetime.now(UTC)
    row = await session.scalar(
        select(BiometricCredential).where(
            BiometricCredential.device_id == device_id,
            BiometricCredential.secret_hash == _hash(secret),
            BiometricCredential.revoked_at.is_(None),
            BiometricCredential.expires_at > now,
        )
    )
    if row is None:
        return None
    new_secret = secrets.token_urlsafe(32)
    row.secret_hash = _hash(new_secret)
    row.last_used_at = now
    row.last_secret = new_secret  # transient, for the endpoint to return
    await session.flush()
    return row


async def revoke_subject(session: AsyncSession, *, subject_key: str) -> int:
    result = await session.execute(
        update(BiometricCredential)
        .where(BiometricCredential.subject_key == subject_key, BiometricCredential.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def revoke_device(session: AsyncSession, *, subject_key: str, device_id: str) -> int:
    result = await session.execute(
        update(BiometricCredential)
        .where(
            BiometricCredential.subject_key == subject_key,
            BiometricCredential.device_id == device_id,
            BiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount or 0


def subject_key_for_child(user_id) -> str:
    return f"child:{user_id}"


def subject_key_for_parent(email: str) -> str:
    return f"parent:{email.lower()}"
```

Note: `last_secret` is a transient Python attribute set on the ORM instance — the test reads `row.last_secret`. Declare it in the model as a non-mapped default to satisfy linters: add `last_secret: str | None = None` is NOT valid on a Mapped model; instead set it dynamically (already done) and in the test access works. If ruff/mypy complains, the endpoint reads it via `getattr(row, "last_secret")`.

- [x] **Step 5: Migration** — `e2f3a4b5c6d7_biometric_credentials.py` (down_revision `d1e2f3a4b5c6`): `op.add_column("users", sa.Column("biometric_allowed", sa.Boolean(), nullable=False, server_default="false"))` + `op.create_table("biometric_credentials", ...)` with all columns above, the unique constraint, and indexes on user_id/parent_email/subject_key/secret_hash. Downgrade drops table + column.

- [x] **Step 6: Validate migration** — single head + scratch replay:
```bash
cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads   # one head
/Users/leeashmore/Local\ Repo/.venv/bin/python -c "import asyncio,asyncpg; asyncio.run((lambda: None)())"  # (use the M8/M9 scratch-replay recipe)
```
Replay the full chain on a scratch DB exactly as in the M9 task (create db → `DATABASE_URL=... alembic upgrade head` → expect exit 0 → drop). MUST pass before commit.

- [x] **Step 7: Run tests + commit** — `pytest backend/tests/test_biometric_service.py -q` PASS; ruff clean. Commit `feat(bio): biometric_credentials model + service + migration`.

---

### Task 2: Child enroll / exchange / unenroll endpoints

**Files:**
- Modify: `backend/app/routers/auth.py`, `backend/app/schemas/user.py` (`UserProfile.biometric_allowed`)
- Test: `backend/tests/test_biometric_child_auth.py`

- [x] **Step 1: Failing test** — covering: enroll 403 without `biometric_allowed`; enroll 200 returns a secret when allowed; exchange with that secret sets a session (subsequent `/users/me` 200) and returns a rotated secret; exchange re-rejects the old secret; exchange 401 after the child is frozen (`is_active=False`); exchange 401 after parent revokes (`biometric_allowed`→False triggers revoke). Use `_register_and_login` from `tests/test_content.py`; set `user.biometric_allowed=True` via db_session.

```python
# backend/tests/test_biometric_child_auth.py  (key cases)
async def test_enroll_requires_consent(client, db_session):
    # register+login, biometric_allowed defaults False
    ... assert (await client.post("/auth/biometric/enroll", json={"device_id":"d1","label":"kid"}, headers=_csrf(client))).status_code == 403

async def test_enroll_then_exchange_roundtrip(client, db_session):
    # set user.biometric_allowed = True, commit
    r = await client.post("/auth/biometric/enroll", json={"device_id":"d1","label":"kid"}, headers=_csrf(client))
    assert r.status_code == 200
    secret = r.json()["secret"]
    # new client (no cookies) exchanges
    fresh = make_fresh_client()   # or clear cookies
    r2 = await fresh.post("/auth/biometric/exchange", json={"device_id":"d1","secret":secret})
    assert r2.status_code == 200
    rotated = r2.json()["secret"]
    assert rotated != secret
    assert (await fresh.get("/users/me")).status_code == 200
    # old secret now rejected
    assert (await fresh.post("/auth/biometric/exchange", json={"device_id":"d1","secret":secret})).status_code == 401
```

(Write the frozen + revoked cases concretely against the seeded child.)

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Implement** in `auth.py` (after `refresh`):

```python
class BiometricEnrollRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    label: str = Field(min_length=1, max_length=60)


class BiometricExchangeRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    secret: str = Field(min_length=8, max_length=128)


@router.post("/biometric/enroll")
async def biometric_enroll(
    payload: BiometricEnrollRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not current_user.biometric_allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "biometric_not_allowed")
    secret = await biometric_service.issue(
        session, subject_kind="child", user_id=current_user.id, parent_email=None,
        device_id=payload.device_id, label=payload.label,
    )
    await session.commit()
    return {"secret": secret}


@router.post("/biometric/exchange", response_model=None)
@limiter.limit("10/hour")
async def biometric_exchange(
    request: Request,
    payload: BiometricExchangeRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    row = await biometric_service.verify_and_rotate(
        session, device_id=payload.device_id, secret=payload.secret
    )
    if row is None or row.subject_kind != "child" or row.user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_biometric")
    user = await session.get(User, row.user_id)
    if user is None or not user.is_active or not user.biometric_allowed:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_biometric")
    secure = settings.environment != "development"
    _set_access_cookie(response, str(user.id), secure)
    await _issue_refresh_token(session, response, user.id, secure)
    _set_csrf_cookie(response, secure)
    new_secret = row.last_secret
    await session.commit()
    return {"secret": new_secret}


@router.delete("/biometric/devices/{device_id}")
async def biometric_unenroll(
    device_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await biometric_service.revoke_device(
        session, subject_key=biometric_service.subject_key_for_child(current_user.id), device_id=device_id
    )
    await session.commit()
    return {"status": "ok"}
```

Add imports: `from app.services import biometric_service`; `from pydantic import Field` (if missing); ensure `Request`, `limiter` imported (they are for login). Add `/auth/biometric/exchange` to the CSRF exempt path list in `app/core/csrf.py` (`_DEFAULT_EXEMPT_PATHS`, beside `/auth/login`). `UserProfile` schema (`app/schemas/user.py`) += `biometric_allowed: bool = False`.

- [x] **Step 4: Run → pass.** Run `tests/test_biometric_child_auth.py` + `tests/test_auth*.py` (no regressions).
- [x] **Step 5: Commit** `feat(bio): child enroll/exchange/unenroll endpoints`.

---

### Task 3: Parent endpoints + master toggle + revocation integration

**Files:**
- Modify: `backend/app/routers/parent_auth.py` (enroll/exchange/unenroll), `backend/app/routers/parent.py` (master toggle), `backend/app/schemas/parent.py` (`ChildOut.biometric_allowed`, `BiometricToggleRequest`), `backend/app/services/account_deletion_service.py`
- Test: `backend/tests/test_biometric_parent.py`

- [x] **Step 1: Failing test** — parent enroll (authed parent) returns secret; exchange sets a parent session (a subsequent `/parent/children` 200) + rotates; exchange 401 if the parent_email owns no non-deleted child; `POST /parent/children/{id}/biometric {enabled:true}` flips `biometric_allowed` and returns ok (audited); disabling revokes the child's creds (a prior child exchange now 401); account deletion revokes parent + child creds. Use `_setup_parent` from `tests/test_billing.py`.

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Implement.**

Parent enroll/exchange/unenroll in `parent_auth.py` (mirror Task 2 but issue/consume a parent session). Exchange:
```python
@router.post("/biometric/exchange")
@limiter.limit("10/hour")
async def parent_biometric_exchange(request: Request, payload: BiometricExchangeRequest, response: Response,
                                    session: AsyncSession = Depends(get_session)):
    row = await biometric_service.verify_and_rotate(session, device_id=payload.device_id, secret=payload.secret)
    if row is None or row.subject_kind != "parent" or not row.parent_email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_biometric")
    has_child = await session.scalar(select(User.id).where(User.parent_email == row.parent_email, User.deleted_at.is_(None)).limit(1))
    if has_child is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_biometric")
    parent_session_token = await issue_parent_session(session, row.parent_email)
    new_secret = row.last_secret
    await session.commit()
    secure = settings.environment != "development"
    response.set_cookie(_PARENT_COOKIE, parent_session_token, max_age=7*86400, httponly=True,
                        samesite=_cookie_samesite(), secure=secure, path="/")
    _set_csrf_cookie(response, secure)
    return {"secret": new_secret}
```
Parent enroll uses `get_current_parent` (parent_email), `subject_kind="parent"`, `parent_email=parent_email`. Add `/parent/auth/biometric/exchange` to CSRF exempt paths.

Master toggle in `parent.py` (mirror `set_child_push` exactly):
```python
@router.post("/children/{user_id}/biometric")
async def set_child_biometric(user_id: uuid.UUID, payload: BiometricToggleRequest,
                              parent_email: str = Depends(get_current_parent),
                              session: AsyncSession = Depends(get_session)):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status.HTTP_410_GONE, "Account deleted")
    child.biometric_allowed = payload.enabled
    if not payload.enabled:
        await biometric_service.revoke_subject(session, subject_key=biometric_service.subject_key_for_child(child.id))
    session.add(AuditLog(user_id=child.id, event_type="biometric_enabled" if payload.enabled else "biometric_disabled",
                         metadata_json={"actor": f"parent:{parent_email}"}))
    await session.commit()
    return {"status": "ok", "biometric_allowed": payload.enabled}
```
`ChildOut` += `biometric_allowed: bool = False` and wire it where ChildOut is built (next to `push_enabled=r.push_enabled`). `BiometricToggleRequest(BaseModel){enabled: bool}`.

Account deletion: in `account_deletion_service`, when deleting a child revoke `subject_key_for_child(child.id)`; when deleting a parent account revoke `subject_key_for_parent(parent_email)`.

- [x] **Step 4: Run → pass** + `tests/test_parent*.py`, `tests/test_billing.py`, `tests/test_parent_account_deletion.py` regressions.
- [x] **Step 5: Commit** `feat(bio): parent endpoints + master toggle + deletion revocation`.

---

### Task 4: Frontend biometric lib

**Files:**
- Create: `frontend/src/lib/biometric.ts`, `frontend/src/lib/__tests__/biometric.test.ts`
- Modify: `frontend/package.json` (`npm i capacitor-native-biometric`)

- [x] **Step 0 (plan-time check):** `npm i capacitor-native-biometric` then verify it resolves for Capacitor 8 (`npm ls @capacitor/core capacitor-native-biometric`). If it pins an incompatible core, fall back to `@aparajita/capacitor-biometric-auth` + `@aparajita/capacitor-secure-storage` and adapt only the plugin calls inside `biometric.ts` (interface below stays identical).

- [x] **Step 1: Failing test** — gating + device id + typed results:
```ts
// frontend/src/lib/__tests__/biometric.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
let native = true;
vi.mock('@/lib/platform', () => ({ isNativeApp: () => native }));
const plugin = { isAvailable: vi.fn(), verifyIdentity: vi.fn(), setCredentials: vi.fn(), getCredentials: vi.fn(), deleteCredentials: vi.fn() };
vi.mock('capacitor-native-biometric', () => ({ NativeBiometric: plugin }));
import { biometric, getDeviceId } from '../biometric';

beforeEach(() => { native = true; localStorage.clear(); vi.clearAllMocks(); });

it('isAvailable false on web', async () => { native = false; expect(await biometric.isAvailable()).toBe(false); });
it('isAvailable true when plugin reports available', async () => {
  plugin.isAvailable.mockResolvedValue({ isAvailable: true });
  expect(await biometric.isAvailable()).toBe(true);
});
it('getDeviceId persists a stable uuid', () => { const a = getDeviceId(); expect(getDeviceId()).toBe(a); });
it('enroll stores under the namespaced key', async () => {
  plugin.setCredentials.mockResolvedValue(undefined);
  await biometric.enroll('child:1', 'Maya', 'secret-xyz');
  expect(plugin.setCredentials).toHaveBeenCalledWith(expect.objectContaining({ server: 'bio:child:1', password: 'secret-xyz', username: 'Maya' }));
});
it('read returns null when biometric cancels', async () => {
  plugin.getCredentials.mockRejectedValue(new Error('cancel'));
  expect(await biometric.read('child:1')).toBeNull();
});
```

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Implement** `frontend/src/lib/biometric.ts`:
```ts
import { isNativeApp } from '@/lib/platform';

const DEVICE_KEY = 'bio-device-id';
const ns = (key: string) => `bio:${key}`;

export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) { id = (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`); localStorage.setItem(DEVICE_KEY, id); }
  return id;
}

async function pluginOrNull() {
  if (!isNativeApp()) return null;
  try { const m = await import('capacitor-native-biometric'); return m.NativeBiometric; } catch { return null; }
}

export const biometric = {
  async isAvailable(): Promise<boolean> {
    const p = await pluginOrNull();
    if (!p) return false;
    try { return Boolean((await p.isAvailable()).isAvailable); } catch { return false; }
  },
  async verify(reason: string): Promise<boolean> {
    const p = await pluginOrNull();
    if (!p) return false;
    try { await p.verifyIdentity({ reason, title: 'InvestiKid' }); return true; } catch { return false; }
  },
  async enroll(key: string, label: string, secret: string): Promise<void> {
    const p = await pluginOrNull();
    if (!p) return;
    await p.setCredentials({ server: ns(key), username: label, password: secret });
  },
  async read(key: string): Promise<string | null> {
    const p = await pluginOrNull();
    if (!p) return null;
    try { const c = await p.getCredentials({ server: ns(key) }); return c.password ?? null; } catch { return null; }
  },
  async clear(key: string): Promise<void> {
    const p = await pluginOrNull();
    if (!p) return;
    try { await p.deleteCredentials({ server: ns(key) }); } catch { /* already gone */ }
  },
};
```

- [x] **Step 4: Run → pass.** **Step 5: Commit** `feat(bio): client biometric plugin wrapper`.

---

### Task 5: BiometricGate state machine + lock screen

**Files:**
- Create: `frontend/src/components/auth/BiometricGate.tsx`, `frontend/src/components/auth/__tests__/BiometricGate.test.tsx`
- Modify: `frontend/src/api/auth.ts` (biometric API), `frontend/src/App.tsx` (mount the gate)

- [x] **Step 1: Failing test** — drive the machine with mocked `biometric` + `@capacitor/app`:
  - web/no-availability/no-enrolled-key → renders children, no lock.
  - enrolled + cold mount → locked; tap account → verify+read → exchange 200 → unlocked (children visible).
  - exchange 401 → shows "Sign in" escape.
  - background event then resume after >LOCK_TIMEOUT → re-locked; resume <timeout → stays unlocked.
  - axe clean on the locked screen.
  (Mock `@/lib/biometric`, `@/api/auth` exchange, and `@capacitor/app` `addListener`.)

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Implement.** `api/auth.ts` adds:
```ts
biometricExchange: (device_id: string, secret: string) =>
  apiFetch<{ secret: string }>('/auth/biometric/exchange', { method: 'POST', body: JSON.stringify({ device_id, secret }) }),
biometricEnroll: (device_id: string, label: string) =>
  apiFetch<{ secret: string }>('/auth/biometric/enroll', { method: 'POST', body: JSON.stringify({ device_id, label }) }),
biometricUnenroll: (device_id: string) =>
  apiFetch(`/auth/biometric/devices/${device_id}`, { method: 'DELETE' }),
```
`BiometricGate.tsx`: enrolled-accounts come from a local registry persisted at enroll time (localStorage `bio-accounts` = `[{key,label,kind}]`, written by the enroll toggles in Task 6). On mount: if web || !available || registry empty → `disabled` (render children). Else `locked`. `@capacitor/app addListener('appStateChange', ...)`: on `!isActive` stamp `Date.now()`; on `isActive` if `Date.now()-stamp > LOCK_TIMEOUT_MS` (120000) → `locked`. Tap account → `unlocking` → `biometric.verify()` then `biometric.read(key)` → if secret: call the matching exchange (child vs parent by `kind`) → 200 → store rotated secret via `biometric.enroll(key,label,rotated)` → `unlocked`; 401 → `biometric.clear(key)` + remove from registry + escape. Lock screen: Penny + account buttons (≥44px) + "Sign in differently" → navigate to `/login` (clears gate via `unlocked` while unauthenticated, real login takes over). `aria-live` on status.

- [x] **Step 4: Run → pass.** Mount `<BiometricGate>` in `App.tsx` wrapping the authed routes (inside Router, around the child/parent shells). **Step 5: Commit** `feat(bio): biometric lock-screen gate`.

---

### Task 6: Consent toggles (child + parent)

**Files:**
- Modify: `frontend/src/components/child/ProfileMenu.tsx` (child enroll toggle), `frontend/src/components/ChildCard.tsx` (parent master switch), parent settings surface (parent self-enroll), `frontend/src/api/parent.ts` (`setChildBiometric`, `Child.biometric_allowed`), `frontend/src/api/auth.ts` (`Me.biometric_allowed`)
- Test: extend ChildCard + ProfileMenu test files

- [x] **Step 1: Failing tests** — parent `ChildCard`: a "Face ID sign-in" switch calls `setChildBiometric(id, enabled)` (mirror push switch test). Child `ProfileMenu`: the "Sign in with Face ID" toggle is hidden unless `me.biometric_allowed && available`; toggling on calls `biometric.verify()` + `authApi.biometricEnroll` + `biometric.enroll` + registry add; off calls `biometricUnenroll` + `biometric.clear` + registry remove.

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Implement.** `api/parent.ts`: `setChildBiometric: (userId, enabled) => apiFetch('/parent/children/'+userId+'/biometric', {method:'POST', body: JSON.stringify({enabled})})` + `Child.biometric_allowed?: boolean`. `api/auth.ts`: `Me.biometric_allowed?: boolean`. ChildCard: add a Switch next to push (optimistic, same pattern). ParentDashboard/parent settings: a self-enroll toggle calling parent enroll endpoints (add `parentApi.biometricEnroll/Exchange/Unenroll` to `api/parent.ts`). ProfileMenu: gated toggle as specced, writing the `bio-accounts` registry.

- [x] **Step 4: Run → pass.** **Step 5: Commit** `feat(bio): consent toggles (parent master + child/parent enroll)`.

---

### Task 7: Native config + privacy + cap sync

**Files:**
- Modify: `frontend/ios/App/App/Info.plist`, `docs/compliance/privacy-notice.md`

- [x] **Step 1:** Add to `Info.plist`: `<key>NSFaceIDUsageDescription</key><string>Use Face ID to unlock InvestiKid and sign in faster.</string>`.
- [x] **Step 2:** Privacy notice: a short "Face ID / biometric sign-in" paragraph — optional, parent-controlled for children, processed on-device by your phone (we never receive biometric data), revocable.
- [x] **Step 3:** `cd frontend && npm run build && npx cap sync ios` (folds the new plugin + web into build 4; verify the plugin count includes `capacitor-native-biometric`). Commit `feat(bio): Info.plist Face ID usage string + privacy notice`.

---

### Task 8: Security review + full verification

- [x] **Step 1:** Dispatch a security-review pass (per `superpowers:requesting-code-review`, security lens) over the diff: secret entropy/hashing, rotation defeats replay, exchange rate-limit + active/consent re-check (no privilege gain), CSRF parity with `/auth/login`, revocation completeness (delete/disable/unenroll), no PII in stored creds, keychain `BiometryCurrentSet` usage. Address findings.
- [x] **Step 2:** Backend ruff + full pytest (check exit code). Frontend tsc + lint + vitest + build (check exit code). `npx cap sync ios`.
- [x] **Step 3:** Push `testing`; CI green; **confirm Railway testing deploy SUCCESS + health 200** (the standing post-push check). Mark SP-Bio in a tracking note + memory. (Do NOT promote — this rides the held build 4; promotion happens with the build-4 archive + device QA.)
