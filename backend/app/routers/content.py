import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.time import today_utc
from app.models.content import Lesson, LessonCompletion, LessonView, Level, LevelMastery, Module
from app.models.market import Market
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
    OfflineBundleOut,
    RewardGrantOut,
)
from app.services import offline_bundle_service, product_analytics_service
from app.services.age_tier import age_in_years
from app.services.content_localize import (
    language_active,
    load_translations,
    localize_fields,
)
from app.services.content_serialize import (
    serialize_lesson,
    serialize_lesson_summaries,
    serialize_levels,
    serialize_modules,
)
from app.services.content_service import (
    compute_streak_milestone,
    derive_lesson_title,
    get_accessible_module,
    grant_module_completion_cash,
    record_daily_activity,
)
from app.services.entitlements import is_premium, market_locked_for
from app.services.event_service import boosted_xp, get_active_event
from app.services.gamification_service import (
    evaluate_and_award_badges,
    update_challenge_progress,
)
from app.services.market_progress_service import (
    award_xp,
    grant_market_completion_reward,
)
from app.services.mastery_service import record_mastery_if_earned
from app.services.next_lesson_service import resolve_next_lesson
from app.services.premium_config import premium_required_error
from app.services.skill_profile_service import (
    record_concept_attempt,
    record_weak_concept,
    reinforce_concept,
    update_mastery_on_completion,
)

router = APIRouter(tags=["content"])


async def _get_accessible_module(
    module_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> Module:
    return await get_accessible_module(session, module_id, current_user)


@router.get("/next-lesson", response_model=NextLessonEnvelope)
async def get_next_lesson(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return NextLessonEnvelope(next=await resolve_next_lesson(session, current_user))


def _parse_iso(value: str) -> datetime | None:
    """Tolerant ISO8601 parse for the `since` cursor. None on blank/invalid input."""
    value = value.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


@router.get("/offline-bundle", response_model=OfflineBundleOut)
async def offline_bundle(
    since: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """One-shot offline-sync snapshot for the user's active market (Task 2).

    `since` (ISO8601, the previous response's `server_time`) deltas the `lessons`
    list; blank/invalid → full set. Metadata + `current_ids` are always full.
    """
    parsed = _parse_iso(since) if since else None
    return await offline_bundle_service.build_bundle(session, current_user, parsed)


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(Module).where(Module.published.is_(True)).order_by(Module.order_index))
    modules = result.all()
    user_age = age_in_years(current_user.dob, today_utc())

    lang = current_user.language
    active = await language_active(session, lang)
    module_translations = (
        await load_translations(session, "module", [m.id for m in modules], lang)
        if active else {}
    )

    out = serialize_modules(
        current_user, list(modules), user_age=user_age,
        translations_active=active, module_translations=module_translations,
    )
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

    lang = current_user.language
    active = await language_active(session, lang)
    lesson_translations = (
        await load_translations(session, "lesson", [lesson.id for lesson in lessons], lang)
        if active else {}
    )

    summaries: list[LessonSummary] = []
    for lesson in lessons:
        content_json = lesson.content_json or {}
        machine_translated = False
        if active:
            content_json, machine_translated = localize_fields(
                "lesson", content_json, lesson_translations.get(lesson.id)
            )
        summaries.append(LessonSummary(
            id=lesson.id,
            type=lesson.type,
            title=derive_lesson_title(lesson.type, content_json),
            xp_reward=lesson.xp_reward,
            order_index=lesson.order_index,
            completed=lesson.id in completed_ids,
            machine_translated=machine_translated,
        ))
    return summaries


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

    mastered_at_by_level: dict = {}
    if levels:
        mastery_rows = (await session.execute(
            select(LevelMastery.level_id, LevelMastery.mastered_at).where(
                LevelMastery.user_id == current_user.id,
                LevelMastery.level_id.in_([lv.id for lv in levels]),
            )
        )).all()
        mastered_at_by_level = dict(mastery_rows)
    return serialize_levels(
        current_user, levels,
        lessons_by_level=lessons_by_level, completed_ids=completed_ids, scores=scores,
        mastered_at_by_level=mastered_at_by_level,
    )


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
    lang = current_user.language
    active = await language_active(session, lang)
    lesson_translations = (
        await load_translations(session, "lesson", [lsn.id for lsn in lessons], lang)
        if active else {}
    )

    return serialize_lesson_summaries(
        lessons, completed_ids=completed_ids,
        translations_active=active, lesson_translations=lesson_translations,
    )


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

    lang = current_user.language
    active = await language_active(session, lang)
    translation = None
    if active:
        translations = await load_translations(session, "lesson", [lesson.id], lang)
        translation = translations.get(lesson.id)

    return serialize_lesson(
        lesson, completed=completed is not None,
        translations_active=active, translation=translation,
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
    await _get_accessible_module(lesson.module_id, current_user, session)  # gate
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

    # Multi-market premium gate: a free user may progress in only one market.
    # The first-ever completion claims their started market; thereafter a locked
    # (different-market) completion 403s BEFORE any award / side-effect.
    if current_user.started_market_code is None:
        current_user.started_market_code = module.market_code
    elif market_locked_for(current_user, module.market_code):
        market = await session.get(Market, module.market_code)
        raise premium_required_error("market", market.name if market else module.market_code)

    # Capture scalar attributes early before session expires ORM objects
    topic = module.topic
    module_id = module.id
    lesson_type = lesson.type
    lesson_level_id = lesson.level_id
    lesson_concept_id = lesson.concept_id
    lesson_content = lesson.content_json or {}
    is_quiz = lesson_type in ("quiz", "scenario")

    progress = await session.get(UserProgress, current_user.id)
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()

    today = today_utc()
    event = await get_active_event(session)
    prev_streak = progress.streak_count
    xp_awarded, already, daily_goal_met, granted_collectables = await _award_completion(
        session, current_user.id, progress, lesson, payload.score, today,
        amount=boosted_xp(lesson.xp_reward, event),
    )
    streak_milestone_reached = compute_streak_milestone(
        prev_streak, progress.streak_count, already=already
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

    level_mastered = False
    if lesson_level_id is not None:
        mastery = await record_mastery_if_earned(session, current_user.id, lesson_level_id)
        level_mastered = mastery is not None

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

        if is_quiz and correct is not None and lesson_concept_id is not None:
            await record_concept_attempt(
                session, current_user.id, lesson_concept_id, correct=correct,
            )

        if is_quiz and correct is False:
            concept = derive_lesson_title(lesson_type, lesson_content)
            await record_weak_concept(session, current_user.id, topic, concept,
                                       market_code=current_user.active_market_code)
        elif is_quiz and correct is True:
            concept = derive_lesson_title(lesson_type, lesson_content)
            await reinforce_concept(session, current_user.id, topic, concept,
                                    market_code=current_user.active_market_code)

    await grant_module_completion_cash(session, current_user.id, lesson.module_id)

    reward = RewardGrantOut()
    if not already:
        grant = await grant_market_completion_reward(
            session, current_user, current_user.active_market_code
        )
        reward = RewardGrantOut(
            coins=grant.coins, badge_name=grant.badge_name, badge_icon=grant.badge_icon
        )

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
        streak_milestone_reached=streak_milestone_reached,
        level_mastered=level_mastered,
        reward=reward,
        granted_collectables=granted_collectables,
    )


async def _award_completion(
    session: AsyncSession,
    user_id,
    progress: UserProgress,
    lesson: Lesson,
    score: float | None,
    today_local,
    *,
    amount: int | None = None,
) -> tuple[int, bool, bool, list[str]]:
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
        return 0, True, False, []

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
        return 0, True, False, []

    awarded = amount if amount is not None else lesson.xp_reward
    # Update streak BEFORE award_xp so grant_eligible (called inside award_xp)
    # sees the post-completion streak_count when evaluating streak_days drops.
    record_daily_activity(progress, today_local)
    goal = await award_xp(session, progress, awarded, today=today_local)
    return awarded, False, goal.goal_met_now, goal.granted_collectables


@router.get("/events/active")
async def active_event(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """The currently running seasonal event, if any (M9)."""
    return {"event": await get_active_event(session)}
