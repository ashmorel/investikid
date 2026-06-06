import pytest
from sqlalchemy import select

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.content import Lesson, Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _login(client, email="missions@example.com", username="missionschild"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_active_missions_returns_list(client):
    await _login(client, email="missions@example.com", username="missionschild")
    resp = await client.get("/missions/active")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_active_missions_excludes_completed(client, db_session):
    await _login(client, email="missions2@example.com", username="missionschild2")
    user = (
        await db_session.execute(select(User).where(User.email == "missions2@example.com"))
    ).scalar_one()

    module = Module(topic="stocks", title="S", order_index=1)
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add(lesson)
    await db_session.flush()

    mission_a = ApplyMission(
        lesson_id=lesson.id, mission_type="first_buy", params_json={},
        title="Buy one", prompt="Make your first buy", xp_reward=20,
    )
    db_session.add(mission_a)
    await db_session.flush()

    lesson_b = Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=2)
    db_session.add(lesson_b)
    await db_session.flush()
    mission_b = ApplyMission(
        lesson_id=lesson_b.id, mission_type="first_sell", params_json={},
        title="Sell one", prompt="Make your first sell", xp_reward=20,
    )
    db_session.add(mission_b)
    await db_session.flush()

    db_session.add(ApplyMissionCompletion(user_id=user.id, mission_id=mission_a.id))
    await db_session.flush()

    resp = await client.get("/missions/active")
    assert resp.status_code == 200
    types = {row["mission_type"] for row in resp.json()}
    assert "first_sell" in types
    assert "first_buy" not in types
