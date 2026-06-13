"""Parent biometric endpoints + master toggle + deletion revocation (SP-Bio Task 3)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services import biometric_service as bio
from tests.test_billing import _csrf_headers, _setup_parent

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _parent(client, db_session):
    parent = f"bp{uuid.uuid4().hex[:6]}@example.com"
    await _setup_parent(
        client, db_session, parent_email=parent,
        child_email=f"bpk{uuid.uuid4().hex[:6]}@example.com",
        child_username=f"bpk{uuid.uuid4().hex[:6]}",
    )
    return parent


async def test_parent_enroll_then_exchange(client, db_session):
    await _parent(client, db_session)
    r = await client.post("/parent/auth/biometric/enroll", json={"device_id": "pdev-aaaa", "label": "Parent"}, headers=_csrf_headers(client))
    assert r.status_code == 200
    secret = r.json()["secret"]

    client.cookies.clear()
    r2 = await client.post("/parent/auth/biometric/exchange", json={"device_id": "pdev-aaaa", "secret": secret})
    assert r2.status_code == 200
    assert r2.json()["secret"] != secret
    assert (await client.get("/parent/children")).status_code == 200


async def test_parent_exchange_rejected_with_no_children(client, db_session):
    parent = await _parent(client, db_session)
    r = await client.post("/parent/auth/biometric/enroll", json={"device_id": "pdev-bbbb", "label": "Parent"}, headers=_csrf_headers(client))
    secret = r.json()["secret"]
    # soft-delete the only child
    child = await db_session.scalar(select(User).where(User.parent_email == parent))
    from datetime import UTC, datetime
    child.deleted_at = datetime.now(UTC)
    await db_session.commit()
    client.cookies.clear()
    assert (await client.post("/parent/auth/biometric/exchange", json={"device_id": "pdev-bbbb", "secret": secret})).status_code == 401


async def test_master_toggle_flips_and_disable_revokes(client, db_session):
    parent = await _parent(client, db_session)
    child = await db_session.scalar(select(User).where(User.parent_email == parent))

    r = await client.post(f"/parent/children/{child.id}/biometric", json={"enabled": True}, headers=_csrf_headers(client))
    assert r.status_code == 200 and r.json() == {"status": "ok", "biometric_allowed": True}
    await db_session.refresh(child)
    assert child.biometric_allowed is True

    # enroll a child credential directly, then parent disable must revoke it
    secret = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="cdev-xxxx", label="kid")
    await db_session.commit()
    assert await bio.verify_and_rotate(db_session, device_id="cdev-xxxx", secret=secret) is not None
    # re-issue (verify rotated it); fetch fresh secret
    secret = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="cdev-yyyy", label="kid")
    await db_session.commit()

    r = await client.post(f"/parent/children/{child.id}/biometric", json={"enabled": False}, headers=_csrf_headers(client))
    assert r.status_code == 200
    assert await bio.verify_and_rotate(db_session, device_id="cdev-yyyy", secret=secret) is None


async def test_children_list_exposes_biometric_allowed(client, db_session):
    await _parent(client, db_session)
    r = await client.get("/parent/children")
    assert r.status_code == 200
    assert all("biometric_allowed" in c for c in r.json())


async def test_parent_account_deletion_revokes_creds(client, db_session):
    parent = await _parent(client, db_session)
    child = await db_session.scalar(select(User).where(User.parent_email == parent))
    psecret = await bio.issue(db_session, subject_kind="parent", user_id=None, parent_email=parent, device_id="pdev-del", label="Parent")
    csecret = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="cdev-del", label="kid")
    await db_session.commit()

    r = await client.post("/parent/account/delete", json={"confirm_email": parent}, headers=_csrf_headers(client))
    assert r.status_code in (200, 202)
    assert await bio.verify_and_rotate(db_session, device_id="pdev-del", secret=psecret) is None
    assert await bio.verify_and_rotate(db_session, device_id="cdev-del", secret=csecret) is None
