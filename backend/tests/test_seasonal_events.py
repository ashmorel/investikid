"""Seasonal events (M9 Task 3)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.content import Lesson
from app.services.event_service import boosted_xp, get_active_event, set_event
from tests.test_billing import _csrf_headers
from tests.test_content import _register_and_login, _seed_modules

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _event(pct=25, *, active=True) -> dict:
    now = datetime.now(UTC)
    delta = timedelta(days=1) if active else timedelta(days=10)
    return {
        "title": "Spooky Savings Week",
        "emoji": "🎃",
        "starts_at": (now - delta).isoformat(),
        "ends_at": (now - delta + timedelta(days=7)).isoformat() if not active else (now + timedelta(days=6)).isoformat(),
        "xp_bonus_pct": pct,
    }


async def test_active_window_and_clear(db_session):
    await set_event(db_session, _event())
    event = await get_active_event(db_session)
    assert event and event["title"] == "Spooky Savings Week" and event["xp_bonus_pct"] == 25

    await set_event(db_session, _event(active=False))
    assert await get_active_event(db_session) is None

    await set_event(db_session, None)
    assert await get_active_event(db_session) is None


async def test_malformed_event_is_ignored(db_session):
    from app.services.app_settings import set_setting
    from app.services.event_service import EVENT_KEY

    await set_setting(db_session, EVENT_KEY, "{not json")
    assert await get_active_event(db_session) is None


def test_boosted_xp_maths():
    assert boosted_xp(10, {"xp_bonus_pct": 25}) == 13  # round(12.5)
    assert boosted_xp(10, {"xp_bonus_pct": 0}) == 10
    assert boosted_xp(10, None) == 10


async def test_lesson_completion_applies_bonus(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await set_event(db_session, _event(pct=50))
    await db_session.commit()

    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"ev{suffix}@example.com", username=f"ev{suffix}")
    r = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r.status_code == 200
    assert r.json()["xp_awarded"] == 15  # 10 * 1.5

    await set_event(db_session, None)
    await db_session.commit()


async def test_events_active_endpoint(client, db_session):
    await set_event(db_session, _event())
    await db_session.commit()
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"ea{suffix}@example.com", username=f"ea{suffix}")
    r = await client.get("/events/active")
    assert r.status_code == 200
    assert r.json()["event"]["title"] == "Spooky Savings Week"
    await set_event(db_session, None)
    await db_session.commit()


async def test_admin_settings_event_roundtrip(admin_client, db_session):
    now = datetime.now(UTC)
    payload = {
        "alert_emails": [],
        "seasonal_event": {
            "title": "Money March",
            "emoji": "💰",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
            "xp_bonus_pct": 10,
        },
    }
    r = await admin_client.put("/admin/settings", json=payload, headers=_csrf_headers(admin_client))
    assert r.status_code == 200
    assert r.json()["seasonal_event"]["title"] == "Money March"

    # invalid window rejected
    bad = dict(payload, seasonal_event=dict(payload["seasonal_event"], ends_at=now.isoformat(), starts_at=(now + timedelta(days=1)).isoformat()))
    assert (await admin_client.put("/admin/settings", json=bad, headers=_csrf_headers(admin_client))).status_code == 422

    # clear
    r = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": [], "clear_seasonal_event": True},
        headers=_csrf_headers(admin_client),
    )
    assert r.status_code == 200
    assert r.json()["seasonal_event"] is None
