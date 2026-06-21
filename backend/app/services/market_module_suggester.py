from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Module
from app.models.market import Market
from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.market_brief_service import require_verified_brief

logger = logging.getLogger(__name__)


async def suggest_modules(session: AsyncSession, market: Market) -> list[dict]:
    brief = await require_verified_brief(session, market.code)  # 409 if not verified
    gb_titles = (await session.scalars(
        select(Module.title).where(Module.market_code == "GB").order_by(Module.order_index)
    )).all()
    system = (
        f"You design youth financial-education curricula. The base (UK) curriculum has these "
        f"modules: {json.dumps(list(gb_titles), ensure_ascii=False)}. Using these verified facts "
        f"about the market '{market.name}' ({market.code}): "
        f"{json.dumps(brief.brief_json, ensure_ascii=False)}, "
        f"propose modules this market NEEDS that the UK set lacks, and flag UK-specific modules to "
        f"replace. Reply ONLY with a JSON array; each item: "
        f'{{"title": str, "topic": str, "rationale": str (one line), "action": "add"|"replace", '
        f'"replaces": str|null (a UK module title when action=replace), '
        f'"suggested_concepts": [str, 3-5]}}.'
    )
    try:
        raw = await get_llm_client("authoring").complete(
            system_prompt=system,
            messages=[{"role": "user", "content": f"Suggest modules for {market.name}."}],
            temperature=0.4, max_tokens=1500, response_format="json",
        )
        items = extract_json_list(json.loads(raw))
        out: list[dict] = []
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("title"), str):
                concepts = it.get("suggested_concepts")
                concepts = concepts if isinstance(concepts, list) else []
                out.append({
                    "title": it["title"], "topic": str(it.get("topic", "")),
                    "rationale": str(it.get("rationale", "")),
                    "action": "replace" if it.get("action") == "replace" else "add",
                    "replaces": it.get("replaces") if isinstance(it.get("replaces"), str) else None,
                    "suggested_concepts": [str(c) for c in concepts if c][:5],
                })
        return out
    except Exception as exc:  # noqa: BLE001 — any failure → no suggestions, never 500 the page
        logger.warning("module suggestion failed for %s: %s", market.code, exc)
        return []
