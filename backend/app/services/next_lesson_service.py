from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.schemas.content import NextLessonOut
from app.services.content_service import (
    content_region_for,
    derive_lesson_title,
    is_module_accessible,
)
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, derive_level_states


async def resolve_next_lesson(session: AsyncSession, user: Any) -> NextLessonOut | None:
    """Return the user's next actionable lesson across all accessible modules,
    or None when genuinely caught up. Reuses derive_level_states so locking and
    completion match the level screens exactly."""
    modules = list(await session.scalars(select(Module).order_by(Module.order_index)))
    for m in modules:
        if not is_module_accessible(
            content_region_for(user), is_premium(user), m.country_codes, m.is_premium
        ):
            continue

        levels = list(await session.scalars(
            select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
        ))
        if not levels:
            continue

        lessons = list(await session.scalars(
            select(Lesson).where(Lesson.module_id == m.id)
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
                    LessonCompletion.user_id == user.id,
                    LessonCompletion.lesson_id.in_(all_lesson_ids),
                )
            )).all()
            for lid, score in rows:
                completed_ids.add(lid)
                scores[lid] = score

        states = derive_level_states(
            [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
            lessons_by_level=lessons_by_level,
            completed_ids=completed_ids, scores=scores,
            user_is_premium=is_premium(user),
        )
        module_has_completion = any(lid in completed_ids for lid in all_lesson_ids)

        for lv in sorted(levels, key=lambda x: x.order_index):
            st = states[lv.id]
            if st.state == "locked" or st.lessons_completed >= st.lessons_total:
                continue
            level_lessons = sorted(
                [lsn for lsn in lessons if lsn.level_id == lv.id],
                key=lambda x: x.order_index,
            )
            target = next((lsn for lsn in level_lessons if lsn.id not in completed_ids), None)
            if target is None:
                continue
            return NextLessonOut(
                module_id=m.id, module_title=m.title, module_icon=m.icon,
                level_id=lv.id, lesson_id=target.id,
                lesson_title=derive_lesson_title(target.type, target.content_json or {}),
                mode="continue" if module_has_completion else "start",
            )
    return None
