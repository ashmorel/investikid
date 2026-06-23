import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module, VideoCandidate

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _candidate(db_session, *, embeddable=True):
    m = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L1", order_index=0)
    db_session.add(lvl)
    await db_session.flush()
    c = VideoCandidate(
        youtube_id="vid1",
        title="Saving 101",
        source="recovered",
        market_code="GB",
        suggested_module_id=m.id,
        suggested_level_id=lvl.id,
        embeddable=embeddable,
    )
    db_session.add(c)
    await db_session.flush()
    return c, m, lvl


async def test_list_pending(admin_client, db_session):
    await _candidate(db_session)
    r = await admin_client.get("/admin/video-candidates?status=pending")
    assert r.status_code == 200
    assert r.json()[0]["youtube_id"] == "vid1"


async def test_approve_creates_video_lesson(admin_client, db_session):
    c, m, lvl = await _candidate(db_session)
    r = await admin_client.post(
        f"/admin/video-candidates/{c.id}/approve",
        json={"module_id": str(m.id), "level_id": str(lvl.id)},
    )
    assert r.status_code == 200
    lesson = (await db_session.scalars(select(Lesson).where(Lesson.type == "video"))).one()
    assert lesson.content_json["youtube_id"] == "vid1"
    assert lesson.level_id == lvl.id
    refreshed = await db_session.get(VideoCandidate, c.id)
    await db_session.refresh(refreshed)
    assert refreshed.status == "approved"
    assert refreshed.created_lesson_id == lesson.id


async def test_approve_blocked_when_not_embeddable(admin_client, db_session):
    c, m, lvl = await _candidate(db_session, embeddable=False)
    r = await admin_client.post(
        f"/admin/video-candidates/{c.id}/approve",
        json={"module_id": str(m.id), "level_id": str(lvl.id)},
    )
    assert r.status_code == 409


async def test_skip(admin_client, db_session):
    c, m, lvl = await _candidate(db_session)
    r = await admin_client.post(f"/admin/video-candidates/{c.id}/skip")
    assert r.status_code == 200
    refreshed = await db_session.get(VideoCandidate, c.id)
    await db_session.refresh(refreshed)
    assert refreshed.status == "skipped"
