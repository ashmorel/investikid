import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Level, Module
from app.models.content_translation import ContentTranslation
from app.schemas.admin import (
    CoverageBucket,
    CuratedTranslationRequest,
    TranslationCoverageOut,
    TranslationGenerateRequest,
    TranslationGenerateResult,
)
from app.services.content_i18n import extract_bundle, source_hash, validate_bundle
from app.services.translation_service import translate_entity

router = APIRouter()


# ── Content translations (i18n pipeline) ────────────────────────────
@router.post("/translations/generate", response_model=TranslationGenerateResult)
async def generate_translations(
    body: TranslationGenerateRequest, session: AsyncSession = Depends(get_session),
):
    """Auto-translate all content entities into a language (optionally one market).

    Tallies on the action returned by translate_entity: generated→translated,
    skipped→skipped_fresh, failed→failed; noop is uncounted.
    """
    res = TranslationGenerateResult()
    mod_q = select(Module)
    if body.market_code:
        mod_q = mod_q.where(Module.market_code == body.market_code)
    modules = (await session.scalars(mod_q)).all()
    module_ids = [m.id for m in modules]
    levels = (
        (await session.scalars(select(Level).where(Level.module_id.in_(module_ids)))).all()
        if module_ids else []
    )
    lessons = (
        (await session.scalars(select(Lesson).where(Lesson.module_id.in_(module_ids)))).all()
        if module_ids else []
    )

    for etype, items in (("module", modules), ("level", levels), ("lesson", lessons)):
        for ent in items:
            _row, action = await translate_entity(session, etype, ent, body.language)
            if action == "generated":
                res.translated += 1
            elif action == "skipped":
                res.skipped_fresh += 1
            elif action == "failed":
                res.failed += 1
            # action == "noop" (empty bundle / unsupported) → not counted
    await session.commit()
    return res


async def _fetch_entity(session: AsyncSession, entity_type: str, entity_id: uuid.UUID):
    model = {"module": Module, "level": Level, "lesson": Lesson}.get(entity_type)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown entity_type {entity_type!r}",
        )
    return await session.get(model, entity_id)


@router.put("/translations/curated")
async def put_curated_translation(
    body: CuratedTranslationRequest, session: AsyncSession = Depends(get_session),
):
    """Store/replace a human-authored (curated) translation for one entity.

    Validates the bundle against the entity's CURRENT English source; curated
    content bypasses moderation (human-authored)."""
    entity = await _fetch_entity(session, body.entity_type, body.entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity_not_found")

    source = extract_bundle(body.entity_type, entity)
    if not validate_bundle(body.entity_type, source, body.translated_json):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="translated_json structure does not match the English source",
        )
    h = source_hash(source)

    row = await session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == body.entity_type,
            ContentTranslation.entity_id == body.entity_id,
            ContentTranslation.language == body.language,
        )
    )
    if row is None:
        row = ContentTranslation(
            entity_type=body.entity_type, entity_id=body.entity_id, language=body.language,
            translated_json=body.translated_json, source="curated",
            source_hash=h, status="active",
        )
        session.add(row)
    else:
        row.translated_json = body.translated_json
        row.source = "curated"
        row.source_hash = h
        row.status = "active"
    await session.commit()
    return {"status": "ok", "entity_id": str(body.entity_id), "language": body.language}


@router.get("/translations/coverage", response_model=TranslationCoverageOut)
async def translation_coverage(
    language: str, session: AsyncSession = Depends(get_session),
):
    """Per-entity-type coverage for a language: active/failed/missing rows."""
    async def _bucket(entity_type: str, model) -> CoverageBucket:
        total = await session.scalar(select(func.count()).select_from(model)) or 0
        active = await session.scalar(
            select(func.count()).select_from(ContentTranslation).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.language == language,
                ContentTranslation.status == "active",
            )
        ) or 0
        failed = await session.scalar(
            select(func.count()).select_from(ContentTranslation).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.language == language,
                ContentTranslation.status == "failed",
            )
        ) or 0
        missing = max(total - active - failed, 0)
        return CoverageBucket(active=active, failed=failed, missing=missing)

    return TranslationCoverageOut(
        language=language,
        modules=await _bucket("module", Module),
        levels=await _bucket("level", Level),
        lessons=await _bucket("lesson", Lesson),
    )
