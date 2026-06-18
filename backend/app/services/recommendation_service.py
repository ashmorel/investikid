import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.age_tier import age_in_years
from app.services.content_service import is_module_in_market
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, first_actionable_lesson

# Scoring weights
_WEIGHT_TOPIC_MATCH = 0.30
_WEIGHT_READINESS = 0.25
_WEIGHT_NEAR_COMPLETION = 0.20
_WEIGHT_NATURAL_ORDER = 0.15
_WEIGHT_TOPIC_VARIETY = 0.10

_READINESS_THRESHOLD = 0.7  # avg prerequisite score required to be "ready"
_MAX_ORDER_INDEX = 100  # normalisation ceiling for order_index


def _calculate_age(dob: date, today: date | None = None) -> int:
    """Calculate age from date of birth (delegates to the shared age_tier helper)."""
    if today is None:
        today = datetime.now(UTC).date()
    return age_in_years(dob, today)


def _apply_hard_filters(
    module: Any,
    user: Any,
    fully_completed_module_ids: set,
    completed_module_ids_for_prereqs: set,
    user_age: int,
) -> bool:
    """Return True if module passes all hard filters (should be included)."""
    # 1. Already fully completed
    if module.id in fully_completed_module_ids:
        return False

    # 2. Prerequisites not met — any prerequisite module has uncompleted lessons
    for prereq_id in module.prerequisite_ids:
        if prereq_id not in completed_module_ids_for_prereqs:
            return False

    # 3. Age out of range
    if module.min_age is not None and user_age < module.min_age:
        return False
    if module.max_age is not None and user_age > module.max_age:
        return False

    # 4. Premium gating
    if module.is_premium and not user.is_premium:
        return False

    # 5. Market filtering
    if not is_module_in_market(module.market_code, user.active_market_code):
        return False

    return True


def _score_module(
    module: Any,
    user: Any,
    completed_count: int,
    total_count: int,
    mastery_by_topic: dict,
) -> dict:
    """Score a module. Returns dict with 'score', 'is_topic_match', 'near_completion', 'variety', 'readiness'."""
    # --- Topic match (30%) ---
    is_topic_match = bool(user.topic_path and module.topic == user.topic_path)
    topic_match_score = 1.0 if is_topic_match else 0.0

    # --- Readiness (25%) — all prerequisites completed with avg mastery >= 0.7 ---
    mastery = mastery_by_topic.get(module.topic)
    readiness_score = mastery.mastery_score if mastery else 0.0
    # Readiness is high if current topic mastery is above threshold
    readiness = 1.0 if readiness_score >= _READINESS_THRESHOLD else readiness_score / _READINESS_THRESHOLD

    # --- Near completion (20%) — scales with % complete ---
    near_completion = False
    if total_count > 0 and 0 < completed_count < total_count:
        near_completion = True
        near_completion_score = completed_count / total_count
    else:
        near_completion_score = 0.0

    # --- Natural order (15%) — lower order_index within same topic scores higher ---
    order_score = 1.0 - min(module.order_index / _MAX_ORDER_INDEX, 1.0)

    # --- Topic variety (10%) — bonus if user hasn't touched this topic recently ---
    variety = mastery is None  # never touched = fresh variety
    variety_score = 1.0 if variety else 0.0

    score = (
        _WEIGHT_TOPIC_MATCH * topic_match_score
        + _WEIGHT_READINESS * readiness
        + _WEIGHT_NEAR_COMPLETION * near_completion_score
        + _WEIGHT_NATURAL_ORDER * order_score
        + _WEIGHT_TOPIC_VARIETY * variety_score
    )

    return {
        "score": round(score, 4),
        "is_topic_match": is_topic_match,
        "near_completion": near_completion,
        "variety": variety,
        "readiness": readiness_score,
    }


def _build_reason(
    module: Any,
    *,
    completed: int,
    total: int,
    is_topic_match: bool,
    is_variety: bool,
    readiness_score: float,
) -> str:
    """Build child-friendly reason string."""
    if completed > 0 and completed < total:
        return "You're halfway through — keep going!"
    if is_topic_match:
        return f"You're great at {module.topic.replace('_', ' ')} — try this next!"
    if is_variety:
        return "Something new to explore!"
    if readiness_score >= _READINESS_THRESHOLD:
        return "You're ready for the next level!"
    return "Recommended for you"


_MAX_PER_CATEGORY = 2


def _categorise_scored_modules(
    scored: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Split scored modules into three categories. Pure function, no DB access.

    Priority: partial completion → continue_learning (even if has due SR).
    Completed with due SR → practise_again.
    Untouched (0 completed) → something_new.
    """
    continue_learning: list[dict[str, Any]] = []
    practise_again: list[dict[str, Any]] = []
    something_new: list[dict[str, Any]] = []

    for entry in scored:
        completed = entry["_completed_count"]
        total = entry["_total_count"]
        has_due = entry.get("_has_due_sr", False)
        weak = entry.get("_weak_concepts", [])

        item: dict[str, Any] = {
            "module_id": entry["module_id"],
            "lesson_id": entry.get("_lesson_id"),
            "level_id": entry.get("_level_id"),
            "level_title": entry.get("_level_title"),
            "score": entry["score"],
            "reason": entry["reason"],
            "review_prompt": None,
            "weak_concepts": [],
        }

        if 0 < completed < total:
            # Partial completion takes priority
            continue_learning.append(item)
        elif has_due and weak:
            # Completed module with due SR items
            item["weak_concepts"] = weak
            item["review_prompt"] = f"{len(weak)} concept{'s' if len(weak) != 1 else ''} to review"
            practise_again.append(item)
        else:
            # Untouched
            something_new.append(item)

    # Sort each category by score descending and cap at max
    continue_learning.sort(key=lambda x: -x["score"])
    practise_again.sort(key=lambda x: -x["score"])
    something_new.sort(key=lambda x: -x["score"])

    return {
        "continue_learning": continue_learning[:_MAX_PER_CATEGORY],
        "practise_again": practise_again[:_MAX_PER_CATEGORY],
        "something_new": something_new[:_MAX_PER_CATEGORY],
    }


async def get_recommendations(
    session: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Return personalised categorised module recommendations."""
    from app.services.spaced_repetition_service import (
        get_due_count,
        get_due_items,
        get_next_due_at,
    )

    empty_result = {
        "continue_learning": [],
        "practise_again": [],
        "something_new": [],
        "review_summary": {"due_count": 0, "next_due_at": None},
    }

    if not user.profiling_enabled:
        seed = await _topic_path_seed(session, user)
        if seed:
            return {
                "continue_learning": [],
                "practise_again": [],
                "something_new": [{
                    "module_id": seed["module_id"],
                    "lesson_id": seed["lesson_id"],
                    "level_id": seed.get("level_id"),
                    "level_title": seed.get("level_title"),
                    "score": 0.0,
                    "reason": seed["reason"],
                    "review_prompt": None,
                    "weak_concepts": [],
                }],
                "review_summary": {"due_count": 0, "next_due_at": None},
            }
        return empty_result

    # Load all modules ordered by order_index
    all_modules = (
        await session.scalars(select(Module).order_by(Module.order_index))
    ).all()

    if not all_modules:
        return empty_result

    module_ids = [m.id for m in all_modules]

    # Load completion counts per module
    lesson_counts_result = await session.execute(
        select(Lesson.module_id, func.count(Lesson.id))
        .where(Lesson.module_id.in_(module_ids))
        .group_by(Lesson.module_id)
    )
    total_lessons: dict[uuid.UUID, int] = dict(lesson_counts_result.all())

    completed_counts_result = await session.execute(
        select(Lesson.module_id, func.count(LessonCompletion.id))
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(Lesson.module_id.in_(module_ids), LessonCompletion.user_id == user.id)
        .group_by(Lesson.module_id)
    )
    completed_lessons: dict[uuid.UUID, int] = dict(completed_counts_result.all())

    # Build sets for hard filtering
    fully_completed_module_ids: set[uuid.UUID] = {
        mid for mid in module_ids
        if total_lessons.get(mid, 0) > 0 and completed_lessons.get(mid, 0) >= total_lessons.get(mid, 0)
    }
    completed_module_ids_for_prereqs: set[uuid.UUID] = fully_completed_module_ids.copy()

    # Calculate user age
    user_age = _calculate_age(user.dob) if user.dob else 0

    # Load mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    ).all()
    mastery_by_topic: dict[str, TopicMastery] = {tm.topic: tm for tm in mastery_rows}

    # Load due SR items to identify topics with due reviews
    due_items = await get_due_items(session, user.id, market_code=user.active_market_code)
    # Map: topic -> list of weak concept names that are due
    from app.models.skill_profile import WeakConcept as WC
    due_concept_ids = {item.weak_concept_id for item in due_items}
    due_concepts_by_topic: dict[str, list[str]] = {}
    if due_concept_ids:
        concepts = (
            await session.scalars(
                select(WC).where(
                    WC.id.in_(due_concept_ids),
                    WC.market_code == user.active_market_code,
                )
            )
        ).all()
        for c in concepts:
            due_concepts_by_topic.setdefault(c.topic, []).append(c.concept)

    # Filter, score, and find first incomplete lesson per module
    scored: list[dict[str, Any]] = []

    for m in all_modules:
        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)

        # For practise_again: include fully completed modules with due SR items
        has_due_sr = m.topic in due_concepts_by_topic
        is_fully_completed = m.id in fully_completed_module_ids

        # Apply hard filters (skip completed unless they have due SR items)
        if is_fully_completed and not has_due_sr:
            continue
        if not is_fully_completed and not _apply_hard_filters(
            m, user, fully_completed_module_ids, completed_module_ids_for_prereqs, user_age
        ):
            continue

        # Score the module
        score_result = _score_module(m, user, completed, total, mastery_by_topic)

        # Build reason string
        reason = _build_reason(
            m,
            completed=completed,
            total=total,
            is_topic_match=score_result["is_topic_match"],
            is_variety=score_result["variety"],
            readiness_score=score_result["readiness"],
        )

        # Find the next actionable lesson (level-aware when the module has levels)
        lesson_id = None
        level_id = None
        level_title = None
        if not is_fully_completed:
            lessons = (
                await session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == m.id)
                    .order_by(Lesson.order_index)
                )
            ).all()
            lesson_ids = [lsn.id for lsn in lessons]
            comp_rows = (
                await session.execute(
                    select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                        LessonCompletion.user_id == user.id,
                        LessonCompletion.lesson_id.in_(lesson_ids),
                    )
                )
            ).all()
            completed_ids = {lid for lid, _ in comp_rows}
            scores = {lid: score for lid, score in comp_rows}

            levels = (
                await session.scalars(
                    select(Level)
                    .where(Level.module_id == m.id)
                    .order_by(Level.order_index)
                )
            ).all()

            if levels:
                lessons_by_level_ordered: dict[uuid.UUID, list[uuid.UUID]] = {}
                for lsn in lessons:  # already ordered by order_index
                    if lsn.level_id is not None:
                        lessons_by_level_ordered.setdefault(lsn.level_id, []).append(lsn.id)
                pointer = first_actionable_lesson(
                    [
                        LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold)
                        for lv in levels
                    ],
                    lessons_by_level_ordered=lessons_by_level_ordered,
                    completed_ids=completed_ids,
                    scores=scores,
                    user_is_premium=is_premium(user),
                )
                if pointer is not None:
                    level_id, lesson_id = pointer
                    level_title = {lv.id: lv.title for lv in levels}.get(level_id)
            else:
                # Unlevelled module — first incomplete lesson (legacy behaviour)
                for lesson in lessons:
                    if lesson.id not in completed_ids:
                        lesson_id = lesson.id
                        break

        scored.append({
            "module_id": m.id,
            "score": score_result["score"],
            "reason": reason,
            "topic": m.topic,
            "_completed_count": completed,
            "_total_count": total,
            "_order_index": m.order_index,
            "_lesson_id": lesson_id,
            "_level_id": level_id,
            "_level_title": level_title,
            "_has_due_sr": has_due_sr,
            "_weak_concepts": due_concepts_by_topic.get(m.topic, []),
        })

    if not scored:
        return empty_result

    # Sort by score descending, then order_index for ties
    scored.sort(key=lambda s: (-s["score"], s["_order_index"]))

    # Categorise
    categories = _categorise_scored_modules(scored)

    # Build review summary
    due_count = await get_due_count(session, user.id, market_code=user.active_market_code)
    next_due = await get_next_due_at(session, user.id, market_code=user.active_market_code)

    return {
        "continue_learning": categories["continue_learning"],
        "practise_again": categories["practise_again"],
        "something_new": categories["something_new"],
        "review_summary": {
            "due_count": due_count,
            "next_due_at": next_due.isoformat() if next_due else None,
        },
    }


async def _topic_path_seed(session: AsyncSession, user: User):
    """Profiling-off only: first incomplete lesson in the self-declared topic, for a brand-new learner."""
    pref = user.topic_path
    if not pref:
        return None

    completion_count = int(
        await session.scalar(
            select(func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == user.id
            )
        )
        or 0
    )
    if completion_count > 0:
        return None

    modules = (
        await session.scalars(
            select(Module).where(Module.topic == pref).order_by(Module.order_index)
        )
    ).all()
    for m in modules:
        # Basic accessibility check: premium and country
        if m.is_premium and not is_premium(user):
            continue
        if not is_module_in_market(m.market_code, user.active_market_code):
            continue
        lessons = (
            await session.scalars(
                select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order_index)
            )
        ).all()
        if not lessons:
            continue
        levels = (
            await session.scalars(
                select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
            )
        ).all()
        lesson_id = lessons[0].id
        level_id = None
        level_title = None
        if levels:
            lessons_by_level_ordered: dict = {}
            for lsn in lessons:
                if lsn.level_id is not None:
                    lessons_by_level_ordered.setdefault(lsn.level_id, []).append(lsn.id)
            pointer = first_actionable_lesson(
                [
                    LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold)
                    for lv in levels
                ],
                lessons_by_level_ordered=lessons_by_level_ordered,
                completed_ids=set(),
                scores={},
                user_is_premium=is_premium(user),
            )
            if pointer is not None:
                level_id, lesson_id = pointer
                level_title = {lv.id: lv.title for lv in levels}.get(level_id)
        return {
            "module_id": m.id,
            "lesson_id": lesson_id,
            "level_id": level_id,
            "level_title": level_title,
            "reason": f"Start your {pref.replace('_', ' ')} journey",
        }
    return None
