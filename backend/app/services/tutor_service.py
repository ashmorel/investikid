from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Lesson
from app.models.skill_profile import TopicMastery
from app.models.tutor import TutorConversation
from app.models.user import User
from app.services.llm_client import get_llm_client, get_model_name


class TutorLimitReached(Exception):
    """User has hit the message limit for this conversation."""


class TutorInputTooLong(Exception):
    """User message exceeds the maximum character limit."""


_SYSTEM_PROMPT_TEMPLATE = (
    "You are Coach Eddie, a friendly and encouraging money tutor for kids learning "
    "about finance. You are helping with a specific lesson — its content is provided below.\n\n"
    "Rules:\n"
    "1. Only explain concepts from the provided lesson content.\n"
    "2. Never give real financial advice or suggest the child spend, save, or invest real money.\n"
    "3. Never mention specific real companies, stock prices, or crypto values.\n"
    "4. Keep responses under 100 words.\n"
    "5. Use simple, encouraging language.\n"
    "6. If the child asks something outside the lesson topic, say: "
    "'Great question! That's outside what we're covering in this quest — ask a parent or teacher!'\n"
    "7. {skill_level_instruction}\n\n"
    "Lesson content:\n{lesson_content}"
)

_SKILL_INSTRUCTIONS = {
    "low": (
        "The student is a beginner. Use very simple words, short sentences, and lots of encouragement."
        " Give examples they can relate to (pocket money, toys, snacks)."
    ),
    "medium": (
        "The student has some understanding. Give clear explanations with relatable examples."
        " Encourage them to think about why."
    ),
    "high": (
        "The student is doing well. Challenge them with deeper questions."
        " Ask 'what if' scenarios to deepen understanding."
    ),
}

# Patterns that suggest financial advice
_ADVICE_PATTERNS = re.compile(
    r"\byou should (buy|sell|invest|spend|save|trade)\b"
    r"|\b(buy|sell|invest in) [A-Z][a-z]",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "That's a great question! Ask a parent or teacher for advice "
    "about real money decisions. 😊"
)


def safety_filter(response: str) -> str:
    """Replace responses containing financial advice patterns with a safe fallback."""
    if _ADVICE_PATTERNS.search(response):
        return _SAFE_FALLBACK
    return response


def _skill_level(mastery_score: float) -> str:
    if mastery_score < 0.3:
        return "low"
    if mastery_score <= 0.7:
        return "medium"
    return "high"


async def chat(
    *,
    session: AsyncSession,
    user: User,
    lesson: Lesson,
    topic: str,
    message: str,
    conversation_id: uuid.UUID | None,
    premium: bool,
) -> dict[str, Any]:
    """Process a Coach Eddie message and return the response."""
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise TutorInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = (
        settings.tutor_max_messages_premium if premium
        else settings.tutor_max_messages_free
    )

    # Load or create conversation
    conversation: TutorConversation | None = None
    if conversation_id:
        conversation = await session.get(TutorConversation, conversation_id)

    model_name = get_model_name("premium" if premium else "standard")

    if conversation is None:
        conversation = TutorConversation(
            user_id=user.id,
            lesson_id=lesson.id,
            messages=[],
            message_count=0,
            model_used=model_name,
        )
        session.add(conversation)
        await session.flush()

    if conversation.message_count >= max_messages:
        raise TutorLimitReached(
            f"Message limit reached ({max_messages}). "
            + ("Upgrade to premium for more!" if not premium else "Limit reached for this conversation.")
        )

    # Get mastery for tone adaptation
    mastery = await session.get(TopicMastery, (user.id, topic))
    mastery_score = mastery.mastery_score if mastery else 0.0
    level = _skill_level(mastery_score)

    # Build system prompt
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        lesson_content=json.dumps(lesson.content_json or {}),
    )

    # Build message history
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    # Call LLM
    client = get_llm_client(tier="premium" if premium else "standard")
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    # Safety filter
    filtered_response = safety_filter(raw_response)

    # Persist conversation
    conversation.messages = [
        *conversation.messages,
        {"role": "user", "content": message},
        {"role": "assistant", "content": filtered_response},
    ]
    conversation.message_count += 2
    await session.flush()

    return {
        "response": filtered_response,
        "conversation_id": conversation.id,
        "messages_remaining": max(0, max_messages - conversation.message_count),
    }
