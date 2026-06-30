"""B5 — delight signals on lesson completion (for the in-app-review trigger).

`LessonCompletionResult` must surface, for THIS completion:
- `streak_milestone_reached: int | None` — the streak value when it just advanced to a
  multiple of STREAK_MILESTONE (else None); None on same-day repeat / already-completed.
  (The pure decision is unit-tested in test_streak_milestone_helper.py.)
- `level_mastered: bool` — True when this completion mastered a level for the first time.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.time import today_utc
from app.models.content import Lesson, Level, LevelMastery, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- endpoint wiring: level_mastered + milestone field present ---------------

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


async def _level_with_lessons(db_session, *, threshold=0.7):
    m = Module(topic="savings", title="B5 Mod", country_codes=[],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False,
               pass_threshold=threshold)
    db_session.add(lv)
    await db_session.flush()
    lessons = [
        Lesson(module_id=m.id, level_id=lv.id, type="quiz", order_index=i, xp_reward=10,
               content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0})
        for i in range(2)
    ]
    db_session.add_all(lessons)
    await db_session.flush()
    return m, lv, lessons


async def test_completion_response_exposes_review_signal_fields(client, db_session):
    """First lesson of a fresh user: response carries both new fields, both falsy."""
    await _login(client, "b5-fields@example.com", "b5fields")
    _, lv, lessons = await _level_with_lessons(db_session)

    r = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert "streak_milestone_reached" in body
    assert "level_mastered" in body
    # first lesson of one level → streak just started (1), level not yet mastered
    assert body["streak_milestone_reached"] is None
    assert body["level_mastered"] is False


async def test_level_mastered_true_on_final_lesson(client, db_session):
    await _login(client, "b5-mastery@example.com", "b5mastery")
    _, lv, lessons = await _level_with_lessons(db_session)

    r1 = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r1.status_code == 200
    assert r1.json()["level_mastered"] is False  # one lesson still outstanding

    r2 = await client.post(f"/lessons/{lessons[1].id}/complete", json={"score": 0.9})
    assert r2.status_code == 200
    assert r2.json()["level_mastered"] is True
    # and a mastery row was actually written
    rows = (await db_session.scalars(
        select(LevelMastery).where(LevelMastery.level_id == lv.id)
    )).all()
    assert len(rows) == 1


async def test_streak_milestone_reached_end_to_end(client, db_session):
    """Drive the streak from 6 → 7 through the real endpoint and assert the signal.

    Locks the prev_streak snapshot-vs-mutation ordering against future refactors of
    _award_completion (the subtlest part of the change).
    """
    await _login(client, "b5-streak@example.com", "b5streak")
    _, _, lessons = await _level_with_lessons(db_session)

    user = await db_session.scalar(select(User).where(User.email == "b5-streak@example.com"))
    # Seed a 6-day streak whose last activity was yesterday (gap == 1 → increments to 7).
    progress = await db_session.scalar(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    if progress is None:
        progress = UserProgress(user_id=user.id)
        db_session.add(progress)
    progress.streak_count = 6
    progress.last_activity_date = today_utc() - timedelta(days=1)
    await db_session.flush()

    r = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["streak_count"] == 7
    assert body["streak_milestone_reached"] == 7


async def test_replay_does_not_remaster(client, db_session):
    await _login(client, "b5-replay@example.com", "b5replay")
    _, lv, lessons = await _level_with_lessons(db_session)
    await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    await client.post(f"/lessons/{lessons[1].id}/complete", json={"score": 0.9})
    # replay the final lesson → already completed, no new mastery
    r = await client.post(f"/lessons/{lessons[1].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    assert r.json()["level_mastered"] is False
    assert r.json()["already_completed"] is True
