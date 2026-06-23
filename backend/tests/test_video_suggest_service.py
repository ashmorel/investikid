import httpx
import pytest
from sqlalchemy import select

from app.models.content import Level, Module, VideoCandidate

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _client():
    def handler(request):
        if "search" in str(request.url):
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "ytA"}, "snippet": {"title": "Saving for kids",
                 "thumbnails": {"medium": {"url": "http://t/A.jpg"}}}},
            ]})
        # videos.list health probe
        return httpx.Response(200, json={"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_suggest_inserts_embeddable_candidates(db_session):
    from app.services.video_suggest_service import suggest_videos

    m = Module(topic="saving", title="Saving Money", market_code="GB", order_index=0, published=True)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L1", order_index=0)
    db_session.add(lvl)
    await db_session.flush()
    async with _client() as c:
        res = await suggest_videos(db_session, module_id=m.id, level_id=lvl.id, client=c)
    assert res["created"] == 1
    cand = (await db_session.scalars(select(VideoCandidate))).one()
    assert cand.source == "suggested"
    assert cand.youtube_id == "ytA"
    assert cand.suggested_module_id == m.id
    assert cand.suggested_level_id == lvl.id
    assert cand.embeddable is True
