import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import UserProgress
from app.schemas.parent import BadgeOut, ChildAnalyticsOut, RecentLessonOut
from app.services.content_service import derive_lesson_title

# XP thresholds per level — mirrors content_service._LEVEL_THRESHOLDS
_LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2500, 5000]


def _xp_to_next_level(level: int, xp: int) -> int:
    """XP remaining to reach the next level. 0 if already at max."""
    if level >= len(_LEVEL_THRESHOLDS):
        return 0
    return max(0, _LEVEL_THRESHOLDS[level] - xp)


async def build_child_analytics(
    session: AsyncSession,
    user_id: uuid.UUID,
    country_code: str,
) -> ChildAnalyticsOut:
    # 1. UserProgress
    progress = await session.scalar(
        select(UserProgress).where(UserProgress.user_id == user_id)
    )
    level = progress.level if progress else 1
    xp = progress.xp if progress else 0
    streak_count = progress.streak_count if progress else 0

    # 2. Lesson counts
    lessons_total = await session.scalar(
        select(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.country_codes.any(country_code)
            | (Module.country_codes == [])
        )
    ) or 0

    lessons_completed = await session.scalar(
        select(func.count(LessonCompletion.id))
        .where(LessonCompletion.user_id == user_id)
    ) or 0

    # 3. Recent lessons (last 5)
    recent_rows = (await session.execute(
        select(LessonCompletion, Lesson)
        .join(Lesson, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user_id)
        .order_by(LessonCompletion.completed_at.desc())
        .limit(5)
    )).all()

    recent_lessons = [
        RecentLessonOut(
            title=derive_lesson_title(lesson.type, lesson.content_json),
            type=lesson.type,
            score=completion.score,
            completed_at=completion.completed_at,
        )
        for completion, lesson in recent_rows
    ]

    # 4. Badges
    badge_rows = (await session.execute(
        select(UserBadge, Badge)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user_id)
        .order_by(UserBadge.earned_at.desc())
    )).all()

    badges = [
        BadgeOut(
            name=badge.name,
            icon=badge.icon_url,
            earned_at=ub.earned_at,
        )
        for ub, badge in badge_rows
    ]

    return ChildAnalyticsOut(
        level=level,
        xp=xp,
        xp_to_next_level=_xp_to_next_level(level, xp),
        streak_count=streak_count,
        lessons_completed=lessons_completed,
        lessons_total=lessons_total,
        recent_lessons=recent_lessons,
        badges=badges,
    )
