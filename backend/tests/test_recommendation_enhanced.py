"""Tests for the enhanced recommendation algorithm with DB-driven prerequisites and age filtering."""
import uuid
from datetime import date
from unittest.mock import MagicMock

from app.services.recommendation_service import (
    _apply_hard_filters,
    _build_reason,
    _calculate_age,
    _score_module,
)


def _make_user(*, dob=date(2015, 1, 1), topic_path="stocks", country_code="GB",
               home_market_code="GB", active_market_code=None,
               is_premium_val=False, profiling_enabled=True):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.dob = dob
    user.topic_path = topic_path
    user.country_code = country_code
    user.home_market_code = home_market_code
    user.active_market_code = active_market_code if active_market_code is not None else home_market_code
    user.content_region = None
    user.is_premium = is_premium_val
    user.profiling_enabled = profiling_enabled
    return user


def _make_module(*, topic="stocks", prerequisite_ids=None, min_age=None, max_age=None,
                 is_premium=False, country_codes=None, market_code="GB", order_index=0):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.topic = topic
    m.title = f"Module {topic}"
    m.prerequisite_ids = prerequisite_ids or []
    m.min_age = min_age
    m.max_age = max_age
    m.is_premium = is_premium
    m.country_codes = country_codes or []
    m.market_code = market_code
    m.order_index = order_index
    return m


class TestCalculateAge:
    def test_basic_age(self):
        assert _calculate_age(date(2015, 1, 1), date(2026, 6, 1)) == 11

    def test_before_birthday(self):
        assert _calculate_age(date(2015, 7, 1), date(2026, 6, 1)) == 10

    def test_on_birthday(self):
        assert _calculate_age(date(2015, 6, 1), date(2026, 6, 1)) == 11


class TestHardFilters:
    def test_excludes_completed_module(self):
        user = _make_user()
        module = _make_module()
        assert _apply_hard_filters(module, user, {module.id}, set(), 11) is False

    def test_excludes_unmet_prerequisites(self):
        prereq_id = uuid.uuid4()
        user = _make_user()
        module = _make_module(prerequisite_ids=[prereq_id])
        assert _apply_hard_filters(module, user, set(), set(), 11) is False

    def test_includes_met_prerequisites(self):
        prereq_id = uuid.uuid4()
        user = _make_user()
        module = _make_module(prerequisite_ids=[prereq_id])
        assert _apply_hard_filters(module, user, set(), {prereq_id}, 11) is True

    def test_excludes_age_too_young(self):
        user = _make_user(dob=date(2020, 1, 1))
        module = _make_module(min_age=10)
        assert _apply_hard_filters(module, user, set(), set(), 6) is False

    def test_excludes_age_too_old(self):
        user = _make_user(dob=date(2010, 1, 1))
        module = _make_module(max_age=12)
        assert _apply_hard_filters(module, user, set(), set(), 16) is False

    def test_includes_age_in_range(self):
        user = _make_user(dob=date(2015, 1, 1))
        module = _make_module(min_age=8, max_age=14)
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_includes_no_age_restriction(self):
        user = _make_user()
        module = _make_module()
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_excludes_premium_for_free_user(self):
        user = _make_user(is_premium_val=False)
        module = _make_module(is_premium=True)
        assert _apply_hard_filters(module, user, set(), set(), 11) is False

    def test_excludes_wrong_market(self):
        user = _make_user(home_market_code="GB")
        module = _make_module(market_code="US")
        assert _apply_hard_filters(module, user, set(), set(), 11) is False

    def test_includes_matching_market(self):
        user = _make_user(home_market_code="GB")
        module = _make_module(market_code="GB")
        assert _apply_hard_filters(module, user, set(), set(), 11) is True

    def test_includes_same_market(self):
        user = _make_user(home_market_code="US")
        module = _make_module(market_code="US")
        assert _apply_hard_filters(module, user, set(), set(), 11) is True


class TestScoring:
    def test_topic_match_scores_higher(self):
        user = _make_user(topic_path="stocks")
        matching = _make_module(topic="stocks")
        non_matching = _make_module(topic="savings")
        mastery_by_topic = {}
        s1 = _score_module(matching, user, 0, 3, mastery_by_topic)
        s2 = _score_module(non_matching, user, 0, 3, mastery_by_topic)
        assert s1["score"] > s2["score"]

    def test_partially_completed_scores_higher(self):
        user = _make_user(topic_path=None)
        m = _make_module(topic="stocks")
        mastery_by_topic = {}
        partial = _score_module(m, user, 2, 5, mastery_by_topic)
        untouched = _score_module(m, user, 0, 5, mastery_by_topic)
        assert partial["score"] > untouched["score"]


class TestReasonStrings:
    def test_near_completion_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=3, total=5, is_topic_match=False, is_variety=False, readiness_score=1.0)
        assert "keep going" in reason.lower() or "halfway" in reason.lower()

    def test_topic_match_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=0, total=5, is_topic_match=True, is_variety=False, readiness_score=1.0)
        assert "stocks" in reason.lower()

    def test_variety_reason(self):
        m = _make_module(topic="savings")
        reason = _build_reason(m, completed=0, total=5, is_topic_match=False, is_variety=True, readiness_score=1.0)
        assert "new" in reason.lower() or "explore" in reason.lower()

    def test_readiness_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=0, total=5, is_topic_match=False, is_variety=False, readiness_score=1.0)
        assert "ready" in reason.lower() or "next level" in reason.lower()

    def test_default_reason(self):
        m = _make_module(topic="stocks")
        reason = _build_reason(m, completed=0, total=5, is_topic_match=False, is_variety=False, readiness_score=0.3)
        assert "recommended" in reason.lower()
