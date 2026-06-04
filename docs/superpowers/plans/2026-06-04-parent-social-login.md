# Parent Social Login (SP-D1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let parents sign in with Apple + Google (web + native iOS) via server-side ID-token verification (no client secrets), reusing the existing `parent_session`; children/consent/magic-link unchanged.

**Architecture:** A `parent_identity` table links a provider `sub` → parent email. An `oidc` service verifies provider ID tokens against cached JWKS (issuer/aud/exp/nonce). New endpoints under `/parent/auth/oauth/*` verify → resolve/link a parent → issue the existing parent session. Frontend uses one Capacitor plugin (`@capgo/capacitor-social-login`) for web+native, posting the ID token + nonce.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + `python-jose` (already a dep) + `httpx`; React + Capacitor.

**Spec:** `docs/superpowers/specs/2026-06-04-parent-social-login-design.md`

**Conventions:** Backend from `invest-ed/backend`: `/Users/leeashmore/Local Repo/.venv/bin/{pytest,ruff,alembic}`. Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + conftest `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient`. Local test Postgres can hang ~90s → environmental, rely on CI. Frontend from `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` warning), `npm test`, `npm run build`. Git from repo root; commit to `main`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs incl. `security`). **Never read/modify `.env`** — only `.env.example`. **READ each existing file before editing.** iOS device verification is deferred to the user (needs their OAuth creds + Xcode capability).

**Verified integration points:**
- `app/services/tokens.py`: `issue_parent_session(email) -> str` (7-day `parent_session` JWT). `PARENT_SESSION_AUDIENCE`.
- `app/routers/parent_auth.py`: `_PARENT_COOKIE = "parent_session"`, `get_current_parent(request, session) -> str`, magic-link callback sets the cookie via `response.set_cookie(_PARENT_COOKIE, …, httponly=True, samesite=_cookie_samesite(), secure=…, path="/")` + `_set_csrf_cookie(response, secure)`. Reuse `_cookie_samesite` + `_set_csrf_cookie` (imported from `app/routers/auth.py`).
- `app/core/csrf.py`: `_DEFAULT_EXEMPT_PATHS` (exact paths incl. `/parent/auth/request`, `/billing/webhook`) + `_DEFAULT_EXEMPT_PREFIXES`. Add the two sign-in paths as **exact** exempts (keeps `…/link` protected).
- `app/core/rate_limit.py`: `limiter` (slowapi) — used as `@limiter.limit("5/hour")` with a `request: Request` arg.
- Alembic current head: **`e5f6a7b8c9d0`** (new migration's `down_revision`). Migrations live in `backend/alembic/versions/`, run from `backend/`.
- `app/core/config.py` `Settings`: add fields as `str = ""` (unset → provider not configured).

---

### Task 1: `parent_identity` model + migration

**Files:** Create `app/models/parent_identity.py`; Create `alembic/versions/f6a7b8c9d0e1_add_parent_identity.py`.

- [ ] **Step 1: Model.** Create `app/models/parent_identity.py` (follow the SQLAlchemy 2.0 pattern of `app/models/content.py`):
```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParentIdentity(Base):
    __tablename__ = "parent_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_parent_identity_provider_sub"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```
Confirm the Base import path matches the other models (READ `app/models/content.py` head; if it imports `from app.core.database import Base`, use that; adapt if different). Ensure the model is imported where models are registered for Alembic autogenerate/metadata (READ `app/models/__init__.py` and add `from app.models.parent_identity import ParentIdentity` if that file lists models).

- [ ] **Step 2: Confirm the head.** Run from `invest-ed/backend`: `/Users/leeashmore/Local Repo/.venv/bin/alembic heads` → expect `e5f6a7b8c9d0 (head)`. If it differs, use the reported head as `down_revision`.

- [ ] **Step 3: Hand-write the migration** `alembic/versions/f6a7b8c9d0e1_add_parent_identity.py`:
```python
"""add parent_identities table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-04 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parent_identities",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("parent_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_parent_identity_provider_sub"),
    )
    op.create_index("ix_parent_identities_parent_email", "parent_identities", ["parent_email"])


def downgrade() -> None:
    op.drop_index("ix_parent_identities_parent_email", table_name="parent_identities")
    op.drop_table("parent_identities")
```

- [ ] **Step 4: Apply + sanity.** Run from `invest-ed/backend`: `/Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head`. Expected: applies `f6a7b8c9d0e1`. If the local DB hangs ~90s, it's environmental — note it and rely on CI (the migration chains correctly: `alembic history` shows `e5f6a7b8c9d0 -> f6a7b8c9d0e1`). Then `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` → clean.

- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/parent_identity.py invest-ed/backend/app/models/__init__.py invest-ed/backend/alembic/versions/f6a7b8c9d0e1_add_parent_identity.py
git commit -m "feat(auth): parent_identity model + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Config + `.env.example` (public identifiers)

**Files:** Modify `app/core/config.py`, `backend/.env.example`.

- [ ] **Step 1: Settings.** In `app/core/config.py` `Settings`, add (near the other auth settings):
```python
    google_web_client_id: str = ""
    google_ios_client_id: str = ""
    apple_services_id: str = ""
    apple_bundle_id: str = ""
```
- [ ] **Step 2: `.env.example`.** Append (documentation only — these are PUBLIC identifiers, not secrets):
```
# Parent social login (public client identifiers — see docs/parent-social-login-setup.md)
GOOGLE_WEB_CLIENT_ID=
GOOGLE_IOS_CLIENT_ID=
APPLE_SERVICES_ID=
APPLE_BUNDLE_ID=
```
- [ ] **Step 3: Verify + commit.** `ruff check .` clean.
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/core/config.py invest-ed/backend/.env.example
git commit -m "feat(auth): config for parent social-login client identifiers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `oidc` verification service + unit tests (TDD)

**Files:** Create `app/services/oidc.py`, `tests/test_oidc_service.py`.

- [ ] **Step 1: Write the failing tests** `tests/test_oidc_service.py` (mints real RS256 tokens against an injected JWKS — no network, no real creds):
```python
import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose import jwk, jwt

from app.services import oidc

pytestmark = pytest.mark.anyio  # if the repo uses asyncio marker, match it; see note below


def _keypair(kid="test-kid"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    pub_jwk = jwk.construct(pub_pem, "RS256").to_dict()
    pub_jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return priv_pem, {"keys": [pub_jwk]}, kid


def _token(priv_pem, kid, *, iss, aud, sub="sub-1", email="p@example.com", email_verified=True, nonce="n1", exp_delta=600):
    now = int(time.time())
    return jwt.encode(
        {"iss": iss, "aud": aud, "sub": sub, "email": email, "email_verified": email_verified,
         "nonce": nonce, "iat": now, "exp": now + exp_delta},
        priv_pem, algorithm="RS256", headers={"kid": kid},
    )


@pytest.fixture
def google_cfg(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_web_client_id", "web-aud", raising=False)
    monkeypatch.setattr(settings, "google_ios_client_id", "ios-aud", raising=False)


async def _verify(id_token, jwks, nonce="n1", provider="google"):
    return await oidc.verify_id_token(provider, id_token, nonce, jwks_fetch=lambda _url: jwks)


async def test_valid_google_token(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    result = await _verify(tok, jwks)
    assert result.sub == "sub-1"
    assert result.email == "p@example.com"
    assert result.email_verified is True


async def test_wrong_audience(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="someone-else")
    with pytest.raises(oidc.OidcAudienceMismatch):
        await _verify(tok, jwks)


async def test_expired(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud", exp_delta=-10)
    with pytest.raises(oidc.OidcExpired):
        await _verify(tok, jwks)


async def test_bad_signature(google_cfg):
    priv, jwks, kid = _keypair()
    _, other_jwks, _ = _keypair(kid="test-kid")  # different key, same kid
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    with pytest.raises(oidc.OidcInvalid):
        await _verify(tok, other_jwks)


async def test_nonce_mismatch(google_cfg):
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud", nonce="n1")
    with pytest.raises(oidc.OidcNonceMismatch):
        await _verify(tok, jwks, nonce="different")


async def test_not_configured(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_web_client_id", "", raising=False)
    monkeypatch.setattr(settings, "google_ios_client_id", "", raising=False)
    priv, jwks, kid = _keypair()
    tok = _token(priv, kid, iss="https://accounts.google.com", aud="web-aud")
    with pytest.raises(oidc.OidcNotConfigured):
        await _verify(tok, jwks)
```
**Note for the implementer:** match the repo's async test convention — READ a sibling test (e.g. `tests/test_*service*.py`); if they use `pytestmark = pytest.mark.asyncio(loop_scope="session")`, use that instead of `pytest.mark.anyio`. Keep the test bodies.

- [ ] **Step 2: Run, verify FAIL** (module missing): `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_oidc_service.py -q`

- [ ] **Step 3: Implement** `app/services/oidc.py`:
```python
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.config import settings

GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_ISSUERS = {"https://appleid.apple.com"}
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

_JWKS_TTL = 3600
_jwks_cache: dict[str, tuple[float, dict]] = {}


class OidcError(Exception): ...
class OidcInvalid(OidcError): ...
class OidcExpired(OidcError): ...
class OidcAudienceMismatch(OidcError): ...
class OidcNonceMismatch(OidcError): ...
class OidcNotConfigured(OidcError): ...


@dataclass
class VerifiedIdentity:
    sub: str
    email: str | None
    email_verified: bool


def _provider_config(provider: str) -> tuple[set[str], str, set[str]]:
    if provider == "google":
        auds = {a for a in (settings.google_web_client_id, settings.google_ios_client_id) if a}
        return GOOGLE_ISSUERS, GOOGLE_JWKS_URL, auds
    if provider == "apple":
        auds = {a for a in (settings.apple_services_id, settings.apple_bundle_id) if a}
        return APPLE_ISSUERS, APPLE_JWKS_URL, auds
    raise OidcInvalid(f"unknown provider: {provider}")


async def _http_fetch(url: str) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


async def _get_jwks(url: str, fetch: Callable[[str], Awaitable[dict]] | None) -> dict:
    now = time.time()
    cached = _jwks_cache.get(url)
    if cached and cached[0] > now:
        return cached[1]
    data = await (fetch or _http_fetch)(url)
    _jwks_cache[url] = (now + _JWKS_TTL, data)
    return data


async def verify_id_token(
    provider: str,
    id_token: str,
    nonce: str,
    *,
    jwks_fetch: Callable[[str], Awaitable[dict]] | None = None,
) -> VerifiedIdentity:
    issuers, jwks_url, auds = _provider_config(provider)
    if not auds:
        raise OidcNotConfigured(provider)
    jwks = await _get_jwks(jwks_url, jwks_fetch)
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise OidcInvalid(f"bad header: {exc}") from exc
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise OidcInvalid("no matching JWKS key")
    try:
        payload = jwt.decode(
            id_token, key, algorithms=[key.get("alg", "RS256")],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError as exc:
        raise OidcExpired() from exc
    except JWTError as exc:
        raise OidcInvalid(str(exc)) from exc
    if payload.get("iss") not in issuers:
        raise OidcInvalid("issuer mismatch")
    if payload.get("aud") not in auds:
        raise OidcAudienceMismatch()
    if payload.get("nonce") != nonce:
        raise OidcNonceMismatch()
    ev = payload.get("email_verified")
    if isinstance(ev, str):
        ev = ev.lower() == "true"  # Apple returns "true"/"false" strings
    return VerifiedIdentity(sub=payload["sub"], email=payload.get("email"), email_verified=bool(ev))
```
Note: a "different key, same kid" token will fail `jwt.decode` signature → `JWTError` → `OidcInvalid` (covers `test_bad_signature`).

- [ ] **Step 4: Run, verify PASS** (all 6). Then `ruff check .`.
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/oidc.py invest-ed/backend/tests/test_oidc_service.py
git commit -m "feat(auth): OIDC ID-token verification service (Apple/Google)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Sign-in endpoint `POST /parent/auth/oauth/{provider}` + schemas + CSRF exempt + tests

**Files:** Modify `app/schemas/parent.py`, `app/routers/parent_auth.py`, `app/core/csrf.py`; Create `tests/test_parent_oauth.py`.

- [ ] **Step 1: Schemas.** READ `app/schemas/parent.py`, then add:
```python
class OAuthSignInRequest(BaseModel):
    id_token: str
    nonce: str


class IdentityOut(BaseModel):
    provider: str
    parent_email: str
```
(Match the file's existing Pydantic v2 import/style.)

- [ ] **Step 2: CSRF exempt the two sign-in paths.** In `app/core/csrf.py`, add to `_DEFAULT_EXEMPT_PATHS` (the exact-path set) — NOT a prefix, so `…/link` stays protected:
```python
    "/parent/auth/oauth/google",
    "/parent/auth/oauth/apple",
```

- [ ] **Step 3: Write the failing endpoint test** `tests/test_parent_oauth.py` (mocks `verify_id_token` so no real tokens needed; uses the conftest `client` + `db_session` fixtures; match the async marker convention of sibling tests):
```python
import pytest
from app.services import oidc
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _patch_verify(monkeypatch, *, sub, email, email_verified=True):
    async def fake(provider, id_token, nonce, **kw):
        return oidc.VerifiedIdentity(sub=sub, email=email, email_verified=email_verified)
    monkeypatch.setattr("app.routers.parent_auth.verify_id_token", fake)


async def test_signin_autolinks_on_matching_parent_email(client, db_session, monkeypatch):
    # a child user whose parent_email is the social email
    db_session.add(User(username="kid", email="kid@example.com", parent_email="parent@example.com", hashed_password="x", dob="2015-01-01", country_code="GB", currency_code="GBP"))
    await db_session.commit()
    _patch_verify(monkeypatch, sub="g-sub-1", email="parent@example.com", email_verified=True)
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code == 200
    assert r.json()["status"] == "signed_in"
    assert "parent_session" in r.cookies


async def test_signin_no_parent_account(client, monkeypatch):
    _patch_verify(monkeypatch, sub="g-sub-x", email="nobody@example.com", email_verified=True)
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code in (401, 404)
    assert "parent_session" not in r.cookies


async def test_signin_rejects_unverified_email_autolink(client, db_session, monkeypatch):
    db_session.add(User(username="kid2", email="kid2@example.com", parent_email="parent2@example.com", hashed_password="x", dob="2015-01-01", country_code="GB", currency_code="GBP"))
    await db_session.commit()
    _patch_verify(monkeypatch, sub="g-sub-2", email="parent2@example.com", email_verified=False)
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code in (401, 404)


async def test_signin_via_existing_link(client, db_session, monkeypatch):
    from app.models.parent_identity import ParentIdentity
    import uuid as _uuid
    from datetime import datetime, UTC
    db_session.add(ParentIdentity(id=_uuid.uuid4(), provider="google", provider_subject="g-sub-3", parent_email="linked@example.com", created_at=datetime.now(UTC)))
    await db_session.commit()
    _patch_verify(monkeypatch, sub="g-sub-3", email=None, email_verified=False)  # e.g. Apple private relay, no email
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code == 200
    assert "parent_session" in r.cookies
```
(READ `conftest.py` + a sibling test to confirm the `User(...)` constructor kwargs — adjust the User fields to the real model if they differ; the point is "a user with parent_email == X exists".)

- [ ] **Step 4: Run, verify FAIL.**

- [ ] **Step 5: Implement the endpoint** in `app/routers/parent_auth.py`. Add imports (`select` already there): `from app.services.oidc import verify_id_token, OidcError, OidcNotConfigured`, `from app.services.tokens import issue_parent_session` (already imported), `from app.models.parent_identity import ParentIdentity`, `from app.schemas.parent import OAuthSignInRequest, IdentityOut`, `from datetime import datetime, UTC`, `import uuid`. Then:
```python
_OAUTH_PROVIDERS = {"google", "apple"}


def _set_parent_cookies(response: Response, email: str) -> None:
    secure = settings.environment != "development"
    response.set_cookie(
        _PARENT_COOKIE, issue_parent_session(email),
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)


@router.post("/oauth/{provider}", status_code=200)
@limiter.limit("10/hour")
async def oauth_sign_in(
    request: Request,  # noqa: ARG001  -- required by slowapi
    provider: str,
    payload: OAuthSignInRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    try:
        identity = await verify_id_token(provider, payload.id_token, payload.nonce)
    except OidcNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Provider not configured")
    except OidcError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sign-in")

    # 1) existing link by (provider, sub)
    link = await session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider,
            ParentIdentity.provider_subject == identity.sub,
        ).limit(1)
    )
    parent_email: str | None = link.parent_email if link else None

    # 2) auto-link on verified email matching an existing parent_email
    if parent_email is None and identity.email and identity.email_verified:
        match = await session.scalar(
            select(User).where(User.parent_email == identity.email).limit(1)
        )
        if match is not None:
            parent_email = identity.email
            session.add(ParentIdentity(
                id=uuid.uuid4(), provider=provider, provider_subject=identity.sub,
                parent_email=parent_email, created_at=datetime.now(UTC),
            ))
            await session.commit()

    # 3) no parent account
    if parent_email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No parent account for this sign-in")

    _set_parent_cookies(response, parent_email)
    return {"status": "signed_in", "email": parent_email}
```

- [ ] **Step 6: Run, verify PASS.** `ruff check .` clean. (If the Postgres run hangs, rely on CI.)
- [ ] **Step 7: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/parent.py invest-ed/backend/app/routers/parent_auth.py invest-ed/backend/app/core/csrf.py invest-ed/backend/tests/test_parent_oauth.py
git commit -m "feat(auth): parent OAuth sign-in endpoint (verify + link + session)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Link / unlink / list endpoints + tests

**Files:** Modify `app/routers/parent_auth.py`; extend `tests/test_parent_oauth.py`.

- [ ] **Step 1: Tests** (append): a signed-in parent (use the magic-link callback or directly set the `parent_session` cookie via a helper — READ how existing parent tests authenticate; reuse that) can `POST /parent/auth/oauth/{provider}/link` (creates a link to their email for a new sub), `GET /parent/auth/identities` (lists it), `DELETE /parent/auth/oauth/{provider}/link` (removes it). Verify link is idempotent (second POST same sub+email → still one row / 200). Mock `verify_id_token` as in Task 4.
- [ ] **Step 2: Run, verify FAIL.**
- [ ] **Step 3: Implement** in `app/routers/parent_auth.py`:
```python
@router.post("/oauth/{provider}/link", status_code=200)
async def link_provider(
    provider: str,
    payload: OAuthSignInRequest,
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    try:
        identity = await verify_id_token(provider, payload.id_token, payload.nonce)
    except OidcNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Provider not configured")
    except OidcError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    existing = await session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider, ParentIdentity.provider_subject == identity.sub
        ).limit(1)
    )
    if existing is None:
        session.add(ParentIdentity(
            id=uuid.uuid4(), provider=provider, provider_subject=identity.sub,
            parent_email=parent_email, created_at=datetime.now(UTC),
        ))
        await session.commit()
    elif existing.parent_email != parent_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked to another account")
    return {"status": "linked", "provider": provider}


@router.delete("/oauth/{provider}/link", status_code=200)
async def unlink_provider(
    provider: str,
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    rows = (await session.scalars(
        select(ParentIdentity).where(
            ParentIdentity.provider == provider, ParentIdentity.parent_email == parent_email
        )
    )).all()
    for row in rows:
        await session.delete(row)
    await session.commit()
    return {"status": "unlinked", "provider": provider}


@router.get("/identities", response_model=list[IdentityOut])
async def list_identities(
    session: AsyncSession = Depends(get_session),
    parent_email: str = Depends(get_current_parent),
):
    rows = (await session.scalars(
        select(ParentIdentity).where(ParentIdentity.parent_email == parent_email)
    )).all()
    return [IdentityOut(provider=r.provider, parent_email=r.parent_email) for r in rows]
```
- [ ] **Step 4: Run, verify PASS.** `ruff check .`.
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/parent_auth.py invest-ed/backend/tests/test_parent_oauth.py
git commit -m "feat(auth): parent provider link/unlink/list endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Frontend API client + nonce util + tests

**Files:** Create `src/api/parentAuth.ts`, `src/lib/nonce.ts`, `src/api/__tests__/parentAuth.test.ts` (or the repo's test location).

- [ ] **Step 1: READ** `src/api/client.ts` (`apiFetch` adds `Content-Type`, CSRF header on non-GET, `X-Capacitor-App` for native, `credentials: include`). Then create `src/lib/nonce.ts`:
```ts
export function makeNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
```
- [ ] **Step 2: Create `src/api/parentAuth.ts`:**
```ts
import { apiFetch } from './client';

export type Provider = 'apple' | 'google';
export type ParentIdentity = { provider: string; parent_email: string };

export const parentAuthApi = {
  oauthSignIn: (provider: Provider, idToken: string, nonce: string) =>
    apiFetch<{ status: string; email: string }>(`/parent/auth/oauth/${provider}`, {
      method: 'POST', body: JSON.stringify({ id_token: idToken, nonce }),
    }),
  linkProvider: (provider: Provider, idToken: string, nonce: string) =>
    apiFetch<{ status: string }>(`/parent/auth/oauth/${provider}/link`, {
      method: 'POST', body: JSON.stringify({ id_token: idToken, nonce }),
    }),
  unlinkProvider: (provider: Provider) =>
    apiFetch<{ status: string }>(`/parent/auth/oauth/${provider}/link`, { method: 'DELETE' }),
  listIdentities: () => apiFetch<ParentIdentity[]>('/parent/auth/identities'),
};
```
- [ ] **Step 3: Test** `makeNonce` (16-byte hex, unique across calls) + the api client shapes (mock `apiFetch`). Run `npm test -- nonce` / the api test. 
- [ ] **Step 4: Verify + commit.** `npx tsc -b && npm run lint && npm test`.
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/parentAuth.ts invest-ed/frontend/src/lib/nonce.ts invest-ed/frontend/src/api/__tests__
git commit -m "feat(auth): frontend parent-auth API client + nonce util

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Provider buttons on ParentLogin (plugin mocked in tests)

**Files:** Add dep `@capgo/capacitor-social-login`; Create `src/lib/socialLogin.ts` (thin wrapper around the plugin); Modify `src/pages/ParentLogin.tsx`; tests.

- [ ] **Step 1: Install the plugin** (from `invest-ed/frontend`): `npm install @capgo/capacitor-social-login`. (It is vetted by the `security`/npm-audit CI job — if audit flags a high/critical advisory, STOP and report so we can reassess the plugin.)
- [ ] **Step 2: Wrapper `src/lib/socialLogin.ts`** — isolates the plugin so tests can mock one module:
```ts
import { SocialLogin } from '@capgo/capacitor-social-login';
import { makeNonce } from './nonce';
import type { Provider } from '@/api/parentAuth';

// Returns the provider ID token + the nonce used (caller posts both to the backend).
export async function socialIdToken(provider: Provider): Promise<{ idToken: string; nonce: string }> {
  const nonce = makeNonce();
  const res = await SocialLogin.login({ provider, options: { nonce } });
  // Plugin returns provider-specific result; the ID token field name differs by provider.
  // Normalise: Apple → result.result.idToken; Google → result.result.idToken (both expose idToken).
  const idToken = (res as { result?: { idToken?: string } }).result?.idToken;
  if (!idToken) throw new Error('No ID token from provider');
  return { idToken, nonce };
}
```
(READ the plugin's README during implementation to confirm the exact result shape + any `initialize` call needed with the client IDs; adjust the normalisation accordingly. If `initialize` is required, add a `src/lib/socialLogin.ts` `init()` using `import.meta.env` public client-id vars and call it once at app start — keep client IDs as PUBLIC `VITE_` env, not secrets.)
- [ ] **Step 3: ParentLogin buttons.** READ `src/pages/ParentLogin.tsx`. Above the magic-link form, add an "Continue with Apple" + "Continue with Google" button group + a divider ("or"). On click: `const { idToken, nonce } = await socialIdToken(provider); await parentAuthApi.oauthSignIn(provider, idToken, nonce); navigate('/parent');` with try/catch surfacing a friendly error (e.g. "We couldn't find a parent account for that sign-in — ask your child to sign up with your email, or use the email link below."). Buttons use existing button styling; ensure ≥16px text + visible focus + accessible names ("Continue with Apple").
- [ ] **Step 4: Tests.** Mock `@/lib/socialLogin` (`socialIdToken`) and `@/api/parentAuth`; assert clicking a button calls `oauthSignIn` then navigates; the no-account error renders. `vitest-axe` on the buttons. Run `npm test`.
- [ ] **Step 5: Verify + commit.** `npx tsc -b && npm run lint && npm test && npm run build`.
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/package.json invest-ed/frontend/package-lock.json invest-ed/frontend/src/lib/socialLogin.ts invest-ed/frontend/src/pages/ParentLogin.tsx invest-ed/frontend/src/pages/__tests__ invest-ed/frontend/tests
git commit -m "feat(auth): Continue with Apple/Google on parent sign-in

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Connect/unlink in parent settings

**Files:** Modify the parent settings/account area (READ `src/pages/ParentDashboard.tsx` + components under `src/components/parent/` to find the settings/account section); tests.

- [ ] **Step 1: READ** the parent dashboard to find where account controls live. Add a "Sign-in methods" section that calls `parentAuthApi.listIdentities()` and shows connected providers with **Connect** (runs `socialIdToken` → `linkProvider`) / **Disconnect** (`unlinkProvider`) buttons. Refetch the list after each action. Friendly errors (e.g. 409 "already linked to another account").
- [ ] **Step 2: Tests.** Mock `socialLogin` + `parentAuthApi`; assert Connect links + refreshes, Disconnect unlinks; `vitest-axe`.
- [ ] **Step 3: Verify + commit.** `npx tsc -b && npm run lint && npm test && npm run build`.
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/ParentDashboard.tsx invest-ed/frontend/src/components/parent invest-ed/frontend/src/pages/__tests__ invest-ed/frontend/tests
git commit -m "feat(auth): connect/disconnect social providers in parent settings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Native iOS wiring + setup doc

**Files:** `ios/App/` (entitlement + URL scheme via `npx cap sync`); Create `docs/parent-social-login-setup.md`.

- [ ] **Step 1: Sync native.** From `invest-ed/frontend`: `npm run build && npx cap sync ios`. Commit the resulting `ios/App` changes (the plugin's pod/SPM registration). Note in the report that **enabling the "Sign in with Apple" capability in Xcode and adding the Google reversed-client-id URL scheme are USER tasks** (documented in the setup doc) — do what `cap sync` does automatically; do NOT hand-edit signing/capabilities.
- [ ] **Step 2: Setup doc.** Create `docs/parent-social-login-setup.md` covering: (a) Google Cloud — OAuth consent screen + Web client ID + iOS client ID (bundle `leeashmore.investikid.ai.app`); (b) Apple Developer — enable Sign in with Apple on the App ID, create a Services ID + return URLs; (c) enable the Sign-in-with-Apple capability in Xcode + add the Google reversed-client-id URL scheme; (d) set `GOOGLE_WEB_CLIENT_ID`, `GOOGLE_IOS_CLIENT_ID`, `APPLE_SERVICES_ID`, `APPLE_BUNDLE_ID` in env (Railway + local `.env`) and the matching `VITE_` public client-id vars in the frontend env; (e) note: ID-token-only — no client secrets/keys.
- [ ] **Step 3: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/ios invest-ed/docs/parent-social-login-setup.md
git commit -m "feat(auth): native social-login sync + setup guide

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Final regression + push

- [ ] **Step 1: Backend regression.** From `invest-ed/backend`: `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` (clean) + `/Users/leeashmore/Local Repo/.venv/bin/pytest -q` (green; if the DB hangs locally, rely on CI). Confirm `alembic heads` shows the single head `f6a7b8c9d0e1`.
- [ ] **Step 2: Frontend regression.** From `invest-ed/frontend`: `npx tsc -b && npm run lint && npm test && npm run build`. Expected green (button.tsx warning only).
- [ ] **Step 3: Push.** From repo root: `git push origin main`.
- [ ] **Step 4: Confirm green CI** — all 5 jobs, **especially `security`** (bandit/pip-audit/npm audit must pass, incl. the new plugin). Fix any failure before declaring SP-D1 done.
- [ ] **Step 5: Report SP-D1 complete** — parent Apple/Google sign-in (web + native) behind real OIDC verification, no secrets; the four client identifiers + Xcode capability are the user's setup tasks (per `docs/parent-social-login-setup.md`) before real end-to-end sign-in works. Next: SP-D2 (auth-screen polish) or SP-E.

---

## Self-Review

**1. Spec coverage:** `parent_identity` model+migration → T1; config/`.env.example` → T2; `oidc` verify + tests → T3; sign-in endpoint + CSRF-exempt + linking rules → T4; link/unlink/list → T5; FE api+nonce → T6; ParentLogin buttons (plugin) → T7; settings connect/unlink → T8; native + setup doc → T9; regression/security → T10. All spec sections covered. ✓

**2. Placeholder scan:** Load-bearing backend code (model, migration, oidc service + tests, endpoints + tests) is complete and concrete. Frontend tasks carry the api client, nonce, and wrapper code, with READ-first steps for the plugin result shape + ParentLogin/settings integration (genuinely needs the file contents + plugin README — flagged, not hand-waved). No TBD/"handle errors".

**3. Type consistency:** `verify_id_token(provider, id_token, nonce, *, jwks_fetch)` → `VerifiedIdentity{sub,email,email_verified}` used identically in T3/T4/T5. `OidcError`/subclasses consistent. `ParentIdentity` fields (`provider`,`provider_subject`,`parent_email`,`created_at`) match across model (T1), migration (T1), endpoints (T4/T5), tests. `OAuthSignInRequest{id_token,nonce}` + `IdentityOut{provider,parent_email}` consistent T4/T5/T6. Frontend `parentAuthApi` methods match the endpoints. Migration `down_revision="e5f6a7b8c9d0"` chains the real head; revision `f6a7b8c9d0e1` referenced in T10. ✓
