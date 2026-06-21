from datetime import UTC, datetime

import pytest

from app.models.content import Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session, *, published, market="GB"):
    m = Module(topic="t", title="M", country_codes=[], market_code=market,
               is_premium=False, order_index=0, icon="📚", published=published)
    db_session.add(m)
    await db_session.flush()
    return m


async def test_module_archived_at_defaults_null(db_session):
    m = await _module(db_session, published=True)
    assert m.archived_at is None


async def test_delete_archives_non_live_module(admin_client, db_session):
    m = await _module(db_session, published=False)
    await db_session.commit()
    r = await admin_client.delete(f"/admin/modules/{m.id}")
    assert r.status_code == 200, r.text
    await db_session.refresh(m)
    assert m.archived_at is not None


async def test_delete_live_module_blocked_409(admin_client, db_session):
    m = await _module(db_session, published=True)
    await db_session.commit()
    r = await admin_client.delete(f"/admin/modules/{m.id}")
    assert r.status_code == 409, r.text
    await db_session.refresh(m)
    assert m.archived_at is None


async def test_restore_clears_archived_at(admin_client, db_session):
    m = await _module(db_session, published=False)
    m.archived_at = datetime.now(UTC)
    await db_session.commit()
    r = await admin_client.post(f"/admin/modules/{m.id}/restore")
    assert r.status_code == 200, r.text
    await db_session.refresh(m)
    assert m.archived_at is None
