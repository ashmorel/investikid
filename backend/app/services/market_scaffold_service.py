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


def _merge_adapted(source: dict, parsed: object) -> dict:
    """Per-key: take the adapted value if present and valid, else the GB source."""
    if not isinstance(parsed, dict):
        return dict(source)
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


async def _adapt_titles_batch(
    client: LLMClient, brief: MarketBrief, sources: dict[str, dict]
) -> dict[str, dict]:
    """Adapt ALL module/level title metadata in ONE premium call, keyed by id.

    Returns {id: adapted_dict}. On ANY failure (parse, timeout, malformed) it
    falls back to the GB sources per key, so scaffolding never hard-fails. Doing
    this as a single batched call (not one-per-entity) is essential: GB has ~15
    modules + ~50 levels, and ~65 sequential reasoning-model calls would run for
    minutes and time out the request.
    """
    if not sources:
        return {}
    system = (
        f"You localise children's finance-education curriculum metadata into the market "
        f"'{brief.market_code}' using these verified facts: "
        f"{json.dumps(brief.brief_json, ensure_ascii=False)}. The user sends a JSON object "
        f"mapping ids to records; each record has a 'title' plus either 'conversation_prompt' "
        f"or 'learning_objectives'. Return a JSON object with the SAME ids, each record adapted "
        f"— replace UK products, regulators, currency and examples with the market's real "
        f"equivalents; keep the meaning, age level and the SAME keys per record. JSON only."
    )
    try:
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": json.dumps(sources, ensure_ascii=False)}],
            temperature=0.3,
            max_tokens=4000,
            response_format="json",
        )
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("batch adapter response is not a JSON object")
    except Exception as exc:  # noqa: BLE001 — ANY failure (timeout, API, parse) → GB fallback
        logger.warning("batch title adaptation failed; falling back to GB sources: %s", exc)
        parsed = {}
    return {key: _merge_adapted(src, parsed.get(key)) for key, src in sources.items()}


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

    gb_modules = (await session.scalars(
        select(Module).where(Module.market_code == "GB").order_by(Module.order_index)
    )).all()
    mod_ids = [m.id for m in gb_modules]
    gb_levels_all = (await session.scalars(
        select(Level).where(Level.module_id.in_(mod_ids)).order_by(Level.order_index)
    )).all() if mod_ids else []
    levels_by_mod: dict = {}
    for lvl in gb_levels_all:
        levels_by_mod.setdefault(lvl.module_id, []).append(lvl)

    # Build ONE batch of every module/level's title metadata, keyed by stable id,
    # and adapt it all in a single LLM call (see _adapt_titles_batch).
    sources: dict[str, dict] = {}
    for i, gb_mod in enumerate(gb_modules):
        sources[f"m{i}"] = {
            "title": gb_mod.title,
            "conversation_prompt": gb_mod.conversation_prompt or "",
        }
        for j, gb_lvl in enumerate(levels_by_mod.get(gb_mod.id, [])):
            sources[f"m{i}_l{j}"] = {
                "title": gb_lvl.title,
                "learning_objectives": list(gb_lvl.learning_objectives or []),
            }

    client = get_llm_client("premium")
    adapted = await _adapt_titles_batch(client, brief, sources)

    modules_created = 0
    levels_created = 0
    for i, gb_mod in enumerate(gb_modules):
        am = adapted[f"m{i}"]
        new_mod = Module(
            topic=gb_mod.topic,
            title=am["title"],
            country_codes=list(gb_mod.country_codes or []),
            market_code=code,
            is_premium=gb_mod.is_premium,
            order_index=gb_mod.order_index,
            icon=gb_mod.icon,
            prerequisite_ids=[],
            min_age=gb_mod.min_age,
            max_age=gb_mod.max_age,
            conversation_prompt=am["conversation_prompt"] or None,
        )
        session.add(new_mod)
        await session.flush()
        modules_created += 1

        for j, gb_lvl in enumerate(levels_by_mod.get(gb_mod.id, [])):
            al = adapted[f"m{i}_l{j}"]
            session.add(Level(
                module_id=new_mod.id,
                title=al["title"],
                order_index=gb_lvl.order_index,
                is_premium=gb_lvl.is_premium,
                pass_threshold=gb_lvl.pass_threshold,
                icon=gb_lvl.icon,
                learning_objectives=al["learning_objectives"] or None,
            ))
            levels_created += 1

    await session.commit()
    return {"modules_created": modules_created, "levels_created": levels_created}
