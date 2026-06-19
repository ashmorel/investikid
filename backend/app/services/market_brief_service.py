from __future__ import annotations

import json
import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.services.llm_client import get_llm_client, get_model_name

logger = logging.getLogger(__name__)

BRIEF_KEYS = [
    "currency",
    "tax_advantaged_accounts",
    "regulators",
    "deposit_protection",
    "typical_products",
    "local_examples",
    "notes",
]

_BRIEF_ATTEMPTS = 2


class BriefGenerationError(Exception):
    """The premium model failed to return a usable JSON brief (after retries).

    Wraps the underlying cause (LLM/network/API error, empty response, or bad
    JSON) so the endpoint can return a single clean 502 while the real reason
    is logged server-side.
    """


async def generate_brief(session: AsyncSession, market: Market) -> MarketBrief:
    """Premium-model draft of the market's youth-finance facts. Stored status=draft.

    Retries the LLM call; raises BriefGenerationError (logged) if every attempt
    fails — whether from an LLM/API error, an empty response, or non-JSON output.
    """
    client = get_llm_client("premium")
    system = (
        f"You are a financial-education researcher. Produce a concise, FACTUAL brief of the "
        f"{market.name} ({market.code}) youth-finance landscape for curriculum writers. "
        f"Reply ONLY with a JSON object containing exactly these keys: {', '.join(BRIEF_KEYS)}. "
        f"Use arrays for tax_advantaged_accounts, regulators, typical_products and local_examples; "
        f"strings for currency, deposit_protection and notes. Be accurate and age-appropriate."
    )

    parsed: dict | None = None
    last_error: Exception | str | None = None
    for attempt in range(_BRIEF_ATTEMPTS):
        try:
            raw = await client.complete(
                system_prompt=system,
                messages=[{"role": "user", "content": f"Brief for {market.name}."}],
                temperature=0.3,
                max_tokens=1200,
                response_format="json",
            )
        except Exception as exc:  # noqa: BLE001 — LLM/network/API errors are all retryable here
            last_error = exc
            logger.warning(
                "brief LLM call failed for %s (attempt %d/%d): %s",
                market.code, attempt + 1, _BRIEF_ATTEMPTS, exc,
            )
            continue
        if not raw or not raw.strip():
            last_error = "empty LLM response"
            logger.warning(
                "brief LLM returned empty for %s (attempt %d/%d)",
                market.code, attempt + 1, _BRIEF_ATTEMPTS,
            )
            continue
        try:
            candidate = json.loads(raw)
        except (ValueError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "brief LLM returned non-JSON for %s (attempt %d/%d): %.120s",
                market.code, attempt + 1, _BRIEF_ATTEMPTS, raw,
            )
            continue
        if not isinstance(candidate, dict):
            last_error = "brief response is not a JSON object"
            continue
        parsed = candidate
        break

    if parsed is None:
        logger.error(
            "brief generation failed for %s after %d attempts (model=%s): %s",
            market.code, _BRIEF_ATTEMPTS, get_model_name("premium"), last_error,
        )
        raise BriefGenerationError(f"brief generation failed: {last_error}")

    brief = await session.get(MarketBrief, market.code)
    if brief is None:
        brief = MarketBrief(market_code=market.code)
        session.add(brief)
    brief.brief_json = parsed
    brief.status = "draft"
    brief.model_used = get_model_name("premium")
    await session.flush()
    return brief


async def require_verified_brief(session: AsyncSession, market_code: str) -> MarketBrief:
    brief = await session.get(MarketBrief, market_code)
    if brief is None or brief.status != "verified":
        raise HTTPException(status.HTTP_409_CONFLICT, "market brief not verified")
    return brief
