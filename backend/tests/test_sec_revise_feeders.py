"""Security tests: revise feeders must filter by market_code and published.

Gap A: list_revisable_modules must exclude modules from other markets.
Gap B: build_session refresher query must exclude unpublished and cross-market modules.
Gap C: build_session weak-concept path (_lesson_for_concept) must not resolve to
       cross-market or unpublished modules even when the same topic string exists
       in multiple markets.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User
from app.services.revise_service import build_session, list_revisable_modules

pytestmark = pytest.mark.asyncio(loop_scope="session")

_mock_quiz = {
    "question": "Q?",
    "choices": ["A", "B"],
    "answer_index": 0,
    "explanation": "E",
    "variant_rung": "core",
}


async def _make_user(db_session, *, email: str, market_code: str) -> User:
    user = User(
        email=email,
        username=email.split("@")[0].replace(".", "_"),
        password_hash="x",
        dob=datetime(2012, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        active_market_code=market_code,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_module_with_completion(
    db_session,
    *,
    user: User,
    market_code: str,
    published: bool,
) -> tuple[Module, Lesson]:
    module = Module(
        topic="saving",
        title="Saving Basics",
        country_codes=[],
        is_premium=False,
        order_index=0,
        icon="💰",
        market_code=market_code,
        published=published,
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=10,
        order_index=0,
        content_json={
            "question": "What is saving?",
            "choices": ["A", "B"],
            "answer_index": 0,
            "explanation": "It means putting money aside.",
        },
    )
    db_session.add(lesson)
    await db_session.flush()

    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    return module, lesson


# ---------------------------------------------------------------------------
# Test 1: list_revisable_modules excludes unpublished modules
# ---------------------------------------------------------------------------

async def test_list_revisable_modules_excludes_unpublished(db_session):
    user = await _make_user(db_session, email="sec_feeder1@example.com", market_code="GB")
    await _make_module_with_completion(
        db_session, user=user, market_code="GB", published=False
    )

    result = await list_revisable_modules(db_session, user)
    assert result == [], (
        "list_revisable_modules must not return unpublished modules"
    )


# ---------------------------------------------------------------------------
# Test 2: list_revisable_modules excludes cross-market modules
# ---------------------------------------------------------------------------

async def test_list_revisable_modules_excludes_cross_market(db_session):
    user = await _make_user(db_session, email="sec_feeder2@example.com", market_code="GB")
    await _make_module_with_completion(
        db_session, user=user, market_code="US", published=True
    )

    result = await list_revisable_modules(db_session, user)
    assert result == [], (
        "list_revisable_modules must not return modules from other markets"
    )


# ---------------------------------------------------------------------------
# Test 3: build_session refresher excludes unpublished modules
# ---------------------------------------------------------------------------

async def test_build_session_refresher_excludes_unpublished(db_session):
    user = await _make_user(db_session, email="sec_feeder3@example.com", market_code="GB")
    await _make_module_with_completion(
        db_session, user=user, market_code="GB", published=False
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new=AsyncMock(return_value=_mock_quiz),
    ):
        result = await build_session(db_session, user, module_id=None)

    assert result == [], (
        "build_session refresher must not surface unpublished modules"
    )


# ---------------------------------------------------------------------------
# Test 4: build_session refresher excludes cross-market modules
# ---------------------------------------------------------------------------

async def test_build_session_refresher_excludes_cross_market(db_session):
    user = await _make_user(db_session, email="sec_feeder4@example.com", market_code="GB")
    await _make_module_with_completion(
        db_session, user=user, market_code="US", published=True
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new=AsyncMock(return_value=_mock_quiz),
    ):
        result = await build_session(db_session, user, module_id=None)

    assert result == [], (
        "build_session refresher must not surface modules from other markets"
    )


# ---------------------------------------------------------------------------
# Tests 5 & 6: build_session WEAK-CONCEPT path (_lesson_for_concept) must
# not resolve to cross-market or unpublished modules even when the same topic
# string ("saving") exists in multiple markets.
# ---------------------------------------------------------------------------

async def _make_weak_concept_setup(
    db_session,
    *,
    user_market: str,
    other_market: str,
    other_published: bool,
    email_suffix: str,
) -> tuple[User, WeakConcept]:
    """Create a GB user whose WeakConcept topic also exists in another market."""
    user = await _make_user(
        db_session,
        email=f"sec_feeder_{email_suffix}@example.com",
        market_code=user_market,
    )

    # The 'other' module: same topic as the weak concept but wrong market/unpublished.
    other_module = Module(
        topic="saving",
        title="Saving (other market)",
        country_codes=[],
        is_premium=False,
        order_index=0,
        icon="💰",
        market_code=other_market,
        published=other_published,
    )
    db_session.add(other_module)
    await db_session.flush()

    other_lesson = Lesson(
        module_id=other_module.id,
        type="quiz",
        xp_reward=10,
        order_index=0,
        content_json={
            "question": "What is saving?",  # concept key used by _concept_of
            "choices": ["A", "B"],
            "answer_index": 0,
            "explanation": "Putting money aside.",
        },
    )
    db_session.add(other_lesson)
    await db_session.flush()

    # WeakConcept for the user matching this topic+concept.
    wc = WeakConcept(
        user_id=user.id,
        topic="saving",
        concept="What is saving?",
        resolved=False,
        market_code=user_market,
    )
    db_session.add(wc)
    await db_session.flush()

    # SpacedRepetitionItem so the weak concept is "due now".
    sr = SpacedRepetitionItem(
        user_id=user.id,
        weak_concept_id=wc.id,
        next_review_at=datetime(2000, 1, 1, tzinfo=UTC),
    )
    db_session.add(sr)
    await db_session.flush()

    return user, wc


async def test_build_session_weak_concept_excludes_cross_market_module(db_session):
    """Weak-concept path: topic exists in US module only; GB user must get empty session."""
    user, _wc = await _make_weak_concept_setup(
        db_session,
        user_market="GB",
        other_market="US",
        other_published=True,
        email_suffix="5a",
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new=AsyncMock(return_value=_mock_quiz),
    ) as mock_quiz:
        result = await build_session(db_session, user, module_id=None)

    assert result == [], (
        "_lesson_for_concept must not resolve to a cross-market module; "
        "weak-concept path leaked cross-market content"
    )
    mock_quiz.assert_not_called()


async def test_build_session_weak_concept_excludes_unpublished_module(db_session):
    """Weak-concept path: topic exists only in an unpublished GB module; must get empty session."""
    user, _wc = await _make_weak_concept_setup(
        db_session,
        user_market="GB",
        other_market="GB",
        other_published=False,
        email_suffix="5b",
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new=AsyncMock(return_value=_mock_quiz),
    ) as mock_quiz:
        result = await build_session(db_session, user, module_id=None)

    assert result == [], (
        "_lesson_for_concept must not resolve to an unpublished module; "
        "weak-concept path leaked unpublished content"
    )
    mock_quiz.assert_not_called()
