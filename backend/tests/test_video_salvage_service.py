# backend/tests/test_video_salvage_service.py
import datetime as dt

import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module, VideoCandidate
from app.services.video_salvage_service import extract_recovered_candidates

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _ok_client():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]}
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))

async def _seed(db_session):
    # archived module (old) with a video lesson, + a current published module same topic
    old = Module(topic="saving", title="Old Saving", market_code="GB", order_index=0,
                 published=True, archived_at=dt.datetime.now(dt.UTC))
    new = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add_all([old, new])
    await db_session.flush()
    new_level = Level(module_id=new.id, title="Level 1", order_index=0)
    old_level = Level(module_id=old.id, title="Old L1", order_index=0)
    db_session.add_all([new_level, old_level])
    await db_session.flush()
    db_session.add(Lesson(module_id=old.id, level_id=old_level.id, type="video",
                          content_json={"video_source": "youtube", "youtube_id": "vid1", "caption": "Saving 101"},
                          xp_reward=10, order_index=0))
    await db_session.flush()
    return new, new_level

async def test_extracts_archived_video_and_topic_matches(db_session):
    new, new_level = await _seed(db_session)
    async with _ok_client() as c:
        res = await extract_recovered_candidates(db_session, client=c)
    assert res == {"found": 1, "created": 1}
    cand = (await db_session.scalars(select(VideoCandidate))).one()
    assert cand.youtube_id == "vid1"
    assert cand.source == "recovered"
    assert cand.market_code == "GB"
    assert cand.suggested_module_id == new.id          # topic-matched to current module
    assert cand.suggested_level_id == new_level.id
    assert cand.embeddable is True

async def test_extraction_is_idempotent(db_session):
    await _seed(db_session)
    async with _ok_client() as c:
        await extract_recovered_candidates(db_session, client=c)
        res2 = await extract_recovered_candidates(db_session, client=c)
    assert res2["created"] == 0
    assert len((await db_session.scalars(select(VideoCandidate))).all()) == 1

async def test_extract_endpoint_requires_cron_secret(client):
    r = await client.post("/internal/video-candidates/extract")  # no header
    assert r.status_code in (401, 503)
