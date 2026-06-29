import asyncio
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.time import today_utc
from app.services import (
    concept_backfill_service,
    concept_classify_service,
    digest_service,
    investing_missions,
    market_content_pipeline,
    market_warm_service,
    module_purge_service,
    product_analytics_service,
    retention,
    streak_risk_push,
    subscription_reconcile_service,
    trial_reminder_service,
)
from app.services.video_salvage_service import extract_recovered_candidates
from app.video_health.run import run

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/video-health/run")
async def trigger_video_health(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    summary = await run(session)
    return {"ok": summary["ok"], "dead": summary["dead"], "unknown": summary["unknown"]}


@router.post("/trial-reminders/run")
async def trigger_trial_reminders(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await trial_reminder_service.run(session)


@router.post("/analytics-retention/run")
async def trigger_analytics_retention(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    deleted = await product_analytics_service.purge_old_events(
        session, now=datetime.now(UTC)
    )
    await session.commit()
    return {"deleted": deleted}


@router.post("/push-streak-risk/run")
async def trigger_streak_risk_push(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await streak_risk_push.run(session)


@router.post("/weekly-digest/run")
async def trigger_weekly_digests(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await digest_service.run_weekly_digests(session)


@router.post("/subscriptions/reconcile")
async def trigger_subscription_reconcile(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    summary = await subscription_reconcile_service.run(session)
    await session.commit()
    return summary


@router.post("/purge-archived-modules")
async def trigger_purge_archived_modules(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    purged = await module_purge_service.purge_archived_modules(session, now=datetime.now(UTC))
    await session.commit()
    return {"purged": purged}


@router.post("/purge-accounts/run")
async def trigger_purge_accounts(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Hard-purge PII for accounts soft-deleted past the retention window
    (the cron equivalent of the `purge-accounts` CLI command)."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    purged = await retention.purge_expired_accounts(session, today_utc())
    return {"purged": purged}


@router.post("/market-warm/run")
async def trigger_market_warm(
    x_cron_secret: str | None = Header(default=None),
):
    """Warm the shared market cache (featured quotes + movers) for all regions."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    from app.routers.simulator import get_price_provider
    provider = get_price_provider()
    return await asyncio.to_thread(market_warm_service.warm_all, provider)


@router.post("/video-candidates/extract")
async def trigger_video_candidate_extract(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await extract_recovered_candidates(session)


@router.post("/collectables/reconcile")
async def trigger_collectables_reconcile(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    from sqlalchemy import select

    from app.models.user import UserProgress
    from app.services.collectables_service import grant_eligible
    progresses = (await session.scalars(select(UserProgress).where(UserProgress.streak_count > 0))).all()
    total = 0
    for p in progresses:
        total += len(await grant_eligible(session, p))
    await session.commit()
    return {"status": "ok", "granted": total}


@router.post("/market-content")
async def market_content_step(
    market: str,
    action: str,
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """One step of the market content pipeline (operator automation). action ∈
    {scaffold, generate, publish, sync-missions}; call `generate` repeatedly until
    remaining==0, then `publish`. `sync-missions` (re)attaches simulator missions to
    investing modules without republishing. Cron-secret gated (no admin UI / JWT)."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    market = market.upper()
    try:
        if action == "scaffold":
            return await market_content_pipeline.scaffold_market(session, market)
        if action == "generate":
            return await market_content_pipeline.generate_next_level(session, market)
        if action == "publish":
            return await market_content_pipeline.publish_market(session, market)
        if action == "sync-missions":
            result = await investing_missions.sync_investing_missions(session, market_code=market)
            await session.commit()
            return {"market": market, "stage": "sync-missions", **result}
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST, "action must be scaffold|generate|publish|sync-missions"
    )


@router.post("/concepts/classify/reset")
async def trigger_concept_classify_reset(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Reset concept_classified_at to NULL for lessons that are still untagged
    (concept_id IS NULL).  This lets the corrected global-matching classifier
    retry lessons the previous topic-scoped run stamped-and-skipped.

    ONLY lessons with concept_id IS NULL are touched — already-tagged lessons
    (concept_id IS NOT NULL) are never modified.  Returns the reset count."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    from sqlalchemy import update

    from app.models.content import Lesson
    result = await session.execute(
        update(Lesson)
        .where(Lesson.concept_id.is_(None), Lesson.concept_classified_at.isnot(None))
        .values(concept_classified_at=None)
    )
    await session.commit()
    return {"reset": result.rowcount}


_CLASSIFY_ALLOWED_TIERS = {"lite", "standard", "premium"}


@router.post("/concepts/classify")
async def trigger_concept_classify(
    limit: int = 200,
    tier: str = "lite",
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Idempotent LLM-based backfill: classify published lessons without a
    concept_id by asking the LLM to pick from the full concept taxonomy
    (matching is global by unique slug, independent of the module's topic).
    The model can NEVER invent a concept — every pick is validated via
    resolve_slug_global before being written.  Safe to run repeatedly.

    tier ∈ {lite, standard, premium} (default: lite).  Use standard or premium
    for a coverage pass over lessons the lite model abstained on."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    if tier not in _CLASSIFY_ALLOWED_TIERS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"tier must be one of {sorted(_CLASSIFY_ALLOWED_TIERS)}",
        )
    effective_limit = max(1, min(limit, 500))
    result = await concept_classify_service.classify_untagged_lessons(
        session, limit=effective_limit, tier=tier
    )
    await session.commit()
    return result


_VERIFY_ALLOWED_TIERS = {"lite", "standard", "premium"}
_VERIFY_MAX_LIMIT = 100


@router.post("/diagnostic-items/verify")
async def trigger_diagnostic_verify(
    limit: int = 25,
    tier: str = "premium",
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Cron-gated sweep of approved diagnostic items that have not yet been
    verified (verifier_status IS NULL).  Mirrors the admin sweep endpoint but
    is accessible without an admin session, guarded by X-Cron-Secret instead.

    Sweeps approved items with verifier_status IS NULL first (drain-safe:
    re-running the same batch never re-bills already-verified items).

    tier ∈ {lite, standard, premium} (default: premium).
    limit is capped at 100; default 25.
    Returns {verified, agree, mismatch, ambiguous, error, flagged: [...]}.
    """
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    if tier not in _VERIFY_ALLOWED_TIERS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"tier must be one of {sorted(_VERIFY_ALLOWED_TIERS)}",
        )
    effective_limit = max(1, min(limit, _VERIFY_MAX_LIMIT))
    from app.services.diagnostic_item_service import run_verify_sweep

    result = await run_verify_sweep(
        session,
        status="approved",
        market_code=None,
        topic=None,
        limit=effective_limit,
        only_unverified=True,
        tier=tier,
    )
    await session.commit()
    return result


@router.post("/concepts/backfill")
async def trigger_concept_backfill(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Idempotent backfill: map existing WeakConcept + published Lesson rows without
    a concept_id to taxonomy concepts.  Safe to run repeatedly — only NULL rows are
    touched and already-tagged rows are never modified."""
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    result = await concept_backfill_service.run_backfill(session)
    await session.commit()
    return result
