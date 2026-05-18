import uuid

import pytest

from app.models.content import Lesson, Module

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


async def _register_and_login(client, email="learner@example.com", username="learner", country_code="GB"):
    payload = {**_USER_BASE, "email": email, "username": username, "country_code": country_code}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed_modules(db_session):
    gb_free = Module(topic="stocks", title="Stocks GB", country_codes=["GB"], is_premium=False, order_index=0)
    us_free = Module(topic="stocks", title="Stocks US", country_codes=["US"], is_premium=False, order_index=1)
    global_free = Module(topic="savings", title="Savings Global", country_codes=[], is_premium=False, order_index=2)
    gb_premium = Module(topic="real_estate", title="REITs GB", country_codes=["GB"], is_premium=True, order_index=3)
    db_session.add_all([gb_free, us_free, global_free, gb_premium])
    await db_session.commit()
    return gb_free, us_free, global_free, gb_premium


async def test_list_modules_filters_by_country_and_premium(client, db_session):
    await _seed_modules(db_session)
    await _register_and_login(client, country_code="GB")
    response = await client.get("/modules")
    assert response.status_code == 200
    modules = response.json()
    titles = {m["title"]: m for m in modules}
    assert "Stocks GB" in titles and titles["Stocks GB"]["locked"] is False
    assert "Savings Global" in titles and titles["Savings Global"]["locked"] is False
    assert "REITs GB" in titles and titles["REITs GB"]["locked"] is True
    assert "Stocks US" not in titles


async def test_list_modules_unauthenticated(client):
    response = await client.get("/modules")
    assert response.status_code == 401


async def test_list_lessons_includes_completed_flag(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson1 = Lesson(module_id=gb_free.id, type="card", content_json={"title": "Hi"}, xp_reward=10, order_index=0)
    lesson2 = Lesson(module_id=gb_free.id, type="quiz", content_json={"q": "?"}, xp_reward=25, order_index=1)
    db_session.add_all([lesson1, lesson2])
    await db_session.commit()

    await _register_and_login(client)
    response = await client.get(f"/modules/{gb_free.id}/lessons")
    assert response.status_code == 200
    lessons = response.json()
    assert len(lessons) == 2
    assert all("completed" in item for item in lessons)
    assert lessons[0]["order_index"] == 0


async def test_list_lessons_blocked_on_inaccessible_module(client, db_session):
    _, _, _, gb_premium = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_premium.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    response = await client.get(f"/modules/{gb_premium.id}/lessons")
    assert response.status_code == 403


async def test_get_lesson_returns_content(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={"body": "hello"}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    response = await client.get(f"/lessons/{lesson.id}")
    assert response.status_code == 200
    assert response.json()["content_json"] == {"body": "hello"}


async def test_get_lesson_not_found(client):
    await _register_and_login(client)
    response = await client.get(f"/lessons/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_lesson_blocked_on_inaccessible_module(client, db_session):
    _, _, _, gb_premium = await _seed_modules(db_session)
    lesson = Lesson(
        module_id=gb_premium.id, type="card", content_json={"secret": "hidden"}, xp_reward=10, order_index=0
    )
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    response = await client.get(f"/lessons/{lesson.id}")
    assert response.status_code == 403


async def test_complete_lesson_awards_xp(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    response = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["xp_awarded"] == 10
    assert body["already_completed"] is False
    assert body["total_xp"] == 10
    assert body["level"] == 1
    assert body["streak_count"] == 1


async def test_complete_lesson_idempotent(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    r1 = await client.post(f"/lessons/{lesson.id}/complete", json={})
    r2 = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["already_completed"] is True
    assert r2.json()["xp_awarded"] == 0
    assert r2.json()["total_xp"] == 10


async def test_complete_lesson_levels_up(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lessons = [
        Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=50, order_index=i)
        for i in range(3)
    ]
    db_session.add_all(lessons)
    await db_session.commit()

    await _register_and_login(client)
    responses = []
    for lesson in lessons:
        r = await client.post(f"/lessons/{lesson.id}/complete", json={})
        responses.append(r.json())
    assert responses[-1]["total_xp"] == 150
    assert responses[-1]["level"] == 2


async def test_complete_lesson_premium_gated(client, db_session):
    _, _, _, gb_premium = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_premium.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    response = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert response.status_code == 403


async def test_complete_lesson_requires_csrf(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    await _register_and_login(client)
    client.headers.pop("X-CSRF-Token", None)
    response = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert response.status_code == 403


async def test_premium_module_gated_for_free_user(client, db_session):
    from sqlalchemy import select

    from app.models.content import Module
    from app.seed.content import seed_modules_and_lessons
    from app.seed.gamification import seed_badges_and_challenges

    await seed_modules_and_lessons(db_session)
    await seed_badges_and_challenges(db_session)
    await db_session.commit()

    premium_mod = await db_session.scalar(
        select(Module).where(Module.is_premium.is_(True)).limit(1)
    )
    assert premium_mod is not None, "expected at least one seeded premium module"

    # Register and log in as a free (non-premium) child user
    await _register_and_login(client, email="freecontent@example.com", username="freecontentkid")

    # A free user must be blocked from accessing a premium module's lessons
    detail = await client.get(f"/modules/{premium_mod.id}/lessons")
    assert detail.status_code == 403

    # The module must appear in the list but show locked: true
    lst = await client.get("/modules")
    assert lst.status_code == 200
    locked = [m for m in lst.json() if m["id"] == str(premium_mod.id)]
    assert locked and locked[0]["locked"] is True


async def test_lesson_summary_includes_derived_title(client, db_session):
    module = Module(topic="stocks", title="Title Test", country_codes=[], is_premium=False, order_index=10)
    db_session.add(module)
    await db_session.flush()

    db_session.add_all([
        Lesson(module_id=module.id, type="card", order_index=0, xp_reward=10,
               content_json={"title": "Card title", "body": "b"}),
        Lesson(module_id=module.id, type="quiz", order_index=1, xp_reward=10,
               content_json={"question": "Quiz question?", "choices": ["a", "b"],
                              "answer_index": 0, "explanation": "e"}),
        Lesson(module_id=module.id, type="scenario", order_index=2, xp_reward=10,
               content_json={"prompt": "Scenario prompt",
                              "choices": [{"label": "x", "outcome": "o"}], "correct_index": 0}),
        Lesson(module_id=module.id, type="video", order_index=3, xp_reward=10,
               content_json={"youtube_id": "abc", "caption": "Caption text"}),
        Lesson(module_id=module.id, type="video", order_index=4, xp_reward=10,
               content_json={"youtube_id": "def"}),  # no caption
    ])
    await db_session.commit()

    await _register_and_login(client, email="ts@example.com", username="tsuser", country_code="GB")
    response = await client.get(f"/modules/{module.id}/lessons")
    assert response.status_code == 200
    titles = [lesson["title"] for lesson in response.json()]
    assert titles == ["Card title", "Quiz question?", "Scenario prompt", "Caption text", "Video lesson"]
