from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, LessonView, Level, Module
from app.services.content_service import derive_lesson_title


@dataclass(frozen=True)
class LessonInput:
    lesson_id: uuid.UUID
    type: str
    content_json: dict


@dataclass(frozen=True)
class LessonEngagement:
    lesson_id: uuid.UUID
    type: str
    label: str
    order: int
    views: int
    completions: int
    completion_rate: float | None
    average_score: float | None
    drop_off: int


@dataclass(frozen=True)
class ModuleEngagement:
    module_id: uuid.UUID
    learners_started: int
    learners_completed: int
    completion_rate: float | None
    average_score: float | None
    lessons: list[LessonEngagement]


def compute_module_engagement(
    module_id: uuid.UUID,
    lessons: list[LessonInput],
    viewers_by_lesson: dict[uuid.UUID, set[uuid.UUID]],
    completers_by_lesson: dict[uuid.UUID, set[uuid.UUID]],
    scores_by_lesson: dict[uuid.UUID, list[float]],
) -> ModuleEngagement:
    """Pure: compute per-lesson and module engagement from already-fetched sets.

    Completing a lesson implies having viewed it, so completers are unioned into
    viewers. drop_off is completers(prev) - completers(this), clamped at >= 0.
    A learner has 'completed the module' iff they completed every lesson.
    """
    lesson_out: list[LessonEngagement] = []
    started: set[uuid.UUID] = set()
    module_scores: list[float] = []
    completed_all: set[uuid.UUID] | None = None
    prev_completions: int | None = None

    for i, lsn in enumerate(lessons):
        completers = completers_by_lesson.get(lsn.lesson_id, set())
        viewers = viewers_by_lesson.get(lsn.lesson_id, set()) | completers
        scores = scores_by_lesson.get(lsn.lesson_id, [])
        views = len(viewers)
        completions = len(completers)
        rate = (completions / views) if views else None
        avg = (sum(scores) / len(scores)) if scores else None
        drop = 0 if prev_completions is None else max(0, prev_completions - completions)

        lesson_out.append(LessonEngagement(
            lesson_id=lsn.lesson_id, type=lsn.type,
            label=derive_lesson_title(lsn.type, lsn.content_json), order=i,
            views=views, completions=completions,
            completion_rate=rate, average_score=avg, drop_off=drop,
        ))

        started |= viewers
        module_scores.extend(scores)
        completed_all = completers if completed_all is None else (completed_all & completers)
        prev_completions = completions

    learners_started = len(started)
    learners_completed = len(completed_all) if completed_all is not None else 0
    completion_rate = (learners_completed / learners_started) if learners_started else None
    average_score = (sum(module_scores) / len(module_scores)) if module_scores else None

    return ModuleEngagement(
        module_id=module_id,
        learners_started=learners_started,
        learners_completed=learners_completed,
        completion_rate=completion_rate,
        average_score=average_score,
        lessons=lesson_out,
    )


async def get_module_engagement(
    session: AsyncSession, module_id: uuid.UUID
) -> ModuleEngagement | None:
    """Load views/completions for a module's lessons and aggregate them.
    Returns None if the module does not exist."""
    module = await session.get(Module, module_id)
    if module is None:
        return None

    rows = (await session.execute(
        select(Lesson)
        .outerjoin(Level, Lesson.level_id == Level.id)
        .where(Lesson.module_id == module_id)
        .order_by(Level.order_index.nulls_first(), Lesson.order_index)
    )).scalars().all()

    lessons = [LessonInput(lesson_id=r.id, type=r.type, content_json=r.content_json or {}) for r in rows]
    lesson_ids = [r.id for r in rows]

    viewers_by: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    completers_by: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    scores_by: dict[uuid.UUID, list[float]] = defaultdict(list)

    if lesson_ids:
        for lid, uid in (await session.execute(
            select(LessonView.lesson_id, LessonView.user_id).where(LessonView.lesson_id.in_(lesson_ids))
        )).all():
            viewers_by[lid].add(uid)
        for lid, uid, score in (await session.execute(
            select(LessonCompletion.lesson_id, LessonCompletion.user_id, LessonCompletion.score)
            .where(LessonCompletion.lesson_id.in_(lesson_ids))
        )).all():
            completers_by[lid].add(uid)
            if score is not None:
                scores_by[lid].append(score)

    return compute_module_engagement(module_id, lessons, viewers_by, completers_by, scores_by)
