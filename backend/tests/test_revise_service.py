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
    list_revisable_modules,
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


@pytest.mark.asyncio(loop_scope="session")
async def test_list_modules_weak_first(db_session):
    user, module = await _seed_user(db_session)  # stocks
    saving = Module(topic="saving", title="Saving", country_codes=[],
                    is_premium=False, order_index=1, icon="🐷")
    db_session.add(saving)
    await db_session.flush()
    for m in (module, saving):
        lesson = Lesson(module_id=m.id, type="quiz", xp_reward=10, order_index=0,
                        content_json={"question": f"{m.topic}?", "choices": ["a"], "answer_index": 0})
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    wc = WeakConcept(user_id=user.id, topic="saving", concept="saving?", resolved=False)
    db_session.add(wc)
    await db_session.flush()
    db_session.add(SpacedRepetitionItem(
        user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5, interval_days=1,
        repetition_count=0, next_review_at=datetime.now(UTC) - timedelta(days=1)))
    await db_session.flush()

    mods = await list_revisable_modules(db_session, user)
    assert mods[0]["topic"] == "saving"  # weak-first
    assert mods[0]["due_weak_count"] == 1
    assert {m["topic"] for m in mods} == {"stocks", "saving"}


def test_award_revise_xp_is_daily_capped():
    from datetime import date

    from app.services.revise_service import (
        REVISE_XP_DAILY_CAP,
        XP_PER_CORRECT,
        award_revise_xp,
    )

    p = UserProgress(
        user_id=uuid.uuid4(), xp=0, xp_today=0, xp_today_date=None,
        virtual_coins=0, level=1, daily_goal_xp=30, revise_xp_today=0,
    )
    today = date(2026, 6, 16)
    awarded = [(award_revise_xp(p, today) or None) for _ in range(7)]
    amounts = [r.awarded if r else 0 for r in awarded]
    # cap 25, 5 XP each -> exactly 5 awards then 0
    assert amounts[:5] == [XP_PER_CORRECT] * 5
    assert amounts[5] == 0 and amounts[6] == 0
    assert sum(amounts) == REVISE_XP_DAILY_CAP
    assert p.revise_xp_today == REVISE_XP_DAILY_CAP


@pytest.mark.asyncio(loop_scope="session")
async def test_get_due_items_most_overdue_first(db_session):
    from app.services.spaced_repetition_service import get_due_items

    user, module = await _seed_user(db_session)
    by_days = {}
    for i, days in enumerate((1, 5)):  # the 5-days-overdue item should come first
        wc = WeakConcept(user_id=user.id, topic="stocks", concept=f"c{i}", resolved=False)
        db_session.add(wc)
        await db_session.flush()
        db_session.add(SpacedRepetitionItem(
            user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5, interval_days=1,
            repetition_count=0, next_review_at=datetime.now(UTC) - timedelta(days=days)))
        by_days[days] = wc.id
    await db_session.flush()

    due = await get_due_items(db_session, user.id)
    assert [d.weak_concept_id for d in due] == [by_days[5], by_days[1]]


@pytest.mark.asyncio(loop_scope="session")
async def test_correct_refresher_schedules_future_review(db_session):
    user, module = await _seed_user(db_session)
    await _progress(db_session, user)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Fresh2?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    await db_session.flush()
    ref = encode_ref(kind="refresher", topic="stocks", lesson_id=lesson.id,
                     concept="Fresh2?", weak_concept_id=None)

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload("Fresh2?"))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        result = await record_answer(db_session, user, ref, selected_index=1)  # correct (ans=1)

    assert result["correct"] is True
    wc = await db_session.scalar(select(WeakConcept).where(
        WeakConcept.user_id == user.id, WeakConcept.concept == "Fresh2?"))
    assert wc is not None and wc.resolved is True  # mastered, but tracked for scheduling
    sr = await db_session.scalar(select(SpacedRepetitionItem).where(
        SpacedRepetitionItem.weak_concept_id == wc.id))
    assert sr is not None and sr.next_review_at > datetime.now(UTC)  # spaced forward


@pytest.mark.asyncio(loop_scope="session")
async def test_build_session_skips_not_yet_due_refresher(db_session):
    user, module = await _seed_user(db_session)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Done?", "choices": ["a"], "answer_index": 0})
    db_session.add(lesson)
    wc = WeakConcept(user_id=user.id, topic="stocks", concept="Done?", resolved=True)
    db_session.add(wc)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    db_session.add(SpacedRepetitionItem(
        user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5, interval_days=3,
        repetition_count=1, next_review_at=datetime.now(UTC) + timedelta(days=3)))  # future
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=None)

    assert session == []  # recently revised -> not due -> excluded -> nothing to revise
