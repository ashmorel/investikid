from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tutor import ChartCoachConversation
from app.models.user import User
from app.services.llm_client import get_llm_client, get_model_name
from app.services.price_provider import PricePoint


class ChartCoachLimitReached(Exception):
    """User has hit the message limit for this conversation."""


class ChartCoachInputTooLong(Exception):
    """User message exceeds the maximum character limit."""


_ADVICE_PATTERNS = re.compile(
    r"\byou should (buy|sell|invest|spend|save|trade)\b"
    r"|\b(buy|sell|invest in) [A-Z][a-z]",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "That's a great question! Ask a parent or teacher for advice "
    "about real money decisions."
)


def _safety_filter(response: str) -> str:
    if _ADVICE_PATTERNS.search(response):
        return _SAFE_FALLBACK
    return response


def _build_stats(ticker: str, period: str, points: list[PricePoint]) -> str:
    start = points[0].close
    end = points[-1].close
    change_pct = ((end - start) / start * 100) if start > 0 else 0
    high = max(p.high for p in points)
    low = min(p.low for p in points)
    avg_vol = sum(p.volume for p in points) / len(points)
    return (
        f"Ticker: {ticker}, Period: {period}\n"
        f"Start price: {start:.2f}, End price: {end:.2f}, Change: {change_pct:+.1f}%\n"
        f"Period high: {high:.2f}, Period low: {low:.2f}\n"
        f"Average daily volume: {avg_vol:,.0f} shares\n"
        f"Number of data points: {len(points)}"
    )


def _build_system_prompt(age: int, ticker: str, name: str, period: str, stats: str) -> str:
    return (
        f"You are Coach Eddie, a friendly investing teacher for a {age}-year-old. "
        f"You're helping them understand a stock chart for {ticker} ({name}).\n\n"
        f"Here's the chart data for the {period} period:\n{stats}\n\n"
        "Rules:\n"
        "1. Only discuss what the chart shows — never give investment advice\n"
        "2. Use age-appropriate language (simple for 8-11, more detail for 12-14, technical terms OK for 15+)\n"
        "3. Reference actual numbers from the chart data\n"
        "4. If asked about something not related to this chart, say: "
        "\"That's a great question, but let's focus on reading this chart! "
        "Try asking about what you see in the graph.\"\n"
        "5. Keep responses under 100 words\n"
        "6. Be encouraging and use questions to make them think"
    )


async def chart_coach_chat(
    *,
    session: AsyncSession,
    user: User,
    ticker: str,
    exchange: str,
    name: str,
    period: str,
    message: str,
    conversation_id: uuid.UUID | None,
    points: list[PricePoint],
) -> dict[str, Any]:
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise ChartCoachInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = settings.tutor_max_messages_free

    conversation: ChartCoachConversation | None = None
    if conversation_id:
        conversation = await session.get(ChartCoachConversation, conversation_id)

    model_name = get_model_name("standard")

    if conversation is None:
        conversation = ChartCoachConversation(
            user_id=user.id,
            ticker=ticker,
            exchange=exchange,
            messages=[],
            message_count=0,
            model_used=model_name,
        )
        session.add(conversation)
        await session.flush()

    if conversation.message_count >= max_messages:
        raise ChartCoachLimitReached(
            f"Message limit reached ({max_messages}). Start a new conversation to keep learning!"
        )

    age = (date.today() - user.dob).days // 365
    stats = _build_stats(ticker, period, points)
    system_prompt = _build_system_prompt(age, ticker, name, period, stats)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    client = get_llm_client(tier="standard")
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    filtered_response = _safety_filter(raw_response)

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
