import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth
from app.services.video_health_service import check_all_videos, classify

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_classify():
    assert classify(200) == "ok"
    assert classify(404) == "dead"
    assert classify(401) == "dead"
    assert classify(500) == "unknown"
    assert classify(429) == "unknown"
    assert classify(None) == "unknown"


async def _video_lesson(db_session, youtube_id, title="V"):
    m = Module(topic="savings", title=f"Mod {title}", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "c"})
    db_session.add(lesson)
    await db_session.flush()
    return m, lesson


async def test_check_all_classifies_and_upserts(db_session):
    _, ok_lesson = await _video_lesson(db_session, "liveID", "ok")
    _, dead_lesson = await _video_lesson(db_session, "deadID", "dead")

    def handler(request: httpx.Request) -> httpx.Response:
        # oembed returns 200 for live, 404 for dead.
        return httpx.Response(200 if "liveID" in str(request.url) else 404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await check_all_videos(db_session, client=client)
    await client.aclose()
    await db_session.flush()

    assert summary["ok"] >= 1 and summary["dead"] >= 1
    assert any(d["youtube_id"] == "deadID" for d in summary["dead_items"])
    ok_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == ok_lesson.id))
    dead_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == dead_lesson.id))
    assert ok_row.status == "ok"
    assert dead_row.status == "dead"


async def test_blank_youtube_id_is_dead(db_session):
    _, lesson = await _video_lesson(db_session, "", "blank")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)  # should not even be called for blank id

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await check_all_videos(db_session, client=client)
    await client.aclose()
    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "dead"
