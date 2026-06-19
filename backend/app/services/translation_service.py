from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.languages import SUPPORTED_LANGUAGES, is_supported_language
from app.models.content_translation import ContentTranslation
from app.services.content_i18n import (
    extract_bundle,
    source_hash,
    validate_bundle,
)
from app.services.llm_client import get_llm_client
from app.services.moderation import moderate_output

# Map BCP-47 code → human language name for the prompt.
_LANG_NAME = {str(x["code"]): str(x["prompt_name"]) for x in SUPPORTED_LANGUAGES}


def _prompt(language: str) -> str:
    name = _LANG_NAME.get(language, language)
    return (
        f"You are a professional translator localizing a children's financial-"
        f"education app into {name}. Translate ONLY the string values of the JSON "
        f"the user sends into {name}. Return a JSON object with the SAME keys and "
        f"the SAME array lengths. Keep numbers, currency symbols, proper nouns, "
        f"company names and ticker symbols unchanged. Do not add or remove keys. "
        f"For objects in arrays, translate only their text fields. Reply with JSON only."
    )


async def translate_entity(
    session: AsyncSession, entity_type: str, entity: Any, language: str
) -> tuple[ContentTranslation | None, str]:
    """Returns (row, action) where action ∈ {'generated','skipped','failed','noop'}."""
    if language == "en" or not is_supported_language(language):
        return None, "noop"
    bundle = extract_bundle(entity_type, entity)
    if not bundle:
        return None, "noop"
    h = source_hash(bundle)

    existing = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id == entity.id,
            ContentTranslation.language == language,
        )
    )
    if existing is not None:
        if existing.source == "curated":
            return existing, "skipped"  # never overwrite curated
        if existing.status == "active" and existing.source_hash == h:
            return existing, "skipped"  # fresh

    # Generate
    client = get_llm_client("standard")
    raw = await client.complete(
        _prompt(language),
        [{"role": "user", "content": json.dumps(bundle, ensure_ascii=False)}],
        temperature=0.2, max_tokens=1500, response_format="json",
    )
    status = "failed"
    translated: dict | None = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and validate_bundle(entity_type, bundle, parsed):
            verdict = await moderate_output(
                json.dumps(parsed, ensure_ascii=False), surface="content", language=language
            )
            if verdict.safe:
                translated, status = parsed, "active"
    except (ValueError, TypeError, KeyError):
        translated, status = None, "failed"

    row = await _upsert(session, entity_type, entity.id, language, translated, h, status)
    return row, ("generated" if status == "active" else "failed")


async def _upsert(session, entity_type, entity_id, language, translated, h, status):
    row = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id == entity_id,
            ContentTranslation.language == language,
        )
    )
    payload = translated if translated is not None else {}
    if row is None:
        row = ContentTranslation(
            entity_type=entity_type, entity_id=entity_id, language=language,
            translated_json=payload, source="auto", source_hash=h, status=status,
        )
        session.add(row)
    else:
        row.translated_json = payload
        row.source = "auto"
        row.source_hash = h
        row.status = status
    await session.flush()
    return row
