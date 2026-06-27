"""Server push via FCM (M7).

Safe-by-default: a logged no-op until ``FIREBASE_SERVICE_ACCOUNT_JSON`` is set
(same guard pattern as Stripe/Apple). One push per child per UTC day, enforced
via ``user_progress.last_push_sent_date``. Consent is double-gated upstream
(parent master switch + child toggle) — this module only ever sees tokens that
both gates allowed to register.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.time import today_utc
from app.models.push_device import PushDevice
from app.models.user import UserProgress
from app.services import product_analytics_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class UnregisteredTokenError(Exception):
    """The FCM token is dead — prune the device."""


def is_configured() -> bool:
    return bool(settings.firebase_service_account_json)


def _fcm_credentials():
    """Service-account credentials via google-auth (already a dependency of the
    Play-billing client) — deliberately NOT firebase-admin, whose httpx pin
    conflicts with this repo's."""
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_info(
        json.loads(settings.firebase_service_account_json),
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )


def _send_fcm(token: str, title: str, body: str) -> None:
    """One FCM HTTP v1 send. Raises UnregisteredTokenError for dead tokens."""
    import google.auth.transport.requests
    import httpx

    creds = _fcm_credentials()
    creds.refresh(google.auth.transport.requests.Request())
    response = httpx.post(
        f"https://fcm.googleapis.com/v1/projects/{creds.project_id}/messages:send",
        headers={"Authorization": f"Bearer {creds.token}"},
        json={
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
            }
        },
        timeout=10,
    )
    if response.status_code == 404 or "UNREGISTERED" in response.text:
        raise UnregisteredTokenError(token[:12])
    response.raise_for_status()


async def send_to_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    kind: str,
    title: str,
    body: str,
    today: date | None = None,
) -> bool:
    """Send one push to all of a user's devices. Returns True if anything sent.

    Applies the 1/day cap and prunes dead tokens. Never raises into the caller.
    """
    today = today or today_utc()
    progress = await session.get(UserProgress, user_id)
    if progress is None or progress.last_push_sent_date == today:
        return False
    devices = (
        await session.scalars(select(PushDevice).where(PushDevice.user_id == user_id))
    ).all()
    if not devices:
        return False
    if not is_configured():
        logger.info("push: unconfigured — would send %r to user %s", kind, user_id)
        return False

    sent_any = False
    for device in devices:
        try:
            # _send_fcm does a synchronous creds refresh + HTTP POST — run it off
            # the event loop so a slow FCM response can't stall the worker.
            await asyncio.to_thread(_send_fcm, device.token, title, body)
            sent_any = True
        except Exception as exc:  # noqa: BLE001 — prune dead tokens, log the rest
            name = type(exc).__name__
            if "Unregistered" in name or "NotFound" in name:
                await session.execute(
                    delete(PushDevice).where(PushDevice.id == device.id)
                )
                logger.info("push: pruned dead token for user %s", user_id)
            else:
                logger.warning("push: send failed for user %s: %s", user_id, name)

    if sent_any:
        progress.last_push_sent_date = today
        await product_analytics_service.record(
            session, "push_sent", user=None, role="child", props={"surface": kind}
        )
    return sent_any
