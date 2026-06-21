"""Security gate tests for POST /lessons/{lesson_id}/view.

TDD: these tests were written BEFORE the fix. Initially:
  - test_record_lesson_view_unpublished_module_rejected → RED (gets 204, expects 404)
  - test_record_lesson_view_cross_market_module_rejected → RED (gets 204, expects 404)
  - test_record_lesson_view_accessible_module_ok → GREEN (already returns 204)

After adding `await _get_accessible_module(...)` to record_lesson_view all three pass.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.content import Lesson, LessonView, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


@pytest_asyncio.fixture
async def view_client(client, db_session):
    """Register and log in a fresh GB user for lesson-view gate tests."""
    payload = {
        **_USER_BASE,
        "email": "viewgate@example.com",
        "username": "viewgatekid",
    }
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


async def test_record_lesson_view_unpublished_module_rejected(view_client, db_session):
    """A child CANNOT record a view on a lesson in an UNPUBLISHED module."""
    module = Module(
        topic="savings",
        title="Unpublished Gate Test Module",
        country_codes=[],
        is_premium=False,
        order_index=900,
        market_code="GB",
        published=False,
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        type="card",
        content_json={"title": "Hidden lesson"},
        xp_reward=10,
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.flush()

    response = await view_client.post(f"/lessons/{lesson.id}/view")
    assert response.status_code == 404, (
        f"Expected 404 for unpublished module, got {response.status_code}"
    )

    # Confirm no LessonView was written
    view = await db_session.scalar(
        select(LessonView).where(LessonView.lesson_id == lesson.id)
    )
    assert view is None, "LessonView must NOT be created for an unpublished module"


async def test_record_lesson_view_cross_market_module_rejected(view_client, db_session):
    """A GB child CANNOT record a view on a lesson in a US-market module."""
    module = Module(
        topic="savings",
        title="Cross-Market Gate Test Module",
        country_codes=[],
        is_premium=False,
        order_index=901,
        market_code="US",
        published=True,
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        type="card",
        content_json={"title": "US-only lesson"},
        xp_reward=10,
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.flush()

    response = await view_client.post(f"/lessons/{lesson.id}/view")
    assert response.status_code == 404, (
        f"Expected 404 for cross-market module, got {response.status_code}"
    )

    # Confirm no LessonView was written
    view = await db_session.scalar(
        select(LessonView).where(LessonView.lesson_id == lesson.id)
    )
    assert view is None, "LessonView must NOT be created for a cross-market module"


async def test_record_lesson_view_accessible_module_ok(view_client, db_session):
    """A GB child CAN record a view on a lesson in a published GB free module."""
    module = Module(
        topic="savings",
        title="Accessible Gate Test Module",
        country_codes=[],
        is_premium=False,
        order_index=902,
        market_code="GB",
        published=True,
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        type="card",
        content_json={"title": "Accessible lesson"},
        xp_reward=10,
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.flush()

    response = await view_client.post(f"/lessons/{lesson.id}/view")
    assert response.status_code == 204, (
        f"Expected 204 for accessible module, got {response.status_code}"
    )

    # Confirm LessonView WAS written
    view = await db_session.scalar(
        select(LessonView).where(LessonView.lesson_id == lesson.id)
    )
    assert view is not None, "LessonView MUST be created for an accessible module"
