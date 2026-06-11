import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.services import digest_service, trial_reminder_service
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
