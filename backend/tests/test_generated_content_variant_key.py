from app.models.generated_content import GeneratedContent


def test_model_has_variant_key_column():
    cols = GeneratedContent.__table__.columns
    assert "variant_key" in cols
    assert cols["variant_key"].nullable is False


def test_unique_constraint_includes_variant_key():
    uniques = [
        c for c in GeneratedContent.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    ]
    cols = {tuple(sorted(col.name for col in u.columns)) for u in uniques}
    assert ("concept", "lesson_id", "model_used", "variant_key") in cols
