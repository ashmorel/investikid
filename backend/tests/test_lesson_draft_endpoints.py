import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

CARD = json.dumps({"title": "T", "body": "B"})


async def _make_level(admin_client) -> str:
    """Create a module + level via the admin API, returning the level id."""
    r = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Gen Mod", "icon": "📈", "order_index": 0,
    })
    assert r.status_code == 200
    module_id = r.json()["id"]
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 1", "order_index": 0, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200
    return r.json()["id"]


async def test_generate_requires_admin(client):
    resp = await client.post(
        "/admin/levels/00000000-0000-0000-0000-000000000000/generate",
        json={"concept": "x", "count": 1, "types": ["card"]},
    )
    assert resp.status_code in (401, 403)


async def test_generate_happy_path(admin_client):
    level_id = await _make_level(admin_client)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.post(
            f"/admin/levels/{level_id}/generate",
            json={"concept": "compound interest", "count": 2, "types": ["card"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["created"]) == 2 and body["skipped"] == 0


async def test_generate_unknown_level_404(admin_client):
    resp = await admin_client.post(
        "/admin/levels/00000000-0000-0000-0000-000000000000/generate",
        json={"concept": "x", "count": 1, "types": ["card"]},
    )
    assert resp.status_code == 404


async def test_list_drafts(admin_client):
    level_id = await _make_level(admin_client)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        await admin_client.post(
            f"/admin/levels/{level_id}/generate",
            json={"concept": "x", "count": 1, "types": ["card"]},
        )
    resp = await admin_client.get(f"/admin/levels/{level_id}/drafts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_edit_draft_revalidates_and_remoderates(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft)
    await db_session.flush()
    with patch("app.routers.admin.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.put(f"/admin/lesson-drafts/{draft.id}",
                                      json={"content_json": {"title": "New", "body": "Body"}})
    assert resp.status_code == 200
    assert resp.json()["content_json"]["title"] == "New"


async def test_edit_draft_invalid_content_422(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft)
    await db_session.flush()
    resp = await admin_client.put(f"/admin/lesson-drafts/{draft.id}", json={"content_json": {"title": "only"}})
    assert resp.status_code == 422


async def test_approve_flagged_draft_409(admin_client, db_session):
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=False, moderation_category="violence")
    db_session.add(draft)
    await db_session.flush()
    resp = await admin_client.post(f"/admin/lesson-drafts/{draft.id}/approve")
    assert resp.status_code == 409
    # no Lesson created
    from sqlalchemy import select

    from app.models.content import Lesson
    lessons = (await db_session.scalars(select(Lesson).where(Lesson.level_id == draft.level_id))).all()
    assert lessons == []


async def test_approve_safe_draft_materialises_lesson(admin_client, db_session):
    from sqlalchemy import select

    from app.models.content import Lesson
    from app.models.lesson_draft import LessonDraft
    level_id = await _make_level(admin_client)
    draft = LessonDraft(level_id=level_id, type="card", content_json={"title": "A", "body": "B"},
                        concept="x", model_used="m", moderation_safe=True, moderation_category=None)
    db_session.add(draft)
    await db_session.flush()
    resp = await admin_client.post(f"/admin/lesson-drafts/{draft.id}/approve")
    assert resp.status_code == 200
    lessons = (await db_session.scalars(select(Lesson).where(Lesson.level_id == draft.level_id))).all()
    assert any(le.type == "card" and le.content_json["title"] == "A" for le in lessons)
    assert await db_session.get(LessonDraft, draft.id) is None
