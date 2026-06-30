"""Tests for UserProgress.active_days counter (Task 1, A2 Unit 4).

Rules:
- First-ever activity → active_days becomes 1.
- A second call the SAME day → no increment (idempotent).
- Activity on a NEW day → +1.
"""
import uuid
from datetime import date

from app.models.user import UserProgress
from app.services.content_service import record_daily_activity


def _progress(streak=0, last=None, freezes=0, active_days=0):
    return UserProgress(
        user_id=uuid.uuid4(),
        streak_count=streak,
        last_activity_date=last,
        streak_freezes=freezes,
        active_days=active_days,
    )


def test_first_activity_sets_active_days_one():
    up = _progress()
    record_daily_activity(up, date(2026, 6, 10))
    assert up.active_days == 1


def test_same_day_second_call_does_not_increment():
    up = _progress(last=date(2026, 6, 10), active_days=1)
    record_daily_activity(up, date(2026, 6, 10))
    assert up.active_days == 1  # unchanged


def test_new_day_increments_active_days():
    up = _progress(streak=1, last=date(2026, 6, 10), active_days=1)
    record_daily_activity(up, date(2026, 6, 11))
    assert up.active_days == 2


def test_active_days_independent_of_streak_reset():
    """A streak can reset (gap > 1) but active_days still increments."""
    up = _progress(streak=5, last=date(2026, 6, 1), active_days=5)
    record_daily_activity(up, date(2026, 6, 10))  # gap of 9 days → streak resets to 1
    assert up.streak_count == 1
    assert up.active_days == 6
