"""Security tests: record_answer must gate against forged refs.

A child can craft a base64 ref pointing at any lesson_id. Without a gate,
they could drive the LLM on content from unpublished, cross-market, or
premium-only modules. The fix calls get_accessible_module before the LLM.
"""
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.content import Lesson, Module
from app.models.user import User
from app.services.revise_service import encode_ref, record_answer

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user(db_session, *, email, username, is_premium=False,
                     active_market_code="GB"):
    user = User(
        email=email,
        username=username,
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_premium=is_premium,
        active_market_code=active_market_code,
        home_market_code=active_market_code,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_module(db_session, *, topic, published, market_code="GB",
                       is_premium=False):
    module = Module(
        topic=topic,
        title=f"{topic} module",
        country_codes=[],
        is_premium=is_premium,
        order_index=0,
        icon="📚",
        published=published,
        market_code=market_code,
    )
    db_session.add(module)
    await db_session.flush()
    return module


async def _make_lesson(db_session, module_id, concept="What is saving?"):
    lesson = Lesson(
        module_id=module_id,
        type="quiz",
        xp_reward=10,
        order_index=0,
        content_json={
            "question": concept,
            "choices": ["a", "b", "c"],
            "answer_index": 1,
            "explanation": "because",
            "variant_rung": "core",
        },
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_record_answer_rejects_forged_ref_unpublished_module(
    db_session, seed_markets_once
):
    """Forged ref pointing at a lesson in an UNPUBLISHED module -> 404."""
    user = await _make_user(db_session, email="sec-t1@example.com",
                            username="sec_t1")
    module = await _make_module(db_session, topic="sec-unpub-1",
                                published=False, market_code="GB")
    lesson = await _make_lesson(db_session, module.id)

    ref = encode_ref(
        kind="refresher",
        topic=module.topic,
        lesson_id=lesson.id,
        concept="What is saving?",
        weak_concept_id=None,
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new_callable=AsyncMock,
    ) as mock_quiz:
        with pytest.raises(HTTPException) as exc_info:
            await record_answer(db_session, user, ref, 0)

    assert exc_info.value.status_code == 404
    mock_quiz.assert_not_called()


async def test_record_answer_rejects_forged_ref_cross_market_module(
    db_session, seed_markets_once
):
    """Forged ref pointing at a lesson in a US module for a GB user -> 404."""
    user = await _make_user(db_session, email="sec-t2@example.com",
                            username="sec_t2", active_market_code="GB")
    module = await _make_module(db_session, topic="sec-cross-1",
                                published=True, market_code="US")
    lesson = await _make_lesson(db_session, module.id)

    ref = encode_ref(
        kind="refresher",
        topic=module.topic,
        lesson_id=lesson.id,
        concept="What is saving?",
        weak_concept_id=None,
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new_callable=AsyncMock,
    ) as mock_quiz:
        with pytest.raises(HTTPException) as exc_info:
            await record_answer(db_session, user, ref, 0)

    assert exc_info.value.status_code == 404
    mock_quiz.assert_not_called()


async def test_record_answer_rejects_forged_ref_premium_module_free_user(
    db_session, seed_markets_once
):
    """Forged ref pointing at a premium lesson for a free user -> 402."""
    user = await _make_user(db_session, email="sec-t3@example.com",
                            username="sec_t3", is_premium=False,
                            active_market_code="GB")
    module = await _make_module(db_session, topic="sec-premium-1",
                                published=True, market_code="GB",
                                is_premium=True)
    lesson = await _make_lesson(db_session, module.id)

    ref = encode_ref(
        kind="refresher",
        topic=module.topic,
        lesson_id=lesson.id,
        concept="What is saving?",
        weak_concept_id=None,
    )

    with patch(
        "app.services.revise_service.generate_practice_quiz",
        new_callable=AsyncMock,
    ) as mock_quiz:
        with pytest.raises(HTTPException) as exc_info:
            await record_answer(db_session, user, ref, 0)

    assert exc_info.value.status_code == 403
    mock_quiz.assert_not_called()
