"""biometric_service: issue / verify_and_rotate / revoke (SP-Bio Task 1)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.models.biometric import BiometricCredential
from app.models.user import User
from app.services import biometric_service as bio

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session) -> User:
    s = uuid.uuid4().hex[:8]
    u = User(
        username=f"b{s}", email=f"b{s}@example.com", password_hash="x",
        dob=datetime(2014, 1, 1).date(), country_code="GB", currency_code="GBP",
        parent_email="p@example.com",
    )
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
    rotated = row.last_secret
    # old secret no longer verifies; rotated one does
    assert await bio.verify_and_rotate(db_session, device_id="dev-1", secret=secret) is None
    assert await bio.verify_and_rotate(db_session, device_id="dev-1", secret=rotated) is not None


async def test_reenroll_same_device_replaces(db_session):
    child = await _child(db_session)
    await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-2", label="a")
    await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-2", label="a")
    await db_session.flush()
    rows = (await db_session.scalars(
        select(BiometricCredential).where(BiometricCredential.device_id == "dev-2")
    )).all()
    assert len(rows) == 1


async def test_revoked_and_expired_do_not_verify(db_session):
    child = await _child(db_session)
    secret = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-3", label="a")
    await db_session.flush()
    await bio.revoke_subject(db_session, subject_key=bio.subject_key_for_child(child.id))
    assert await bio.verify_and_rotate(db_session, device_id="dev-3", secret=secret) is None

    secret2 = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dev-4", label="a")
    await db_session.flush()
    await db_session.execute(
        update(BiometricCredential).where(BiometricCredential.device_id == "dev-4")
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    assert await bio.verify_and_rotate(db_session, device_id="dev-4", secret=secret2) is None


async def test_revoke_device_scopes_to_one_device(db_session):
    child = await _child(db_session)
    s1 = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dA", label="a")
    s2 = await bio.issue(db_session, subject_kind="child", user_id=child.id, parent_email=None, device_id="dB", label="a")
    await db_session.flush()
    await bio.revoke_device(db_session, subject_key=bio.subject_key_for_child(child.id), device_id="dA")
    assert await bio.verify_and_rotate(db_session, device_id="dA", secret=s1) is None
    assert await bio.verify_and_rotate(db_session, device_id="dB", secret=s2) is not None


async def test_parent_subject_lowercased(db_session):
    secret = await bio.issue(db_session, subject_kind="parent", user_id=None, parent_email="P@Example.com", device_id="dev-5", label="Parent")
    await db_session.flush()
    row = await bio.verify_and_rotate(db_session, device_id="dev-5", secret=secret)
    assert row is not None and row.parent_email == "p@example.com" and row.subject_kind == "parent"
