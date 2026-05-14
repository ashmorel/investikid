import uuid

from app.schemas.content import LessonOut, ModuleOut


def test_module_out_accepts_orm_like_dict():
    data = dict(
        id=uuid.uuid4(), topic="stocks", title="Intro",
        country_codes=["GB", "US"], is_premium=False, order_index=0,
        locked=False,
    )
    m = ModuleOut.model_validate(data)
    assert m.topic == "stocks"
    assert m.locked is False


def test_lesson_out_preserves_content_json():
    data = dict(
        id=uuid.uuid4(), module_id=uuid.uuid4(), type="card",
        content_json={"body": "hello"}, xp_reward=10, order_index=0,
        completed=False, locked=False,
    )
    lesson_out = LessonOut.model_validate(data)
    assert lesson_out.content_json == {"body": "hello"}
