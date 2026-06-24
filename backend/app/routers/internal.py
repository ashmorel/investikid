import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.services import (
    digest_service,
    investing_missions,
    market_content_pipeline,
    module_purge_service,
    product_analytics_service,
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
