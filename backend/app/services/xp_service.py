"""XP awarding seam with the daily-goal window (M7).

Every XP award (lessons, simulator trades, missions) flows through record_xp so
``xp_today`` stays correct and the daily goal can celebrate exactly once per day.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from app.services.content_service import compute_level

if TYPE_CHECKING:
    from app.models.user import UserProgress


@dataclass(frozen=True)
class XpResult:
    awarded: int
    goal_met_now: bool    # this award crossed the daily-goal line
    goal_met_today: bool  # the goal is met after this award


def record_xp(progress: UserProgress, amount: int, *, today: date | None = None) -> XpResult:
    """Add XP, maintain the per-day window, recompute level.

    Mutates ``progress`` in place (caller owns the transaction, matching the
    existing award-site convention).
    """
    today = today or datetime.now(UTC).date()
    # Column defaults only materialise on flush; tolerate fresh in-memory rows.
    goal = progress.daily_goal_xp or 30
    if progress.xp_today_date != today:
        progress.xp_today_date = today
        progress.xp_today = 0
    xp_today = progress.xp_today or 0
    met_before = xp_today >= goal
    progress.xp += amount
    progress.xp_today = xp_today + amount
    progress.level = compute_level(progress.xp)
    met_after = progress.xp_today >= goal
    return XpResult(amount, met_after and not met_before, met_after)
