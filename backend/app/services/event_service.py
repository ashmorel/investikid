"""Seasonal events (M9) — AppSetting-driven, deploy-free.

One JSON blob under the `seasonal_event` key: {title, emoji, starts_at, ends_at,
xp_bonus_pct}. Bonus XP applies to LESSON completions only — the simulator/mission
economy stays untouched. Malformed/absent config = no event (defensive).
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.services.app_settings import get_setting, set_setting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

EVENT_KEY = "seasonal_event"


async def get_active_event(
    session: AsyncSession, *, now: datetime | None = None
) -> dict[str, Any] | None:
    raw = await get_setting(session, EVENT_KEY)
    if not raw:
        return None
    try:
        event = json.loads(raw)
        starts = datetime.fromisoformat(event["starts_at"])
        ends = datetime.fromisoformat(event["ends_at"])
        if starts.tzinfo is None or ends.tzinfo is None:
            raise ValueError("event window must be timezone-aware")
        now = now or datetime.now(UTC)
        if not (starts <= now < ends):
            return None
        return {
            "title": str(event.get("title", ""))[:60],
            "emoji": str(event.get("emoji", ""))[:8],
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
            "xp_bonus_pct": max(0, min(100, int(event.get("xp_bonus_pct", 0)))),
        }
    except Exception:  # noqa: BLE001 — bad config must never break child flows
        logger.warning("seasonal_event: malformed config ignored")
        return None


async def set_event(session: AsyncSession, event: dict | None) -> None:
    await set_setting(session, EVENT_KEY, json.dumps(event) if event else "")


def boosted_xp(base: int, event: dict[str, Any] | None) -> int:
    if not event or not event.get("xp_bonus_pct"):
        return base
    # Half-up (not banker's rounding): +25% of 10 XP reads as 13, never 12.
    import math

    return math.floor(base * (1 + event["xp_bonus_pct"] / 100) + 0.5)
