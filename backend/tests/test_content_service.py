from datetime import date

import pytest

from app.services.content_service import (
    compute_level,
    is_module_accessible,
    streak_after_activity,
)


def test_compute_level_progression():
    assert compute_level(0) == 1
    assert compute_level(99) == 1
    assert compute_level(100) == 2
    assert compute_level(249) == 2
    assert compute_level(250) == 3
    assert compute_level(500) == 4
    assert compute_level(1000) == 5
    assert compute_level(2500) == 6
    assert compute_level(5000) == 7
    assert compute_level(10_000) == 7


@pytest.mark.parametrize("user_country,module_countries,expected", [
    ("GB", ["GB", "US"], True),
    ("GB", ["US"], False),
    ("GB", [], True),
])
def test_is_module_accessible_country(user_country, module_countries, expected):
    assert is_module_accessible(
        user_country=user_country, is_premium_user=False,
        module_country_codes=module_countries, module_is_premium=False,
    ) is expected


def test_is_module_accessible_premium_gating():
    assert is_module_accessible("GB", False, ["GB"], True) is False
    assert is_module_accessible("GB", True, ["GB"], True) is True
    assert is_module_accessible("GB", False, ["GB"], False) is True


def test_streak_same_day_no_change():
    today = date(2026, 4, 24)
    assert streak_after_activity(last=today, current=3, freezes=0, today=today) == (3, today, 0)


def test_streak_next_day_increments():
    yesterday = date(2026, 4, 23)
    today = date(2026, 4, 24)
    assert streak_after_activity(last=yesterday, current=3, freezes=0, today=today) == (4, today, 0)


def test_streak_gap_resets_to_one():
    two_days_ago = date(2026, 4, 22)
    today = date(2026, 4, 24)
    assert streak_after_activity(last=two_days_ago, current=5, freezes=0, today=today) == (1, today, 0)


def test_streak_first_ever_activity():
    today = date(2026, 4, 24)
    assert streak_after_activity(last=None, current=0, freezes=0, today=today) == (1, today, 0)
