"""Content/curriculum routes for the admin area.

This is a bare sub-router (no prefix, no dependencies) that is mounted by
``admin.py`` via ``router.include_router(admin_content.router)``.  Auth is
enforced by the parent router's ``dependencies=[Depends(get_current_admin)]``.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.apply_mission import ApplyMission
from app.models.concept import Concept
from app.models.content import Lesson, Level, Module
from app.models.gamification import Badge, Challenge
from app.models.lesson_draft import LessonDraft
from app.schemas.admin import (
    AdminLevelCreate,
    AdminLevelOut,
    AdminLevelUpdate,
    ApplyMissionOut,
    LessonCreate,
    LessonOut,
    LessonUpdate,
    ModuleCreate,
    ModuleEngagementOut,
    ModuleOut,
    ModuleUpdate,
    ReorderRequest,
)
from app.schemas.concept import (
    ConceptIn,
    ConceptOut,
    ConceptPatch,
    ConceptsOverview,
    LessonConceptPatch,
    TopicGroup,
)
from app.services.engagement_service import get_module_engagement
from app.services.level_service import premium_for_position

_TOPIC_ORDER = [
    "stocks", "savings", "real_estate", "budgeting", "risk",
    "crypto", "taxes", "debt", "entrepreneurship",
]

router = APIRouter()


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
            market_code=m.market_code, published=m.published, archived_at=m.archived_at,
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
        market_code=module.market_code, published=module.published,
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
        market_code=module.market_code, published=module.published,
        order_index=module.order_index, lesson_count=len(module.lessons),
        prerequisite_ids=module.prerequisite_ids, min_age=module.min_age, max_age=module.max_age,
        completion_cash_reward=module.completion_cash_reward,
        standards_alignment=module.standards_alignment, sources=module.sources,
    )


@router.delete("/modules/{module_id}")
async def delete_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Soft-archive a module (moves it to the admin Archived section; hard-purged
    after the retention window). Live (published) modules are refused — unpublish
    or replace them first so content can't vanish from the app mid-use."""
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unpublish or replace this live module before archiving",
        )
    module.archived_at = datetime.now(UTC)
    await session.commit()
    return {"status": "archived"}


@router.post("/modules/{module_id}/restore")
async def restore_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Un-archive a module: back to the admin main list, 30-day purge clock reset."""
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    module.archived_at = None
    await session.commit()
    return {"status": "restored"}


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
def _level_out(level: Level, lesson_count: int, draft_count: int = 0) -> AdminLevelOut:
    return AdminLevelOut(
        id=level.id, module_id=level.module_id, title=level.title,
        order_index=level.order_index, is_premium=level.is_premium,
        pass_threshold=level.pass_threshold, content_source=level.content_source,
        icon=level.icon, lesson_count=lesson_count, draft_count=draft_count,
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
        d = await session.scalar(
            select(func.count()).select_from(LessonDraft).where(LessonDraft.level_id == lv.id)
        )
        out.append(_level_out(lv, n or 0, d or 0))
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


# ── Concepts ────────────────────────────────────────────────────────

async def _concept_lesson_count(session: AsyncSession, concept_id: uuid.UUID) -> int:
    n = await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.concept_id == concept_id)
    )
    return n or 0


async def _global_unmapped_lessons(session: AsyncSession) -> int:
    """Count published-module lessons (across all topics) whose concept_id is NULL.

    This is the global figure shown in the admin header.  It matches the backfill
    scope (concept_backfill_service only resolves published lessons).
    """
    n = await session.scalar(
        select(func.count())
        .select_from(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.published.is_(True),
            Lesson.concept_id.is_(None),
        )
    )
    return n or 0


@router.get("/concepts", response_model=ConceptsOverview)
async def list_concepts(session: AsyncSession = Depends(get_session)) -> ConceptsOverview:
    """Return concepts grouped by topic with per-concept lesson_count and a global unmapped_lessons count."""
    result = await session.scalars(
        select(Concept).order_by(Concept.topic, Concept.order_index, Concept.name)
    )
    concepts = list(result.all())

    # Group by topic preserving canonical order.
    topic_map: dict[str, list[Concept]] = {}
    for c in concepts:
        topic_map.setdefault(c.topic, []).append(c)

    groups: list[TopicGroup] = []
    for topic in _TOPIC_ORDER:
        topic_concepts = topic_map.get(topic, [])
        concept_outs = []
        for c in topic_concepts:
            lc = await _concept_lesson_count(session, c.id)
            concept_outs.append(ConceptOut(
                id=c.id, topic=c.topic, slug=c.slug, name=c.name,
                blurb=c.blurb, difficulty_tier=c.difficulty_tier,
                order_index=c.order_index, lesson_count=lc,
            ))
        groups.append(TopicGroup(topic=topic, concepts=concept_outs))

    unmapped_lessons = await _global_unmapped_lessons(session)
    return ConceptsOverview(unmapped_lessons=unmapped_lessons, groups=groups)


@router.post("/concepts", response_model=ConceptOut, status_code=status.HTTP_201_CREATED)
async def create_concept(
    payload: ConceptIn, session: AsyncSession = Depends(get_session)
) -> ConceptOut:
    existing = await session.scalar(select(Concept).where(Concept.slug == payload.slug))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")
    concept = Concept(
        topic=payload.topic,
        slug=payload.slug,
        name=payload.name,
        blurb=payload.blurb,
        difficulty_tier=payload.difficulty_tier,
        order_index=payload.order_index,
    )
    session.add(concept)
    await session.commit()
    await session.refresh(concept)
    return ConceptOut(
        id=concept.id, topic=concept.topic, slug=concept.slug, name=concept.name,
        blurb=concept.blurb, difficulty_tier=concept.difficulty_tier,
        order_index=concept.order_index, lesson_count=0,
    )


@router.patch("/concepts/{concept_id}", response_model=ConceptOut)
async def patch_concept(
    concept_id: uuid.UUID, payload: ConceptPatch, session: AsyncSession = Depends(get_session)
) -> ConceptOut:
    concept = await session.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    data = payload.model_dump(exclude_unset=True)
    # Slug uniqueness check if slug is being changed.
    if "slug" in data and data["slug"] != concept.slug:
        clash = await session.scalar(select(Concept).where(Concept.slug == data["slug"]))
        if clash is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")
    for field, value in data.items():
        setattr(concept, field, value)
    await session.commit()
    await session.refresh(concept)
    lc = await _concept_lesson_count(session, concept.id)
    return ConceptOut(
        id=concept.id, topic=concept.topic, slug=concept.slug, name=concept.name,
        blurb=concept.blurb, difficulty_tier=concept.difficulty_tier,
        order_index=concept.order_index, lesson_count=lc,
    )


@router.patch("/lessons/{lesson_id}/concept")
async def patch_lesson_concept(
    lesson_id: uuid.UUID, payload: LessonConceptPatch, session: AsyncSession = Depends(get_session)
) -> dict:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    if payload.concept_id is not None:
        concept = await session.get(Concept, payload.concept_id)
        if concept is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    lesson.concept_id = payload.concept_id
    await session.commit()
    return {"id": str(lesson.id), "concept_id": str(lesson.concept_id) if lesson.concept_id else None}
