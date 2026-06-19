from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.services.llm_client import get_llm_client, get_model_name

BRIEF_KEYS = [
    "currency",
    "tax_advantaged_accounts",
    "regulators",
    "deposit_protection",
    "typical_products",
    "local_examples",
    "notes",
]


async def generate_brief(session: AsyncSession, market: Market) -> MarketBrief:
    """Premium-model draft of the market's youth-finance facts. Stored status=draft.

    Raises ValueError on invalid JSON so the endpoint can return 502.
    """
    client = get_llm_client("premium")
    system = (
        f"You are a financial-education researcher. Produce a concise, FACTUAL brief of the "
        f"{market.name} ({market.code}) youth-finance landscape for curriculum writers. "
        f"Reply ONLY with a JSON object containing exactly these keys: {', '.join(BRIEF_KEYS)}. "
        f"Use arrays for tax_advantaged_accounts, regulators, typical_products and local_examples; "
        f"strings for currency, deposit_protection and notes. Be accurate and age-appropriate."
    )
    raw = await client.complete(
        system_prompt=system,
        messages=[{"role": "user", "content": f"Brief for {market.name}."}],
        temperature=0.3,
        max_tokens=900,
        response_format="json",
    )
    parsed = json.loads(raw)  # may raise ValueError → 502 in the endpoint
    if not isinstance(parsed, dict):
        raise ValueError("brief response is not a JSON object")

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
