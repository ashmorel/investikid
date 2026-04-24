import pytest
import uuid
from datetime import date
from sqlalchemy.exc import IntegrityError

from app.models.content import LessonCompletion, Module, Lesson
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_lesson_completion_unique_per_user_lesson(db_session):
    user = User(
        email="u@x.com", username="u", password_hash="x",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
    )
    module = Module(topic="stocks", title="t", country_codes=["GB"], order_index=0)
    db_session.add_all([user, module])
    await db_session.flush()

    lesson = Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.flush()

    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()
