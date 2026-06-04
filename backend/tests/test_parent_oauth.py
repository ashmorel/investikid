import uuid as _uuid
from datetime import UTC, date, datetime

import pytest

from app.services import oidc

pytestmark = pytest.mark.asyncio(loop_scope="session")


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
