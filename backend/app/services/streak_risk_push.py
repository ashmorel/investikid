"""Streak-at-risk push trigger (M7) — the v1 server-push use case.

Selection: children with an active streak whose last activity was YESTERDAY
(streak dies at the end of today), parent master switch on, at least one
registered device. The per-user daily cap lives in push_service.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from app.core.pagination import iter_keyset
from app.core.time import today_utc
from app.models.push_device import PushDevice
from app.models.user import User, UserProgress
from app.services import push_service
from app.services.age_tier import age_tier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _copy(streak: int, tier: str) -> tuple[str, str]:
    if tier == "investor":
        return ("Keep your streak", f"Your {streak}-day streak ends today — one lesson keeps it going.")
    return ("Your streak misses you!", f"Your {streak}-day streak is waiting — one lesson keeps it alive 🔥")


async def run(session: AsyncSession, *, today: date | None = None) -> dict:
    today = today or today_utc()
    yesterday = today - timedelta(days=1)

    stmt = (
        select(User, UserProgress)
        .join(UserProgress, UserProgress.user_id == User.id)
        .where(
            User.push_enabled.is_(True),
            User.is_active.is_(True),
            UserProgress.streak_count > 0,
            UserProgress.last_activity_date == yesterday,
            exists().where(PushDevice.user_id == User.id),
        )
    )

    candidates = sent = 0
    async for user, progress in iter_keyset(session, stmt, key_col=User.id, key_of=lambda r: r[0].id):
        candidates += 1
        tier = age_tier(user.dob, today)
        title, body = _copy(progress.streak_count, tier)
        if await push_service.send_to_user(
            session, user.id, kind="streak_risk", title=title, body=body, today=today
        ):
            sent += 1
    await session.commit()
    return {"candidates": candidates, "sent": sent}
