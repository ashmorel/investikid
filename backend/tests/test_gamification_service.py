import pytest
from app.services.gamification_service import is_badge_earned

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_lesson_count_badge_earned():
    assert is_badge_earned("lesson_count", 5,
        {"lesson_count": 5, "streak_days": 0, "trade_count": 0, "total_xp": 0}) is True


def test_lesson_count_badge_not_yet():
    assert is_badge_earned("lesson_count", 5,
        {"lesson_count": 4, "streak_days": 0, "trade_count": 0, "total_xp": 0}) is False


def test_streak_days_badge():
    assert is_badge_earned("streak_days", 7,
        {"lesson_count": 0, "streak_days": 7, "trade_count": 0, "total_xp": 0}) is True


def test_trade_count_badge():
    assert is_badge_earned("trade_count", 1,
        {"lesson_count": 0, "streak_days": 0, "trade_count": 1, "total_xp": 0}) is True


def test_total_xp_badge():
    assert is_badge_earned("total_xp", 100,
        {"lesson_count": 0, "streak_days": 0, "trade_count": 0, "total_xp": 100}) is True


def test_unknown_condition_returns_false():
    assert is_badge_earned("asteroids_destroyed", 1,
        {"lesson_count": 99, "streak_days": 99, "trade_count": 99, "total_xp": 9999}) is False
