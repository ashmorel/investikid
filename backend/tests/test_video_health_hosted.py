import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth
from app.services.video_health_service import check_all_videos

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _hosted_lesson(db_session, url):
    m = Module(topic="savings", title="Hosted Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=15,
                    content_json={"video_source": "hosted", "video_url": url, "caption": "c"})
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_hosted_url_checked_via_http(db_session):
    live = await _hosted_lesson(db_session, "https://cdn/live.mp4")
    dead = await _hosted_lesson(db_session, "https://cdn/dead.mp4")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200 if "live" in str(request.url) else 404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    live_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == live.id))
    dead_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == dead.id))
    assert live_row.status == "ok"
    assert dead_row.status == "dead"
