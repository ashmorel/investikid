"""Tests for categorised recommendation and strengths schemas."""
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.ai import (
    CategorisedRecommendations,
    RecommendationCategoryItem,
    ReviewSummary,
    StrengthsAndGaps,
    TopicStrength,
)


class TestRecommendationCategoryItem:
    def test_valid_item(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.75,
            reason="Keep going!",
        )
        assert item.review_prompt is None
        assert item.weak_concepts == []

    def test_with_review_prompt_and_concepts(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.6,
            reason="Time to review!",
            review_prompt="3 concepts due",
            weak_concepts=["compound interest", "APR"],
        )
        assert item.review_prompt == "3 concepts due"
        assert len(item.weak_concepts) == 2

    def test_lesson_id_nullable(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=None,
            score=0.5,
            reason="Something new",
        )
        assert item.lesson_id is None


class TestReviewSummary:
    def test_valid_summary(self):
        s = ReviewSummary(due_count=3, next_due_at=datetime.now(UTC))
        assert s.due_count == 3

    def test_next_due_at_nullable(self):
        s = ReviewSummary(due_count=0, next_due_at=None)
        assert s.next_due_at is None


class TestCategorisedRecommendations:
    def test_empty_categories(self):
        r = CategorisedRecommendations(
            continue_learning=[],
            practise_again=[],
            something_new=[],
            review_summary=ReviewSummary(due_count=0, next_due_at=None),
        )
        assert len(r.continue_learning) == 0

    def test_full_response(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.8,
            reason="Great!",
        )
        r = CategorisedRecommendations(
            continue_learning=[item],
            practise_again=[],
            something_new=[item],
            review_summary=ReviewSummary(due_count=1, next_due_at=datetime.now(UTC)),
        )
        assert len(r.continue_learning) == 1
        assert len(r.something_new) == 1


class TestTopicStrength:
    def test_valid_strength(self):
        t = TopicStrength(
            topic="savings",
            mastery_score=0.85,
            status="strong",
            weak_count=0,
            due_for_review=0,
            total_concepts=5,
        )
        assert t.status == "strong"

    def test_needs_practice(self):
        t = TopicStrength(
            topic="interest_rates",
            mastery_score=0.58,
            status="needs_practice",
            weak_count=2,
            due_for_review=1,
            total_concepts=4,
        )
        assert t.weak_count == 2


class TestStrengthsAndGaps:
    def test_valid_response(self):
        r = StrengthsAndGaps(
            topics=[
                TopicStrength(
                    topic="savings",
                    mastery_score=0.85,
                    status="strong",
                    weak_count=0,
                    due_for_review=0,
                    total_concepts=5,
                ),
            ],
            overall_mastery=0.85,
        )
        assert r.overall_mastery == 0.85

    def test_empty_topics(self):
        r = StrengthsAndGaps(topics=[], overall_mastery=0.0)
        assert len(r.topics) == 0
