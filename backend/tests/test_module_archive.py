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


async def test_publish_archives_retired_modules(db_session):
    # Publishing a new curriculum retires the previously-live modules — and now
    # also archives them so they leave the admin main list.
    from app.models.content import Lesson
    from app.models.market_curriculum import MarketCurriculumProposal
    from app.services.market_curriculum.curriculum_publish_service import (
        publish_market_curriculum,
    )

    old = await _module(db_session, published=True, market="US")
    old.order_index = 99
    staged = await _module(db_session, published=False, market="US")
    db_session.add(Lesson(module_id=staged.id, type="card", xp_reward=0,
                          order_index=0, content_json={"title": "x", "body": "y"}))
    db_session.add(MarketCurriculumProposal(
        market_code="US", status="accepted",
        proposal_json={"market_code": "US", "modules": [{"module_id": str(staged.id),
            "topic": "t", "title": "New", "icon": "📚", "min_age": 10, "max_age": 14,
            "order_index": 0, "levels": []}]},
        coverage_json={"ok": True}))
    await db_session.flush()

    await publish_market_curriculum(db_session, "US")
    await db_session.refresh(old)
    await db_session.refresh(staged)
    assert old.archived_at is not None      # retired → archived
    assert staged.published is True and staged.archived_at is None
