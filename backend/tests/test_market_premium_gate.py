import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, LessonCompletion, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username):
    """Register + login a GB child (home == active == "GB"), set CSRF, return User.
    Mirrors test_market_completion_reward._register_child."""
    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"{username}_parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return await db_session.scalar(select(User).where(User.username == username))


async def _make_lesson(db_session, *, market_code, title, order_index):
    """Create a non-premium module + a single card lesson in the given market."""
    module = Module(
        topic="savings", title=title, country_codes=[],
        is_premium=False, order_index=order_index, icon="💷", market_code=market_code,
    )
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, type="card", xp_reward=10, order_index=0,
        content_json={"title": "Saving up", "body": "A plan for your money."},
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_first_completion_sets_started_market(client, db_session):
    lesson = await _make_lesson(
        db_session, market_code="GB", title="GB Gate Mod A", order_index=910
    )
    child = await _register_child(client, db_session, username="gatekid_first")
    assert child.active_market_code == "GB"
    assert child.started_market_code is None

    r = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 1.0})
    assert r.status_code == 200

    user = await db_session.get(User, child.id)
    await db_session.refresh(user)
    assert user.started_market_code == "GB"


async def test_free_second_market_completion_blocked(client, db_session):
    gb_lesson = await _make_lesson(
        db_session, market_code="GB", title="GB Gate Mod B", order_index=911
    )
    us_lesson = await _make_lesson(
        db_session, market_code="US", title="US Gate Mod B", order_index=912
    )
    child = await _register_child(client, db_session, username="gatekid_block")

    # First GB completion claims the started market.
    r0 = await client.post(f"/lessons/{gb_lesson.id}/complete", json={"score": 1.0})
    assert r0.status_code == 200
    user = await db_session.get(User, child.id)
    await db_session.refresh(user)
    assert user.started_market_code == "GB"

    # Switch active market to US so the US module is fetchable, then attempt
    # completion of a DIFFERENT market's lesson while free.
    user.active_market_code = "US"
    await db_session.flush()

    xp_before = (await db_session.get(UserProgress, child.id)).xp

    r = await client.post(f"/lessons/{us_lesson.id}/complete", json={"score": 1.0})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "premium_required"

    # No completion row for the US lesson, and no XP awarded.
    us_completions = await db_session.scalar(
        select(func.count(LessonCompletion.id)).where(
            LessonCompletion.user_id == child.id,
            LessonCompletion.lesson_id == us_lesson.id,
        )
    )
    assert us_completions == 0
    prog = await db_session.get(UserProgress, child.id)
    await db_session.refresh(prog)
    assert prog.xp == xp_before


async def test_premium_second_market_completion_allowed(client, db_session):
    await _make_lesson(
        db_session, market_code="GB", title="GB Gate Mod C", order_index=913
    )
    us_lesson = await _make_lesson(
        db_session, market_code="US", title="US Gate Mod C", order_index=914
    )
    child = await _register_child(client, db_session, username="gatekid_premium")

    # Premium with started=GB, but completing a US lesson (active=US).
    child.is_premium = True
    child.started_market_code = "GB"
    child.active_market_code = "US"
    await db_session.flush()

    r = await client.post(f"/lessons/{us_lesson.id}/complete", json={"score": 1.0})
    assert r.status_code == 200


async def test_free_same_market_recompletion_allowed(client, db_session):
    gb_lesson = await _make_lesson(
        db_session, market_code="GB", title="GB Gate Mod D", order_index=915
    )
    child = await _register_child(client, db_session, username="gatekid_same")

    r1 = await client.post(f"/lessons/{gb_lesson.id}/complete", json={"score": 1.0})
    assert r1.status_code == 200
    user = await db_session.get(User, child.id)
    await db_session.refresh(user)
    assert user.started_market_code == "GB"

    # Same-market re-completion is allowed (not a 403).
    r2 = await client.post(f"/lessons/{gb_lesson.id}/complete", json={"score": 1.0})
    assert r2.status_code == 200
