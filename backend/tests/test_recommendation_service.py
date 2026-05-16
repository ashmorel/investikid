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


async def test_new_user_gets_no_prerequisite_modules_first(db_session, seeded):
    """A brand-new user should see stocks and budgeting (no prerequisites) before risk and crypto."""
    recs = await get_recommendations(db_session, seeded["user"])
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    # stocks and budgeting should come before risk and crypto
    stocks_idx = module_ids.index(seeded["stocks"].id)
    budgeting_idx = module_ids.index(seeded["budgeting"].id)
    risk_idx = module_ids.index(seeded["risk"].id)
    crypto_idx = module_ids.index(seeded["crypto"].id)
    assert stocks_idx < risk_idx
    assert stocks_idx < crypto_idx
    assert budgeting_idx < crypto_idx


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
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    budgeting_idx = module_ids.index(seeded["budgeting"].id)
    # budgeting should be first or second (weakness boost)
    assert budgeting_idx <= 1


async def test_next_quest_returns_first_incomplete_lesson(db_session, seeded):
    """next_quest should point to the first incomplete lesson in the top-ranked module."""
    recs = await get_recommendations(db_session, seeded["user"])
    assert recs["next_quest"] is not None
    assert recs["next_quest"]["lesson_id"] is not None


async def test_completed_modules_ranked_last(db_session, seeded):
    """Fully completed modules should appear at the end of the list."""
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
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    stocks_idx = module_ids.index(seeded["stocks"].id)
    # Stocks should be last (or near last) since it's complete
    assert stocks_idx >= len(module_ids) - 2


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
    assert result == {"next_quest": None, "suggested_modules": []}
