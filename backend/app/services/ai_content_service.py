from __future__ import annotations

import json
import random
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.content import Lesson
from app.models.generated_content import GeneratedContent
from app.models.user import User
from app.services import llm_usage
from app.services.content_variety_service import resolve_variant
from app.services.guardrails import with_guardrail_preamble
from app.services.llm_client import (
    LLMError,
    get_llm_client,
    get_model_name,
    get_strict_premium_client,
)
from app.services.moderation import moderate_output


class PracticeQuizSchema(BaseModel):
    """Validates LLM-generated practice quiz JSON."""
    question: str
    choices: list[str]
    answer_index: int
    explanation: str

    @field_validator("choices")
    @classmethod
    def choices_length(cls, v: list[str]) -> list[str]:
        if len(v) < 2 or len(v) > 5:
            raise ValueError("choices must have 2-5 items")
        return v

    @field_validator("answer_index")
    @classmethod
    def answer_in_range(cls, v: int, info) -> int:
        if v < 0:
            raise ValueError("answer_index must be >= 0")
        return v


_SYSTEM_PROMPT = (
    "You are a quiz generator for a children's financial education app. "
    "Generate a single multiple-choice question that tests the same concept as the "
    "provided lesson, but from a different angle. "
    "Rules:\n"
    "1. Only use facts from the provided lesson content. Do not introduce new financial claims.\n"
    "2. Never mention specific real companies, stock prices, or crypto values.\n"
    "3. Never give real financial advice.\n"
    "4. Use simple, kid-friendly language.\n"
    "5. Return ONLY valid JSON with this exact schema: "
    '{"question": "...", "choices": ["...", "...", "..."], "answer_index": 0, "explanation": "..."}\n'
    "6. choices must have exactly 3 items. answer_index is 0-based."
)


# Bump when the generation pipeline changes so stale cached quiz variants are not
# reused. v2 = answer-verification; v3 = choice shuffle; v4 = strict-premium
# verifier (no silent Llama fallback) + deterministic fallback ordering.
_QUIZ_CACHE_VERSION = "v4"


def _shuffle_choices(quiz: dict[str, Any]) -> dict[str, Any]:
    """Randomise choice order so the correct answer isn't always first, keeping
    answer_index pointed at the same (correct) choice."""
    choices = list(quiz["choices"])
    correct = choices[quiz["answer_index"]]
    random.shuffle(choices)
    return {**quiz, "choices": choices, "answer_index": choices.index(correct)}


_VERIFIER_SYSTEM_PROMPT = (
    "You are a meticulous maths and finance answer-checker for a children's quiz. "
    "Solve the multiple-choice question YOURSELF, working step by step and computing "
    "carefully — do not assume any option is correct. Then reply with ONLY compact "
    'JSON giving the 0-based index of the single correct choice: {"answer_index": <int>}.'
)


async def _verify_answer(question: str, choices: list[str], answer_index: int) -> bool:
    """Independently re-solve the question with the strongest model and return True
    only if it agrees with ``answer_index``. Catches wrong answer keys (especially
    arithmetic from the weaker free tier) before a question is served/cached.
    Fail-closed: any error or disagreement → not verified."""
    # Verify with the REAL premium model only — no silent fallback to the weak
    # tier, which would just re-confirm its own mistakes. If premium isn't
    # available, treat the answer as unverified so the caller serves the authored
    # question instead.
    client = get_strict_premium_client()
    if client is None:
        return False
    try:
        numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(choices))
        raw = await client.complete(
            system_prompt=_VERIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Question: {question}\nChoices:\n{numbered}"}],
            temperature=0.0,
            max_tokens=300,
            response_format="json",
        )
        return int(json.loads(raw)["answer_index"]) == int(answer_index)
    except Exception:  # noqa: BLE001
        return False


@llm_usage.surface("quiz")
async def generate_practice_quiz(
    session: AsyncSession,
    lesson: Lesson,
    *,
    user: User,
    topic: str,
    concept: str,
    premium: bool,
    wrong_answer_index: int | None = None,
) -> dict[str, Any]:
    """Generate or serve a cached practice quiz variant for a lesson concept."""
    model_name = get_model_name("premium" if premium else "standard")
    spec = await resolve_variant(session, user, lesson, concept)
    # Cache version: bumping it bypasses all quiz variants cached before the
    # answer-verification pipeline existed, so old (possibly wrong-keyed)
    # questions are regenerated + verified rather than served from cache.
    variant_key = f"{spec.variant_key}:{_QUIZ_CACHE_VERSION}"

    def _with_rung(d: dict[str, Any]) -> dict[str, Any]:
        out = dict(d)
        out["variant_rung"] = spec.rung
        return out

    cached = await session.scalar(
        select(GeneratedContent).where(
            GeneratedContent.lesson_id == lesson.id,
            GeneratedContent.concept == concept,
            GeneratedContent.model_used == model_name,
            GeneratedContent.variant_key == variant_key,
        )
    )
    if cached:
        return _with_rung(cached.content_json)

    content = lesson.content_json or {}

    # Without a trustworthy verifier (no premium model configured), don't generate
    # unverifiable LLM questions — serve the authored lesson question instead
    # (guaranteed correct). Skips the LLM entirely so we don't thrash.
    if get_strict_premium_client() is None:
        return _with_rung(
            await _safe_cached_or_fallback(session, lesson.id, concept, model_name, content)
        )

    user_message = f"Lesson topic: {topic}\nLesson content: {json.dumps(content)}"
    if wrong_answer_index is not None and "choices" in content:
        choices = content.get("choices", [])
        if 0 <= wrong_answer_index < len(choices):
            user_message += f"\nThe student chose: {choices[wrong_answer_index]} (wrong)"
    if spec.rung == "easier":
        user_message += "\nMake this question slightly easier and more encouraging."
    elif spec.rung == "harder":
        user_message += "\nMake this question slightly more challenging (still kid-friendly)."

    client = get_llm_client(tier="premium" if premium else "standard")

    for attempt in range(2):
        try:
            raw = await client.complete(
                system_prompt=with_guardrail_preamble(_SYSTEM_PROMPT),
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
                max_tokens=400,
                response_format="json",
            )
            parsed = json.loads(raw)
            validated = PracticeQuizSchema(**parsed)
            if validated.answer_index >= len(validated.choices):
                raise ValueError("answer_index out of range")
            result = validated.model_dump()

            _mod = await moderate_output(
                " ".join([result["question"], *result["choices"], result["explanation"]]),
                surface="quiz",
            )
            if not _mod.safe:
                session.add(AuditLog(
                    user_id=None,
                    event_type="moderation_block",
                    metadata_json={"surface": "quiz", "category": _mod.category},
                ))
                if attempt == 0:
                    continue
                return _with_rung(await _safe_cached_or_fallback(
                    session, lesson.id, concept, model_name, content
                ))

            # Independent answer check: never serve a question whose key a stronger
            # model disagrees with (catches wrong arithmetic from the weak tier).
            if not await _verify_answer(
                result["question"], result["choices"], result["answer_index"]
            ):
                if attempt == 0:
                    continue
                return _with_rung(await _safe_cached_or_fallback(
                    session, lesson.id, concept, model_name, content
                ))

            # Randomise choice order before caching so the answer isn't always first.
            result = _shuffle_choices(result)

            session.add(GeneratedContent(
                lesson_id=lesson.id,
                concept=concept,
                content_json=result,
                model_used=model_name,
                variant_key=variant_key,
            ))
            await session.flush()
            return _with_rung(result)

        except (json.JSONDecodeError, ValueError, LLMError):
            if attempt == 0:
                continue
            return _with_rung(await _safe_cached_or_fallback(
                session, lesson.id, concept, model_name, content
            ))

    return _with_rung(await _safe_cached_or_fallback(
        session, lesson.id, concept, model_name, content
    ))


async def _safe_cached_or_fallback(
    session: AsyncSession,
    lesson_id,
    concept: str,
    model_name: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    """Prefer an already-cached (moderation-passed) variant; else the authored
    question. DETERMINISTIC by design — revise re-derives the answer by re-calling
    generate_practice_quiz, so this must return the same question + choice order
    every time (a stable row pick + a seeded shuffle), not a random one."""
    rng = random.Random(f"{lesson_id}:{concept}")
    rows = (
        await session.scalars(
            select(GeneratedContent).where(
                GeneratedContent.lesson_id == lesson_id,
                GeneratedContent.concept == concept,
                GeneratedContent.model_used == model_name,
                # Only reuse current-pipeline (answer-verified) variants.
                GeneratedContent.variant_key.like(f"%:{_QUIZ_CACHE_VERSION}"),
            )
        )
    ).all()
    if rows:
        return sorted(rows, key=lambda r: str(r.id))[0].content_json
    return _fallback(content, rng)


def _fallback(original_content: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any]:
    """Return the original question with shuffled choices as a fallback. Pass `rng`
    (seeded) for a deterministic order when the result must be reproducible."""
    choices = list(original_content.get("choices", ["A", "B", "C"]))
    answer_idx = original_content.get("answer_index", 0)
    correct = choices[answer_idx] if answer_idx < len(choices) else choices[0]
    (rng or random).shuffle(choices)
    return {
        "question": original_content.get("question", original_content.get("prompt", "Practice question")),
        "choices": choices,
        "answer_index": choices.index(correct),
        "explanation": original_content.get("explanation", "Review the lesson for the answer."),
    }
