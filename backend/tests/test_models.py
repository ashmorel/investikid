from app.models.user import User, UserProgress


def test_user_model_columns():
    cols = {c.key for c in User.__table__.columns}
    assert {"id", "email", "username", "password_hash", "dob",
            "country_code", "currency_code", "topic_path",
            "is_premium", "parent_email", "parent_consent_given_at",
            "created_at"}.issubset(cols)


def test_user_progress_model_columns():
    cols = {c.key for c in UserProgress.__table__.columns}
    assert {"user_id", "xp", "level", "streak_count",
            "last_activity_date", "virtual_coins"}.issubset(cols)
