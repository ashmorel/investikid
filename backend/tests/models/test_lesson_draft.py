import pytest

from app.models.lesson_draft import LessonDraft

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_lesson_draft_persists(db_session):
    from app.models.content import Level, Module

    module = Module(
        topic="saving", title="Saving Basics", country_codes=[], is_premium=True, order_index=0
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(
        module_id=module.id, title="Level 2", order_index=1, is_premium=True, pass_threshold=0.7
    )
    db_session.add(level)
    await db_session.flush()

    draft = LessonDraft(
        level_id=level.id,
        type="card",
        content_json={"title": "T", "body": "B"},
        concept="compound interest",
        model_used="test-model",
        moderation_safe=True,
        moderation_category=None,
    )
    db_session.add(draft)
    await db_session.flush()
    fetched = await db_session.get(LessonDraft, draft.id)
    assert fetched is not None
    assert fetched.moderation_safe is True
    assert fetched.content_json["title"] == "T"
