import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.content import Lesson, Level, Module
from app.models.content_translation import ContentTranslation
from app.models.gamification import Badge, Challenge, UserBadge
from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.models.user import User
from app.models.video_asset import VideoAsset
from app.models.video_health import VideoHealth
from app.routers import admin_content, admin_drafts, admin_generation
from app.routers.admin_auth import get_current_admin
from app.schemas.admin import (
    AdminSettingsOut,
    AdminSettingsUpdate,
    BadgeCreate,
    BadgeOut,
    BadgeUpdate,
    ChallengeCreate,
    ChallengeOut,
    ChallengeUpdate,
    CoverageBucket,
    CuratedModuleSuggestion,
    CuratedTranslationRequest,
    MarketBriefOut,
    MarketBriefUpdate,
    MarketScaffoldResult,
    ModuleFromSuggestionResult,
    ModuleSuggestion,
    TranslationCoverageOut,
    TranslationGenerateRequest,
    TranslationGenerateResult,
    VideoHealthCheckResult,
    VideoHealthItem,
    VideoPresignRequest,
    VideoPresignResponse,
)
from app.schemas.parent import PremiumToggleRequest
from app.services import storage, video_health_service
from app.services.app_settings import (
    get_alert_emails,
    get_enabled_content_languages,
    get_investing_mission_cash,
    get_market_completion_bonus_coins,
    get_market_enroll_bonus_coins,
    get_setting,
    get_starting_cash,
    get_trade_commission_pct,
    set_alert_emails,
    set_enabled_content_languages,
    set_investing_mission_cash,
    set_market_completion_bonus_coins,
    set_market_enroll_bonus_coins,
    set_starting_cash,
    set_trade_commission_pct,
)
from app.services.content_i18n import extract_bundle, source_hash, validate_bundle
from app.services.entitlements import set_premium
from app.services.event_service import EVENT_KEY, set_event
from app.services.llm_client import probe_all_providers
from app.services.market_brief_service import (
    BriefGenerationError,
    generate_brief,
)
from app.services.market_module_suggester import suggest_modules
from app.services.market_scaffold_service import scaffold_market_from_gb
from app.services.translation_service import translate_entity

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])
router.include_router(admin_content.router)
router.include_router(admin_generation.router)
router.include_router(admin_drafts.router)


# ── Market briefs ───────────────────────────────────────────────────
@router.post("/markets/{code}/brief/generate", response_model=MarketBriefOut)
@limiter.limit("5/minute")
async def generate_market_brief(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    try:
        brief = await generate_brief(session, market)
    except (BriefGenerationError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="brief generation failed"
        ) from exc
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.get("/markets/{code}/brief", response_model=MarketBriefOut)
async def get_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return MarketBriefOut.model_validate(brief)


@router.put("/markets/{code}/brief", response_model=MarketBriefOut)
async def update_market_brief(
    code: str,
    payload: MarketBriefUpdate,
    session: AsyncSession = Depends(get_session),
):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    if not isinstance(payload.brief_json, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brief_json must be an object"
        )
    brief.brief_json = payload.brief_json
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/brief/verify", response_model=MarketBriefOut)
async def verify_market_brief(code: str, session: AsyncSession = Depends(get_session)):
    brief = await session.get(MarketBrief, code)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    brief.status = "verified"
    await session.commit()
    return MarketBriefOut.model_validate(brief)


@router.post("/markets/{code}/scaffold", response_model=MarketScaffoldResult)
@limiter.limit("5/minute")
async def scaffold_market(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    summary = await scaffold_market_from_gb(session, code)
    return MarketScaffoldResult.model_validate(summary)


@router.post("/markets/{code}/module-suggestions", response_model=list[ModuleSuggestion])
@limiter.limit("5/minute")
async def market_module_suggestions(
    request: Request,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    suggestions = await suggest_modules(session, market)
    return [ModuleSuggestion(**s) for s in suggestions]


@router.post(
    "/markets/{code}/modules/from-suggestion", response_model=ModuleFromSuggestionResult
)
@limiter.limit("5/minute")
async def create_module_from_suggestion(
    request: Request,
    code: str,
    body: CuratedModuleSuggestion,
    session: AsyncSession = Depends(get_session),
):
    """One-click scaffold: create a new module + one starter level (no lessons) in
    the given market from a curated suggester item. No auto-publish, no auto-delete."""
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    max_order = await session.scalar(
        select(func.max(Module.order_index)).where(Module.market_code == code)
    )
    module = Module(
        topic=(body.topic or "general")[:30],
        title=body.title,
        country_codes=[],
        market_code=code,
        is_premium=False,
        order_index=(max_order or -1) + 1,
        prerequisite_ids=[],
    )
    session.add(module)
    await session.flush()
    level = Level(module_id=module.id, title="Level 1", order_index=0, is_premium=False)
    session.add(level)
    await session.commit()
    return ModuleFromSuggestionResult(
        module_id=module.id,
        level_id=level.id,
        suggested_concepts=body.suggested_concepts,
    )


@router.post("/markets/{code}/publish")
async def publish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    lesson_count = await session.scalar(
        select(func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == code)
    ) or 0
    if lesson_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="market has no lessons to publish"
        )
    market.has_content = True
    await session.commit()
    return {"code": code, "has_content": True}


@router.post("/markets/{code}/unpublish")
async def unpublish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    market.has_content = False
    await session.commit()
    return {"code": code, "has_content": False}


# ── Badges ──────────────────────────────────────────────────────────
@router.get("/badges", response_model=list[BadgeOut])
async def list_badges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Badge))
    return list(result.all())


@router.post("/badges", response_model=BadgeOut)
async def create_badge(payload: BadgeCreate, session: AsyncSession = Depends(get_session)):
    badge = Badge(**payload.model_dump())
    session.add(badge)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.put("/badges/{badge_id}", response_model=BadgeOut)
async def update_badge(
    badge_id: uuid.UUID, payload: BadgeUpdate, session: AsyncSession = Depends(get_session),
):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(badge, field, value)
    await session.commit()
    await session.refresh(badge)
    return badge


@router.delete("/badges/{badge_id}")
async def delete_badge(badge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    badge = await session.get(Badge, badge_id)
    if badge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    # Check for user references
    earned_count = await session.scalar(
        select(func.count()).select_from(UserBadge).where(UserBadge.badge_id == badge_id)
    )
    if earned_count and earned_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete badge — {earned_count} user(s) have earned it",
        )
    await session.delete(badge)
    await session.commit()
    return {"status": "ok"}


# ── Challenges ──────────────────────────────────────────────────────
@router.get("/challenges", response_model=list[ChallengeOut])
async def list_challenges(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Challenge).order_by(Challenge.starts_at.desc()))
    return list(result.all())


@router.post("/challenges", response_model=ChallengeOut)
async def create_challenge(payload: ChallengeCreate, session: AsyncSession = Depends(get_session)):
    challenge = Challenge(**payload.model_dump())
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.put("/challenges/{challenge_id}", response_model=ChallengeOut)
async def update_challenge(
    challenge_id: uuid.UUID, payload: ChallengeUpdate, session: AsyncSession = Depends(get_session),
):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(challenge, field, value)
    await session.commit()
    await session.refresh(challenge)
    return challenge


@router.delete("/challenges/{challenge_id}")
async def delete_challenge(challenge_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    challenge = await session.get(Challenge, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    await session.delete(challenge)
    await session.commit()
    return {"status": "ok"}


# ── Utility ─────────────────────────────────────────────────────────
@router.get("/countries")
async def list_countries(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(User.country_code).where(User.country_code.isnot(None)).distinct()
    )
    return sorted(result.all())


# ── Settings ────────────────────────────────────────────────────────
@router.get("/settings", response_model=AdminSettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)):
    emails = await get_alert_emails(session)
    cash = await get_starting_cash(session)
    mission_cash = await get_investing_mission_cash(session)
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        investing_mission_cash={k: str(v) for k, v in mission_cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


@router.put("/settings", response_model=AdminSettingsOut)
async def update_settings(
    body: AdminSettingsUpdate, session: AsyncSession = Depends(get_session),
):
    await set_alert_emails(session, body.alert_emails)
    if body.starting_cash is not None:
        await set_starting_cash(session, {k: Decimal(v) for k, v in body.starting_cash.items()})
    if body.investing_mission_cash is not None:
        await set_investing_mission_cash(
            session, {k: Decimal(v) for k, v in body.investing_mission_cash.items()}
        )
    if body.trade_commission_pct is not None:
        await set_trade_commission_pct(session, Decimal(body.trade_commission_pct))
    if body.market_enroll_bonus_coins is not None:
        await set_market_enroll_bonus_coins(session, body.market_enroll_bonus_coins)
    if body.market_completion_bonus_coins is not None:
        await set_market_completion_bonus_coins(session, body.market_completion_bonus_coins)
    if body.enabled_content_languages is not None:
        await set_enabled_content_languages(session, body.enabled_content_languages)
    if body.clear_seasonal_event:
        await set_event(session, None)
    elif body.seasonal_event is not None:
        await set_event(session, {
            "title": body.seasonal_event.title,
            "emoji": body.seasonal_event.emoji,
            "starts_at": body.seasonal_event.starts_at.isoformat(),
            "ends_at": body.seasonal_event.ends_at.isoformat(),
            "xp_bonus_pct": body.seasonal_event.xp_bonus_pct,
        })
    await session.commit()
    cash = await get_starting_cash(session)
    mission_cash = await get_investing_mission_cash(session)
    pct = await get_trade_commission_pct(session)
    enroll_bonus = await get_market_enroll_bonus_coins(session)
    completion_bonus = await get_market_completion_bonus_coins(session)
    content_languages = await get_enabled_content_languages(session)
    raw_event = await get_setting(session, EVENT_KEY)
    return AdminSettingsOut(
        alert_emails=body.alert_emails,
        starting_cash={k: str(v) for k, v in cash.items()},
        investing_mission_cash={k: str(v) for k, v in mission_cash.items()},
        trade_commission_pct=str(pct),
        market_enroll_bonus_coins=enroll_bonus,
        market_completion_bonus_coins=completion_bonus,
        enabled_content_languages=content_languages,
        seasonal_event=json.loads(raw_event) if raw_event else None,
    )


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


# ── Video health ────────────────────────────────────────────────────
async def _video_health_items(session: AsyncSession) -> list[VideoHealthItem]:
    rows = (await session.execute(
        select(Lesson, Module.id, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.type == "video")
        .order_by(Module.order_index, Lesson.order_index)
    )).all()
    health = {
        h.lesson_id: h
        for h in (await session.scalars(select(VideoHealth))).all()
    }
    out: list[VideoHealthItem] = []
    for lesson, module_id, module_title in rows:
        h = health.get(lesson.id)
        out.append(VideoHealthItem(
            lesson_id=lesson.id, module_id=module_id, module_title=module_title,
            lesson_title=(lesson.content_json or {}).get("caption") or "Video lesson",
            youtube_id=(lesson.content_json or {}).get("youtube_id", ""),
            status=h.status if h else None,
            http_status=h.http_status if h else None,
            checked_at=h.checked_at if h else None,
        ))
    return out


@router.get("/video-health", response_model=list[VideoHealthItem])
async def admin_video_health(session: AsyncSession = Depends(get_session)):
    return await _video_health_items(session)


@router.post("/video-health/check", response_model=VideoHealthCheckResult)
async def admin_video_health_check(session: AsyncSession = Depends(get_session)):
    summary = await video_health_service.check_all_videos(session)
    await session.commit()
    items = await _video_health_items(session)
    return VideoHealthCheckResult(summary=summary, items=items)


# ── Video assets (R2 presigned upload) ──────────────────────────────
@router.post("/video-assets/presign", response_model=VideoPresignResponse)
async def admin_presign_video(
    payload: VideoPresignRequest,
    session: AsyncSession = Depends(get_session),
):
    if not storage.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if payload.size_bytes > settings.r2_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file too large")
    key = f"videos/{uuid.uuid4()}.mp4"
    asset = VideoAsset(
        storage_key=key,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        original_filename=payload.filename[:255],
        created_at=datetime.now(UTC),
    )
    session.add(asset)
    await session.commit()
    return VideoPresignResponse(
        asset_id=asset.id,
        key=key,
        upload_url=storage.create_presigned_put(
            key, payload.content_type, content_length=payload.size_bytes
        ),
        public_url=storage.public_url(key),
    )


# ── Premium comp (admin-only) ────────────────────────────────────────────────
@router.post("/users/{user_id}/premium")
async def admin_set_user_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    await set_premium(session, user, value=payload.premium, actor="admin")
    await session.commit()
    return {"status": "ok", "premium": payload.premium}


# ── LLM provider health probe ────────────────────────────────────────────────
@router.get("/llm-status")
async def llm_status() -> list[dict]:
    """Ping each configured LLM provider with a trivial completion.

    Returns per-provider ok/error status without exposing any API key material.
    Admin-only (enforced by the router-level dependency).
    """
    return await probe_all_providers()


