import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.content_translation import ContentTranslation

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unique_per_entity_language(db_session):
    eid = uuid.uuid4()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=eid, language="fr",
        translated_json={"title": "Bonjour"}, source="auto", source_hash="abc", status="active",
    ))
    await db_session.flush()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=eid, language="fr",
        translated_json={"title": "Salut"}, source="auto", source_hash="def", status="active",
    ))
    with pytest.raises(IntegrityError):
        await db_session.flush()
