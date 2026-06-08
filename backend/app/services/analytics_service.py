import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import User, UserProgress
from app.schemas.parent import (
    BadgeOut,
    ChildAnalyticsOut,
    LevelProgressOut,
    ModuleProgressOut,
    RecentLessonOut,
)
from app.services.content_service import derive_lesson_title, is_module_accessible
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, derive_level_states

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

    # 5. Per-module / per-level progress (modules with levels only)
    child = await session.scalar(select(User).where(User.id == user_id))
    child_premium = is_premium(child) if child else False

    all_completions = (await session.execute(
        select(LessonCompletion.lesson_id, LessonCompletion.score)
        .where(LessonCompletion.user_id == user_id)
    )).all()
    completed_ids = {lid for lid, _ in all_completions}
    completion_scores = {lid: s for lid, s in all_completions}

    modules = list(await session.scalars(
        select(Module).order_by(Module.order_index)
    ))
    modules_progress: list[ModuleProgressOut] = []
    for m in modules:
        if not is_module_accessible(country_code, child_premium, m.country_codes, m.is_premium):
            continue
        levels = list(await session.scalars(
            select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
        ))
        if not levels:
            continue
        module_lessons = list(await session.scalars(
            select(Lesson).where(Lesson.module_id == m.id)
        ))
        lessons_by_level: dict[uuid.UUID, list[uuid.UUID]] = {}
        for lsn in module_lessons:
            if lsn.level_id is not None:
                lessons_by_level.setdefault(lsn.level_id, []).append(lsn.id)
        states = derive_level_states(
            [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
            lessons_by_level=lessons_by_level,
            completed_ids=completed_ids,
            scores=completion_scores,
            user_is_premium=child_premium,
        )
        level_outs: list[LevelProgressOut] = []
        m_completed = 0
        m_total = 0
        for lv in sorted(levels, key=lambda x: x.order_index):
            st = states[lv.id]
            m_completed += st.lessons_completed
            m_total += st.lessons_total
            level_outs.append(LevelProgressOut(
                level_id=lv.id, title=lv.title, state=st.state,
                locked_reason=st.locked_reason, passed=st.passed,
                lessons_completed=st.lessons_completed, lessons_total=st.lessons_total,
            ))
        modules_progress.append(ModuleProgressOut(
            module_id=m.id, title=m.title, icon=m.icon,
            lessons_completed=m_completed, lessons_total=m_total,
            levels=level_outs,
        ))

    return ChildAnalyticsOut(
        level=level,
        xp=xp,
        xp_to_next_level=_xp_to_next_level(level, xp),
        streak_count=streak_count,
        lessons_completed=lessons_completed,
        lessons_total=lessons_total,
        recent_lessons=recent_lessons,
        badges=badges,
        modules_progress=modules_progress,
    )
