"""Level-aware recommendation pointer (DB-backed)."""
from datetime import date

import pytest

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User
from app.services.recommendation_service import get_recommendations

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, *, premium=False):
    u = User(
        email=f"rl-{date.today()}-{premium}@example.com",
        username=f"rl{int(premium)}",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
        is_premium=premium, profiling_enabled=True, topic_path="stocks",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _module_two_levels(db_session, *, second_premium=False):
    m = Module(topic="stocks", title="Stocks 101", country_codes=["GB"],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    l1 = Level(module_id=m.id, title="Level 1", order_index=0,
               is_premium=False, pass_threshold=0.7, icon="1️⃣")
    l2 = Level(module_id=m.id, title="Level 2", order_index=1,
               is_premium=second_premium, pass_threshold=0.7, icon="2️⃣")
    db_session.add_all([l1, l2])
    await db_session.flush()
    lessons = []
    for lv in (l1, l2):
        for i in range(2):
            lsn = Lesson(module_id=m.id, level_id=lv.id, type="card",
                         xp_reward=10, order_index=i, content_json={"title": f"{lv.title}-{i}"})
            db_session.add(lsn)
            lessons.append((lv, lsn))
    await db_session.flush()
    return m, l1, l2, lessons


def _find(recs, module_id):
    for cat in ("continue_learning", "practise_again", "something_new"):
        for item in recs[cat]:
            if item["module_id"] == module_id:
                return item
    return None


async def test_pointer_targets_first_level_not_locked_second(db_session):
    u = await _user(db_session)
    m, l1, l2, lessons = await _module_two_levels(db_session, second_premium=True)
    first = [lsn for lv, lsn in lessons if lv.id == l1.id][0]
    db_session.add(LessonCompletion(user_id=u.id, lesson_id=first.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    second_l1 = [lsn for lv, lsn in lessons if lv.id == l1.id][1]
    assert item["lesson_id"] == second_l1.id
    assert item["level_id"] == l1.id
    assert item["level_title"] == "Level 1"


async def test_pointer_advances_to_second_level_when_first_passed(db_session):
    u = await _user(db_session)
    m, l1, l2, lessons = await _module_two_levels(db_session)
    for lv, lsn in lessons:
        if lv.id == l1.id:
            db_session.add(LessonCompletion(user_id=u.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    assert item["level_id"] == l2.id
    assert item["level_title"] == "Level 2"


async def test_pointer_none_when_remaining_level_locked(db_session):
    u = await _user(db_session)  # free user
    m, l1, l2, lessons = await _module_two_levels(db_session, second_premium=True)
    for lv, lsn in lessons:
        if lv.id == l1.id:
            db_session.add(LessonCompletion(user_id=u.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None  # module still surfaced
    assert item["lesson_id"] is None
    assert item["level_id"] is None


async def test_unlevelled_module_keeps_first_incomplete_lesson(db_session):
    u = await _user(db_session)
    m = Module(topic="stocks", title="Legacy", country_codes=["GB"],
               is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lessons = []
    for i in range(3):
        lsn = Lesson(module_id=m.id, level_id=None, type="card", xp_reward=10,
                     order_index=i, content_json={"title": f"L{i}"})
        db_session.add(lsn)
        lessons.append(lsn)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=u.id, lesson_id=lessons[0].id, score=0.9))
    await db_session.flush()

    recs = await get_recommendations(db_session, u)
    item = _find(recs, m.id)
    assert item is not None
    assert item["lesson_id"] == lessons[1].id
    assert item["level_id"] is None
    assert item["level_title"] is None
