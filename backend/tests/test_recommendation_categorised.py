"""Tests for categorised recommendation logic."""
import uuid

from app.services.recommendation_service import _categorise_scored_modules


def _make_scored(*, topic="stocks", completed=0, total=5, score=0.5, order_index=0,
                 has_due_sr=False, weak_concepts=None):
    return {
        "module_id": uuid.uuid4(),
        "score": score,
        "reason": "Test reason",
        "topic": topic,
        "_completed_count": completed,
        "_total_count": total,
        "_order_index": order_index,
        "_lesson_id": uuid.uuid4(),
        "_has_due_sr": has_due_sr,
        "_weak_concepts": weak_concepts or [],
    }


class TestCategoriseModules:
    def test_partial_completion_goes_to_continue_learning(self):
        scored = [_make_scored(completed=2, total=5)]
        result = _categorise_scored_modules(scored)
        assert len(result["continue_learning"]) == 1
        assert len(result["practise_again"]) == 0
        assert len(result["something_new"]) == 0

    def test_due_sr_items_go_to_practise_again(self):
        scored = [_make_scored(completed=5, total=5, has_due_sr=True,
                               weak_concepts=["compound interest"])]
        result = _categorise_scored_modules(scored)
        assert len(result["practise_again"]) == 1
        assert result["practise_again"][0]["weak_concepts"] == ["compound interest"]

    def test_untouched_goes_to_something_new(self):
        scored = [_make_scored(completed=0, total=5)]
        result = _categorise_scored_modules(scored)
        assert len(result["something_new"]) == 1

    def test_max_2_per_category(self):
        scored = [
            _make_scored(completed=0, total=5, score=0.9),
            _make_scored(completed=0, total=5, score=0.8),
            _make_scored(completed=0, total=5, score=0.7),
        ]
        result = _categorise_scored_modules(scored)
        assert len(result["something_new"]) == 2

    def test_empty_input_returns_empty_categories(self):
        result = _categorise_scored_modules([])
        assert result["continue_learning"] == []
        assert result["practise_again"] == []
        assert result["something_new"] == []

    def test_review_prompt_when_due(self):
        scored = [_make_scored(completed=5, total=5, has_due_sr=True,
                               weak_concepts=["APR", "compound interest"])]
        result = _categorise_scored_modules(scored)
        item = result["practise_again"][0]
        assert item["review_prompt"] is not None
        assert "2" in item["review_prompt"]

    def test_no_review_prompt_when_not_due(self):
        scored = [_make_scored(completed=2, total=5)]
        result = _categorise_scored_modules(scored)
        item = result["continue_learning"][0]
        assert item.get("review_prompt") is None

    def test_partial_with_due_sr_goes_to_continue_learning(self):
        """Partial completion takes priority over practice — user is mid-module."""
        scored = [_make_scored(completed=2, total=5, has_due_sr=True,
                               weak_concepts=["APR"])]
        result = _categorise_scored_modules(scored)
        assert len(result["continue_learning"]) == 1

    def test_sorted_by_score_within_category(self):
        scored = [
            _make_scored(completed=0, total=5, score=0.3),
            _make_scored(completed=0, total=5, score=0.9),
        ]
        result = _categorise_scored_modules(scored)
        assert result["something_new"][0]["score"] >= result["something_new"][1]["score"]
