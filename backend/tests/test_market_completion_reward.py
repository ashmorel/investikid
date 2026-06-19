import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Module
from app.models.gamification import UserBadge
from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username="completionkid"):
    """Register + login a GB child (home == active == "GB"), set CSRF, return User.
    Mirrors test_market_enroll_reward._register_child."""
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


async def test_completing_only_gb_lesson_grants_completion_reward_once(client, db_session):
    # The test DB seeds ONLY the market catalog at session scope (see conftest's
    # seed_markets_once) and the db_session transaction rolls back per test, so the
    # module + lesson created here are the ONLY GB curriculum content visible. Assert
    # that invariant so the single-lesson "market complete" assumption stays honest.
    gb_lessons_before = await db_session.scalar(
        select(func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.market_code == "GB")
    )
    assert gb_lessons_before == 0

    # conftest seeds only the market catalog, not gamification badges, so seed the
    # "Market Mastered" badges here (idempotent) so the GB badge exists to grant.
    from app.seed.gamification import seed_market_badges

    await seed_market_badges(db_session)
    await db_session.flush()

    module = Module(
        topic="savings", title="GB Completion Mod", country_codes=[],
        is_premium=False, order_index=900, icon="💷", market_code="GB",
    )
    db_session.add(module)
    await db_session.flush()
    # xp_reward=0 so the lesson itself adds no coins (XP is mirrored to coins by
    # record_xp); the only coin delta is then the 250 completion bonus, keeping the
    # assertion exact rather than approximate.
    lesson = Lesson(
        module_id=module.id, type="card", xp_reward=0, order_index=0,
        content_json={"title": "Saving up", "body": "A plan for your money."},
    )
    db_session.add(lesson)
    await db_session.flush()

    child = await _register_child(client, db_session)
    # Registration enrols the home market (GB); active market is GB by default.
    assert child.active_market_code == "GB"
    enrolled = await db_session.get(UserMarketProgress, (child.id, "GB"))
    assert enrolled is not None

    prog = await db_session.get(UserProgress, child.id)
    start = (prog.virtual_coins or 0) if prog else 0

    r = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 1.0})
    assert r.status_code == 200
    assert r.json()["reward"]["coins"] == 250
    assert r.json()["reward"]["badge_name"] == "Market Mastered: United Kingdom"

    prog = await db_session.get(UserProgress, child.id)
    await db_session.refresh(prog)
    assert (prog.virtual_coins or 0) == start + 250

    row = await db_session.get(UserMarketProgress, (child.id, "GB"))
    assert row.completion_rewarded_at is not None

    badge = await db_session.scalar(
        select(UserBadge).where(UserBadge.user_id == child.id)
    )
    assert badge is not None

    # Repeat completion must not re-grant.
    r2 = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 1.0})
    assert r2.status_code == 200
    assert r2.json()["reward"]["coins"] == 0
