import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.video_asset import VideoAsset
from app.models.video_health import VideoHealth
from app.routers import (
    admin_content,
    admin_drafts,
    admin_gamification,
    admin_generation,
    admin_markets,
    admin_settings,
    admin_translations,
)
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    VideoHealthCheckResult,
    VideoHealthItem,
    VideoPresignRequest,
    VideoPresignResponse,
)
from app.services import storage, video_health_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])
router.include_router(admin_content.router)
router.include_router(admin_generation.router)
router.include_router(admin_drafts.router)
router.include_router(admin_markets.router)
router.include_router(admin_translations.router)
router.include_router(admin_gamification.router)
router.include_router(admin_settings.router)


# ── Video health ────────────────────────────────────────────────────
async def _video_health_items(session: AsyncSession) -> list[VideoHealthItem]:
    rows = (await session.execute(
        select(Lesson, Module.id, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.type == "video")
        .order_by(Module.order_index, Lesson.order_index)
    )).all()
    health = {
        h.lesson_id: h
        for h in (await session.scalars(select(VideoHealth))).all()
    }
    out: list[VideoHealthItem] = []
    for lesson, module_id, module_title in rows:
        h = health.get(lesson.id)
        out.append(VideoHealthItem(
            lesson_id=lesson.id, module_id=module_id, module_title=module_title,
            lesson_title=(lesson.content_json or {}).get("caption") or "Video lesson",
            youtube_id=(lesson.content_json or {}).get("youtube_id", ""),
            status=h.status if h else None,
            http_status=h.http_status if h else None,
            checked_at=h.checked_at if h else None,
        ))
    return out


@router.get("/video-health", response_model=list[VideoHealthItem])
async def admin_video_health(session: AsyncSession = Depends(get_session)):
    return await _video_health_items(session)


@router.post("/video-health/check", response_model=VideoHealthCheckResult)
async def admin_video_health_check(session: AsyncSession = Depends(get_session)):
    summary = await video_health_service.check_all_videos(session)
    await session.commit()
    items = await _video_health_items(session)
    return VideoHealthCheckResult(summary=summary, items=items)


# ── Video assets (R2 presigned upload) ──────────────────────────────
@router.post("/video-assets/presign", response_model=VideoPresignResponse)
async def admin_presign_video(
    payload: VideoPresignRequest,
    session: AsyncSession = Depends(get_session),
):
    if not storage.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if payload.size_bytes > settings.r2_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file too large")
    key = f"videos/{uuid.uuid4()}.mp4"
    asset = VideoAsset(
        storage_key=key,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        original_filename=payload.filename[:255],
        created_at=datetime.now(UTC),
    )
    session.add(asset)
    await session.commit()
    return VideoPresignResponse(
        asset_id=asset.id,
        key=key,
        upload_url=storage.create_presigned_put(
            key, payload.content_type, content_length=payload.size_bytes
        ),
        public_url=storage.public_url(key),
    )
