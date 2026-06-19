import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.apply_mission import ApplyMission
from app.models.content import Lesson, Level, Module
from app.models.content_translation import ContentTranslation
from app.models.gamification import Badge, Challenge, UserBadge
from app.models.lesson_draft import LessonDraft
from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.models.user import User
from app.models.video_asset import VideoAsset
from app.models.video_health import VideoHealth
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    AdaptationFlags,
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
    CoverageBucket,
    CuratedTranslationRequest,
    GenerateLessonsRequest,
    GenerateLessonsResponse,
    GenerateMarketLessonsRequest,
    GenerateNativeLessonsRequest,
    LessonCreate,
    LessonDraftOut,
    LessonDraftUpdate,
    LessonOut,
    LessonUpdate,
    MarketBriefOut,
    MarketBriefUpdate,
    MarketScaffoldResult,
    ModuleCreate,
    ModuleEngagementOut,
    ModuleOut,
    ModuleSuggestion,
    ModuleUpdate,
    ReorderRequest,
    TranslationCoverageOut,
    TranslationGenerateRequest,
    TranslationGenerateResult,
    VideoHealthCheckResult,
    VideoHealthItem,
    VideoPresignRequest,
    VideoPresignResponse,
    validate_lesson_content_json,
)
from app.schemas.parent import PremiumToggleRequest
from app.services import storage, video_health_service
from app.services.admin_content_generation_service import (
    _concat_text,
    generate_level_lessons,
    generate_market_level_lessons,
    generate_native_level_lessons,
    regenerate_draft,
)
from app.services.app_settings import (
    get_alert_emails,
    get_enabled_content_languages,
    get_market_completion_bonus_coins,
    get_market_enroll_bonus_coins,
    get_setting,
    get_starting_cash,
    get_trade_commission_pct,
    set_alert_emails,
    set_enabled_content_languages,
    set_market_completion_bonus_coins,
    set_market_enroll_bonus_coins,
    set_starting_cash,
    set_trade_commission_pct,
)
from app.services.content_adaptation_check import find_uk_residue
from app.services.content_i18n import extract_bundle, source_hash, validate_bundle
from app.services.engagement_service import get_module_engagement
from app.services.entitlements import set_premium
from app.services.event_service import EVENT_KEY, set_event
from app.services.level_service import premium_for_position
from app.services.llm_client import probe_all_providers
from app.services.market_brief_service import (
    BriefGenerationError,
    generate_brief,
    require_verified_brief,
)
from app.services.market_module_suggester import suggest_modules
from app.services.market_scaffold_service import scaffold_market_from_gb
from app.services.moderation import moderate_output
from app.services.translation_service import translate_entity

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
            market_code=m.market_code,
            order_index=m.order_index, lesson_count=len(m.lessons),
            prerequisite_ids=m.prerequisite_ids, min_age=m.min_age, max_age=m.max_age,
            standards_alignment=m.standards_alignment, sources=m.sources,
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
        market_code=module.market_code,
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
        market_code=module.market_code,
        order_index=module.order_index, lesson_count=len(module.lessons),
        prerequisite_ids=module.prerequisite_ids, min_age=module.min_age, max_age=module.max_age,
        completion_cash_reward=module.completion_cash_reward,
        standards_alignment=module.standards_alignment, sources=module.sources,
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
        learning_objectives=level.learning_objectives,
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
        is_premium=premium_for_position(payload.order_index),
        pass_threshold=payload.pass_threshold,
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
    data.pop("is_premium", None)  # derived from position, never client-set
    for k, val in data.items():
        setattr(level, k, val)
    level.is_premium = premium_for_position(level.order_index)
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


@router.post("/levels/{level_id}/generate", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    result = await generate_level_lessons(
        session, level, concept=payload.concept, count=payload.count, types=payload.types,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.post("/levels/{level_id}/generate-market", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_market_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateMarketLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    target_level = await session.get(Level, level_id)
    if target_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    source_level = await session.get(Level, payload.source_level_id)
    if source_level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source level not found")
    target_module = await session.get(Module, target_level.module_id)
    if target_module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, target_module.market_code)
    result = await generate_market_level_lessons(
        session, target_level, source_level=source_level, brief=brief,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.post("/levels/{level_id}/generate-native", response_model=GenerateLessonsResponse)
@limiter.limit("5/minute")
async def generate_native_level_lessons_endpoint(
    request: Request,
    level_id: uuid.UUID,
    payload: GenerateNativeLessonsRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    module = await session.get(Module, level.module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    result = await generate_native_level_lessons(
        session, level, brief=brief, concepts=payload.concepts, types=payload.types,
    )
    return GenerateLessonsResponse(
        created=[LessonDraftOut.model_validate(d) for d in result.created],
        skipped=result.skipped,
    )


@router.get("/levels/{level_id}/drafts", response_model=list[LessonDraftOut])
async def list_lesson_drafts(
    level_id: uuid.UUID, session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level_id).order_by(LessonDraft.created_at)
    )).all()

    def _draft_out(d):
        residue = find_uk_residue(_concat_text(d.content_json or {}))
        out = LessonDraftOut.model_validate(d)
        out.adaptation_flags = AdaptationFlags(uk_residue=residue, suspect=bool(residue))
        return out

    return [_draft_out(d) for d in rows]


@router.put("/lesson-drafts/{draft_id}", response_model=LessonDraftOut)
async def update_lesson_draft(
    draft_id: uuid.UUID,
    payload: LessonDraftUpdate,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    try:
        validate_lesson_content_json(draft.type, payload.content_json)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    mod = await moderate_output(_concat_text(payload.content_json), surface="lesson")
    draft.content_json = payload.content_json
    draft.moderation_safe = mod.safe
    draft.moderation_category = mod.category
    await session.commit()
    return LessonDraftOut.model_validate(draft)


@router.post("/lesson-drafts/{draft_id}/approve", response_model=LessonOut)
async def approve_lesson_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if not draft.moderation_safe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Draft failed moderation")
    level = await session.get(Level, draft.level_id)
    max_order = await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == draft.level_id)
    )
    lesson = Lesson(
        module_id=level.module_id, level_id=draft.level_id, type=draft.type,
        content_json=draft.content_json, xp_reward=10, order_index=(max_order or 0) + 1,
    )
    session.add(lesson)
    await session.delete(draft)
    await session.commit()
    await session.refresh(lesson)
    return await _lesson_out(session, lesson)


@router.post("/lesson-drafts/{draft_id}/regenerate", response_model=LessonDraftOut)
@limiter.limit("5/minute")
async def regenerate_lesson_draft(
    request: Request,
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    updated = await regenerate_draft(session, draft)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Generation failed")
    return LessonDraftOut.model_validate(updated)


@router.delete("/lesson-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reject_lesson_draft(
    draft_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    draft = await session.get(LessonDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    await session.delete(draft)
    await session.commit()


# ── Market briefs ───────────────────────────────────────────────────
@router.post("/markets/{code}/brief/generate", response_model=MarketBriefOut)
@limiter.limit("5/minute")
async def generate_market_brief(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    try:
        brief = await generate_brief(session, market)
    except (BriefGenerationError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="brief generation failed"
        ) from exc
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.get("/markets/{code}/brief", response_model=MarketBriefOut)
async def get_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return MarketBriefOut.model_validate(brief)


@router.put("/markets/{code}/brief", response_model=MarketBriefOut)
async def update_market_brief(
    code: str,
    payload: MarketBriefUpdate,
    session: AsyncSession = Depends(get_session),
):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    if not isinstance(payload.brief_json, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brief_json must be an object"
        )
    brief.brief_json = payload.brief_json
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/brief/verify", response_model=MarketBriefOut)
async def verify_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    brief.status = "verified"
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/scaffold", response_model=MarketScaffoldResult)
@limiter.limit("5/minute")
async def scaffold_market(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    summary = await scaffold_market_from_gb(session, code)
    return MarketScaffoldResult.model_validate(summary)


@router.post("/markets/{code}/module-suggestions", response_model=list[ModuleSuggestion])
@limiter.limit("5/minute")
async def market_module_suggestions(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    suggestions = await suggest_modules(session, market)
    return [ModuleSuggestion(**s) for s in suggestions]


@router.post("/markets/{code}/publish")
async def publish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    lesson_count = await session.scalar(
        select(func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == code)
    ) or 0
    if lesson_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="market has no lessons to publish"
        )
    market.has_content = True
    await session.commit()
    return {"code": code, "has_content": True}


@router.post("/markets/{code}/unpublish")
async def unpublish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    market.has_content = False
    await session.commit()
    return {"code": code, "has_content": False}


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
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session),
):
    await set_alert_emails(session, body.alert_emails)
    if body.starting_cash is not None:
        await set_starting_cash(session, {k: Decimal(v) for k, v in body.starting_cash.items()})
    if body.trade_commission_pct is not None:
        await set_trade_commission_pct(session, Decimal(body.trade_commission_pct))
    if body.market_enroll_bonus_coins is not None:
        await set_market_enroll_bonus_coins(session, body.market_enroll_bonus_coins)
    if body.market_completion_bonus_coins is not None:
        await set_market_completion_bonus_coins(session, body.market_completion_bonus_coins)
    if body.enabled_content_languages is not None:
        await set_enabled_content_languages(session, body.enabled_content_languages)
    if body.clear_seasonal_event:
        await set_event(session, None)
    elif body.seasonal_event is not None:
        await set_event(session, {
            "title": body.seasonal_event.title,
            "emoji": body.seasonal_event.emoji,
            "starts_at": body.seasonal_event.starts_at.isoformat(),
            "ends_at": body.seasonal_event.ends_at.isoformat(),
            "xp_bonus_pct": body.seasonal_event.xp_bonus_pct,
        })
    await session.commit()
    cash = await get_starting_cash(session)
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=body.alert_emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


# ── Content translations (i18n pipeline) ────────────────────────────
@router.post("/translations/generate", response_model=TranslationGenerateResult)
async def generate_translations(
    body: TranslationGenerateRequest, session: AsyncSession = Depends(get_session),
):
    """Auto-translate all content entities into a language (optionally one market).

    Tallies on the action returned by translate_entity: generated→translated,
    skipped→skipped_fresh, failed→failed; noop is uncounted.
    """
    res = TranslationGenerateResult()
    mod_q = select(Module)
    if body.market_code:
        mod_q = mod_q.where(Module.market_code == body.market_code)
    modules = (await session.scalars(mod_q)).all()
    module_ids = [m.id for m in modules]
    levels = (
        (await session.scalars(select(Level).where(Level.module_id.in_(module_ids)))).all()
        if module_ids else []
    )
    lessons = (
        (await session.scalars(select(Lesson).where(Lesson.module_id.in_(module_ids)))).all()
        if module_ids else []
    )

    for etype, items in (("module", modules), ("level", levels), ("lesson", lessons)):
        for ent in items:
            _row, action = await translate_entity(session, etype, ent, body.language)
            if action == "generated":
                res.translated += 1
            elif action == "skipped":
                res.skipped_fresh += 1
            elif action == "failed":
                res.failed += 1
            # action == "noop" (empty bundle / unsupported) → not counted
    await session.commit()
    return res


async def _fetch_entity(session: AsyncSession, entity_type: str, entity_id: uuid.UUID):
    model = {"module": Module, "level": Level, "lesson": Lesson}.get(entity_type)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown entity_type {entity_type!r}",
        )
    return await session.get(model, entity_id)


@router.put("/translations/curated")
async def put_curated_translation(
    body: CuratedTranslationRequest, session: AsyncSession = Depends(get_session),
):
    """Store/replace a human-authored (curated) translation for one entity.

    Validates the bundle against the entity's CURRENT English source; curated
    content bypasses moderation (human-authored)."""
    entity = await _fetch_entity(session, body.entity_type, body.entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity_not_found")

    source = extract_bundle(body.entity_type, entity)
    if not validate_bundle(body.entity_type, source, body.translated_json):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="translated_json structure does not match the English source",
        )
    h = source_hash(source)

    row = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == body.entity_type,
            ContentTranslation.entity_id == body.entity_id,
            ContentTranslation.language == body.language,
        )
    )
    if row is None:
        row = ContentTranslation(
            entity_type=body.entity_type, entity_id=body.entity_id, language=body.language,
            translated_json=body.translated_json, source="curated",
            source_hash=h, status="active",
        )
        session.add(row)
    else:
        row.translated_json = body.translated_json
        row.source = "curated"
        row.source_hash = h
        row.status = "active"
    await session.commit()
    return {"status": "ok", "entity_id": str(body.entity_id), "language": body.language}


@router.get("/translations/coverage", response_model=TranslationCoverageOut)
async def translation_coverage(
    language: str, session: AsyncSession = Depends(get_session),
):
    """Per-entity-type coverage for a language: active/failed/missing rows."""
    async def _bucket(entity_type: str, model) -> CoverageBucket:
        total = await session.scalar(select(func.count()).select_from(model)) or 0
        active = await session.scalar(
            select(func.count()).select_from(ContentTranslation).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.language == language,
                ContentTranslation.status == "active",
            )
        ) or 0
        failed = await session.scalar(
            select(func.count()).select_from(ContentTranslation).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.language == language,
                ContentTranslation.status == "failed",
            )
        ) or 0
        missing = max(total - active - failed, 0)
        return CoverageBucket(active=active, failed=failed, missing=missing)

    return TranslationCoverageOut(
        language=language,
        modules=await _bucket("module", Module),
        levels=await _bucket("level", Level),
        lessons=await _bucket("lesson", Lesson),
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
        upload_url=storage.create_presigned_put(
            key, payload.content_type, content_length=payload.size_bytes
        ),
        public_url=storage.public_url(key),
    )


# ── Premium comp (admin-only) ────────────────────────────────────────────────
@router.post("/users/{user_id}/premium")
async def admin_set_user_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    await set_premium(session, user, value=payload.premium, actor="admin")
    await session.commit()
    return {"status": "ok", "premium": payload.premium}


# ── LLM provider health probe ────────────────────────────────────────────────
@router.get("/llm-status")
async def llm_status() -> list[dict]:
    """Ping each configured LLM provider with a trivial completion.

    Returns per-provider ok/error status without exposing any API key material.
    Admin-only (enforced by the router-level dependency).
    """
    return await probe_all_providers()
