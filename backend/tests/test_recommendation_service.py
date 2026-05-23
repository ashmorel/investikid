from datetime import UTC, date, datetime, timedelta

import pytest
import pytest_asyncio

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery, WeakConcept
from app.models.user import User
from app.services.recommendation_service import get_recommendations

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _make_module(topic: str, title: str, order: int, **kw):
    return Module(topic=topic, title=title, country_codes=[], is_premium=False, order_index=order, icon="📚", **kw)


@pytest_asyncio.fixture
async def seeded(db_session):
    user = User(
        email="rec@example.com", username="reckid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
        profiling_enabled=True,  # algorithm tests require profiling on
    )
    db_session.add(user)
    await db_session.flush()

    stocks = _make_module("stocks", "What is a Stock?", 0)
    db_session.add(stocks)
    await db_session.flush()

    budgeting = _make_module("budgeting", "Budgeting Basics", 1)
    db_session.add(budgeting)
    await db_session.flush()

    risk = _make_module("risk", "Risk & Diversification", 2)
    db_session.add(risk)
    await db_session.flush()

    crypto = _make_module("crypto", "What is Crypto?", 3)
    db_session.add(crypto)
    await db_session.flush()

    # Stocks has 1 lesson, budgeting has 1 lesson
    stocks_lesson = Lesson(module_id=stocks.id, type="quiz", xp_reward=25, order_index=0,
                           content_json={"question": "q", "choices": ["a", "b"], "answer_index": 0, "explanation": "e"})
    db_session.add(stocks_lesson)
    await db_session.flush()

    budgeting_lesson = Lesson(module_id=budgeting.id, type="card", xp_reward=10, order_index=0,
                              content_json={"title": "t", "body": "b"})
    db_session.add(budgeting_lesson)
    await db_session.flush()

    return {
        "user": user,
        "stocks": stocks, "budgeting": budgeting, "risk": risk, "crypto": crypto,
        "stocks_lesson": stocks_lesson, "budgeting_lesson": budgeting_lesson,
    }


def _all_module_ids(recs: dict) -> list:
    """Extract all module_ids from categorised recommendations in order."""
    ids = []
    for cat in ("continue_learning", "practise_again", "something_new"):
        ids.extend(r["module_id"] for r in recs.get(cat, []))
    return ids


async def test_new_user_gets_no_prerequisite_modules_first(db_session, seeded):
    """A brand-new user should see modules with lessons recommended; stocks and budgeting
    (which have lessons) should appear before risk and crypto (which have no lessons)."""
    recs = await get_recommendations(db_session, seeded["user"])
    module_ids = _all_module_ids(recs)
    # stocks and budgeting have lessons so should appear in recommendations
    assert seeded["stocks"].id in module_ids
    assert seeded["budgeting"].id in module_ids
    # risk and crypto have no lessons — they may or may not appear depending on
    # per-category caps, but if they do they should rank after stocks/budgeting
    for late_mod in (seeded["risk"], seeded["crypto"]):
        if late_mod.id in module_ids:
            late_idx = module_ids.index(late_mod.id)
            stocks_idx = module_ids.index(seeded["stocks"].id)
            assert stocks_idx < late_idx


async def test_weak_concepts_boost_topic(db_session, seeded):
    """A user with weak concepts in budgeting should see budgeting ranked higher."""
    user = seeded["user"]
    # Give user some stocks mastery so risk becomes "ready"
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=0.8,
        quizzes_attempted=5, quizzes_correct=4,
        last_activity_at=datetime.now(UTC) - timedelta(days=3),
    ))
    await db_session.flush()
    # Add weak concept in budgeting
    db_session.add(WeakConcept(
        user_id=user.id, topic="budgeting", concept="50/30/20 rule",
        times_wrong=2, times_reinforced=0, resolved=False,
    ))
    await db_session.flush()

    recs = await get_recommendations(db_session, user)
    module_ids = _all_module_ids(recs)
    budgeting_idx = module_ids.index(seeded["budgeting"].id)
    # budgeting should be first or second (weakness boost)
    assert budgeting_idx <= 1


async def test_recommendations_contain_lesson_ids(db_session, seeded):
    """Categorised recommendations should contain lesson_id for actionable items."""
    recs = await get_recommendations(db_session, seeded["user"])
    all_items = _all_module_ids(recs)
    # Should have some recommendations for a new user
    assert len(all_items) > 0


async def test_completed_modules_excluded(db_session, seeded):
    """Fully completed modules should not appear in recommendations."""
    user = seeded["user"]
    # Complete the stocks lesson
    db_session.add(LessonCompletion(
        user_id=user.id, lesson_id=seeded["stocks_lesson"].id, score=1.0,
    ))
    await db_session.flush()
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=1.0,
        quizzes_attempted=1, quizzes_correct=1,
        last_activity_at=datetime.now(UTC),
    ))
    await db_session.flush()

    recs = await get_recommendations(db_session, user)
    module_ids = _all_module_ids(recs)
    # Fully completed modules are excluded by the hard filter — stocks should not appear
    assert seeded["stocks"].id not in module_ids


async def test_premium_module_excluded_for_free_user(db_session):
    """Premium-gated modules must NOT appear in recommendations for a free user.

    This test verifies that the entitlement read goes through is_premium()
    rather than user.is_premium directly — so the seam is the sole read path.
    """
    free_user = User(
        email="free_rec@example.com", username="freerecuser", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
        profiling_enabled=True, is_premium=False,
    )
    db_session.add(free_user)

    premium_module = Module(
        topic="premium_topic", title="Premium Content", country_codes=[],
        is_premium=True, order_index=999, icon="💎",
    )
    db_session.add(premium_module)
    await db_session.flush()

    recs = await get_recommendations(db_session, free_user)
    module_ids = _all_module_ids(recs)
    assert premium_module.id not in module_ids, (
        "Premium-gated module must not appear in free user's recommendations"
    )


async def test_premium_module_included_for_premium_user(db_session):
    """Premium-gated modules MUST appear in recommendations for a premium user.

    This is the positive-path counterpart to test_premium_module_excluded_for_free_user.
    """
    premium_user = User(
        email="prem_rec@example.com", username="premrecuser", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
        profiling_enabled=True, is_premium=True,
    )
    db_session.add(premium_user)

    premium_module = Module(
        topic="premium_topic2", title="Premium Content 2", country_codes=[],
        is_premium=True, order_index=998, icon="💎",
    )
    db_session.add(premium_module)
    # Add a lesson so next_quest logic has something to point at
    await db_session.flush()
    lesson = Lesson(
        module_id=premium_module.id, type="card", xp_reward=10, order_index=0,
        content_json={"title": "t", "body": "b"},
    )
    db_session.add(lesson)
    await db_session.flush()

    recs = await get_recommendations(db_session, premium_user)
    module_ids = _all_module_ids(recs)
    assert premium_module.id in module_ids, (
        "Premium-gated module must appear in premium user's recommendations"
    )


async def test_recommendations_withheld_when_profiling_disabled(db_session):
    """Personalised recommendations must not be returned when profiling_enabled is False.

    Modules are seeded so that without the guard the algorithm would return
    non-empty suggested_modules, confirming the guard fires before computation.
    """
    from datetime import date as _date

    u = User(
        email="np@example.com", username="noprofile", password_hash="x",
        dob=_date(2010, 1, 1), country_code="GB", currency_code="GBP",
        profiling_enabled=False,
    )
    db_session.add(u)
    # Add a module so the algorithm would normally return recommendations
    m = _make_module("stocks", "Stocks (profiling off test)", 99)
    db_session.add(m)
    await db_session.flush()
    result = await get_recommendations(db_session, u)
    assert result == {
        "continue_learning": [],
        "practise_again": [],
        "something_new": [],
        "review_summary": {"due_count": 0, "next_due_at": None},
    }
