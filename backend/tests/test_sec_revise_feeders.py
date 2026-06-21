"""Security tests: revise feeders must filter by market_code and published.

Gap A: list_revisable_modules must exclude modules from other markets.
Gap B: build_session refresher query must exclude unpublished and cross-market modules.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Lesson, LessonCompletion, Module
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
