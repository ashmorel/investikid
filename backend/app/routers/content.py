import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, LessonCompletion, Module
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.content import (
    LessonCompletionRequest,
    LessonCompletionResult,
    LessonOut,
    LessonSummary,
    ModuleOut,
)
from app.services.content_service import (
    compute_level,
    derive_lesson_title,
    is_module_accessible,
    streak_after_activity,
)
from app.services.gamification_service import (
    evaluate_and_award_badges,
    update_challenge_progress,
)

router = APIRouter(tags=["content"])


async def _get_accessible_module(
    module_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> Module:
    module = await session.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    country_ok = not module.country_codes or current_user.country_code in module.country_codes
    if not country_ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    if not is_module_accessible(
        current_user.country_code, current_user.is_premium,
        module.country_codes, module.is_premium,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Module requires premium")
    return module


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(Module).order_by(Module.order_index))
    modules = result.all()
    out: list[ModuleOut] = []
    for m in modules:
        country_ok = not m.country_codes or current_user.country_code in m.country_codes
        if not country_ok:
            continue
        accessible = is_module_accessible(
            current_user.country_code, current_user.is_premium,
            m.country_codes, m.is_premium,
        )
        out.append(ModuleOut(
            id=m.id, topic=m.topic, title=m.title,
            country_codes=m.country_codes, is_premium=m.is_premium,
            order_index=m.order_index, locked=not accessible,
        ))
    return out


@router.get("/modules/{module_id}/lessons", response_model=list[LessonSummary])
async def list_lessons(
    module_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_accessible_module(module_id, current_user, session)

    lessons_result = await session.scalars(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order_index)
    )
    lessons = list(lessons_result.all())

    if lessons:
        completions_result = await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_([l.id for l in lessons]),
            )
        )
        completed_ids = set(completions_result.all())
    else:
        completed_ids = set()

    return [
        LessonSummary(
            id=l.id,
            type=l.type,
            title=derive_lesson_title(l.type, l.content_json or {}),
            xp_reward=l.xp_reward,
            order_index=l.order_index,
            completed=l.id in completed_ids,
        )
        for l in lessons
    ]


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    await _get_accessible_module(lesson.module_id, current_user, session)

    completed = await session.scalar(
        select(LessonCompletion.id).where(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == lesson.id,
        )
    )
    return LessonOut(
        id=lesson.id, module_id=lesson.module_id, type=lesson.type,
        content_json=lesson.content_json, xp_reward=lesson.xp_reward,
        order_index=lesson.order_index, completed=completed is not None, locked=False,
    )


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompletionResult)
async def complete_lesson(
    lesson_id: uuid.UUID,
    payload: LessonCompletionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    await _get_accessible_module(lesson.module_id, current_user, session)

    progress = await session.get(UserProgress, current_user.id)
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()

    today = datetime.now(timezone.utc).date()
    xp_awarded, already = await _award_completion(
        session, current_user.id, progress, lesson, payload.score, today
    )

    if not already:
        await update_challenge_progress(
            session, current_user.id, "lessons_completed", increment=1
        )
        await update_challenge_progress(
            session, current_user.id, "xp_earned", increment=xp_awarded
        )
        await evaluate_and_award_badges(session, current_user.id, progress)

    await session.commit()
    await session.refresh(progress)

    return LessonCompletionResult(
        xp_awarded=xp_awarded, already_completed=already,
        total_xp=progress.xp, level=progress.level, streak_count=progress.streak_count,
    )


async def _award_completion(
    session: AsyncSession,
    user_id,
    progress: UserProgress,
    lesson: Lesson,
    score: float | None,
    today_local,
) -> tuple[int, bool]:
    """Insert a LessonCompletion and award XP. Idempotent via DB unique constraint."""
    from sqlalchemy.exc import IntegrityError

    completion = LessonCompletion(
        user_id=user_id, lesson_id=lesson.id, score=score,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(completion)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return 0, True

    progress.xp += lesson.xp_reward
    progress.level = compute_level(progress.xp)
    new_streak, new_last = streak_after_activity(
        progress.last_activity_date, progress.streak_count, today_local
    )
    progress.streak_count = new_streak
    progress.last_activity_date = new_last
    return lesson.xp_reward, False
