"""Diagnostic item service — generation + CRUD/lifecycle.

``generate_items`` asks the LLM to draft ``count`` multiple-choice questions
for a given market, topic, and difficulty tier.  Each candidate is validated
structurally, then run through ``moderate_output``; only survivors are persisted
as DiagnosticItem rows with status="draft", source="generated".

The function is *best-effort per item*: a single bad or erroring candidate
never aborts the whole batch.

``list_items`` queries with optional filters plus a coverage summary.
``get_item`` fetches a single item by id.
``patch_item`` edits draft-only fields.
``approve_item`` / ``reject_item`` / ``retire_item`` handle lifecycle.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.diagnostic import DiagnosticItem
from app.services.admin_content_generation_service import _market_english
from app.services.concept_mapper import resolve_slug_global
from app.services.guardrails import with_generation_framing
from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.moderation import moderate_output

logger = logging.getLogger(__name__)

_DIFFICULTY_LABEL = {
    1: "beginner (first exposure, one concrete idea, very simple vocabulary)",
    2: "intermediate (build on the basics, introduce mechanics and a trade-off)",
    3: "advanced (apply and combine ideas, nuance, and a real financial decision)",
}


def _build_system_prompt(
    *,
    market_code: str,
    topic: str,
    difficulty_tier: int,
    count: int,
    concept_slugs: list[str],
) -> str:
    english = _market_english(market_code)
    difficulty = _DIFFICULTY_LABEL.get(difficulty_tier, "intermediate")
    slug_hint = ""
    if concept_slugs:
        slug_hint = (
            f"\n\nFor each item, optionally include a \"concept_slug\" field: choose "
            f"the single most relevant slug from this taxonomy list (use exact spelling): "
            f"{concept_slugs}.  Omit the field entirely if no slug fits well."
        )
    prompt = (
        f"You write calibrated multiple-choice diagnostic questions for InvestiKid, "
        f"a personal-finance learning app for children aged 8-16. "
        f"Write {count} questions on the topic \"{topic}\" at {difficulty} level. "
        f"Use {english}. "
        f"Each question must test genuine financial understanding, use a fresh concrete "
        f"scenario with varied character names (rotate genders, backgrounds, situations), "
        f"and include exactly 4 answer choices. "
        f"Respond with ONLY a JSON object containing a single key \"items\" whose value "
        f"is an array of {count} objects, each matching exactly: "
        f'{{\"question\": str, \"choices\": [str, str, str, str], '
        f'\"answer_index\": int (0-3), \"explanation\": str, \"concept_slug\"?: str}}'
        f"{slug_hint}"
        f"\n\nSTYLE: Keep language clear and direct, pitched at ages 12-15. "
        f"Never give personalised financial advice. "
        f"Explanations must be 1-2 sentences (max ~35 words). "
        f"Never reference specific investment products by name unless the question "
        f"is specifically about that product."
    )
    return with_generation_framing(prompt)


def _validate_candidate(raw: object) -> dict | None:
    """Return the candidate dict if structurally valid, else None.

    Valid means:
    - Is a dict with non-empty string ``question`` and ``explanation``.
    - ``choices`` is a list of exactly 4 non-empty strings.
    - ``answer_index`` is an int in [0, 3].
    """
    if not isinstance(raw, dict):
        return None
    question = raw.get("question")
    explanation = raw.get("explanation")
    choices = raw.get("choices")
    answer_index = raw.get("answer_index")

    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(explanation, str) or not explanation.strip():
        return None
    if not isinstance(choices, list) or len(choices) != 4:
        return None
    if not all(isinstance(c, str) and c.strip() for c in choices):
        return None
    if not isinstance(answer_index, int) or not (0 <= answer_index <= 3):
        return None

    return {
        "question": question.strip(),
        "choices": [c.strip() for c in choices],
        "answer_index": answer_index,
        "explanation": explanation.strip(),
        "concept_slug": raw.get("concept_slug"),
    }


async def _fetch_concept_slugs(session: AsyncSession, topic: str) -> list[str]:
    """Return concept slugs for the given topic, ordered by order_index."""
    rows = (
        await session.scalars(
            select(Concept.slug)
            .where(Concept.topic == topic)
            .order_by(Concept.order_index)
        )
    ).all()
    return list(rows)


async def generate_items(
    session: AsyncSession,
    *,
    market_code: str,
    topic: str,
    difficulty_tier: int,
    count: int,
    tier: str = "standard",
) -> list[DiagnosticItem]:
    """Generate ``count`` draft diagnostic MCQs via the LLM.

    Steps:
    1. Fetch topic Concept slugs for grounding.
    2. Build a framed system prompt; call the LLM.
    3. Parse via ``extract_json_list`` (object-wrapped-array safe).
    4. For each candidate: validate structure → moderate_output → persist.
    5. Return persisted DiagnosticItem rows (status="draft", source="generated").

    Best-effort: a single bad/erroring candidate never aborts the batch.
    """
    concept_slugs = await _fetch_concept_slugs(session, topic)
    system = _build_system_prompt(
        market_code=market_code,
        topic=topic,
        difficulty_tier=difficulty_tier,
        count=count,
        concept_slugs=concept_slugs,
    )
    client = get_llm_client(tier)
    try:
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": f"Generate {count} diagnostic questions."}],
            temperature=0.5,
            max_tokens=2000,
            response_format="json",
        )
        parsed = json.loads(raw)
        candidates = extract_json_list(parsed)
    except Exception:
        logger.exception(
            "diagnostic_item_service: LLM call or parse failed for topic=%s market=%s",
            topic,
            market_code,
        )
        return []

    persisted: list[DiagnosticItem] = []
    for raw_candidate in candidates:
        try:
            candidate = _validate_candidate(raw_candidate)
            if candidate is None:
                logger.debug(
                    "diagnostic_item_service: dropping malformed candidate: %r",
                    raw_candidate,
                )
                continue

            # Build the text blob to moderate (question + choices + explanation).
            mod_text = "\n".join(
                [candidate["question"]] + candidate["choices"] + [candidate["explanation"]]
            )
            mod_result = await moderate_output(mod_text, surface="lesson")
            if not mod_result.safe:
                logger.info(
                    "diagnostic_item_service: moderation blocked item "
                    "(category=%s) for topic=%s market=%s",
                    mod_result.category,
                    topic,
                    market_code,
                )
                continue

            # Resolve optional concept_slug → concept_id (NULL when unresolvable).
            raw_slug = candidate["concept_slug"]
            concept_id = None
            if isinstance(raw_slug, str) and raw_slug.strip():
                concept_id = await resolve_slug_global(session, raw_slug.strip())

            item = DiagnosticItem(
                market_code=market_code,
                topic=topic,
                difficulty_tier=difficulty_tier,
                question=candidate["question"],
                choices=candidate["choices"],
                answer_index=candidate["answer_index"],
                explanation=candidate["explanation"],
                status="draft",
                source="generated",
                concept_id=concept_id,
            )
            session.add(item)
            await session.flush()
            persisted.append(item)
        except Exception:
            logger.exception(
                "diagnostic_item_service: error processing candidate for topic=%s; skipping",
                topic,
            )
            continue

    return persisted


# ---------------------------------------------------------------------------
# CRUD / lifecycle helpers
# ---------------------------------------------------------------------------


async def get_item(
    session: AsyncSession, item_id: uuid.UUID
) -> DiagnosticItem | None:
    """Return a DiagnosticItem by id, or None."""
    return await session.get(DiagnosticItem, item_id)


async def list_items(
    session: AsyncSession,
    *,
    market_code: str | None = None,
    topic: str | None = None,
    status: str | None = None,
) -> tuple[list[DiagnosticItem], list[dict]]:
    """Return (items, coverage) for the given filters.

    ``coverage`` is the count of **approved** items per (topic, difficulty_tier)
    cell within the filtered market (if provided).  The ≥2 target is informational;
    callers decide what to display.
    """
    q = select(DiagnosticItem)
    if market_code:
        q = q.where(DiagnosticItem.market_code == market_code)
    if topic:
        q = q.where(DiagnosticItem.topic == topic)
    if status:
        q = q.where(DiagnosticItem.status == status)
    q = q.order_by(DiagnosticItem.created_at.desc())
    items = list((await session.scalars(q)).all())

    # Coverage: approved counts per (topic, difficulty_tier) in the filtered market
    cov_q = (
        select(
            DiagnosticItem.topic,
            DiagnosticItem.difficulty_tier,
            func.count().label("approved_count"),
        )
        .where(DiagnosticItem.status == "approved")
        .group_by(DiagnosticItem.topic, DiagnosticItem.difficulty_tier)
    )
    if market_code:
        cov_q = cov_q.where(DiagnosticItem.market_code == market_code)
    if topic:
        cov_q = cov_q.where(DiagnosticItem.topic == topic)
    cov_rows = (await session.execute(cov_q)).all()
    coverage = [
        {"topic": r.topic, "difficulty_tier": r.difficulty_tier, "approved_count": r.approved_count}
        for r in cov_rows
    ]

    return items, coverage


async def patch_item(
    session: AsyncSession,
    item: DiagnosticItem,
    *,
    fields_set: set[str],
    question: str | None = None,
    choices: list[str] | None = None,
    answer_index: int | None = None,
    explanation: str | None = None,
    difficulty_tier: int | None = None,
    concept_id: uuid.UUID | None = None,
) -> DiagnosticItem:
    """Update editable fields on a draft item and flush.

    Only fields present in *fields_set* (the caller's ``model_fields_set``) are
    written.  This means an explicitly-provided ``concept_id=null`` clears the
    field, while an omitted ``concept_id`` leaves the existing value untouched.
    """
    if "question" in fields_set and question is not None:
        item.question = question
    if "choices" in fields_set and choices is not None:
        item.choices = choices
    if "answer_index" in fields_set and answer_index is not None:
        item.answer_index = answer_index
    if "explanation" in fields_set and explanation is not None:
        item.explanation = explanation
    if "difficulty_tier" in fields_set and difficulty_tier is not None:
        item.difficulty_tier = difficulty_tier
    if "concept_id" in fields_set:
        # concept_id may be explicitly null (to clear it) — assign regardless.
        item.concept_id = concept_id
    await session.flush()
    return item


async def approve_item(
    session: AsyncSession,
    item: DiagnosticItem,
    *,
    admin_id: uuid.UUID,
) -> DiagnosticItem:
    """Transition draft → approved."""
    item.status = "approved"
    item.approved_by = admin_id
    item.approved_at = datetime.now(UTC)
    await session.flush()
    return item


async def reject_item(
    session: AsyncSession,
    item: DiagnosticItem,
) -> DiagnosticItem:
    """Transition draft → retired (kept for audit)."""
    item.status = "retired"
    await session.flush()
    return item


async def retire_item(
    session: AsyncSession,
    item: DiagnosticItem,
) -> DiagnosticItem:
    """Transition approved → retired."""
    item.status = "retired"
    await session.flush()
    return item
