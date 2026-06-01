import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {
    "password": "SecurePass123!", "dob": "2006-01-01",
    "country_code": "GB", "currency_code": "GBP",
}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    r = await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    assert r.status_code == 200


async def _seed_quiz_lesson(db_session):
    """Create a module → level → quiz lesson directly; return the lesson id."""
    from app.models.content import Lesson, Level, Module
    m = Module(topic="stocks", title="BS Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    lesson = Lesson(
        module_id=m.id, level_id=lvl.id, type="quiz", order_index=0, xp_reward=10,
        content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0},
    )
    db_session.add(lesson)
    await db_session.flush()
    return str(lesson.id)


async def test_recompletion_keeps_best_score_and_awards_xp_once(client, db_session):
    await _login(client, "bs@example.com", "bsuser")
    lesson_id = await _seed_quiz_lesson(db_session)

    r1 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.4})
    assert r1.status_code == 200
    assert r1.json()["xp_awarded"] == 10
    assert r1.json()["already_completed"] is False

    r2 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.9})
    assert r2.status_code == 200
    assert r2.json()["xp_awarded"] == 0           # XP only once
    assert r2.json()["already_completed"] is True

    # Lower score must NOT lower the stored best
    r3 = await client.post(f"/lessons/{lesson_id}/complete", json={"score": 0.2})
    assert r3.status_code == 200

    from sqlalchemy import select

    from app.models.content import LessonCompletion
    score = await db_session.scalar(
        select(LessonCompletion.score).where(LessonCompletion.lesson_id == lesson_id)
    )
    assert score == 0.9
