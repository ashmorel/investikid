import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Lesson, Module
from app.models.content_translation import ContentTranslation

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_gb_lesson(db_session) -> uuid.UUID:
    """Create one GB module + card lesson inline (mirrors
    test_market_completion_reward's content creation). Returns the lesson id."""
    module = Module(
        topic="savings", title="GB Translations Mod", country_codes=[],
        is_premium=False, order_index=901, icon="💷", market_code="GB",
    )
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, type="card", xp_reward=0, order_index=0,
        content_json={"title": "Saving up", "body": "A plan for your money."},
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson.id


async def test_coverage_empty(admin_client):
    r = await admin_client.get("/admin/translations/coverage?language=fr")
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "fr"
    assert "modules" in body and "levels" in body and "lessons" in body
    for bucket in ("modules", "levels", "lessons"):
        assert set(body[bucket].keys()) == {"active", "failed", "missing"}


async def test_curated_override_roundtrip(admin_client, db_session):
    lesson_id = await _create_gb_lesson(db_session)
    r = await admin_client.put("/admin/translations/curated", json={
        "entity_type": "lesson", "entity_id": str(lesson_id), "language": "fr",
        "translated_json": {"title": "Bonjour", "body": "Monde"},
    })
    assert r.status_code == 200

    cov = await admin_client.get("/admin/translations/coverage?language=fr")
    assert cov.status_code == 200
    assert cov.json()["lessons"]["active"] >= 1

    # The stored row is curated + active.
    from sqlalchemy import select
    row = await db_session.scalar(
        select(ContentTranslation).where(
            ContentTranslation.entity_id == lesson_id,
            ContentTranslation.language == "fr",
        )
    )
    assert row is not None
    assert row.source == "curated"
    assert row.status == "active"
    assert row.translated_json == {"title": "Bonjour", "body": "Monde"}


async def test_curated_rejects_invalid_structure(admin_client, db_session):
    lesson_id = await _create_gb_lesson(db_session)
    # Missing the "body" key → structural validation must reject.
    r = await admin_client.put("/admin/translations/curated", json={
        "entity_type": "lesson", "entity_id": str(lesson_id), "language": "fr",
        "translated_json": {"title": "Bonjour"},
    })
    assert r.status_code == 422


async def test_generate_tallies_actions(admin_client, db_session):
    await _create_gb_lesson(db_session)

    async def _stub(session, entity_type, entity, language):
        return (object(), "generated")

    with patch("app.routers.admin_translations.translate_entity", new=AsyncMock(side_effect=_stub)):
        r = await admin_client.post(
            "/admin/translations/generate",
            json={"language": "fr", "market_code": "GB"},
        )
    assert r.status_code == 200
    body = r.json()
    # 1 module + 1 lesson (no levels) → 2 "generated" entities.
    assert body["translated"] == 2
    assert body["skipped_fresh"] == 0
    assert body["failed"] == 0
