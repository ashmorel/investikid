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


from app.models.content import Module, Lesson, LessonCompletion
from app.models.gamification import Badge, UserBadge, Challenge, UserChallenge
from app.models.simulator import Portfolio, Holding, Trade
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.audit import AuditLog


def test_module_columns():
    cols = {c.key for c in Module.__table__.columns}
    assert {"id", "topic", "title", "country_codes", "is_premium", "order_index"}.issubset(cols)


def test_lesson_columns():
    cols = {c.key for c in Lesson.__table__.columns}
    assert {"id", "module_id", "type", "content_json", "xp_reward", "order_index"}.issubset(cols)


def test_portfolio_columns():
    cols = {c.key for c in Portfolio.__table__.columns}
    assert {"id", "user_id", "virtual_cash", "currency_code"}.issubset(cols)


def test_audit_log_columns():
    cols = {c.key for c in AuditLog.__table__.columns}
    assert {"id", "user_id", "event_type", "ip_address", "metadata_json", "created_at"}.issubset(cols)
