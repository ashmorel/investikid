import uuid

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.content_variety_service import VariantSpec, resolve_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk_lesson(db_session) -> Lesson:
    m = Module(topic="savings", title="T", country_codes=[], is_premium=False, order_index=0, icon="🏦")
    db_session.add(m)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, type="quiz", content_json={"question": "q"}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _mk_user(db_session, *, premium: bool, profiling: bool) -> User:
    u = User(
        username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
        dob=__import__("datetime").date(2014, 1, 1), country_code="GB",
        currency_code="GBP", is_premium=premium, profiling_enabled=profiling,
        email=f"{uuid.uuid4().hex[:8]}@e.com",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_free_user_always_core_pool_one(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=False, profiling=True)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec == VariantSpec(rung="core", ordinal=0, pool_size=1)


async def test_premium_profiling_off_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=False)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"
    assert spec.pool_size == 3


async def test_premium_profiling_on_no_completion_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"
    assert spec.ordinal == 0


async def test_premium_low_score_is_easier_and_ordinal_rotates(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.2))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "easier"
    assert spec.ordinal == 1  # 1 completion % pool 3


async def test_premium_high_score_with_mastery_is_harder(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.9))
    db_session.add(TopicMastery(user_id=user.id, topic="savings", mastery_score=0.7))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "harder"


async def test_premium_high_score_without_mastery_is_core(db_session):
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=True)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=0.9))
    await db_session.flush()
    spec = await resolve_variant(db_session, user, lesson, "concept")
    assert spec.rung == "core"


async def test_profiling_off_does_not_query_score(db_session, monkeypatch):
    """AADC: profiling-off path must not read completion score / mastery."""
    lesson = await _mk_lesson(db_session)
    user = await _mk_user(db_session, premium=True, profiling=False)
    import app.services.content_variety_service as cvs
    calls = {"n": 0}
    real = cvs._latest_completion_score

    async def spy(*a, **k):
        calls["n"] += 1
        return await real(*a, **k)

    monkeypatch.setattr(cvs, "_latest_completion_score", spy)
    await resolve_variant(db_session, user, lesson, "concept")
    assert calls["n"] == 0
