import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import TopicMastery, WeakConcept


async def update_mastery_on_completion(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    *,
    is_quiz: bool,
    correct: bool | None,
) -> None:
    """Update or create a TopicMastery row after a lesson completion.

    For quiz/scenario lessons, ``is_quiz=True`` and ``correct`` is True/False.
    For card/video lessons, ``is_quiz=False`` and ``correct`` is None — only
    the last_activity_at timestamp is updated.
    """
    mastery = await session.get(TopicMastery, (user_id, topic))
    now = datetime.now(UTC)

    if mastery is None:
        mastery = TopicMastery(
            user_id=user_id,
            topic=topic,
            mastery_score=0.0,
            quizzes_attempted=0,
            quizzes_correct=0,
            last_activity_at=now,
        )
        session.add(mastery)

    mastery.last_activity_at = now

    if is_quiz and correct is not None:
        mastery.quizzes_attempted += 1
        if correct:
            mastery.quizzes_correct += 1
        mastery.mastery_score = (
            mastery.quizzes_correct / mastery.quizzes_attempted
            if mastery.quizzes_attempted > 0
            else 0.0
        )


async def record_weak_concept(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
    market_code: str = "GB",
) -> None:
    """Record or increment a weak concept when a user gets a question wrong."""
    existing = await session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.topic == topic,
            WeakConcept.concept == concept,
            WeakConcept.market_code == market_code,
        )
    )
    if existing:
        existing.times_wrong += 1
        existing.resolved = False  # re-open if they struggle again
    else:
        session.add(
            WeakConcept(
                user_id=user_id,
                topic=topic,
                concept=concept,
                times_wrong=1,
                market_code=market_code,
            )
        )


async def reinforce_concept(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
    market_code: str = "GB",
) -> None:
    """Increment reinforcement count when user gets a previously-weak concept right.

    Scoped to the given market so a right answer in market X only updates the X row.
    """
    existing = await session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.topic == topic,
            WeakConcept.concept == concept,
            WeakConcept.resolved == False,  # noqa: E712
            WeakConcept.market_code == market_code,
        )
    )
    if existing:
        existing.times_reinforced += 1
        if existing.times_reinforced >= 2:
            existing.resolved = True


async def get_mastery_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Return the user's full mastery profile for the /profile/mastery endpoint."""
    topics_result = await session.scalars(
        select(TopicMastery).where(TopicMastery.user_id == user_id)
    )
    topics = [
        {
            "topic": tm.topic,
            "mastery_score": tm.mastery_score,
            "quizzes_attempted": tm.quizzes_attempted,
            "quizzes_correct": tm.quizzes_correct,
            "last_activity_at": tm.last_activity_at.isoformat(),
        }
        for tm in topics_result.all()
    ]

    weak_result = await session.scalars(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    weak = [
        {
            "topic": wc.topic,
            "concept": wc.concept,
            "times_wrong": wc.times_wrong,
            "times_reinforced": wc.times_reinforced,
        }
        for wc in weak_result.all()
    ]

    return {"topics": topics, "weak_concepts": weak}
