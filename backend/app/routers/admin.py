import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.content import Lesson, Level, Module
from app.models.gamification import Badge, Challenge, UserBadge
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    AdminLevelCreate,
    AdminLevelOut,
    AdminLevelUpdate,
    AdminSettingsOut,
    AdminSettingsUpdate,
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
)
from app.services.app_settings import get_alert_emails, set_alert_emails
from app.services.engagement_service import get_module_engagement

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


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
    )
    session.add(module)
    await session.commit()
    await session.refresh(module)
    return ModuleOut(
        id=module.id, topic=module.topic, title=module.title, icon=module.icon,
        is_premium=module.is_premium, country_codes=module.country_codes,
        order_index=module.order_index, lesson_count=0,
        prerequisite_ids=module.prerequisite_ids, min_age=module.min_age, max_age=module.max_age,
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
    await session.commit()
    await session.refresh(lesson)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: uuid.UUID, payload: LessonUpdate, session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    update_data = payload.model_dump(exclude_unset=True)
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
    await session.commit()
    await session.refresh(lesson)
    return lesson


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
    await session.commit()
    await session.refresh(lesson)
    return LessonOut.model_validate(lesson)


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
    return AdminSettingsOut(alert_emails=emails)


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session),
):
    await set_alert_emails(session, body.alert_emails)
    await session.commit()
    return AdminSettingsOut(alert_emails=body.alert_emails)
