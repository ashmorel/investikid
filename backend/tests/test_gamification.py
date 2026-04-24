import pytest
from datetime import datetime, timedelta, timezone
from app.models.gamification import Badge, Challenge
from app.models.content import Module, Lesson

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


async def _login(client, email="gplayer@example.com", username="gplayer"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed(db_session):
    module = Module(topic="stocks", title="T", country_codes=["GB"], is_premium=False, order_index=0)
    db_session.add(module)
    await db_session.flush()
    lessons = [
        Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=i)
        for i in range(3)
    ]
    db_session.add_all(lessons)

    first_lesson_badge = Badge(
        name="First Step", description="First lesson",
        icon_url="/x.svg", condition_type="lesson_count", condition_value=1,
    )
    db_session.add(first_lesson_badge)

    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = monday + timedelta(days=7)
    challenge = Challenge(
        title="Weekly Learner", description="3 lessons this week",
        type="lessons_completed", target_value=3, xp_reward=50,
        starts_at=monday, ends_at=end, is_premium=False,
    )
    db_session.add(challenge)
    await db_session.commit()
    return lessons, first_lesson_badge, challenge


async def test_completing_lesson_awards_badge(client, db_session):
    lessons, badge, _ = await _seed(db_session)
    await _login(client)
    await client.post(f"/lessons/{lessons[0].id}/complete", json={})

    r = await client.get("/users/me/badges")
    assert r.status_code == 200
    names = [b["name"] for b in r.json()]
    assert "First Step" in names


async def test_challenge_progress_increments(client, db_session):
    lessons, _, challenge = await _seed(db_session)
    await _login(client)

    await client.post(f"/lessons/{lessons[0].id}/complete", json={})
    r = await client.get("/challenges")
    assert r.status_code == 200
    body = [c for c in r.json() if c["id"] == str(challenge.id)]
    assert body and body[0]["progress"] == 1
    assert body[0]["completed_at"] is None


async def test_challenge_completion_sets_completed_at(client, db_session):
    lessons, _, challenge = await _seed(db_session)
    await _login(client)

    for l in lessons:
        await client.post(f"/lessons/{l.id}/complete", json={})
    r = await client.get("/challenges")
    body = [c for c in r.json() if c["id"] == str(challenge.id)]
    assert body[0]["progress"] == 3
    assert body[0]["completed_at"] is not None


async def test_leaderboard_lists_user(client, db_session):
    lessons, _, _ = await _seed(db_session)
    await _login(client)
    await client.post(f"/lessons/{lessons[0].id}/complete", json={})

    r = await client.get("/leaderboard")
    assert r.status_code == 200
    entries = r.json()
    assert any(e["username"] == "gplayer" and e["xp_this_week"] >= 10 for e in entries)


async def test_badges_list_empty_for_new_user(client):
    await _login(client)
    r = await client.get("/users/me/badges")
    assert r.status_code == 200
    assert r.json() == []
