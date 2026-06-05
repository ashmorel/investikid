import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Module
from app.models.video_health import VideoHealth

_TIMEOUT = 8.0
_CONCURRENCY = 5


def oembed_url(youtube_id: str) -> str:
    return (
        "https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={youtube_id}&format=json"
    )


def classify(http_status: int | None) -> str:
    if http_status == 200:
        return "ok"
    if http_status in (401, 404):
        return "dead"
    return "unknown"


async def _probe(client: httpx.AsyncClient, youtube_id: str, sem: asyncio.Semaphore) -> tuple[str, int | None]:
    if not youtube_id:
        return "dead", None
    async with sem:
        try:
            resp = await client.get(oembed_url(youtube_id), timeout=_TIMEOUT)
            return classify(resp.status_code), resp.status_code
        except httpx.HTTPError:
            return "unknown", None  # transient — never alerted


async def check_all_videos(
    session: AsyncSession, *, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    rows = (await session.execute(
        select(Lesson, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.type == "video")
    )).all()

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient()
    sem = asyncio.Semaphore(_CONCURRENCY)
    try:
        results = await asyncio.gather(*[
            _probe(client, (lesson.content_json or {}).get("youtube_id", ""), sem)
            for lesson, _ in rows
        ])
    finally:
        if owns_client:
            await client.aclose()

    # Clean up stale rows (lessons that are gone / no longer video).
    valid_ids = [lesson.id for lesson, _ in rows]
    if valid_ids:
        await session.execute(delete(VideoHealth).where(VideoHealth.lesson_id.notin_(valid_ids)))
    else:
        await session.execute(delete(VideoHealth))

    now = datetime.now(UTC)
    summary: dict[str, Any] = {"ok": 0, "dead": 0, "unknown": 0, "dead_items": []}
    for (lesson, module_title), (status, http_status) in zip(rows, results):
        yt = (lesson.content_json or {}).get("youtube_id", "")
        existing = await session.scalar(
            select(VideoHealth).where(VideoHealth.lesson_id == lesson.id)
        )
        if existing is None:
            session.add(VideoHealth(
                lesson_id=lesson.id, youtube_id=yt, status=status,
                http_status=http_status, checked_at=now,
            ))
        else:
            existing.youtube_id = yt
            existing.status = status
            existing.http_status = http_status
            existing.checked_at = now
        summary[status] += 1
        if status == "dead":
            summary["dead_items"].append({
                "lesson_id": str(lesson.id), "youtube_id": yt,
                "module_title": module_title,
                "lesson_title": (lesson.content_json or {}).get("caption") or "Video lesson",
            })
    await session.flush()
    return summary
