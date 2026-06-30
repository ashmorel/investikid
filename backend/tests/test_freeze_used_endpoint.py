"""B6 — endpoint wiring for the `freeze_used` celebration signal.

A completion that bridges exactly one missed day with a freeze held →
`freeze_used True`; a normal consecutive day → False; same-day repeat → False.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.time import today_utc
from app.models.content import Lesson, Level, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")

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


async def _lessons(db_session, n=2):
    m = Module(topic="savings", title="B6 Mod", country_codes=[],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lessons = [
        Lesson(module_id=m.id, level_id=lv.id, type="quiz", order_index=i, xp_reward=10,
               content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0})
        for i in range(n)
    ]
    db_session.add_all(lessons)
    await db_session.flush()
    return lessons


async def _progress(db_session, email):
    user = await db_session.scalar(select(User).where(User.email == email))
    progress = await db_session.scalar(select(UserProgress).where(UserProgress.user_id == user.id))
    if progress is None:
        progress = UserProgress(user_id=user.id)
        db_session.add(progress)
    return progress


async def test_freeze_used_true_when_freeze_bridges_missed_day(client, db_session):
    await _login(client, "b6-freeze@example.com", "b6freeze")
    lessons = await _lessons(db_session)
    progress = await _progress(db_session, "b6-freeze@example.com")
    progress.streak_count = 5
    progress.last_activity_date = today_utc() - timedelta(days=2)  # gap == 2
    progress.streak_freezes = 1
    await db_session.flush()

    r = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["freeze_used"] is True
    # streak continued (not reset) and a freeze was spent
    assert body["streak_count"] == 6
    assert body["streak_freezes"] == 0


async def test_freeze_used_false_on_consecutive_day(client, db_session):
    await _login(client, "b6-consec@example.com", "b6consec")
    lessons = await _lessons(db_session)
    progress = await _progress(db_session, "b6-consec@example.com")
    progress.streak_count = 5
    progress.last_activity_date = today_utc() - timedelta(days=1)  # gap == 1
    progress.streak_freezes = 1
    await db_session.flush()

    r = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    assert r.json()["freeze_used"] is False


async def test_freeze_used_false_on_same_day_replay(client, db_session):
    await _login(client, "b6-replay@example.com", "b6replay")
    lessons = await _lessons(db_session)
    # first completion today → counts; replay same lesson → already_completed
    await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    r = await client.post(f"/lessons/{lessons[0].id}/complete", json={"score": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["already_completed"] is True
    assert body["freeze_used"] is False
