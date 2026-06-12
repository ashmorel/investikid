import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, LessonCompletion, LessonView, Level, LevelMastery, Module
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.content import (
    LessonCompletionRequest,
    LessonCompletionResult,
    LessonOut,
    LessonSummary,
    LevelOut,
    ModuleOut,
    NextLessonEnvelope,
)
from app.services import product_analytics_service
from app.services.age_tier import age_in_years
from app.services.content_service import (
    content_region_for,
    derive_lesson_title,
    grant_module_completion_cash,
    is_module_accessible,
    is_module_age_ok,
    record_daily_activity,
)
from app.services.entitlements import is_premium
from app.services.gamification_service import (
    evaluate_and_award_badges,
    update_challenge_progress,
)
from app.services.level_service import LevelStateInput, derive_level_states
from app.services.mastery_service import record_mastery_if_earned
from app.services.next_lesson_service import resolve_next_lesson
from app.services.premium_config import premium_required_error
from app.services.skill_profile_service import (
    record_weak_concept,
    reinforce_concept,
    update_mastery_on_completion,
)
from app.services.xp_service import record_xp

router = APIRouter(tags=["content"])


async def _get_accessible_module(
    module_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> Module:
    module = await session.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    country_ok = not module.country_codes or content_region_for(current_user) in module.country_codes
    if not country_ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    # Age gate uses the actual age from dob (NEVER the parent tier_override) and
    # mirrors the inaccessible-country behaviour: a plain 404, no content tease.
    user_age = age_in_years(current_user.dob, datetime.now(UTC).date())
    if not is_module_age_ok(user_age, module.min_age, module.max_age):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    if not is_module_accessible(
        content_region_for(current_user), is_premium(current_user),
        module.country_codes, module.is_premium,
    ):
        raise premium_required_error("module", module.title)
    return module


@router.get("/next-lesson", response_model=NextLessonEnvelope)
async def get_next_lesson(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return NextLessonEnvelope(next=await resolve_next_lesson(session, current_user))


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(Module).order_by(Module.order_index))
    modules = result.all()
    user_age = age_in_years(current_user.dob, datetime.now(UTC).date())
    out: list[ModuleOut] = []
    for m in modules:
        country_ok = not m.country_codes or content_region_for(current_user) in m.country_codes
        if not country_ok:
            continue
        # Hidden, not teased: out-of-age modules never appear in the list
        # (actual age from dob — the parent tier_override must not unlock these).
        if not is_module_age_ok(user_age, m.min_age, m.max_age):
            continue
        accessible = is_module_accessible(
            content_region_for(current_user), is_premium(current_user),
            m.country_codes, m.is_premium,
        )
        out.append(ModuleOut(
            id=m.id, topic=m.topic, title=m.title,
            country_codes=m.country_codes, is_premium=m.is_premium,
            order_index=m.order_index, icon=m.icon, locked=not accessible,
            standards_alignment=m.standards_alignment, sources=m.sources,
        ))
    pref = current_user.topic_path
    if pref and pref in {m.topic for m in modules}:
        out.sort(key=lambda mo: (0 if mo.topic == pref else 1))
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
                LessonCompletion.lesson_id.in_([lesson.id for lesson in lessons]),
            )
        )
        completed_ids = set(completions_result.all())
    else:
        completed_ids = set()

    return [
        LessonSummary(
            id=lesson.id,
            type=lesson.type,
            title=derive_lesson_title(lesson.type, lesson.content_json or {}),
            xp_reward=lesson.xp_reward,
            order_index=lesson.order_index,
            completed=lesson.id in completed_ids,
        )
        for lesson in lessons
    ]


async def _get_accessible_level(level_id, current_user, session) -> Level:
    level = await session.get(Level, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")
    # Reuse module access (country/age/premium-module gate)
    await _get_accessible_module(level.module_id, current_user, session)
    if level.is_premium and not is_premium(current_user):
        raise premium_required_error("level", level.title)
    return level


@router.get("/modules/{module_id}/levels", response_model=list[LevelOut])
async def list_levels(
    module_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_accessible_module(module_id, current_user, session)
    levels = list(await session.scalars(
        select(Level).where(Level.module_id == module_id).order_by(Level.order_index)
    ))
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.module_id == module_id)
    ))
    lessons_by_level: dict = {}
    for lsn in lessons:
        if lsn.level_id is not None:
            lessons_by_level.setdefault(lsn.level_id, []).append(lsn.id)

    all_lesson_ids = [lsn.id for lsn in lessons]
    completed_ids: set = set()
    scores: dict = {}
    if all_lesson_ids:
        rows = (await session.execute(
            select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_(all_lesson_ids),
            )
        )).all()
        for lid, score in rows:
            completed_ids.add(lid)
            scores[lid] = score

    states = derive_level_states(
        [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
        lessons_by_level=lessons_by_level,
        completed_ids=completed_ids, scores=scores,
        user_is_premium=is_premium(current_user),
    )
    mastered_at_by_level: dict = {}
    if levels:
        mastery_rows = (await session.execute(
            select(LevelMastery.level_id, LevelMastery.mastered_at).where(
                LevelMastery.user_id == current_user.id,
                LevelMastery.level_id.in_([lv.id for lv in levels]),
            )
        )).all()
        mastered_at_by_level = dict(mastery_rows)
    return [
        LevelOut(
            id=lv.id, module_id=lv.module_id, title=lv.title, order_index=lv.order_index,
            is_premium=lv.is_premium, icon=lv.icon,
            state=states[lv.id].state, locked_reason=states[lv.id].locked_reason,
            passed=states[lv.id].passed, lessons_total=states[lv.id].lessons_total,
            lessons_completed=states[lv.id].lessons_completed,
            learning_objectives=lv.learning_objectives,
            mastered_at=mastered_at_by_level.get(lv.id),
        )
        for lv in levels
    ]


@router.get("/levels/{level_id}/lessons", response_model=list[LessonSummary])
async def list_level_lessons(
    level_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_accessible_level(level_id, current_user, session)
    lessons = list(await session.scalars(
        select(Lesson).where(Lesson.level_id == level_id).order_by(Lesson.order_index)
    ))
    completed_ids: set = set()
    if lessons:
        completed_ids = set(await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_([lsn.id for lsn in lessons]),
            )
        ))
    return [
        LessonSummary(
            id=lsn.id, type=lsn.type,
            title=derive_lesson_title(lsn.type, lsn.content_json or {}),
            xp_reward=lsn.xp_reward, order_index=lsn.order_index,
            completed=lsn.id in completed_ids,
        )
        for lsn in lessons
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


@router.post("/lessons/{lesson_id}/view", status_code=204)
async def record_lesson_view(
    lesson_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    existing = await session.scalar(
        select(LessonView).where(
            LessonView.user_id == current_user.id,
            LessonView.lesson_id == lesson_id,
        )
    )
    if existing is None:
        session.add(LessonView(user_id=current_user.id, lesson_id=lesson_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()  # another request already recorded the view
    return None


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

    module = await _get_accessible_module(lesson.module_id, current_user, session)
    # Capture scalar attributes early before session expires ORM objects
    topic = module.topic
    module_id = module.id
    lesson_type = lesson.type
    lesson_level_id = lesson.level_id
    lesson_content = lesson.content_json or {}
    is_quiz = lesson_type in ("quiz", "scenario")

    progress = await session.get(UserProgress, current_user.id)
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()

    today = datetime.now(UTC).date()
    xp_awarded, already, daily_goal_met = await _award_completion(
        session, current_user.id, progress, lesson, payload.score, today
    )

    await product_analytics_service.record(
        session,
        "lesson_completed",
        user=current_user,
        role="child",
        props={
            "module_id": str(module_id),
            "level_id": str(lesson_level_id) if lesson_level_id else None,
            "lesson_id": str(lesson_id),
            "repeat": already,
        },
    )

    if lesson_level_id is not None:
        await record_mastery_if_earned(session, current_user.id, lesson_level_id)

    if not already:
        await update_challenge_progress(
            session, current_user.id, "lessons_completed", increment=1
        )
        await update_challenge_progress(
            session, current_user.id, "xp_earned", increment=xp_awarded
        )
        await evaluate_and_award_badges(session, current_user.id, progress)

    # Update skill profile
    correct = payload.score is not None and payload.score >= 0.5 if is_quiz else None

    if not already:
        await update_mastery_on_completion(
            session, current_user.id, topic, is_quiz=is_quiz, correct=correct,
        )

        if is_quiz and correct is False:
            concept = derive_lesson_title(lesson_type, lesson_content)
            await record_weak_concept(session, current_user.id, topic, concept)
        elif is_quiz and correct is True:
            concept = derive_lesson_title(lesson_type, lesson_content)
            await reinforce_concept(session, current_user.id, topic, concept)

    await grant_module_completion_cash(session, current_user.id, lesson.module_id)

    await session.commit()
    await session.refresh(progress)

    practice_available = (
        not already
        and is_quiz
        and payload.score is not None
        and payload.score < 0.5
    )

    return LessonCompletionResult(
        xp_awarded=xp_awarded, already_completed=already,
        total_xp=progress.xp, level=progress.level, streak_count=progress.streak_count,
        streak_freezes=progress.streak_freezes,
        practice_available=practice_available,
        daily_goal_met=daily_goal_met,
    )


async def _award_completion(
    session: AsyncSession,
    user_id,
    progress: UserProgress,
    lesson: Lesson,
    score: float | None,
    today_local,
) -> tuple[int, bool]:
    """Insert a LessonCompletion + award XP once. On repeat, keep the best score."""
    existing = await session.scalar(
        select(LessonCompletion).where(
            LessonCompletion.user_id == user_id,
            LessonCompletion.lesson_id == lesson.id,
        )
    )
    if existing is not None:
        # Best-score-wins; XP already awarded on first completion.
        if score is not None and (existing.score is None or score > existing.score):
            existing.score = score
            existing.completed_at = datetime.now(UTC)
        return 0, True, False

    try:
        async with session.begin_nested():
            session.add(LessonCompletion(
                user_id=user_id, lesson_id=lesson.id, score=score,
                completed_at=datetime.now(UTC),
            ))
            await session.flush()
    except IntegrityError:
        # Lost a concurrent first-completion race (same user, same lesson).
        # The SAVEPOINT rollback keeps the outer transaction usable; treat
        # this as a repeat completion and apply best-score-wins, no XP.
        existing = await session.scalar(
            select(LessonCompletion).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.lesson_id == lesson.id,
            )
        )
        if existing is not None and score is not None and (
            existing.score is None or score > existing.score
        ):
            existing.score = score
            existing.completed_at = datetime.now(UTC)
        return 0, True, False

    goal = record_xp(progress, lesson.xp_reward, today=today_local)
    record_daily_activity(progress, today_local)
    return lesson.xp_reward, False, goal.goal_met_now
