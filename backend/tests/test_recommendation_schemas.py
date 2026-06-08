import uuid

import pytest
from pydantic import ValidationError

from app.schemas.admin import ModuleCreate, ModuleOut, ModuleUpdate


def test_module_create_with_prerequisites():
    pid = uuid.uuid4()
    m = ModuleCreate(
        topic="stocks", title="Test", icon="📈", order_index=0,
        prerequisite_ids=[pid], min_age=8, max_age=12,
    )
    assert m.prerequisite_ids == [pid]
    assert m.min_age == 8
    assert m.max_age == 12


def test_module_create_defaults_empty_prerequisites():
    m = ModuleCreate(topic="stocks", title="Test", icon="📈", order_index=0)
    assert m.prerequisite_ids == []
    assert m.min_age is None
    assert m.max_age is None


def test_module_update_accepts_prerequisites():
    pid = uuid.uuid4()
    m = ModuleUpdate(prerequisite_ids=[pid], min_age=10, max_age=14)
    assert m.prerequisite_ids == [pid]
    assert m.min_age == 10
    assert m.max_age == 14


def test_module_out_includes_new_fields():
    m = ModuleOut(
        id=uuid.uuid4(), topic="stocks", title="Test", icon="📈",
        is_premium=False, country_codes=[], order_index=0, lesson_count=3,
        prerequisite_ids=[], min_age=8, max_age=None,
    )
    assert m.prerequisite_ids == []
    assert m.min_age == 8
    assert m.max_age is None


def test_module_create_rejects_min_age_greater_than_max_age():
    with pytest.raises(ValidationError, match="min_age.*max_age"):
        ModuleCreate(
            topic="stocks", title="Test", icon="📈", order_index=0,
            min_age=15, max_age=8,
        )


def test_recommendation_item_accepts_level_context():
    import uuid as _uuid

    from app.schemas.ai import RecommendationCategoryItem

    lvl = _uuid.uuid4()
    item = RecommendationCategoryItem(
        module_id=_uuid.uuid4(),
        lesson_id=_uuid.uuid4(),
        level_id=lvl,
        level_title="Level 2",
        score=0.5,
        reason="Keep going!",
    )
    assert item.level_id == lvl
    assert item.level_title == "Level 2"


def test_recommendation_item_level_context_defaults_none():
    import uuid as _uuid

    from app.schemas.ai import RecommendationCategoryItem

    item = RecommendationCategoryItem(module_id=_uuid.uuid4(), score=0.0, reason="x")
    assert item.level_id is None
    assert item.level_title is None
