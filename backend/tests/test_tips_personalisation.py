from app.services.tips_service import learning_stage


def test_learning_stage_buckets():
    assert learning_stage(0) == "new"
    assert learning_stage(1) == "beginner"
    assert learning_stage(5) == "beginner"
    assert learning_stage(6) == "intermediate"
    assert learning_stage(15) == "intermediate"
    assert learning_stage(16) == "advanced"
    assert learning_stage(999) == "advanced"
