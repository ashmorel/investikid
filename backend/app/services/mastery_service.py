"""W3a — record immutable level-mastery rows when a user first passes a level."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Level, LevelMastery
from app.services.level_service import _complete_and_passed


async def record_mastery_if_earned(
    session: AsyncSession,
    user_id: uuid.UUID,
    level_id: uuid.UUID,
) -> LevelMastery | None:
    """Insert one immutable LevelMastery row the first time a user passes a level.

    Reuses level_service._complete_and_passed for the pass decision. Returns the
    new row, or None when the level is not yet passed, mastery was already
    recorded (rows are never updated — auditable), or a concurrent request won
    the insert race.
    """
    level = await session.get(Level, level_id)
    if level is None:
        return None

    lesson_ids = list(
        (await session.scalars(select(Lesson.id).where(Lesson.level_id == level_id))).all()
    )
    completed_ids: set[uuid.UUID] = set()
    scores: dict[uuid.UUID, float | None] = {}
    if lesson_ids:
        rows = (
            await session.execute(
                select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                    LessonCompletion.user_id == user_id,
                    LessonCompletion.lesson_id.in_(lesson_ids),
                )
            )
        ).all()
        completed_ids = {lid for lid, _ in rows}
        scores = {lid: score for lid, score in rows}

    _, passed, _ = _complete_and_passed(
        lesson_ids, completed_ids, scores, level.pass_threshold
    )
    if not passed:
        return None

    existing = await session.scalar(
        select(LevelMastery.id).where(
            LevelMastery.user_id == user_id, LevelMastery.level_id == level_id
        )
    )
    if existing is not None:
        return None  # immutable — never update an existing mastery row

    scored = [s for s in scores.values() if s is not None]
    score = sum(scored) / len(scored) if scored else level.pass_threshold
    mastery = LevelMastery(
        user_id=user_id, level_id=level_id,
        mastered_at=datetime.now(UTC), score=score,
    )
    try:
        async with session.begin_nested():
            session.add(mastery)
            await session.flush()
    except IntegrityError:
        # Lost a concurrent first-mastery race; the SAVEPOINT rollback keeps
        # the outer transaction usable.
        return None
    return mastery
