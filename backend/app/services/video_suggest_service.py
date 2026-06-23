import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Module, VideoCandidate
from app.services.video_health_service import video_embeddability

_SEARCH = "https://www.googleapis.com/youtube/v3/search"


async def suggest_videos(
    session: AsyncSession, *, module_id, level_id, client: httpx.AsyncClient | None = None
) -> dict:
    module = await session.get(Module, module_id)
    if module is None:
        return {"created": 0}
    owns = client is None
    client = client or httpx.AsyncClient()
    created = 0
    try:
        query = f"{module.title} {module.topic} for kids money lesson"
        resp = await client.get(_SEARCH, params={
            "part": "snippet", "type": "video", "videoEmbeddable": "true",
            "safeSearch": "strict", "maxResults": 8, "q": query, "key": settings.youtube_api_key,
        }, timeout=10.0)
        if resp.status_code != 200:
            return {"created": 0}
        for item in resp.json().get("items", []):
            yt = item.get("id", {}).get("videoId")
            if not yt:
                continue
            if (await session.scalars(select(VideoCandidate).where(
                VideoCandidate.youtube_id == yt,
                VideoCandidate.market_code == module.market_code,
            ))).first():
                continue
            embeddable, detail = await video_embeddability(yt, client=client)
            if not embeddable:
                continue
            snip = item.get("snippet", {})
            session.add(VideoCandidate(
                youtube_id=yt,
                title=(snip.get("title") or yt)[:300],
                thumbnail_url=snip.get("thumbnails", {}).get("medium", {}).get("url"),
                source="suggested",
                market_code=module.market_code,
                origin_context=f"{module.topic} / {module.title}",
                suggested_module_id=module.id,
                suggested_level_id=level_id,
                embeddable=True,
                health_detail=detail,
            ))
            created += 1
        await session.commit()
        return {"created": created}
    finally:
        if owns:
            await client.aclose()
