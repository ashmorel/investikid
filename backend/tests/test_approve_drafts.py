import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.lesson_approval_service import approve_level_drafts

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(db_session, *, n_lessons, safe_drafts, unsafe_drafts, order_index=950):
    module = Module(topic="savings", title="Appr Mod", country_codes=[], is_premium=False,
                    order_index=order_index, icon="💵", market_code="US")
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Appr L1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    for i in range(n_lessons):
        db_session.add(Lesson(module_id=module.id, level_id=level.id, type="card",
                              content_json={"title": f"old{i}", "body": "x"}, xp_reward=10, order_index=i))
    for i in range(safe_drafts):
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": f"new{i}", "body": "y"}, concept="c",
                                   model_used="test", moderation_safe=True, moderation_category=None))
    for i in range(unsafe_drafts):
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": f"bad{i}", "body": "z"}, concept="c",
                                   model_used="test", moderation_safe=False, moderation_category="x"))
    await db_session.flush()
    return level


async def _lesson_count(db_session, level_id):
    return await db_session.scalar(select(func.count(Lesson.id)).where(Lesson.level_id == level_id))


async def test_replace_deletes_old_and_creates_new(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=2, unsafe_drafts=1, order_index=951)
    res = await approve_level_drafts(db_session, level, replace=True)
    assert res == {"approved": 2, "replaced": 2, "skipped_unsafe": 1}
    assert await _lesson_count(db_session, level.id) == 2


async def test_no_replace_appends(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=2, unsafe_drafts=0, order_index=952)
    res = await approve_level_drafts(db_session, level, replace=False)
    assert res["approved"] == 2 and res["replaced"] == 0
    assert await _lesson_count(db_session, level.id) == 4


async def test_replace_with_no_safe_drafts_keeps_existing(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=0, unsafe_drafts=1, order_index=953)
    res = await approve_level_drafts(db_session, level, replace=True)
    assert res == {"approved": 0, "replaced": 0, "skipped_unsafe": 1}
    assert await _lesson_count(db_session, level.id) == 2  # NOT emptied


async def test_endpoint_smoke(admin_client, db_session):
    level = await _seed(db_session, n_lessons=1, safe_drafts=1, unsafe_drafts=0, order_index=954)
    await db_session.commit()
    resp = await admin_client.post(f"/admin/levels/{level.id}/approve-drafts", json={"replace": True})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"approved", "replaced", "skipped_unsafe"}
    bad = await admin_client.post("/admin/levels/00000000-0000-0000-0000-000000000000/approve-drafts", json={"replace": False})
    assert bad.status_code == 404
