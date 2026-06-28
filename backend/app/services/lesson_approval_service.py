from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.concept_mapper import resolve_concept_slug

logger = logging.getLogger(__name__)


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

    # Resolve concept slugs to concept ids. Load the module topic once.
    module = await session.get(Module, level.module_id)
    topic = module.topic if module is not None else ""

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
        concept_id = None
        if d.concept_slug:
            concept_id = await resolve_concept_slug(session, d.concept_slug, topic)
            if concept_id is None:
                logger.info("concept_unmapped topic=%s slug=%s", topic, d.concept_slug)
        session.add(Lesson(
            module_id=level.module_id, level_id=level.id, type=d.type,
            content_json=d.content_json, xp_reward=10, order_index=base + i,
            concept_id=concept_id,
        ))
        await session.delete(d)
    await session.commit()
    return {"approved": len(safe), "replaced": replaced, "skipped_unsafe": skipped_unsafe}
