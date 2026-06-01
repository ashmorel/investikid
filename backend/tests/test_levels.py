import pytest
from sqlalchemy import select  # noqa: F401  (kept if needed by helpers)

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _module_two_levels(db_session, *, l2_premium=False):
    m = Module(topic="stocks", title="LV Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    l1 = Level(module_id=m.id, title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)
    l2 = Level(module_id=m.id, title="Level 2", order_index=1, is_premium=l2_premium, pass_threshold=0.7)
    db_session.add_all([l1, l2])
    await db_session.flush()
    q1 = Lesson(module_id=m.id, level_id=l1.id, type="quiz", order_index=0, xp_reward=10,
                content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0})
    q2 = Lesson(module_id=m.id, level_id=l2.id, type="card", order_index=0, xp_reward=10,
                content_json={"title": "t", "body": "b"})
    db_session.add_all([q1, q2])
    await db_session.flush()
    return m, l1, l2, q1, q2


async def test_list_levels_returns_states(client, db_session):
    await _login(client, "lv1@example.com", "lv1user")
    m, l1, l2, q1, q2 = await _module_two_levels(db_session)
    r = await client.get(f"/modules/{m.id}/levels")
    assert r.status_code == 200
    body = sorted(r.json(), key=lambda x: x["order_index"])
    assert body[0]["state"] == "in_progress"
    assert body[1]["state"] == "locked" and body[1]["locked_reason"] == "progression"


async def test_level_lessons_premium_gate(client, db_session):
    await _login(client, "lv2@example.com", "lv2user")
    m, l1, l2, q1, q2 = await _module_two_levels(db_session, l2_premium=True)
    r = await client.get(f"/levels/{l2.id}/lessons")
    assert r.status_code == 403
    r1 = await client.get(f"/levels/{l1.id}/lessons")
    assert r1.status_code == 200
    assert len(r1.json()) == 1
