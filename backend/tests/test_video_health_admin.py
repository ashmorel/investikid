import httpx
import pytest

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_video(db_session, youtube_id):
    m = Module(topic="savings", title="VH Admin Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "Intro"})
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_check_then_list(admin_client, db_session, monkeypatch):
    lesson = await _seed_video(db_session, "deadID")

    # Force the checker's client to return 404 for everything.
    import app.services.video_health_service as svc
    real = svc.check_all_videos

    async def patched(session, *, client=None):
        def handler(req):
            return httpx.Response(404)
        c = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await real(session, client=c)
        finally:
            await c.aclose()
    monkeypatch.setattr(svc, "check_all_videos", patched)

    r = await admin_client.post("/admin/video-health/check")
    assert r.status_code == 200
    assert r.json()["summary"]["dead"] >= 1

    r2 = await admin_client.get("/admin/video-health")
    assert r2.status_code == 200
    item = next(i for i in r2.json() if i["lesson_id"] == str(lesson.id))
    assert item["status"] == "dead"
    assert item["youtube_id"] == "deadID"


async def test_video_health_requires_admin(client):
    r = await client.get("/admin/video-health")
    assert r.status_code in (401, 403)
