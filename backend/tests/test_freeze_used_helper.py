"""B6 — pure unit tests for `freeze_will_be_consumed`.

Sync tests (NO asyncio mark) — the helper is pure date arithmetic, so keeping
them in their own file avoids the asyncio-mark-on-sync warning.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.services.content_service import freeze_will_be_consumed, repair_eligibility
from app.services.streak_config import (
    STREAK_FREEZE_GAP,
    STREAK_REPAIR_COST,
    STREAK_REPAIR_MIN_STREAK,
)

TODAY = date(2026, 6, 30)


class _Prog:
    """Minimal stand-in for UserProgress for the pure eligibility helper."""

    def __init__(self, *, last, streak, freezes=0):
        self.last_activity_date = last
        self.streak_count = streak
        self.streak_freezes = freezes


def _at(days_ago):
    return TODAY - timedelta(days=days_ago)


def test_freeze_consumed_when_one_missed_day_and_freeze_held():
    last = TODAY - timedelta(days=STREAK_FREEZE_GAP)  # gap == 2 (one missed day)
    assert freeze_will_be_consumed(last, 1, TODAY) is True


def test_not_consumed_when_no_freeze_held():
    last = TODAY - timedelta(days=STREAK_FREEZE_GAP)
    assert freeze_will_be_consumed(last, 0, TODAY) is False


def test_not_consumed_on_consecutive_day():
    last = TODAY - timedelta(days=1)  # gap == 1, still alive
    assert freeze_will_be_consumed(last, 1, TODAY) is False


def test_not_consumed_same_day():
    assert freeze_will_be_consumed(TODAY, 1, TODAY) is False


def test_not_consumed_when_gap_too_large():
    last = TODAY - timedelta(days=3)  # gap == 3, beyond a single freeze
    assert freeze_will_be_consumed(last, 1, TODAY) is False


def test_not_consumed_when_last_is_none():
    assert freeze_will_be_consumed(None, 1, TODAY) is False


# --- repair_eligibility matrix ----------------------------------------------

def test_repair_gap1_not_eligible():
    # still alive — no repair
    assert repair_eligibility(_Prog(last=_at(1), streak=5), TODAY).eligible is False


def test_repair_gap2_no_freeze_eligible():
    e = repair_eligibility(_Prog(last=_at(2), streak=5, freezes=0), TODAY)
    assert e.eligible is True
    assert e.restorable_streak == 5
    assert e.cost == STREAK_REPAIR_COST


def test_repair_gap2_with_freeze_not_eligible():
    # auto-saved by the held freeze → no repair needed
    assert repair_eligibility(_Prog(last=_at(2), streak=5, freezes=1), TODAY).eligible is False


def test_repair_gap3_eligible_regardless_of_freeze():
    # one freeze only covers a single missed day, so gap 3 still needs repair
    assert repair_eligibility(_Prog(last=_at(3), streak=5, freezes=1), TODAY).eligible is True
    assert repair_eligibility(_Prog(last=_at(3), streak=5, freezes=0), TODAY).eligible is True


def test_repair_gap4_too_late():
    assert repair_eligibility(_Prog(last=_at(4), streak=5), TODAY).eligible is False


def test_repair_streak_below_minimum_not_eligible():
    below = STREAK_REPAIR_MIN_STREAK - 1
    assert repair_eligibility(_Prog(last=_at(2), streak=below), TODAY).eligible is False


def test_repair_streak_at_minimum_eligible():
    assert repair_eligibility(
        _Prog(last=_at(2), streak=STREAK_REPAIR_MIN_STREAK), TODAY
    ).eligible is True


def test_repair_last_none_not_eligible():
    assert repair_eligibility(_Prog(last=None, streak=5), TODAY).eligible is False
