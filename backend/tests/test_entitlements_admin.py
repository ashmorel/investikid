import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.user import User
from app.services.entitlements import is_admin, set_admin

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk(session, admin=False):
    u = User(
        email=f"adm-{uuid.uuid4().hex[:8]}@example.com",
        username=f"adm{uuid.uuid4().hex[:8]}",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_admin=admin,
    )
    session.add(u)
    await session.flush()
    return u


async def test_is_admin_reads_column(db_session):
    regular = await _mk(db_session, admin=False)
    admin = await _mk(db_session, admin=True)
    assert is_admin(regular) is False
    assert is_admin(admin) is True


async def test_set_admin_grants_and_audits(db_session):
    u = await _mk(db_session, admin=False)
    changed = await set_admin(db_session, u, value=True, actor="test")
    assert changed is True
    assert u.is_admin is True
    rows = (await db_session.scalars(
        select(AuditLog).where(AuditLog.user_id == u.id)
    )).all()
    grant = [r for r in rows if r.event_type == "admin_grant"]
    assert len(grant) == 1
    assert grant[0].metadata_json == {"actor": "test", "old": False, "new": True}


async def test_set_admin_idempotent_noop(db_session):
    u = await _mk(db_session, admin=True)
    changed = await set_admin(db_session, u, value=True, actor="cli")
    assert changed is False
    rows = (await db_session.scalars(
        select(AuditLog).where(AuditLog.user_id == u.id)
    )).all()
    assert rows == []


async def test_set_admin_revoke_audits(db_session):
    u = await _mk(db_session, admin=True)
    changed = await set_admin(db_session, u, value=False, actor="cli")
    assert changed is True
    assert u.is_admin is False
    rows = (await db_session.scalars(
        select(AuditLog).where(
            AuditLog.user_id == u.id, AuditLog.event_type == "admin_revoke"
        )
    )).all()
    assert len(rows) == 1
    assert rows[0].metadata_json == {"actor": "cli", "old": True, "new": False}
