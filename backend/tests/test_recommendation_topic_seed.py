import datetime
import uuid

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.user import User
from app.services.recommendation_service import get_recommendations

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, **kw):
    u = User(username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
             dob=datetime.date(2014, 1, 1), country_code="GB", currency_code="GBP",
             email=f"{uuid.uuid4().hex[:8]}@e.com", **kw)
    db_session.add(u)
    await db_session.flush()
    return u


async def _module_with_lesson(db_session, topic, oi):
    m = Module(topic=topic, title=f"{topic}-m", country_codes=[], is_premium=False,
               order_index=oi, icon="📚")
    db_session.add(m)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, type="card", content_json={"title": "x"},
                    xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.flush()
    return m, lesson


async def test_profiling_off_with_topic_path_seeds_something_new(db_session):
    m, lesson = await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path="savings")
    rec = await get_recommendations(db_session, user)
    assert len(rec["something_new"]) == 1
    assert rec["something_new"][0]["lesson_id"] == lesson.id
    assert rec["continue_learning"] == []
    assert rec["practise_again"] == []


async def test_profiling_off_no_topic_path_returns_empty(db_session):
    await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path=None)
    rec = await get_recommendations(db_session, user)
    assert rec["continue_learning"] == []
    assert rec["practise_again"] == []
    assert rec["something_new"] == []


async def test_profiling_off_with_completion_returns_empty(db_session):
    _, lesson = await _module_with_lesson(db_session, "savings", 0)
    user = await _user(db_session, profiling_enabled=False, topic_path="savings")
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=1.0))
    await db_session.flush()
    rec = await get_recommendations(db_session, user)
    assert rec["something_new"] == []
