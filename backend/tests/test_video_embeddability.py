import httpx
import pytest

from app.services.video_health_service import video_embeddability

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _client(payload):
    def handler(request):
        return httpx.Response(200, json=payload)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))

async def test_embeddable_ok():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (True, None)

async def test_embedding_disabled():
    payload = {"items": [{"status": {"embeddable": False}, "contentDetails": {"contentRating": {}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (False, "embedding_disabled")

async def test_age_restricted():
    payload = {"items": [{"status": {"embeddable": True}, "contentDetails": {"contentRating": {"ytRating": "ytAgeRestricted"}}}]}
    async with _client(payload) as c:
        assert await video_embeddability("vid", client=c) == (False, "age_restricted")

async def test_not_found():
    async with _client({"items": []}) as c:
        assert await video_embeddability("vid", client=c) == (False, "not_found")
