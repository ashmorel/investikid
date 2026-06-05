import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_video_health_row_roundtrips(db_session):
    m = Module(topic="savings", title="VH Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": "abc123"})
    db_session.add(lesson)
    await db_session.flush()

    from datetime import UTC, datetime
    vh = VideoHealth(lesson_id=lesson.id, youtube_id="abc123", status="ok",
                     http_status=200, checked_at=datetime.now(UTC))
    db_session.add(vh)
    await db_session.flush()

    got = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert got is not None and got.status == "ok" and got.youtube_id == "abc123"
