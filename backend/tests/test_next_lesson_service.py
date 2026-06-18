import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User
from app.services.next_lesson_service import resolve_next_lesson

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _register(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _get_user(db_session, email) -> User:
    return await db_session.scalar(select(User).where(User.email == email))


async def _module(db_session, title, order_index, *, lessons_per_level=1, levels=1):
    m = Module(topic="stocks", title=title, country_codes=[], is_premium=False, order_index=order_index, icon="📈")
    db_session.add(m)
    await db_session.flush()
    made = []
    for li in range(levels):
        lv = Level(module_id=m.id, title=f"{title} L{li}", order_index=li, is_premium=False, pass_threshold=0.7)
        db_session.add(lv)
        await db_session.flush()
        lessons = []
        for pi in range(lessons_per_level):
            lsn = Lesson(module_id=m.id, level_id=lv.id, type="card", order_index=pi, xp_reward=10,
                         content_json={"title": f"{title}-{li}-{pi}", "body": "b"})
            db_session.add(lsn)
            lessons.append(lsn)
        await db_session.flush()
        made.append((lv, lessons))
    return m, made


async def _complete(db_session, user, lesson):
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=1.0))
    await db_session.flush()


async def test_new_user_gets_first_module_first_lesson(client, db_session):
    await _register(client, "nl1@example.com", "nl1user")
    user = await _get_user(db_session, "nl1@example.com")
    m, made = await _module(db_session, "Mod A", 0)
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.module_id == m.id
    assert result.lesson_id == made[0][1][0].id
    assert result.mode == "start"


async def test_first_module_done_returns_second_module(client, db_session):
    # THE REPORTED BUG: module 1 complete, module 2 incomplete → must return module 2's lesson
    await _register(client, "nl2@example.com", "nl2user")
    user = await _get_user(db_session, "nl2@example.com")
    m1, made1 = await _module(db_session, "Mod 1", 0)
    m2, made2 = await _module(db_session, "Mod 2", 1)
    await _complete(db_session, user, made1[0][1][0])  # finish module 1's only lesson
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.module_id == m2.id
    assert result.lesson_id == made2[0][1][0].id
    assert result.mode == "start"


async def test_all_complete_returns_none(client, db_session):
    await _register(client, "nl3@example.com", "nl3user")
    user = await _get_user(db_session, "nl3@example.com")
    m, made = await _module(db_session, "Only Mod", 0)
    await _complete(db_session, user, made[0][1][0])
    result = await resolve_next_lesson(db_session, user)
    assert result is None


async def test_partial_module_is_continue(client, db_session):
    await _register(client, "nl4@example.com", "nl4user")
    user = await _get_user(db_session, "nl4@example.com")
    m, made = await _module(db_session, "Two Lessons", 0, lessons_per_level=2)
    await _complete(db_session, user, made[0][1][0])  # 1 of 2 done
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.lesson_id == made[0][1][1].id
    assert result.mode == "continue"


async def test_gb_user_never_gets_us_market_lesson(client, db_session):
    """Regression: market gate must exclude non-GB modules for GB users.

    Without is_module_in_market() the resolver would return the US module
    (order_index=0, first in iteration) rather than the GB module
    (order_index=1). The test fails if the gate is reverted to the old
    country_codes list check, because country_codes=[] was treated as
    "global" and would let the US module through.
    """
    await _register(client, "nl5@example.com", "nl5user")
    user = await _get_user(db_session, "nl5@example.com")
    # US-market module comes first (order_index=0) — gate must skip it.
    us_mod = Module(
        topic="stocks",
        title="US Module",
        market_code="US",
        country_codes=[],
        is_premium=False,
        order_index=0,
        icon="🇺🇸",
    )
    db_session.add(us_mod)
    await db_session.flush()
    us_lv = Level(module_id=us_mod.id, title="US L0", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(us_lv)
    await db_session.flush()
    us_lsn = Lesson(
        module_id=us_mod.id, level_id=us_lv.id, type="card", order_index=0, xp_reward=10,
        content_json={"title": "US Lesson", "body": "b"},
    )
    db_session.add(us_lsn)
    await db_session.flush()

    # GB-market module comes second (order_index=1) — gate must reach it.
    gb_mod, gb_made = await _module(db_session, "GB Module", 1)
    gb_lsn = gb_made[0][1][0]

    result = await resolve_next_lesson(db_session, user)

    assert result is not None, "Expected a GB lesson but got None"
    assert result.lesson_id != us_lsn.id, (
        "GB user was handed a US-market lesson — market gate is broken"
    )
    assert result.lesson_id == gb_lsn.id, (
        f"Expected GB lesson {gb_lsn.id} but got {result.lesson_id}"
    )
