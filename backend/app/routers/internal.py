import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.services import (
    digest_service,
    module_purge_service,
    product_analytics_service,
    streak_risk_push,
    subscription_reconcile_service,
    trial_reminder_service,
)
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
