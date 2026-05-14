import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery, WeakConcept
from app.models.user import User
from app.services.content_service import is_module_accessible


TOPIC_PREREQUISITES: dict[str, list[str]] = {
    "stocks": [],
    "savings": [],
    "budgeting": [],
    "risk": ["stocks"],
    "real_estate": ["stocks"],
    "crypto": ["stocks", "risk"],
    "taxes": ["budgeting"],
    "debt": ["budgeting"],
    "entrepreneurship": ["budgeting"],
}

_WEIGHT_READINESS = 0.4
_WEIGHT_WEAKNESS = 0.3
_WEIGHT_FRESHNESS = 0.2
_WEIGHT_COMPLETION = 0.1

_MASTERY_THRESHOLD = 0.5  # prerequisite considered "met" at this score
_FRESHNESS_CAP_DAYS = 30


async def get_recommendations(
    session: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Return personalised module rankings and a next-quest suggestion."""
    # Load all accessible modules
    all_modules = (
        await session.scalars(select(Module).order_by(Module.order_index))
    ).all()
    modules = [
        m for m in all_modules
        if is_module_accessible(user.country_code, user.is_premium, m.country_codes, m.is_premium)
    ]

    if not modules:
        return {"next_quest": None, "suggested_modules": []}

    # Load user's mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    ).all()
    mastery_by_topic: dict[str, TopicMastery] = {tm.topic: tm for tm in mastery_rows}

    # Load unresolved weak concepts grouped by topic
    weak_rows = (
        await session.scalars(
            select(WeakConcept).where(
                WeakConcept.user_id == user.id,
                WeakConcept.resolved == False,  # noqa: E712
            )
        )
    ).all()
    weak_by_topic: dict[str, list[WeakConcept]] = {}
    for wc in weak_rows:
        weak_by_topic.setdefault(wc.topic, []).append(wc)

    # Load completion counts per module
    module_ids = [m.id for m in modules]
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

    now = datetime.now(timezone.utc)
    scored: list[dict[str, Any]] = []

    for m in modules:
        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)

        # --- Readiness score ---
        prereqs = TOPIC_PREREQUISITES.get(m.topic, [])
        if not prereqs:
            readiness = 1.0
        else:
            met = sum(
                1 for p in prereqs
                if mastery_by_topic.get(p) and mastery_by_topic[p].mastery_score >= _MASTERY_THRESHOLD
            )
            readiness = met / len(prereqs)

        # --- Weakness score ---
        weak_count = len(weak_by_topic.get(m.topic, []))
        weakness = min(weak_count / 3.0, 1.0)  # cap at 3 weak concepts

        # --- Freshness score ---
        mastery = mastery_by_topic.get(m.topic)
        if mastery:
            days_since = (now - mastery.last_activity_at).days
            freshness = min(days_since / _FRESHNESS_CAP_DAYS, 1.0)
        else:
            freshness = 1.0  # never touched = very fresh

        # --- Completion score ---
        if total == 0:
            completion = 0.5
        elif completed == 0:
            completion = 0.5  # untouched
        elif completed < total:
            completion = 0.8  # in progress (momentum)
        else:
            completion = 0.1  # fully done

        score = (
            _WEIGHT_READINESS * readiness
            + _WEIGHT_WEAKNESS * weakness
            + _WEIGHT_FRESHNESS * freshness
            + _WEIGHT_COMPLETION * completion
        )

        # Build reason string
        reason = _build_reason(m, readiness, weakness, completed, total)

        scored.append({
            "module_id": m.id,
            "score": round(score, 4),
            "reason": reason,
            "topic": m.topic,
            "_completed_count": completed,
            "_total_count": total,
        })

    # Sort by score descending, then order_index for ties
    scored.sort(key=lambda s: (-s["score"], modules[[m.id for m in modules].index(s["module_id"])].order_index))

    # Find next quest: first incomplete lesson in the top-ranked module
    next_quest = None
    for entry in scored:
        if entry["_completed_count"] >= entry["_total_count"] and entry["_total_count"] > 0:
            continue  # skip fully complete modules
        lessons = (
            await session.scalars(
                select(Lesson)
                .where(Lesson.module_id == entry["module_id"])
                .order_by(Lesson.order_index)
            )
        ).all()
        completed_ids_result = await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user.id,
                LessonCompletion.lesson_id.in_([l.id for l in lessons]),
            )
        )
        completed_ids = set(completed_ids_result.all())
        for lesson in lessons:
            if lesson.id not in completed_ids:
                next_quest = {
                    "module_id": entry["module_id"],
                    "lesson_id": lesson.id,
                    "reason": entry["reason"],
                }
                break
        if next_quest:
            break

    suggested = [
        {"module_id": s["module_id"], "score": s["score"], "reason": s["reason"]}
        for s in scored
    ]

    return {"next_quest": next_quest, "suggested_modules": suggested}


def _build_reason(
    module: Module,
    readiness: float,
    weakness: float,
    completed: int,
    total: int,
) -> str:
    if completed > 0 and completed < total:
        return f"Continue where you left off in {module.title}"
    if weakness > 0:
        return f"Practice your weak spots in {module.topic.replace('_', ' ')}"
    if readiness >= 1.0:
        return f"You're ready for {module.title}"
    if readiness > 0:
        return f"Almost ready for {module.title} — keep building foundations"
    return f"New topic: {module.title}"
