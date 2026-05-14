from __future__ import annotations

import json
import random
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson
from app.models.generated_content import GeneratedContent
from app.services.llm_client import LLMError, get_llm_client

from app.core.config import settings


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


async def generate_practice_quiz(
    session: AsyncSession,
    lesson: Lesson,
    *,
    topic: str,
    concept: str,
    premium: bool,
    wrong_answer_index: int | None = None,
) -> dict[str, Any]:
    """Generate or serve a cached practice quiz for a lesson concept."""
    model_name = settings.llm_premium_model if premium else settings.llm_free_model

    # Check cache
    cached = await session.scalar(
        select(GeneratedContent).where(
            GeneratedContent.lesson_id == lesson.id,
            GeneratedContent.concept == concept,
            GeneratedContent.model_used == model_name,
        )
    )
    if cached:
        return cached.content_json

    # Build grounded prompt
    content = lesson.content_json or {}
    user_message = f"Lesson topic: {topic}\nLesson content: {json.dumps(content)}"
    if wrong_answer_index is not None and "choices" in content:
        choices = content.get("choices", [])
        if 0 <= wrong_answer_index < len(choices):
            user_message += f"\nThe student chose: {choices[wrong_answer_index]} (wrong)"

    client = get_llm_client(premium=premium)

    for attempt in range(2):
        try:
            raw = await client.complete(
                system_prompt=_SYSTEM_PROMPT,
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

            # Cache it
            session.add(GeneratedContent(
                lesson_id=lesson.id,
                concept=concept,
                content_json=result,
                model_used=model_name,
            ))
            await session.flush()
            return result

        except (json.JSONDecodeError, ValueError, LLMError):
            if attempt == 0:
                continue  # retry once
            # Fall back to original question with shuffled choices
            return _fallback(content)

    return _fallback(content)


def _fallback(original_content: dict[str, Any]) -> dict[str, Any]:
    """Return the original question with shuffled choices as a fallback."""
    choices = list(original_content.get("choices", ["A", "B", "C"]))
    answer_idx = original_content.get("answer_index", 0)
    correct = choices[answer_idx] if answer_idx < len(choices) else choices[0]
    random.shuffle(choices)
    return {
        "question": original_content.get("question", original_content.get("prompt", "Practice question")),
        "choices": choices,
        "answer_index": choices.index(correct),
        "explanation": original_content.get("explanation", "Review the lesson for the answer."),
    }
