"""SM-2 lite spaced repetition scheduling for children's weak concepts."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import SpacedRepetitionItem, WeakConcept

_EASE_FLOOR = 1.3
_DEFAULT_EASE = 2.5


def calculate_next_review(
    *,
    ease_factor: float,
    interval_days: int,
    repetition_count: int,
    quality: int,
) -> tuple[float, int, int]:
    """Pure SM-2 lite math. Returns (new_ease, new_interval, new_rep_count).

    quality: 4 = correct, 1 = wrong (binary, derived from quiz result).
    """
    if quality >= 3:
        # Correct answer
        if repetition_count == 0:
            new_interval = 1
        elif repetition_count == 1:
            new_interval = 3
        else:
            new_interval = round(interval_days * ease_factor)
        new_rep = repetition_count + 1
        new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    else:
        # Wrong answer — reset
        new_interval = 1
        new_rep = 0
        new_ease = ease_factor - 0.2

    new_ease = max(new_ease, _EASE_FLOOR)
    return new_ease, new_interval, new_rep


async def get_due_items(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[SpacedRepetitionItem]:
    """Return SR items that are due for review (next_review_at <= now) and not resolved."""
    now = datetime.now(UTC)
    result = await session.scalars(
        select(SpacedRepetitionItem)
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= now,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return list(result.all())


async def get_due_count(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Count of SR items due for review."""
    now = datetime.now(UTC)
    count = await session.scalar(
        select(func.count(SpacedRepetitionItem.id))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= now,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return int(count or 0)


async def get_next_due_at(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> datetime | None:
    """Earliest next_review_at for unresolved items (may be in the future)."""
    result = await session.scalar(
        select(func.min(SpacedRepetitionItem.next_review_at))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return result


async def record_review(
    session: AsyncSession,
    user_id: uuid.UUID,
    weak_concept_id: uuid.UUID,
    *,
    correct: bool,
) -> None:
    """Upsert SR item with new schedule after a quiz interaction."""
    now = datetime.now(UTC)
    quality = 4 if correct else 1

    # Try to find existing item
    item = await session.scalar(
        select(SpacedRepetitionItem).where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.weak_concept_id == weak_concept_id,
        )
    )

    if item is None:
        # First encounter — create with defaults
        new_ease, new_interval, new_rep = calculate_next_review(
            ease_factor=_DEFAULT_EASE,
            interval_days=1,
            repetition_count=0,
            quality=quality,
        )
        item = SpacedRepetitionItem(
            user_id=user_id,
            weak_concept_id=weak_concept_id,
            ease_factor=new_ease,
            interval_days=new_interval,
            repetition_count=new_rep,
            next_review_at=now + timedelta(days=new_interval),
            last_reviewed_at=now,
            created_at=now,
        )
        session.add(item)
    else:
        # Update existing
        new_ease, new_interval, new_rep = calculate_next_review(
            ease_factor=item.ease_factor,
            interval_days=item.interval_days,
            repetition_count=item.repetition_count,
            quality=quality,
        )
        item.ease_factor = new_ease
        item.interval_days = new_interval
        item.repetition_count = new_rep
        item.next_review_at = now + timedelta(days=new_interval)
        item.last_reviewed_at = now

    await session.flush()
