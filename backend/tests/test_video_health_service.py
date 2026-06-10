import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth
from app.services import video_health_service
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


def _routed_handler(*, embeddable):
    """oembed always 200; Data API returns embeddable per `embeddable`.

    `embeddable` may be True/False to drive items[0].status.embeddable, or
    "error" (HTTP 500) / "empty" (empty items list) / "notjson" (200 with a
    non-JSON body) / "nullstatus" (items[0].status is null) to exercise
    fail-open.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "www.googleapis.com":
            if embeddable == "error":
                return httpx.Response(500)
            if embeddable == "empty":
                return httpx.Response(200, json={"items": []})
            if embeddable == "notjson":
                return httpx.Response(200, text="<html>not json</html>")
            if embeddable == "nullstatus":
                return httpx.Response(200, json={"items": [{"status": None}]})
            return httpx.Response(200, json={"items": [{"status": {"embeddable": embeddable}}]})
        # oembed
        return httpx.Response(200)
    return handler


async def test_embedding_disabled_is_blocked(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "k")
    _, lesson = await _video_lesson(db_session, "blockedID", "blocked")

    client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable=False)))
    summary = await check_all_videos(db_session, client=client)
    await client.aclose()

    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "blocked"
    assert summary["blocked"] >= 1
    assert any(d["youtube_id"] == "blockedID" for d in summary["blocked_items"])


async def test_embeddable_true_is_ok(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "k")
    _, lesson = await _video_lesson(db_session, "okID", "ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable=True)))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "ok"


async def test_data_api_error_fails_open_to_ok(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "k")
    _, err_lesson = await _video_lesson(db_session, "errID", "err")
    _, empty_lesson = await _video_lesson(db_session, "emptyID", "empty")

    err_client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable="error")))
    await check_all_videos(db_session, client=err_client)
    await err_client.aclose()
    err_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == err_lesson.id))
    assert err_row.status == "ok"

    empty_client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable="empty")))
    await check_all_videos(db_session, client=empty_client)
    await empty_client.aclose()
    empty_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == empty_lesson.id))
    assert empty_row.status == "ok"


async def test_data_api_non_json_body_fails_open_to_ok(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "k")
    _, lesson = await _video_lesson(db_session, "notjsonID", "notjson")

    client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable="notjson")))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "ok"


async def test_data_api_null_status_fails_open_to_ok(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "k")
    _, lesson = await _video_lesson(db_session, "nullstatusID", "nullstatus")

    client = httpx.AsyncClient(transport=httpx.MockTransport(_routed_handler(embeddable="nullstatus")))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "ok"


async def test_no_key_skips_data_api(db_session, monkeypatch):
    monkeypatch.setattr(video_health_service.settings, "youtube_api_key", "")
    _, lesson = await _video_lesson(db_session, "okID", "ok")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.googleapis.com":
            raise AssertionError("Data API must not be called when key is empty")
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == lesson.id))
    assert row.status == "ok"
