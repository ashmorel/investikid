"""LLM-based concept classification backfill.

Classifies existing published lessons (concept_id IS NULL AND
concept_classified_at IS NULL) into the FULL taxonomy using the lite LLM tier.
The model can NEVER invent a concept — every pick is validated through
``resolve_slug_global`` before being written.

Monotonic drain guarantee:
- ``concept_classified_at`` is set on EVERY lesson the service processes,
  whether it gets tagged, is unmatched (LLM abstain/hallucinate), or is
  skipped pre-LLM (no text).
- The query filters ``concept_classified_at IS NULL``, so each lesson is
  attempted at most once — re-runs never re-bill.
- A drain loop whose stop condition is ``lessons_seen == 0`` is guaranteed to
  converge even if some lessons are permanently unmatchable.

Safe to run multiple times:
- Already-tagged rows (``concept_id IS NOT NULL``) are excluded by the query
  (they also have ``concept_classified_at`` set from the run that tagged them).
- Already-attempted rows (``concept_classified_at IS NOT NULL``) are excluded.

Why global? The regenerated curriculum uses free-form module topics (e.g.
"growing-your-money") that don't match the 9 canonical taxonomy topics, so the
old per-topic candidate lookup returned empty and every lesson was skipped.
``Concept.slug`` is UNIQUE, so global matching is safe and correct.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.services.concept_mapper import resolve_slug_global
from app.services.guardrails import with_generation_framing
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

_MAX_LIMIT = 500


def _lesson_text(lesson: Lesson) -> str | None:
    """Extract the best candidate text from a lesson's content_json.

    Mirrors the derivation in ``concept_backfill_service._lesson_text``:
    question → title → prompt.  Returns ``None`` when nothing useful is found.
    """
    c = lesson.content_json or {}
    return c.get("question") or c.get("title") or c.get("prompt") or None


async def _fetch_all_concepts(session: AsyncSession) -> list[dict]:
    """Return ALL concept dicts (slug, name, blurb, topic) ordered by topic then
    order_index.  Fetched once per classify run and cached by the caller.

    Including ``topic`` lets the prompt group concepts by topic for readability.
    """
    rows = (
        await session.scalars(
            select(Concept).order_by(Concept.topic, Concept.order_index)
        )
    ).all()
    return [
        {"slug": c.slug, "name": c.name, "blurb": c.blurb or "", "topic": c.topic}
        for c in rows
    ]


def _build_prompt(lesson_text: str, concepts: list[dict]) -> str:
    """Build the classification system prompt, wrapped in generation framing."""
    candidate_lines = "\n".join(
        f'  - slug="{c["slug"]}" name="{c["name"]}" [topic: {c["topic"]}]'
        + (f' ({c["blurb"]})' if c["blurb"] else "")
        for c in concepts
    )
    system = (
        "You are a financial-education content tagger. "
        "Your job is to assign a lesson to exactly one concept from a fixed taxonomy list. "
        "You MUST return a JSON object with a single key 'concept_slug' whose value is "
        "the slug of the best-matching concept from the list below, "
        "or null if no concept clearly fits.\n\n"
        f"Full taxonomy concepts (grouped by topic):\n{candidate_lines}\n\n"
        "Rules:\n"
        "- Only use slugs from the list above — never invent a new slug.\n"
        "- If no concept is a clear match, return {\"concept_slug\": null}.\n"
        "- Return ONLY the JSON object, no other text."
    )
    return with_generation_framing(system)


async def classify_untagged_lessons(
    session: AsyncSession,
    *,
    limit: int = 200,
    tier: str = "lite",
) -> dict[str, int]:
    """Classify published lessons with concept_id IS NULL and concept_classified_at
    IS NULL using the specified LLM tier (default: "lite").

    Each lesson is stamped with ``concept_classified_at`` regardless of outcome,
    so no lesson is ever re-attempted on subsequent runs (monotonic drain).

    Returns counts:
        lessons_seen      — how many unclassified published lessons were processed
        lessons_tagged    — how many got a valid concept_id written
        lessons_unmatched — how many the LLM was called for but abstained or
                            hallucinated (i.e. pick did not resolve to a concept)
        lessons_skipped   — how many were skipped before calling the LLM
                            (no text, or the entire taxonomy is empty)
        lessons_errored   — how many raised an unexpected exception (skipped)

    Invariant: tagged + unmatched + skipped + errored == seen
    """
    effective_limit = min(limit, _MAX_LIMIT)
    now = datetime.now(UTC)

    lesson_rows = (
        await session.scalars(
            select(Lesson)
            .join(Lesson.module)
            .where(
                Lesson.concept_id.is_(None),
                Lesson.concept_classified_at.is_(None),
                Module.published.is_(True),
            )
            .options(selectinload(Lesson.module))
            .order_by(Lesson.id)
            .limit(effective_limit)
        )
    ).all()

    lessons_seen = len(lesson_rows)
    lessons_tagged = 0
    lessons_unmatched = 0
    lessons_skipped = 0
    lessons_errored = 0

    # Fetch the full taxonomy ONCE for the whole batch — no per-topic scoping.
    all_concepts = await _fetch_all_concepts(session)

    # Degenerate guard: if the taxonomy is entirely empty, skip everything.
    if not all_concepts:
        for lesson in lesson_rows:
            lesson.concept_classified_at = now
            lessons_skipped += 1
        await session.flush()
        return {
            "lessons_seen": lessons_seen,
            "lessons_tagged": lessons_tagged,
            "lessons_unmatched": lessons_unmatched,
            "lessons_skipped": lessons_skipped,
            "lessons_errored": lessons_errored,
        }

    client = get_llm_client(tier)

    for lesson in lesson_rows:
        try:
            text = _lesson_text(lesson)
            if not text:
                lesson.concept_classified_at = now
                lessons_skipped += 1
                continue

            system_prompt = _build_prompt(text, all_concepts)
            user_msg = f"Lesson text: {text}"

            raw = await client.complete(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                temperature=0.0,
                max_tokens=60,
                response_format="json",
            )

            # Parse the response.
            pick: str | None = None
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    val = parsed.get("concept_slug")
                    pick = val.strip() if isinstance(val, str) and val.strip() else None
            except (json.JSONDecodeError, ValueError, AttributeError):
                pick = None

            # Validate globally — only a real taxonomy match is ever written.
            concept_id = await resolve_slug_global(session, pick)

            # Stamp as attempted regardless of outcome.
            lesson.concept_classified_at = now

            if concept_id is not None:
                lesson.concept_id = concept_id
                lessons_tagged += 1
            else:
                logger.info(
                    "concept_classify_unmatched lesson=%s topic=%s pick=%s",
                    lesson.id,
                    lesson.module.topic if lesson.module else None,
                    pick,
                )
                lessons_unmatched += 1

        except Exception:  # noqa: BLE001 — one bad lesson must not abort the batch
            logger.exception(
                "concept_classify_error lesson=%s — continuing",
                lesson.id,
            )
            lessons_errored += 1

    await session.flush()

    return {
        "lessons_seen": lessons_seen,
        "lessons_tagged": lessons_tagged,
        "lessons_unmatched": lessons_unmatched,
        "lessons_skipped": lessons_skipped,
        "lessons_errored": lessons_errored,
    }
