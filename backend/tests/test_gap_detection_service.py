"""Tests for gap detection service — per-topic strengths and gaps."""
import pytest

from app.services.gap_detection_service import (
    _classify_topic,
    _compute_overall_mastery,
    _sort_topics,
)


class TestClassifyTopic:
    def test_strong_when_mastery_above_threshold(self):
        assert _classify_topic(0.85) == "strong"

    def test_strong_at_exact_threshold(self):
        assert _classify_topic(0.8) == "strong"

    def test_needs_practice_below_threshold(self):
        assert _classify_topic(0.79) == "needs_practice"

    def test_needs_practice_at_zero(self):
        assert _classify_topic(0.0) == "needs_practice"

    def test_new_when_none(self):
        assert _classify_topic(None) == "new"


class TestComputeOverallMastery:
    def test_average_of_scores(self):
        result = _compute_overall_mastery([0.8, 0.6, 0.9])
        assert result == pytest.approx(0.7667, abs=0.001)

    def test_empty_returns_zero(self):
        assert _compute_overall_mastery([]) == 0.0

    def test_single_score(self):
        assert _compute_overall_mastery([0.75]) == 0.75


class TestSortTopics:
    def test_needs_practice_first(self):
        topics = [
            {"status": "strong", "topic": "a"},
            {"status": "needs_practice", "topic": "b"},
            {"status": "new", "topic": "c"},
        ]
        sorted_topics = _sort_topics(topics)
        assert sorted_topics[0]["status"] == "needs_practice"
        assert sorted_topics[1]["status"] == "strong"
        assert sorted_topics[2]["status"] == "new"

    def test_same_status_preserves_order(self):
        topics = [
            {"status": "needs_practice", "topic": "z"},
            {"status": "needs_practice", "topic": "a"},
        ]
        sorted_topics = _sort_topics(topics)
        assert sorted_topics[0]["topic"] == "z"
        assert sorted_topics[1]["topic"] == "a"
