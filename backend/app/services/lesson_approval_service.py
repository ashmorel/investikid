from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level
from app.models.lesson_draft import LessonDraft


async def approve_level_drafts(session: AsyncSession, level: Level, *, replace: bool) -> dict:
    """Approve all moderation-safe drafts for `level` into Lessons in one
    transaction. When `replace`, the level's existing Lessons are deleted before
    the new ones are inserted — but only if there is at least one safe draft to
    replace them with, so an empty draft set never empties a published level.
    Unsafe drafts are skipped (counted in `skipped_unsafe`), not an error — unlike
    the single-draft approve endpoint which 409s on an unsafe draft."""
    drafts = (await session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level.id)
    )).all()
    safe = [d for d in drafts if d.moderation_safe]
    skipped_unsafe = len(drafts) - len(safe)
    if not safe:
        return {"approved": 0, "replaced": 0, "skipped_unsafe": skipped_unsafe}

    replaced = 0
    if replace:
        existing = (await session.scalars(
            select(Lesson).where(Lesson.level_id == level.id)
        )).all()
        for lesson in existing:
            await session.delete(lesson)
        replaced = len(existing)
        await session.flush()

    base = (await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == level.id)
    )) or 0
    for i, d in enumerate(safe, start=1):
        session.add(Lesson(
            module_id=level.module_id, level_id=level.id, type=d.type,
            content_json=d.content_json, xp_reward=10, order_index=base + i,
        ))
        await session.delete(d)
    await session.commit()
    return {"approved": len(safe), "replaced": replaced, "skipped_unsafe": skipped_unsafe}
