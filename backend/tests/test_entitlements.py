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
