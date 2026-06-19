from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_translation import ContentTranslation
from app.services.app_settings import get_enabled_content_languages
from app.services.content_i18n import apply_bundle


async def language_active(session: AsyncSession, language: str) -> bool:
    """Whether content should be localized for this language (kill-switch)."""
    if language == "en":
        return False
    return language in set(await get_enabled_content_languages(session))


async def load_translations(
    session: AsyncSession, entity_type: str, entity_ids: list[uuid.UUID], language: str
) -> dict[uuid.UUID, ContentTranslation]:
    if not entity_ids or language == "en":
        return {}
    rows = (await session.scalars(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.language == language,
            ContentTranslation.status == "active",
            ContentTranslation.entity_id.in_(entity_ids),
        )
    )).all()
    return {r.entity_id: r for r in rows}


def localize_fields(
    entity_type: str, fields: dict, translation: ContentTranslation | None
) -> tuple[dict, bool]:
    """Return (possibly-localized fields, machine_translated)."""
    if translation is None:
        return fields, False
    localized = apply_bundle(entity_type, fields, translation.translated_json)
    return localized, translation.source == "auto"
