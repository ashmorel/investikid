"""Tests for SM-2 lite spaced repetition service."""
import pytest

from app.services.spaced_repetition_service import calculate_next_review


class TestCalculateNextReview:
    def test_correct_first_rep_sets_interval_1(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=0, quality=4,
        )
        assert interval == 1
        assert rep == 1
        assert ease > 2.0

    def test_correct_second_rep_sets_interval_3(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=1, quality=4,
        )
        assert interval == 3
        assert rep == 2

    def test_correct_third_rep_multiplies_by_ease(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=3, repetition_count=2, quality=4,
        )
        assert interval == round(3 * 2.5)
        assert rep == 3

    def test_correct_adjusts_ease_factor(self):
        ease, _, _ = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=0, quality=4,
        )
        # With quality=4: ef += 0.1 - (5-4)*(0.08 + (5-4)*0.02) = 0.1 - 0.1 = 0
        assert ease == pytest.approx(2.5, abs=0.01)

    def test_wrong_resets_to_interval_1(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=10, repetition_count=5, quality=1,
        )
        assert interval == 1
        assert rep == 0

    def test_wrong_decreases_ease(self):
        ease, _, _ = calculate_next_review(
            ease_factor=2.5, interval_days=10, repetition_count=5, quality=1,
        )
        assert ease == pytest.approx(2.3, abs=0.01)

    def test_ease_factor_floors_at_1_3(self):
        ease, _, _ = calculate_next_review(
            ease_factor=1.3, interval_days=1, repetition_count=0, quality=1,
        )
        assert ease == 1.3

    def test_ease_factor_does_not_go_below_floor(self):
        ease, _, _ = calculate_next_review(
            ease_factor=1.4, interval_days=1, repetition_count=0, quality=1,
        )
        assert ease >= 1.3
