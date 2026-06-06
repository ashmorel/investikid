import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_session
from app.models.apply_mission import ApplyMission
from app.models.content import Lesson, Level, Module
from app.models.gamification import Badge, Challenge, UserBadge
from app.models.user import User
from app.models.video_asset import VideoAsset
from app.models.video_health import VideoHealth
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    AdminLevelCreate,
    AdminLevelOut,
    AdminLevelUpdate,
    AdminSettingsOut,
    AdminSettingsUpdate,
    ApplyMissionOut,
    BadgeCreate,
    BadgeOut,
    BadgeUpdate,
    ChallengeCreate,
    ChallengeOut,
    ChallengeUpdate,
    LessonCreate,
    LessonOut,
    LessonUpdate,
    ModuleCreate,
    ModuleEngagementOut,
    ModuleOut,
    ModuleUpdate,
    ReorderRequest,
    VideoHealthCheckResult,
    VideoHealthItem,
    VideoPresignRequest,
    VideoPresignResponse,
)
from app.services import storage, video_health_service
from app.services.app_settings import (
    get_alert_emails,
    get_starting_cash,
    set_alert_emails,
    set_starting_cash,
)
from app.services.engagement_service import get_module_engagement

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


async def _upsert_apply_mission(session: AsyncSession, lesson: Lesson, payload: LessonCreate | LessonUpdate) -> None:
    """Create or update the (single) ApplyMission for a lesson from the payload."""
    am = payload.apply_mission
    if am is None:
        return
    existing = await session.scalar(
        select(ApplyMission).where(ApplyMission.lesson_id == lesson.id)
    )
    if existing is None:
        session.add(ApplyMission(
            lesson_id=lesson.id, mission_type=am.mission_type, params_json=am.params_json,
            title=am.title, prompt=am.prompt, xp_reward=am.xp_reward,
            cash_reward=am.cash_reward, badge_id=am.badge_id,
        ))
    else:
        existing.mission_type = am.mission_type
        existing.params_json = am.params_json
        existing.title = am.title
        existing.prompt = am.prompt
        existing.xp_reward = am.xp_reward
        existing.cash_reward = am.cash_reward
        existing.badge_id = am.badge_id


async def _lesson_out(session: AsyncSession, lesson: Lesson) -> LessonOut:
    """Serialize a lesson to LessonOut, including its ApplyMission if present."""
    mission = await session.scalar(
        select(ApplyMission).where(ApplyMission.lesson_id == lesson.id)
    )
    return LessonOut(
        id=lesson.id, module_id=lesson.module_id, type=lesson.type,
        content_json=lesson.content_json, xp_reward=lesson.xp_reward,
        order_index=lesson.order_index,
        apply_mission=ApplyMissionOut.model_validate(mission) if mission else None,
    )


# ── Stats ───────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    modules = await session.scalar(select(func.count()).select_from(Module))
    lessons = await session.scalar(select(func.count()).select_from(Lesson))
    badges = await session.scalar(select(func.count()).select_from(Badge))
    challenges = await session.scalar(select(func.count()).select_from(Challenge))
    return {
        "modules": modules or 0,
        "lessons": lessons or 0,
        "badges": badges or 0,
        "challenges": challenges or 0,
    }


# ── Modules ─────────────────────────────────────────────────────────
@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Module).options(selectinload(Module.lessons)).order_by(Module.order_index)
    )
    modules = result.scalars().all()
    return [
        ModuleOut(
            id=m.id, topic=m.topic, title=m.title, icon=m.icon,
            is_premium=m.is_premium, country_codes=m.country_codes,
            order_index=m.order_index, lesson_count=len(m.lessons),
            prerequisite_ids=m.prerequisite_ids, min_age=m.min_age, max_age=m.max_age,
        )
        for m in modules
    ]


@router.post("/modules", response_model=ModuleOut)
async def create_module(payload: ModuleCreate, session: AsyncSession = Depends(get_session)):
    # Validate all prerequisite IDs exist
    for prereq_id in payload.prerequisite_ids:
        prereq = await session.get(Module, prereq_id)
        if prereq is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prerequisite module {prereq_id} not found",
            )
    module = Module(
        topic=payload.topic, title=payload.title, icon=payload.icon,
        is_premium=payload.is_premium, country_codes=payload.country_codes,
        order_index=payload.order_index, prerequisite_ids=payload.prerequisite_ids,
        min_age=payload.min_age, max_age=payload.max_age,
        completion_cash_reward=payload.completion_cash_reward,
    )
    session.add(module)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=0,
        prerequisite_ids=module.prerequisite_ids, min_age=module.min_age, max_age=module.max_age,
        completion_cash_reward=module.completion_cash_reward,
    )


@router.put("/modules/{module_id}", response_model=ModuleOut)
async def update_module(
    module_id: uuid.UUID, payload: ModuleUpdate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id, options=[selectinload(Module.lessons)])
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    update_data = payload.model_dump(exclude_unset=True)
    # Prerequisite validation
    if "prerequisite_ids" in update_data:
        prereq_ids = update_data["prerequisite_ids"]
        if module_id in prereq_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prerequisite self-reference not allowed",
            )
        for prereq_id in prereq_ids:
            prereq = await session.get(Module, prereq_id)
            if prereq is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prerequisite module {prereq_id} not found",
                )
    for field, value in update_data.items():
        setattr(module, field, value)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=len(module.lessons),
        prerequisite_ids=module.prerequisite_ids, min_age=module.min_age, max_age=module.max_age,
        completion_cash_reward=module.completion_cash_reward,
    )


@router.delete("/modules/{module_id}")
async def delete_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    # Use bulk delete to trigger DB-level CASCADE on lessons
    await session.execute(delete(Lesson).where(Lesson.module_id == module_id))
    await session.execute(delete(Module).where(Module.id == module_id))
    await session.commit()
    return {"status": "ok"}


@router.patch("/modules/reorder")
async def reorder_modules(payload: ReorderRequest, session: AsyncSession = Depends(get_session)):
    for item in payload.order:
        await session.execute(
            update(Module).where(Module.id == item.id).values(order_index=item.order_index)
        )
    await session.commit()
    return {"status": "ok"}


# ── Lessons ─────────────────────────────────────────────────────────
@router.get("/modules/{module_id}/lessons", response_model=list[LessonOut])
async def list_lessons(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order_index)
    )
    return list(result.all())


@router.get("/modules/{module_id}/engagement", response_model=ModuleEngagementOut)
async def module_engagement(
    module_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await get_module_engagement(session, module_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return result


@router.post("/modules/{module_id}/lessons", response_model=LessonOut)
async def create_lesson(
    module_id: uuid.UUID, payload: LessonCreate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    lesson = Lesson(
        module_id=module_id, type=payload.type, content_json=payload.content_json,
        xp_reward=payload.xp_reward, order_index=payload.order_index,
    )
    session.add(lesson)
    await session.flush()
    await _upsert_apply_mission(session, lesson, payload)
    await session.commit()
    await session.refresh(lesson)
    return await _lesson_out(session, lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: uuid.UUID, payload: LessonUpdate, session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("apply_mission", None)
    # If both type and content_json are being updated, validate together
    if "content_json" in update_data:
        effective_type = update_data.get("type", lesson.type)
        LessonCreate(
            type=effective_type, content_json=update_data["content_json"],
            xp_reward=update_data.get("xp_reward", lesson.xp_reward),
            order_index=lesson.order_index,
        )
    for field, value in update_data.items():
        setattr(lesson, field, value)
    await _upsert_apply_mission(session, lesson, payload)
    await session.commit()
    await session.refresh(lesson)
    return await _lesson_out(session, lesson)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await session.delete(lesson)
    await session.commit()
    return {"status": "ok"}


@router.patch("/modules/{module_id}/lessons/reorder")
async def reorder_lessons(
    module_id: uuid.UUID, payload: ReorderRequest, session: AsyncSession = Depends(get_session),
):
    for item in payload.order:
        await session.execute(
            update(Lesson).where(Lesson.id == item.id, Lesson.module_id == module_id)
            .values(order_index=item.order_index)
        )
    await session.commit()
    return {"status": "ok"}


# ── Levels ──────────────────────────────────────────────────────────
def _level_out(level: Level, lesson_count: int) -> AdminLevelOut:
    return AdminLevelOut(
        id=level.id, module_id=level.module_id, title=level.title,
        order_index=level.order_index, is_premium=level.is_premium,
        pass_threshold=level.pass_threshold, content_source=level.content_source,
        icon=level.icon, lesson_count=lesson_count,
    )


@router.get("/modules/{module_id}/levels", response_model=list[AdminLevelOut])
async def admin_list_levels(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    levels = list(await session.scalars(
        select(Level).where(Level.module_id == module_id).order_by(Level.order_index)
    ))
    out = []
    for lv in levels:
        n = await session.scalar(
            select(func.count()).select_from(Lesson).where(Lesson.level_id == lv.id)
        )
        out.append(_level_out(lv, n or 0))
    return out


@router.post("/modules/{module_id}/levels", response_model=AdminLevelOut)
async def admin_create_level(
    module_id: uuid.UUID, payload: AdminLevelCreate, session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    level = Level(
        module_id=module_id, title=payload.title, order_index=payload.order_index,
        is_premium=payload.is_premium, pass_threshold=payload.pass_threshold,
        content_source="authored", icon=payload.icon,
    )
    session.add(level)
    await session.commit()
    await session.refresh(level)
    return _level_out(level, 0)


@router.put("/levels/{level_id}", response_model=AdminLevelOut)
async def admin_update_level(
    level_id: uuid.UUID, payload: AdminLevelUpdate, session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    data = payload.model_dump(exclude_unset=True)
    for k, val in data.items():
        setattr(level, k, val)
    await session.commit()
    await session.refresh(level)
    n = await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.level_id == level.id)
    )
    return _level_out(level, n or 0)


@router.delete("/levels/{level_id}")
async def admin_delete_level(level_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    await session.delete(level)
    await session.commit()
    return {"status": "deleted"}


@router.get("/levels/{level_id}/lessons", response_model=list[LessonOut])
async def admin_list_level_lessons(level_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.level_id == level_id).order_by(Lesson.order_index)
    ))
    return [LessonOut.model_validate(lsn) for lsn in lessons]


@router.post("/levels/{level_id}/lessons", response_model=LessonOut)
async def admin_create_level_lesson(
    level_id: uuid.UUID, payload: LessonCreate, session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    lesson = Lesson(
        module_id=level.module_id, level_id=level.id, type=payload.type,
        content_json=payload.content_json, xp_reward=payload.xp_reward,
        order_index=payload.order_index,
    )
    session.add(lesson)
    await session.flush()
    await _upsert_apply_mission(session, lesson, payload)
    await session.commit()
    await session.refresh(lesson)
    return await _lesson_out(session, lesson)


# ── Badges ──────────────────────────────────────────────────────────
@router.get("/badges", response_model=list[BadgeOut])
async def list_badges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Badge))
    return list(result.all())


@router.post("/badges", response_model=BadgeOut)
async def create_badge(payload: BadgeCreate, session: AsyncSession = Depends(get_session)):
    badge = Badge(**payload.model_dump())
    session.add(badge)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.put("/badges/{badge_id}", response_model=BadgeOut)
async def update_badge(
    badge_id: uuid.UUID, payload: BadgeUpdate, session: AsyncSession = Depends(get_session),
):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(badge, field, value)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.delete("/badges/{badge_id}")
async def delete_badge(badge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    # Check for user references
    earned_count = await session.scalar(
        select(func.count()).select_from(UserBadge).where(UserBadge.badge_id == badge_id)
    )
    if earned_count and earned_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete badge — {earned_count} user(s) have earned it",
        )
    await session.delete(badge)
    await session.commit()
    return {"status": "ok"}


# ── Challenges ──────────────────────────────────────────────────────
@router.get("/challenges", response_model=list[ChallengeOut])
async def list_challenges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Challenge).order_by(Challenge.starts_at.desc()))
    return list(result.all())


@router.post("/challenges", response_model=ChallengeOut)
async def create_challenge(payload: ChallengeCreate, session: AsyncSession = Depends(get_session)):
    challenge = Challenge(**payload.model_dump())
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.put("/challenges/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(
    challenge_id: uuid.UUID, payload: ChallengeUpdate, session: AsyncSession = Depends(get_session),
):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(challenge, field, value)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.delete("/challenges/{challenge_id}")
async def delete_challenge(challenge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    await session.delete(challenge)
    await session.commit()
    return {"status": "ok"}


# ── Utility ─────────────────────────────────────────────────────────
@router.get("/countries")
async def list_countries(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(User.country_code).where(User.country_code.isnot(None)).distinct()
    )
    return sorted(result.all())


# ── Settings ────────────────────────────────────────────────────────
@router.get("/settings", response_model=AdminSettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)):
    emails = await get_alert_emails(session)
    cash = await get_starting_cash(session)
    return AdminSettingsOut(
        alert_emails=emails, starting_cash={k: str(v) for k, v in cash.items()}
    )


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session),
):
    await set_alert_emails(session, body.alert_emails)
    if body.starting_cash is not None:
        await set_starting_cash(session, {k: Decimal(v) for k, v in body.starting_cash.items()})
    await session.commit()
    cash = await get_starting_cash(session)
    return AdminSettingsOut(
        alert_emails=body.alert_emails, starting_cash={k: str(v) for k, v in cash.items()}
    )


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
        upload_url=storage.create_presigned_put(key, payload.content_type),
        public_url=storage.public_url(key),
    )
