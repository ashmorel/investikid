import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content_translation import ContentTranslation
from app.services.translation_service import translate_entity

pytestmark = pytest.mark.asyncio(loop_scope="session")


class FakeLesson:
    def __init__(self):
        self.id = uuid.uuid4()
        self.type = "card"
        self.content_json = {"title": "Hello", "body": "World"}


def _llm_returning(payload: dict):
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps(payload))
    return client


async def test_generates_auto_translation_and_stores(db_session):
    lesson = FakeLesson()
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour", "body": "Monde"})), \
         patch("app.services.translation_service.moderate_output",
               new=AsyncMock(return_value=type("R", (), {"safe": True})())):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    assert action == "generated"
    assert row is not None and row.status == "active" and row.source == "auto"
    assert row.translated_json == {"title": "Bonjour", "body": "Monde"}


async def test_idempotent_skips_fresh(db_session):
    lesson = FakeLesson()
    mod = AsyncMock(return_value=type("R", (), {"safe": True})())
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour", "body": "Monde"})), \
         patch("app.services.translation_service.moderate_output", new=mod):
        await translate_entity(db_session, "lesson", lesson, "fr")
        client2 = _llm_returning({"title": "X", "body": "Y"})
        with patch("app.services.translation_service.get_llm_client", return_value=client2):
            row, action = await translate_entity(db_session, "lesson", lesson, "fr")
            assert action == "skipped"
            client2.complete.assert_not_called()  # fresh → no second LLM call


async def test_structural_failure_marks_failed(db_session):
    lesson = FakeLesson()
    with patch("app.services.translation_service.get_llm_client",
               return_value=_llm_returning({"title": "Bonjour"})), \
         patch("app.services.translation_service.moderate_output",
               new=AsyncMock(return_value=type("R", (), {"safe": True})())):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    assert action == "failed"
    assert row is not None and row.status == "failed"


async def test_curated_not_overwritten(db_session):
    lesson = FakeLesson()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=lesson.id, language="fr",
        translated_json={"title": "Cur", "body": "Ated"}, source="curated",
        source_hash="whatever", status="active",
    ))
    await db_session.flush()
    client = _llm_returning({"title": "Auto", "body": "Gen"})
    with patch("app.services.translation_service.get_llm_client", return_value=client):
        row, action = await translate_entity(db_session, "lesson", lesson, "fr")
    client.complete.assert_not_called()
    assert action == "skipped" and row.source == "curated"
