import uuid
from datetime import date

from app.models.user import UserProgress
from app.services.content_service import record_daily_activity


def _progress(streak=0, last=None, freezes=0):
    up = UserProgress(user_id=uuid.uuid4(), streak_count=streak, last_activity_date=last,
                      streak_freezes=freezes)
    return up


def test_first_activity_sets_streak_one():
    up = _progress()
    record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 1
    assert up.last_activity_date == date(2026, 6, 6)


def test_consecutive_day_increments():
    up = _progress(streak=1, last=date(2026, 6, 5))
    advanced = record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 2
    assert advanced is True


def test_same_day_is_idempotent():
    up = _progress(streak=3, last=date(2026, 6, 6))
    advanced = record_daily_activity(up, date(2026, 6, 6))
    assert up.streak_count == 3  # unchanged
    assert up.last_activity_date == date(2026, 6, 6)
    assert advanced is False
