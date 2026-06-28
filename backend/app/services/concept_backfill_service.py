"""One-off, idempotent backfill: map existing WeakConcept + published Lesson rows
to taxonomy concepts via ``resolve_concept_slug``.

Safe to run multiple times:
- Only rows with ``concept_id IS NULL`` are touched.
- Already-tagged rows (``concept_id IS NOT NULL``) are never modified.
- Unmatched rows are left with ``concept_id = NULL`` (no error).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Lesson, Module
from app.models.skill_profile import WeakConcept
from app.services.concept_mapper import resolve_concept_slug

logger = logging.getLogger(__name__)


def _lesson_text(lesson: Lesson) -> str | None:
    """Extract the best candidate text from a lesson's content_json.

    Mirrors the legacy path in ``_concept_of`` (revise_service):
    question → title → prompt.  Returns ``None`` when nothing useful found.
    """
    c = lesson.content_json or {}
    return c.get("question") or c.get("title") or c.get("prompt") or None


async def run_backfill(session: AsyncSession) -> dict[str, int]:
    """Backfill concept_id on WeakConcept and published Lesson rows.

    Returns a dict with:
        weak_concepts_total    — how many WeakConcept rows had concept_id NULL
        weak_concepts_matched  — how many were successfully linked
        lessons_total          — how many published Lesson rows had concept_id NULL
        lessons_matched        — how many were successfully linked
    """
    # ── WeakConcept backfill ─────────────────────────────────────────────────
    wc_rows = (
        await session.scalars(
            select(WeakConcept).where(WeakConcept.concept_id.is_(None))
        )
    ).all()

    wc_total = len(wc_rows)
    wc_matched = 0

    for wc in wc_rows:
        if not wc.concept or not wc.topic:
            continue
        concept_id = await resolve_concept_slug(session, wc.concept, wc.topic)
        if concept_id is not None:
            wc.concept_id = concept_id
            wc_matched += 1
            logger.info(
                "concept_backfill wc_matched weak_concept_id=%s concept=%r topic=%r concept_id=%s",
                wc.id, wc.concept, wc.topic, concept_id,
            )

    # ── Lesson backfill ──────────────────────────────────────────────────────
    # Load lessons that are published (module.published=True) with concept_id NULL.
    # We need module.topic for scoping, so eagerly load the module.
    lesson_rows = (
        await session.scalars(
            select(Lesson)
            .join(Lesson.module)
            .where(
                Lesson.concept_id.is_(None),
                Module.published.is_(True),
            )
            .options(selectinload(Lesson.module))
        )
    ).all()

    lesson_total = len(lesson_rows)
    lesson_matched = 0

    for lesson in lesson_rows:
        text = _lesson_text(lesson)
        topic = lesson.module.topic if lesson.module else None
        if not text or not topic:
            continue
        concept_id = await resolve_concept_slug(session, text, topic)
        if concept_id is not None:
            lesson.concept_id = concept_id
            lesson_matched += 1
            logger.info(
                "concept_backfill lesson_matched lesson_id=%s text=%r topic=%r concept_id=%s",
                lesson.id, text, topic, concept_id,
            )

    await session.flush()

    return {
        "weak_concepts_total": wc_total,
        "weak_concepts_matched": wc_matched,
        "lessons_total": lesson_total,
        "lessons_matched": lesson_matched,
    }
