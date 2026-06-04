import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _register(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _one_module(db_session, title="Mod", order_index=0):
    m = Module(topic="stocks", title=title, country_codes=[], is_premium=False, order_index=order_index, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L0", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lsn = Lesson(module_id=m.id, level_id=lv.id, type="card", order_index=0, xp_reward=10,
                 content_json={"title": "Intro", "body": "b"})
    db_session.add(lsn)
    await db_session.flush()
    return m, lv, lsn


async def test_next_lesson_returns_envelope(client, db_session):
    await _register(client, "ep1@example.com", "ep1user")
    m, lv, lsn = await _one_module(db_session)
    r = await client.get("/next-lesson")
    assert r.status_code == 200
    body = r.json()
    assert body["next"] is not None
    assert body["next"]["module_id"] == str(m.id)
    assert body["next"]["lesson_id"] == str(lsn.id)
    assert body["next"]["mode"] == "start"


async def test_next_lesson_null_when_caught_up(client, db_session):
    await _register(client, "ep2@example.com", "ep2user")
    m, lv, lsn = await _one_module(db_session)
    user = await db_session.scalar(select(User).where(User.email == "ep2@example.com"))
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lsn.id, score=1.0))
    await db_session.flush()
    r = await client.get("/next-lesson")
    assert r.status_code == 200
    assert r.json()["next"] is None


async def test_next_lesson_requires_auth(client):
    r = await client.get("/next-lesson")
    assert r.status_code == 401
