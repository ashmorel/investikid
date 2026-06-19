from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Level, Module
from app.models.market_brief import MarketBrief
from app.services.llm_client import LLMClient, get_llm_client
from app.services.market_brief_service import require_verified_brief

logger = logging.getLogger(__name__)


async def _adapt_titles(
    client: LLMClient, brief: MarketBrief, source: dict
) -> dict:
    """Adapt a source dict's text fields into the brief's market via a premium-model
    JSON call. Validates the returned object; on any failure falls back to the source
    values so scaffolding never hard-fails.

    ``source`` carries only the text fields present on the row being adapted
    (Module: title/conversation_prompt; Level: title/learning_objectives), so the
    adapter only ever touches fields that exist on that model.
    """
    system = (
        f"You localise children's finance-education curriculum metadata into the "
        f"market '{brief.market_code}' using these verified market facts: "
        f"{json.dumps(brief.brief_json, ensure_ascii=False)}. Replace UK products, "
        f"regulators, currency and examples with the market's real equivalents. Keep "
        f"the meaning, age level and structure. Reply ONLY with a JSON object with the "
        f"SAME keys as the input: {', '.join(source.keys())}."
    )
    try:
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": json.dumps(source, ensure_ascii=False)}],
            temperature=0.3,
            max_tokens=500,
            response_format="json",
        )
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("adapter response is not a JSON object")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("title adaptation failed; falling back to GB source: %s", exc)
        return dict(source)

    # Only accept keys that exist on the source; fall back per-key on missing/empty.
    adapted: dict = {}
    for key, src_value in source.items():
        value = parsed.get(key)
        if isinstance(src_value, str):
            adapted[key] = value if isinstance(value, str) and value.strip() else src_value
        elif isinstance(src_value, list):
            adapted[key] = value if isinstance(value, list) and value else src_value
        else:
            adapted[key] = value if value is not None else src_value
    return adapted


async def scaffold_market_from_gb(session: AsyncSession, code: str) -> dict:
    """Clone GB's module/level skeleton into ``code``, adapting titles/objectives.

    Requires a verified brief (raises 409 otherwise). Idempotent: if the market
    already has any module, it is returned unchanged. Never creates lessons and
    never touches GB rows or ``Market.has_content``.
    """
    brief = await require_verified_brief(session, code)

    existing = await session.scalar(
        select(Module.id).where(Module.market_code == code).limit(1)
    )
    if existing is not None:
        return {"modules_created": 0, "levels_created": 0, "already_scaffolded": True}

    client = get_llm_client("premium")

    gb_modules = (await session.scalars(
        select(Module).where(Module.market_code == "GB").order_by(Module.order_index)
    )).all()

    modules_created = 0
    levels_created = 0
    for gb_mod in gb_modules:
        mod_source = {
            "title": gb_mod.title,
            "conversation_prompt": gb_mod.conversation_prompt or "",
        }
        adapted_mod = await _adapt_titles(client, brief, mod_source)
        new_mod = Module(
            topic=gb_mod.topic,
            title=adapted_mod["title"],
            country_codes=list(gb_mod.country_codes or []),
            market_code=code,
            is_premium=gb_mod.is_premium,
            order_index=gb_mod.order_index,
            icon=gb_mod.icon,
            prerequisite_ids=[],
            min_age=gb_mod.min_age,
            max_age=gb_mod.max_age,
            conversation_prompt=adapted_mod["conversation_prompt"] or None,
        )
        session.add(new_mod)
        await session.flush()
        modules_created += 1

        gb_levels = (await session.scalars(
            select(Level).where(Level.module_id == gb_mod.id).order_by(Level.order_index)
        )).all()
        for gb_lvl in gb_levels:
            lvl_source = {
                "title": gb_lvl.title,
                "learning_objectives": list(gb_lvl.learning_objectives or []),
            }
            adapted_lvl = await _adapt_titles(client, brief, lvl_source)
            session.add(Level(
                module_id=new_mod.id,
                title=adapted_lvl["title"],
                order_index=gb_lvl.order_index,
                is_premium=gb_lvl.is_premium,
                pass_threshold=gb_lvl.pass_threshold,
                icon=gb_lvl.icon,
                learning_objectives=adapted_lvl["learning_objectives"] or None,
            ))
            levels_created += 1

    await session.commit()
    return {"modules_created": modules_created, "levels_created": levels_created}
