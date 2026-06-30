"""B5 — pure unit tests for the streak-milestone decision (no DB, no async)."""
from __future__ import annotations

from app.services.content_service import compute_streak_milestone
from app.services.streak_config import STREAK_MILESTONE


def test_milestone_when_streak_advances_to_multiple():
    assert compute_streak_milestone(STREAK_MILESTONE - 1, STREAK_MILESTONE, already=False) == STREAK_MILESTONE


def test_milestone_at_second_multiple():
    two = STREAK_MILESTONE * 2
    assert compute_streak_milestone(two - 1, two, already=False) == two


def test_no_milestone_on_same_day_repeat_even_at_multiple():
    # streak unchanged this completion (new == prev) → not a NEW milestone
    assert compute_streak_milestone(STREAK_MILESTONE, STREAK_MILESTONE, already=False) is None


def test_no_milestone_when_not_a_multiple():
    assert compute_streak_milestone(STREAK_MILESTONE, STREAK_MILESTONE + 1, already=False) is None


def test_no_milestone_when_already_completed():
    assert compute_streak_milestone(STREAK_MILESTONE - 1, STREAK_MILESTONE, already=True) is None
