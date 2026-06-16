import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User, UserProgress
from app.services.revise_service import (
    build_session,
    decode_ref,
    encode_ref,
    record_answer,
)


def test_ref_roundtrip():
    lesson_id = uuid.uuid4()
    wc_id = uuid.uuid4()
    ref = encode_ref(kind="weak", topic="stocks", lesson_id=lesson_id,
                     concept="What is a stock?", weak_concept_id=wc_id)
    out = decode_ref(ref)
    assert out == {
        "kind": "weak", "topic": "stocks", "lesson_id": str(lesson_id),
        "concept": "What is a stock?", "weak_concept_id": str(wc_id),
    }


def test_ref_refresher_has_no_weak_id():
    lesson_id = uuid.uuid4()
    ref = encode_ref(kind="refresher", topic="saving", lesson_id=lesson_id,
                     concept="Why save?", weak_concept_id=None)
    out = decode_ref(ref)
    assert out["kind"] == "refresher"
    assert out["weak_concept_id"] is None


def test_decode_ref_rejects_garbage():
    with pytest.raises(ValueError):
        decode_ref("not-a-real-ref")


async def _seed_user(db_session):
    user = User(email="rev@example.com", username="revkid", password_hash="x",
                dob=datetime(2012, 1, 1).date(), country_code="GB", currency_code="GBP")
    db_session.add(user)
    module = Module(topic="stocks", title="Stocks", country_codes=[],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    return user, module


def _quiz_payload(q):
    return {"question": q, "choices": ["a", "b", "c"], "answer_index": 1,
            "explanation": "because", "variant_rung": "core"}


async def _progress(db_session, user):
    p = UserProgress(user_id=user.id)
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.mark.asyncio(loop_scope="session")
async def test_build_session_is_weak_first_then_refreshers_capped_5(db_session):
    user, module = await _seed_user(db_session)
    weak_lessons = []
    for i in range(2):
        q = f"Weak concept {i}?"
        lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=i,
                        content_json={"question": q, "choices": ["a", "b"], "answer_index": 0})
        db_session.add(lesson)
        weak_lessons.append((q, lesson))
        wc = WeakConcept(user_id=user.id, topic="stocks", concept=q, resolved=False)
        db_session.add(wc)
        await db_session.flush()
        db_session.add(SpacedRepetitionItem(
            user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5,
            interval_days=1, repetition_count=0,
            next_review_at=datetime.now(UTC) - timedelta(days=1)))
    for i in range(5):
        q = f"Mastered {i}?"
        lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=10 + i,
                        content_json={"question": q, "choices": ["a", "b"], "answer_index": 0})
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=None)

    assert len(session) == 5
    assert session[0]["kind"] == "weak" and session[1]["kind"] == "weak"
    assert all(s["kind"] == "refresher" for s in session[2:])
    assert "answer_index" not in session[0]
    assert set(session[0]) >= {"ref", "kind", "module_id", "lesson_id", "concept",
                               "question", "choices"}


@pytest.mark.asyncio(loop_scope="session")
async def test_build_session_module_filter(db_session):
    user, module = await _seed_user(db_session)
    other = Module(topic="saving", title="Saving", country_codes=[],
                   is_premium=False, order_index=1, icon="🐷")
    db_session.add(other)
    await db_session.flush()
    lesson = Lesson(module_id=other.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Save?", "choices": ["a"], "answer_index": 0})
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=other.id)

    assert all(s["module_id"] == str(other.id) for s in session)
    assert len(session) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_completed_lesson_that_is_weak_not_served_as_refresher(db_session):
    # A completed lesson whose concept is ALSO an unresolved weak concept must not
    # be offered as a refresher. With no SR item due, it should not appear at all.
    user, module = await _seed_user(db_session)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Risk?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    db_session.add(WeakConcept(user_id=user.id, topic="stocks", concept="Risk?", resolved=False))
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=None)

    # not due (no SR item) -> not weak-served; and excluded from refreshers -> empty
    assert session == []


@pytest.mark.asyncio(loop_scope="session")
async def test_record_answer_weak_correct_awards_xp_and_advances(db_session):
    user, module = await _seed_user(db_session)
    await _progress(db_session, user)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Q?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    wc = WeakConcept(user_id=user.id, topic="stocks", concept="Q?", resolved=False)
    db_session.add(wc)
    await db_session.flush()
    ref = encode_ref(kind="weak", topic="stocks", lesson_id=lesson.id,
                     concept="Q?", weak_concept_id=wc.id)

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload("Q?"))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        # _quiz_payload answer_index is 1 -> selecting 1 is correct
        result = await record_answer(db_session, user, ref, selected_index=1)

    assert result["correct"] is True
    assert result["answer_index"] == 1
    assert result["xp_awarded"] == 5
    sr = await db_session.scalar(
        select(SpacedRepetitionItem).where(SpacedRepetitionItem.weak_concept_id == wc.id))
    assert sr is not None and sr.repetition_count >= 1  # advanced


@pytest.mark.asyncio(loop_scope="session")
async def test_record_answer_wrong_refresher_creates_weak_concept(db_session):
    user, module = await _seed_user(db_session)
    await _progress(db_session, user)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Fresh?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    await db_session.flush()
    ref = encode_ref(kind="refresher", topic="stocks", lesson_id=lesson.id,
                     concept="Fresh?", weak_concept_id=None)

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload("Fresh?"))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        result = await record_answer(db_session, user, ref, selected_index=0)  # wrong (ans=1)

    assert result["correct"] is False
    assert result["xp_awarded"] == 0
    wc = await db_session.scalar(
        select(WeakConcept).where(WeakConcept.user_id == user.id,
                                  WeakConcept.concept == "Fresh?"))
    assert wc is not None  # missed refresher re-enters the SR loop
