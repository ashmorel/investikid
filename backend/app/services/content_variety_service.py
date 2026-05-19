from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.entitlements import is_premium

PREMIUM_POOL_SIZE = 3
FREE_POOL_SIZE = 1
_LOW_SCORE = 0.5
_HIGH_SCORE = 0.8
_MASTERY_THRESHOLD = 0.5

_RUNGS = ("easier", "core", "harder")


@dataclass(frozen=True)
class VariantSpec:
    rung: str
    ordinal: int
    pool_size: int

    @property
    def variant_key(self) -> str:
        return f"{self.rung}:{self.ordinal}"


async def _attempt_count(session: AsyncSession, user_id, lesson_id) -> int:
    return int(
        await session.scalar(
            select(func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.lesson_id == lesson_id,
            )
        )
        or 0
    )


async def _latest_completion_score(session: AsyncSession, user_id, lesson_id):
    return await session.scalar(
        select(LessonCompletion.score)
        .where(
            LessonCompletion.user_id == user_id,
            LessonCompletion.lesson_id == lesson_id,
        )
        .order_by(LessonCompletion.completed_at.desc())
        .limit(1)
    )


async def _topic_mastery(session: AsyncSession, user_id, topic) -> float:
    score = await session.scalar(
        select(TopicMastery.mastery_score).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic == topic,
        )
    )
    return float(score) if score is not None else 0.0


async def resolve_variant(
    session: AsyncSession,
    user: User,
    lesson: Lesson,
    concept: str,
) -> VariantSpec:
    """Decide which quiz variant this child gets. DB reads only; never mutates."""
    premium = is_premium(user)
    pool_size = PREMIUM_POOL_SIZE if premium else FREE_POOL_SIZE

    attempt_count = await _attempt_count(session, user.id, lesson.id)
    ordinal = attempt_count % pool_size

    # Free tier: laddering disabled, single core variant.
    if not premium:
        return VariantSpec(rung="core", ordinal=ordinal, pool_size=pool_size)

    # AADC: no behavioural inference unless profiling is explicitly enabled.
    if not user.profiling_enabled:
        return VariantSpec(rung="core", ordinal=ordinal, pool_size=pool_size)

    score = await _latest_completion_score(session, user.id, lesson.id)
    if score is None:
        rung = "core"
    elif score < _LOW_SCORE:
        rung = "easier"
    elif score >= _HIGH_SCORE:
        module = await session.get(Module, lesson.module_id)
        topic = module.topic if module else ""
        mastery = await _topic_mastery(session, user.id, topic)
        rung = "harder" if mastery >= _MASTERY_THRESHOLD else "core"
    else:
        rung = "core"

    return VariantSpec(rung=rung, ordinal=ordinal, pool_size=pool_size)
