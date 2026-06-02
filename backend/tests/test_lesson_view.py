import uuid

import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, LessonView, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="viewer@example.com", username="viewerkid"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed_free_lesson(db_session):
    module = Module(
        topic="savings",
        title="View Test Module",
        country_codes=[],
        is_premium=False,
        order_index=99,
    )
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id,
        type="card",
        content_json={"title": "View me", "body": "Some body"},
        xp_reward=10,
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.commit()
    return lesson


async def test_record_view_inserts_then_is_idempotent(client, db_session):
    lesson = await _seed_free_lesson(db_session)
    await _register_and_login(client)

    r1 = await client.post(f"/lessons/{lesson.id}/view")
    assert r1.status_code == 204

    r2 = await client.post(f"/lessons/{lesson.id}/view")
    assert r2.status_code == 204

    count = await db_session.scalar(
        select(func.count()).select_from(LessonView).where(LessonView.lesson_id == lesson.id)
    )
    assert count == 1


async def test_record_view_404_for_unknown_lesson(client, db_session):
    await _register_and_login(client, email="viewer2@example.com", username="viewerkid2")
    r = await client.post(f"/lessons/{uuid.uuid4()}/view")
    assert r.status_code == 404
