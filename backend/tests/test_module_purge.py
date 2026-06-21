from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.content import Module
from app.services.module_purge_service import purge_archived_modules

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _m(db_session, archived_days_ago):
    m = Module(topic="t", title="M", country_codes=[], market_code="GB",
               is_premium=False, order_index=0, icon="📚", published=False)
    if archived_days_ago is not None:
        m.archived_at = datetime.now(UTC) - timedelta(days=archived_days_ago)
    db_session.add(m)
    await db_session.flush()
    return m


async def test_purges_only_past_window(db_session):
    old = await _m(db_session, 31)
    recent = await _m(db_session, 5)
    active = await _m(db_session, None)
    n = await purge_archived_modules(db_session, now=datetime.now(UTC))
    assert n == 1
    remaining = set((await db_session.execute(select(Module.id))).scalars().all())
    assert old.id not in remaining
    assert recent.id in remaining and active.id in remaining


async def test_purge_endpoint_requires_secret(admin_client, monkeypatch):
    from app.core.config import settings as s
    monkeypatch.setattr(s, "cron_secret", "sekret")
    bad = await admin_client.post("/internal/purge-archived-modules")
    assert bad.status_code == 401
    ok = await admin_client.post("/internal/purge-archived-modules",
                                 headers={"X-Cron-Secret": "sekret"})
    assert ok.status_code == 200 and "purged" in ok.json()
