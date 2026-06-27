"""Time helpers shared across the app.

``today_utc()`` is the single source of truth for "today" used by all the
daily-boundary logic (streaks, daily caps, daily content resets). Previously
``datetime.now(UTC).date()`` was copy-pasted across ~14 modules; centralising it
keeps every daily boundary on the same clock and makes the rule easy to find.
"""
from __future__ import annotations

from datetime import UTC, date, datetime


def today_utc() -> date:
    """The current calendar date in UTC."""
    return datetime.now(UTC).date()
