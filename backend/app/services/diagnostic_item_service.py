"""Diagnostic item generation service.

``generate_items`` asks the LLM to draft ``count`` multiple-choice questions
for a given market, topic, and difficulty tier.  Each candidate is validated
structurally, then run through ``moderate_output``; only survivors are persisted
as DiagnosticItem rows with status="draft", source="generated".

The function is *best-effort per item*: a single bad or erroring candidate
never aborts the whole batch.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
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
