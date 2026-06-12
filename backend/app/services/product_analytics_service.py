"""First-party product analytics (M4).

Not to be confused with ``analytics_service`` (the parent-facing per-child
progress analytics). This module is the ONLY writer for ``analytics_events``
and (with the admin analytics endpoint) the ONLY reader. Events are
service-improvement counts — they must never feed personalization, so nothing
here is imported by recommendation/content paths.
Spec: docs/superpowers/specs/2026-06-12-product-analytics-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete

from app.core.config import settings
from app.models.analytics import AnalyticsEvent
from app.services.age_tier import age_tier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

# Closed event allowlists. Client events may arrive via POST /analytics/events;
# server events may only be recorded by backend code paths.
CLIENT_EVENTS: frozenset[str] = frozenset(
    {"home_view", "home_cta_tap", "quicklink_tap", "paywall_view"}
)
SERVER_EVENTS: frozenset[str] = frozenset(
    {"lesson_completed", "subscription_activated", "trial_started", "digest_sent"}
)
ALL_EVENTS: frozenset[str] = CLIENT_EVENTS | SERVER_EVENTS

# Content-free prop keys. Values are coerced to short strings/bools on ingest.
ALLOWED_PROP_KEYS: frozenset[str] = frozenset(
    {"module_id", "level_id", "lesson_id", "surface", "repeat", "plan", "source", "variant"}
)
_MAX_PROP_VALUE_LEN = 64


def _clean_props(props: dict | None) -> dict | None:
    if not props:
        return None
    cleaned: dict = {}
    for key, value in props.items():
        if key not in ALLOWED_PROP_KEYS:
            continue
        if isinstance(value, bool) or value is None:
            cleaned[key] = value
        else:
            cleaned[key] = str(value)[:_MAX_PROP_VALUE_LEN]
    return cleaned or None


async def record(
    session: AsyncSession,
    name: str,
    *,
    user: User | None = None,
    role: str,
    props: dict | None = None,
) -> None:
    """Record one analytics event. Best-effort: NEVER raises into the caller.

    Snapshots ``age_tier`` (raw DOB tier — the analytics dimension; the W5
    presentation override is deliberately ignored) and ``is_premium`` at event
    time. The row rides the caller's transaction.
    """
    try:
        if name not in ALL_EVENTS:
            logger.warning("analytics: dropped unknown event %r", name)
            return
        tier = None
        premium = None
        if user is not None:
            if getattr(user, "dob", None):
                tier = age_tier(user.dob, datetime.now(UTC).date())
            premium = bool(getattr(user, "is_premium", False))
        session.add(
            AnalyticsEvent(
                event_name=name,
                user_id=user.id if user is not None else None,
                role=role,
                age_tier=tier,
                is_premium=premium,
                props=_clean_props(props),
            )
        )
    except Exception:  # noqa: BLE001 — analytics must never break the feature path
        logger.exception("analytics: failed to record %r", name)


async def detach_user(session: AsyncSession, user_ids: list) -> int:
    """Null the pseudonymous join key on a purged account's events."""
    from sqlalchemy import update

    result = await session.execute(
        update(AnalyticsEvent)
        .where(AnalyticsEvent.user_id.in_(user_ids))
        .values(user_id=None)
    )
    return result.rowcount or 0


async def purge_old_events(session: AsyncSession, *, now: datetime) -> int:
    """Delete raw events older than the retention window. Returns rows deleted."""
    cutoff = now - timedelta(days=settings.analytics_retention_days)
    result = await session.execute(
        delete(AnalyticsEvent).where(AnalyticsEvent.occurred_at < cutoff)
    )
    return result.rowcount or 0
