import uuid as _uuid
from datetime import UTC, date, datetime

import pytest

from app.services import oidc
from app.services.tokens import issue_parent_session

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers for authenticated parent requests
# ---------------------------------------------------------------------------

_TRUSTED_ORIGIN = {"Origin": "https://localhost"}


async def _auth_headers(db_session, parent_email: str) -> dict:
    """Return headers that carry a valid (persisted) parent session and bypass CSRF."""
    token = await issue_parent_session(db_session, parent_email)
    await db_session.commit()
    return {
        "Origin": "https://localhost",
        "Cookie": f"parent_session={token}",
    }


def _patch_verify(monkeypatch, *, sub, email, email_verified=True):
    async def fake(provider, id_token, nonce, **kw):
        return oidc.VerifiedIdentity(sub=sub, email=email, email_verified=email_verified)

    monkeypatch.setattr("app.routers.parent_auth.verify_id_token", fake)


def _make_user(parent_email: str, suffix: str = ""):
    from app.models.user import User

    return User(
        username=f"kid_{suffix or parent_email.replace('@', '_').replace('.', '_')}",
        password_hash="x",
        dob=date(2013, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent_email,
    )


async def test_signin_autolinks_on_matching_parent_email(client, db_session, monkeypatch):
    db_session.add(_make_user("parent@example.com", "auto1"))
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
    db_session.add(_make_user("parent2@example.com", "auto2"))
    await db_session.commit()
    _patch_verify(monkeypatch, sub="g-sub-2", email="parent2@example.com", email_verified=False)
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code in (401, 404)


async def test_signin_via_existing_link(client, db_session, monkeypatch):
    from app.models.parent_identity import ParentIdentity

    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(),
            provider="google",
            provider_subject="g-sub-3",
            parent_email="linked@example.com",
            created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    _patch_verify(monkeypatch, sub="g-sub-3", email=None, email_verified=False)
    r = await client.post("/parent/auth/oauth/google", json={"id_token": "tok", "nonce": "n1"})
    assert r.status_code == 200
    assert "parent_session" in r.cookies


async def test_oauth_returning_user_persists_session_row(client, db_session, monkeypatch):
    """Returning-user sign-in (existing link) must COMMIT a ParentSession row and authenticate."""
    from sqlalchemy import select

    from app.models.parent_identity import ParentIdentity
    from app.models.parent_session import ParentSession

    parent = "returning@example.com"
    sub = "g-sub-returning"
    db_session.add(_make_user(parent, "ret"))
    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(),
            provider="google",
            provider_subject=sub,
            parent_email=parent,
            created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    _patch_verify(monkeypatch, sub=sub, email=parent)
    r = await client.post(
        "/parent/auth/oauth/google",
        json={"id_token": "tok", "nonce": "n1"},
        headers=_TRUSTED_ORIGIN,
    )
    assert r.status_code == 200
    assert "parent_session" in r.cookies

    # Key assertion: the returning-user path must have COMMITTED the session row.
    row = await db_session.scalar(
        select(ParentSession).where(
            ParentSession.parent_email == parent,
            ParentSession.revoked_at.is_(None),
        )
    )
    assert row is not None

    # The issued cookie (persisted on the client) must authenticate.
    r2 = await client.get("/parent/children", headers=_TRUSTED_ORIGIN)
    assert r2.status_code == 200


async def test_unknown_provider(client, monkeypatch):
    _patch_verify(monkeypatch, sub="x", email="x@example.com")
    # Send a trusted origin so CSRF middleware passes through to the router,
    # which then returns 404 for the unsupported provider.
    r = await client.post(
        "/parent/auth/oauth/microsoft",
        json={"id_token": "tok", "nonce": "n1"},
        headers={"Origin": "https://localhost"},
    )
    assert r.status_code == 404


# ===========================================================================
# Task 5 — link / unlink / list
# ===========================================================================

async def test_link_creates_identity(client, db_session, monkeypatch):
    """POST /link for an authenticated parent creates a ParentIdentity row."""
    from sqlalchemy import select

    from app.models.parent_identity import ParentIdentity

    parent = "linkparent1@example.com"
    db_session.add(_make_user(parent, "lp1"))
    await db_session.commit()

    _patch_verify(monkeypatch, sub="link-sub-1", email=parent)
    r = await client.post(
        "/parent/auth/oauth/google/link",
        json={"id_token": "tok", "nonce": "n"},
        headers=await _auth_headers(db_session, parent),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "linked"

    row = await db_session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == "google",
            ParentIdentity.provider_subject == "link-sub-1",
        )
    )
    assert row is not None
    assert row.parent_email == parent


async def test_link_idempotent(client, db_session, monkeypatch):
    """POST /link twice with the same token creates exactly one row."""
    from sqlalchemy import func, select

    from app.models.parent_identity import ParentIdentity

    parent = "linkparent2@example.com"
    db_session.add(_make_user(parent, "lp2"))
    await db_session.commit()

    _patch_verify(monkeypatch, sub="link-sub-2", email=parent)
    headers = await _auth_headers(db_session, parent)
    payload = {"id_token": "tok", "nonce": "n"}

    r1 = await client.post("/parent/auth/oauth/google/link", json=payload, headers=headers)
    assert r1.status_code == 200

    r2 = await client.post("/parent/auth/oauth/google/link", json=payload, headers=headers)
    assert r2.status_code == 200

    count = await db_session.scalar(
        select(func.count()).select_from(ParentIdentity).where(
            ParentIdentity.provider == "google",
            ParentIdentity.provider_subject == "link-sub-2",
        )
    )
    assert count == 1


async def test_link_conflict_different_parent(client, db_session, monkeypatch):
    """POST /link by a different parent for an already-linked identity → 409."""
    from app.models.parent_identity import ParentIdentity

    owner = "linkowner@example.com"
    intruder = "intruder@example.com"
    db_session.add(_make_user(owner, "lo"))
    db_session.add(_make_user(intruder, "li"))
    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(), provider="google", provider_subject="link-sub-conflict",
            parent_email=owner, created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    _patch_verify(monkeypatch, sub="link-sub-conflict", email=intruder)
    r = await client.post(
        "/parent/auth/oauth/google/link",
        json={"id_token": "tok", "nonce": "n"},
        headers=await _auth_headers(db_session, intruder),
    )
    assert r.status_code == 409


async def test_list_identities(client, db_session, monkeypatch):
    """GET /identities returns the linked providers for the authenticated parent only."""
    from app.models.parent_identity import ParentIdentity

    parent_a = "listparent_a@example.com"
    parent_b = "listparent_b@example.com"
    db_session.add(_make_user(parent_a, "la"))
    db_session.add(_make_user(parent_b, "lb"))
    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(), provider="google", provider_subject="list-sub-a",
            parent_email=parent_a, created_at=datetime.now(UTC),
        )
    )
    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(), provider="apple", provider_subject="list-sub-b",
            parent_email=parent_b, created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    r = await client.get(
        "/parent/auth/identities",
        headers=await _auth_headers(db_session, parent_a),
    )
    assert r.status_code == 200
    providers = [item["provider"] for item in r.json()]
    assert "google" in providers
    # Must NOT expose parent_b's apple identity
    assert "apple" not in providers


async def test_unlink_removes_identity(client, db_session, monkeypatch):
    """DELETE /link removes the row; GET /identities no longer lists it."""
    from sqlalchemy import select

    from app.models.parent_identity import ParentIdentity

    parent = "unlinkparent@example.com"
    db_session.add(_make_user(parent, "ulp"))
    db_session.add(
        ParentIdentity(
            id=_uuid.uuid4(), provider="google", provider_subject="unlink-sub-1",
            parent_email=parent, created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    headers = await _auth_headers(db_session, parent)

    r_del = await client.delete("/parent/auth/oauth/google/link", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "unlinked"

    # Row gone
    row = await db_session.scalar(
        select(ParentIdentity).where(
            ParentIdentity.provider == "google",
            ParentIdentity.parent_email == parent,
        )
    )
    assert row is None

    # GET /identities no longer shows it
    r_list = await client.get("/parent/auth/identities", headers=headers)
    assert r_list.status_code == 200
    providers = [item["provider"] for item in r_list.json()]
    assert "google" not in providers


async def test_unauthenticated_link(client, monkeypatch):
    """Requests without a parent session → 401."""
    _patch_verify(monkeypatch, sub="x", email="x@example.com")
    r = await client.post(
        "/parent/auth/oauth/google/link",
        json={"id_token": "tok", "nonce": "n"},
        headers=_TRUSTED_ORIGIN,
    )
    assert r.status_code == 401


async def test_unauthenticated_unlink(client):
    """DELETE without a parent session → 401."""
    r = await client.delete(
        "/parent/auth/oauth/google/link",
        headers=_TRUSTED_ORIGIN,
    )
    assert r.status_code == 401


async def test_unauthenticated_list(client):
    """GET /identities without a parent session → 401."""
    r = await client.get("/parent/auth/identities")
    assert r.status_code == 401
