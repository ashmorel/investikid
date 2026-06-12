"""record_xp daily-goal seam (M7 Task 1)."""
from datetime import date

import pytest

from app.models.user import UserProgress
from app.services.xp_service import record_xp

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2026, 6, 12)
YESTERDAY = date(2026, 6, 11)


def _progress(**kw) -> UserProgress:
    base = dict(xp=0, level=1, daily_goal_xp=30, xp_today=0, xp_today_date=None)
    base.update(kw)
    return UserProgress(**base)


def test_accumulates_within_the_day_and_flips_goal_once():
    p = _progress()
    r1 = record_xp(p, 10, today=TODAY)
    assert (p.xp, p.xp_today, p.xp_today_date) == (10, 10, TODAY)
    assert r1.goal_met_now is False and r1.goal_met_today is False

    r2 = record_xp(p, 25, today=TODAY)  # 35 >= 30 — crosses the line
    assert r2.goal_met_now is True and r2.goal_met_today is True

    r3 = record_xp(p, 10, today=TODAY)  # already met — no second celebration
    assert r3.goal_met_now is False and r3.goal_met_today is True


def test_resets_window_on_new_day():
    p = _progress(xp=100, xp_today=50, xp_today_date=YESTERDAY)
    record_xp(p, 5, today=TODAY)
    assert p.xp == 105
    assert p.xp_today == 5
    assert p.xp_today_date == TODAY


def test_respects_custom_goal_and_updates_level():
    p = _progress(daily_goal_xp=10, xp=95)
    r = record_xp(p, 10, today=TODAY)
    assert r.goal_met_now is True
    assert p.level >= 2  # 105 XP crosses the 100-XP level threshold


def test_zero_award_never_flips():
    p = _progress(daily_goal_xp=10, xp_today=0)
    r = record_xp(p, 0, today=TODAY)
    assert r.goal_met_now is False


async def test_progress_endpoint_and_goal_patch(client, db_session):
    import uuid as _uuid

    from tests.test_content import _register_and_login

    suffix = _uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"g{suffix}@example.com", username=f"g{suffix}")

    r = await client.get("/users/me/progress")
    assert r.status_code == 200
    body = r.json()
    assert body["daily_goal_xp"] == 30
    assert body["xp_today"] == 0
    assert body["goal_met"] is False

    r = await client.patch("/users/me/goal", json={"daily_goal_xp": 10})
    assert r.status_code == 200
    assert r.json()["daily_goal_xp"] == 10

    r = await client.patch("/users/me/goal", json={"daily_goal_xp": 25})
    assert r.status_code == 422


async def test_completion_reports_daily_goal_met_once(client, db_session):
    import uuid as _uuid

    from app.models.content import Lesson
    from tests.test_content import _register_and_login, _seed_modules

    gb_free, _, _, _ = await _seed_modules(db_session)
    l1 = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    l2 = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add_all([l1, l2])
    await db_session.commit()

    suffix = _uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"gm{suffix}@example.com", username=f"gm{suffix}")
    r = await client.patch("/users/me/goal", json={"daily_goal_xp": 10})
    assert r.status_code == 200

    r1 = await client.post(f"/lessons/{l1.id}/complete", json={})
    assert r1.status_code == 200
    assert r1.json()["daily_goal_met"] is True  # 10/10 — crossed now

    r2 = await client.post(f"/lessons/{l2.id}/complete", json={})
    assert r2.json()["daily_goal_met"] is False  # already met today
