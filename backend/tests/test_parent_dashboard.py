import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup(client, db_session, parent_email="dad@example.com",
                 child_email="kid7@example.com", child_username="kid7"):
    """Create child + parent magic-link session in client cookies."""
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


async def test_list_children_returns_own(client, db_session):
    await _setup(client, db_session)
    r = await client.get("/parent/children")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["username"] == "kid7"
    assert body[0]["is_active"] is False


async def test_list_children_unauthenticated(client):
    client.cookies.clear()
    r = await client.get("/parent/children")
    assert r.status_code == 401


async def test_freeze_toggles_is_active(client, db_session):
    await _setup(client, db_session, child_email="kid8@example.com", child_username="kid8")
    children = (await client.get("/parent/children")).json()
    cid = children[0]["user_id"]
    r = await client.post(
        f"/parent/children/{cid}/freeze",
        json={"frozen": True},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200
    user = await db_session.scalar(
        select(User).where(User.id == uuid.UUID(cid))
        .execution_options(include_deleted=True)
    )
    await db_session.refresh(user)
    assert user.is_active is False


async def test_freeze_other_parents_child_404(client, db_session):
    await client.post("/auth/register", json={
        "email": "stranger@example.com", "username": "stranger", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "other@example.com",
    })
    other = await db_session.scalar(select(User).where(User.email == "stranger@example.com"))
    await _setup(client, db_session, child_email="kid9@example.com", child_username="kid9")
    r = await client.post(
        f"/parent/children/{other.id}/freeze",
        json={"frozen": True},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 404


async def test_erasure_sets_deleted_at(client, db_session):
    await _setup(client, db_session, child_email="kid10@example.com", child_username="kid10")
    children = (await client.get("/parent/children")).json()
    cid = children[0]["user_id"]
    r = await client.post(
        f"/parent/children/{cid}/erasure",
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200
    user = await db_session.scalar(
        select(User).where(User.id == uuid.UUID(cid))
        .execution_options(include_deleted=True)
    )
    await db_session.refresh(user)
    assert user.deleted_at is not None
    assert user.deletion_requested_at is not None
    assert user.is_active is False


async def test_parent_export_child(client, db_session):
    await _setup(
        client, db_session,
        parent_email="pexparent@example.com",
        child_email="pexkid@example.com",
        child_username="pexkid",
    )
    children = (await client.get("/parent/children")).json()
    cid = children[0]["user_id"]
    resp = await client.get(f"/parent/children/{cid}/export")
    assert resp.status_code == 200
    assert resp.json()["profile"]["username"] == "pexkid"


async def test_parent_export_not_owned_404(client, db_session):
    import uuid as _uuid
    await _setup(
        client, db_session,
        parent_email="stranger@example.com",
        child_email="strangerchild@example.com",
        child_username="strangerchild",
    )
    resp = await client.get(f"/parent/children/{_uuid.uuid4()}/export")
    assert resp.status_code == 404


async def test_freeze_deleted_child_returns_410(client, db_session):
    await _setup(client, db_session, child_email="kid11@example.com", child_username="kid11")
    children = (await client.get("/parent/children")).json()
    cid = children[0]["user_id"]
    erasure = await client.post(
        f"/parent/children/{cid}/erasure",
        headers=_csrf_headers(client),
    )
    assert erasure.status_code == 200
    r = await client.post(
        f"/parent/children/{cid}/freeze",
        json={"frozen": True},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 410


async def test_parent_can_toggle_child_premium(client, db_session):
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.models.user import User

    await client.post("/auth/register", json={
        "username": "ptierkid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "ptierparent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    child = await db_session.scalar(select(User).where(User.username == "ptierkid"))
    await _setup(client, db_session, parent_email="ptierparent@example.com",
                 child_email="ptierparent_dummy@example.com", child_username="ptierparentdummy")

    up = await client.post(
        f"/parent/children/{child.id}/premium", json={"premium": True},
        headers=_csrf_headers(client))
    assert up.status_code == 200
    assert up.json() == {"status": "ok", "premium": True}
    await db_session.refresh(child)
    assert child.is_premium is True
    aud = (await db_session.scalars(select(AuditLog).where(
        AuditLog.user_id == child.id, AuditLog.event_type == "premium_grant"))).all()
    assert len(aud) == 1

    down = await client.post(
        f"/parent/children/{child.id}/premium", json={"premium": False},
        headers=_csrf_headers(client))
    assert down.status_code == 200
    assert down.json() == {"status": "ok", "premium": False}
    await db_session.refresh(child)
    assert child.is_premium is False


async def test_parent_premium_toggle_not_owned_404(client, db_session):
    import uuid
    await _setup(client, db_session, parent_email="ptierstranger@example.com",
                 child_email="ptierstrangerchild@example.com", child_username="ptierstrangerchild")
    resp = await client.post(
        f"/parent/children/{uuid.uuid4()}/premium", json={"premium": True},
        headers=_csrf_headers(client))
    assert resp.status_code == 404
