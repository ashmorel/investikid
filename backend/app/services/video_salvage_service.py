import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module, VideoCandidate
from app.services.video_health_service import video_embeddability


async def _topic_match(session: AsyncSession, *, topic: str, market_code: str) -> tuple[object, object]:
    """Current published, non-archived module with the same topic + market → (module_id, level_id)
    of its first level. Returns (None, None) on no match."""
    module = (await session.scalars(
        select(Module).where(
            Module.topic == topic, Module.market_code == market_code,
            Module.published.is_(True), Module.archived_at.is_(None),
        ).order_by(Module.order_index)
    )).first()
    if module is None:
        return None, None
    level = (await session.scalars(
        select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
    )).first()
    return module.id, (level.id if level else None)


async def extract_recovered_candidates(
    session: AsyncSession, *, client: httpx.AsyncClient | None = None
) -> dict:
    """Scan ARCHIVED modules for video lessons; create a recovered VideoCandidate for each
    (idempotent on youtube_id+market), topic-matched to the current curriculum, health-backfilled."""
    owns = client is None
    client = client or httpx.AsyncClient()
    found = created = 0
    try:
        rows = (await session.execute(
            select(Lesson, Module)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.archived_at.is_not(None), Lesson.type == "video")
        )).all()
        for lesson, module in rows:
            cj = lesson.content_json or {}
            youtube_id = cj.get("youtube_id")
            if not youtube_id:
                continue
            found += 1
            exists = (await session.scalars(select(VideoCandidate).where(
                VideoCandidate.youtube_id == youtube_id,
                VideoCandidate.market_code == module.market_code,
            ))).first()
            if exists:
                continue
            mod_id, lvl_id = await _topic_match(session, topic=module.topic, market_code=module.market_code)
            embeddable, detail = await video_embeddability(youtube_id, client=client)
            session.add(VideoCandidate(
                youtube_id=youtube_id,
                title=cj.get("caption") or f"Video ({youtube_id})",
                source="recovered", market_code=module.market_code,
                origin_context=f"{module.topic} / {module.title}",
                suggested_module_id=mod_id, suggested_level_id=lvl_id,
                embeddable=embeddable, health_detail=detail,
            ))
            created += 1
        await session.commit()
        return {"found": found, "created": created}
    finally:
        if owns:
            await client.aclose()
