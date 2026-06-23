import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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


async def video_embeddability(
    youtube_id: str, *, client: httpx.AsyncClient | None = None
) -> tuple[bool, str | None]:
    """Single-video health probe. (True, None) if embeddable AND not age-restricted,
    else (False, reason). reason: not_found | embedding_disabled | age_restricted | api_error."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=status,contentDetails&id={youtube_id}&key={settings.youtube_api_key}",
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return False, "api_error"
        items = resp.json().get("items", [])
        if not items:
            return False, "not_found"
        item = items[0]
        if item.get("contentDetails", {}).get("contentRating", {}).get("ytRating") == "ytAgeRestricted":
            return False, "age_restricted"
        if not item.get("status", {}).get("embeddable", False):
            return False, "embedding_disabled"
        return True, None
    except (httpx.HTTPError, ValueError):
        return False, "api_error"
    finally:
        if owns_client:
            await client.aclose()


async def _embeddable(client: httpx.AsyncClient, youtube_id: str) -> bool:
    """Whether the YouTube owner allows embedding (via the Data API).

    Fail-open: returns True on any HTTP error, non-200, or missing item, so a
    transient API issue never raises a false "blocked" alarm. Returns False
    only when the API clearly reports items[0].status.embeddable is False.
    """
    try:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=status&id={youtube_id}&key={settings.youtube_api_key}",
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return True
        items = resp.json().get("items") or []
        if not items:
            return True
        status = items[0].get("status") or {}
        return status.get("embeddable", True) is not False
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return True


async def _probe(client: httpx.AsyncClient, youtube_id: str, sem: asyncio.Semaphore) -> tuple[str, int | None]:
    if not youtube_id:
        return "dead", None
    async with sem:
        try:
            resp = await client.get(oembed_url(youtube_id), timeout=_TIMEOUT)
            status = classify(resp.status_code)
            if status == "ok" and settings.youtube_api_key:
                if not await _embeddable(client, youtube_id):
                    return "blocked", resp.status_code
            return status, resp.status_code
        except httpx.HTTPError:
            return "unknown", None  # transient — never alerted


async def _probe_hosted(
    client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore
) -> tuple[str, int | None]:
    if not url:
        return "dead", None
    async with sem:
        try:
            resp = await client.get(url, timeout=_TIMEOUT, headers={"Range": "bytes=0-0"})
            sc = resp.status_code
            if sc in (200, 206):
                return "ok", sc
            if sc in (401, 403, 404):
                return "dead", sc
            return "unknown", sc
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

    def _identifier(lesson: Lesson) -> str:
        cj = lesson.content_json or {}
        if cj.get("video_source") == "hosted":
            return cj.get("video_url", "")
        return cj.get("youtube_id", "")

    def _probe_for(lesson: Lesson) -> Any:
        cj = lesson.content_json or {}
        if cj.get("video_source") == "hosted":
            return _probe_hosted(client, cj.get("video_url", ""), sem)
        return _probe(client, cj.get("youtube_id", ""), sem)

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient()
    sem = asyncio.Semaphore(_CONCURRENCY)
    try:
        results = await asyncio.gather(*[_probe_for(lesson) for lesson, _ in rows])
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
    summary: dict[str, Any] = {
        "ok": 0, "dead": 0, "unknown": 0, "blocked": 0,
        "dead_items": [], "blocked_items": [],
    }
    for (lesson, module_title), (status, http_status) in zip(rows, results):
        yt = _identifier(lesson)
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
        if status in ("dead", "blocked"):
            summary[f"{status}_items"].append({
                "lesson_id": str(lesson.id), "youtube_id": yt,
                "module_title": module_title,
                "lesson_title": (lesson.content_json or {}).get("caption") or "Video lesson",
            })
    await session.flush()
    return summary
