"""W3a Task 2 — record level mastery automatically on lesson completion."""

import datetime as dt
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Level, LevelMastery, Module
from app.models.user import User
from app.services.mastery_service import record_mastery_if_earned

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _user() -> User:
    return User(
        username=f"m{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=dt.date(2015, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="p@x.test",
    )


async def _level_with_lessons(db_session, *, types=("quiz", "quiz"), threshold=0.7):
    m = Module(
        topic="savings", title="Mastery Mod", country_codes=[],
        is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False,
               pass_threshold=threshold)
    db_session.add(lv)
    await db_session.flush()
    lessons = []
    for i, t in enumerate(types):
        content = (
            {"question": "q", "choices": ["A", "B"], "answer_index": 0}
            if t in ("quiz", "scenario")
            else {"title": "t", "body": "b"}
        )
        lessons.append(Lesson(module_id=m.id, level_id=lv.id, type=t,
                              order_index=i, xp_reward=10, content_json=content))
    db_session.add_all(lessons)
    await db_session.flush()
    return m, lv, lessons


async def _complete(db_session, user, lesson, score):
    db_session.add(LessonCompletion(
        user_id=user.id, lesson_id=lesson.id, score=score,
        completed_at=datetime.now(UTC),
    ))
    await db_session.flush()


async def _mastery_rows(db_session, user, level):
    return (await db_session.scalars(
        select(LevelMastery).where(
            LevelMastery.user_id == user.id, LevelMastery.level_id == level.id
        )
    )).all()


async def test_incomplete_level_records_nothing(db_session):
    _, lv, lessons = await _level_with_lessons(db_session)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    await _complete(db_session, user, lessons[0], 1.0)  # second lesson missing
    result = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert result is None
    assert await _mastery_rows(db_session, user, lv) == []


async def test_avg_exactly_at_threshold_masters(db_session):
    _, lv, lessons = await _level_with_lessons(db_session, threshold=0.7)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    await _complete(db_session, user, lessons[0], 0.6)
    await _complete(db_session, user, lessons[1], 0.8)  # avg == 0.7
    result = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert result is not None
    rows = await _mastery_rows(db_session, user, lv)
    assert len(rows) == 1
    assert rows[0].score == pytest.approx(0.7)
    assert rows[0].mastered_at is not None


async def test_avg_below_threshold_records_nothing(db_session):
    _, lv, lessons = await _level_with_lessons(db_session, threshold=0.7)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    await _complete(db_session, user, lessons[0], 0.5)
    await _complete(db_session, user, lessons[1], 0.8)  # avg == 0.65 < 0.7
    result = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert result is None
    assert await _mastery_rows(db_session, user, lv) == []


async def test_repeat_pass_keeps_single_immutable_row(db_session):
    _, lv, lessons = await _level_with_lessons(db_session, threshold=0.7)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    await _complete(db_session, user, lessons[0], 0.7)
    await _complete(db_session, user, lessons[1], 0.7)
    first = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert first is not None
    original_at = first.mastered_at
    original_score = first.score

    # Improve a score later, then re-evaluate — still exactly one row, unchanged.
    completion = await db_session.scalar(
        select(LessonCompletion).where(
            LessonCompletion.user_id == user.id,
            LessonCompletion.lesson_id == lessons[0].id,
        )
    )
    completion.score = 1.0
    await db_session.flush()

    again = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert again is None
    rows = await _mastery_rows(db_session, user, lv)
    assert len(rows) == 1
    assert rows[0].mastered_at == original_at
    assert rows[0].score == original_score


async def test_card_only_level_masters_on_completion(db_session):
    _, lv, lessons = await _level_with_lessons(
        db_session, types=("card", "card"), threshold=0.7
    )
    user = _user()
    db_session.add(user)
    await db_session.flush()

    await _complete(db_session, user, lessons[0], None)
    await _complete(db_session, user, lessons[1], None)
    result = await record_mastery_if_earned(db_session, user.id, lv.id)
    assert result is not None
    rows = await _mastery_rows(db_session, user, lv)
    assert len(rows) == 1
    # No scored lessons → score falls back to the level's pass_threshold
    # (matches the Task-1 backfill COALESCE).
    assert rows[0].score == pytest.approx(0.7)


_USER = {
    "password": "SecurePass123!", "dob": "2006-01-01",
    "country_code": "GB", "currency_code": "GBP",
}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_endpoint_records_mastery_on_final_lesson(client, db_session):
    await _login(client, "mastery-e2e@example.com", "masterye2e")
    _, lv, lessons = await _level_with_lessons(db_session, threshold=0.7)

    r1 = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r1.status_code == 200
    assert (await db_session.scalars(
        select(LevelMastery).where(LevelMastery.level_id == lv.id)
    )).all() == []  # not yet — one lesson outstanding

    r2 = await client.post(f"/lessons/{lessons[1].id}/complete", json={"score": 0.9})
    assert r2.status_code == 200
    rows = (await db_session.scalars(
        select(LevelMastery).where(LevelMastery.level_id == lv.id)
    )).all()
    assert len(rows) == 1
    assert rows[0].score == pytest.approx(0.9)
