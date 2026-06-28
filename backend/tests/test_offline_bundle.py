from datetime import UTC, datetime

import pytest

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PAST = datetime(2020, 1, 1, tzinfo=UTC)
_FUTURE = datetime(2030, 1, 1, tzinfo=UTC)
_BETWEEN = "2025-01-01T00:00:00+00:00"

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="bundle@example.com", username="bundlekid"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed_market(db_session):
    """Seed a GB module/level/lessons + a US module/lesson the GB child must never see."""
    gb_mod = Module(topic="stocks", title="Stocks GB", country_codes=[], is_premium=False,
                    order_index=0, market_code="GB")
    us_mod = Module(topic="stocks", title="Stocks US", country_codes=[], is_premium=False,
                    order_index=1, market_code="US")
    db_session.add_all([gb_mod, us_mod])
    await db_session.flush()

    gb_level = Level(module_id=gb_mod.id, title="GB L1", order_index=0, is_premium=False)
    db_session.add(gb_level)
    await db_session.flush()

    # Explicit updated_at set at INSERT (onupdate=func.now() only fires on UPDATE),
    # so the delta test has a deterministic timeline without fighting the shared-txn
    # fixture's frozen now()/identity map: lessons 0 & 2 in the past, lesson 1 future.
    stamps = [_PAST, _FUTURE, _PAST]
    gb_lessons = [
        Lesson(module_id=gb_mod.id, level_id=gb_level.id, type="card",
               content_json={"title": f"GB lesson {i}"}, xp_reward=10, order_index=i,
               updated_at=stamps[i])
        for i in range(3)
    ]
    us_lesson = Lesson(module_id=us_mod.id, type="card",
                       content_json={"title": "US lesson"}, xp_reward=10, order_index=0)
    db_session.add_all([*gb_lessons, us_lesson])
    await db_session.commit()
    return gb_mod, gb_level, gb_lessons, us_mod, us_lesson


async def test_empty_since_returns_full_market(client, db_session):
    gb_mod, gb_level, gb_lessons, _, _ = await _seed_market(db_session)
    await _register_and_login(client)

    resp = await client.get("/offline-bundle")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["market"] == "GB"
    # All GB lessons present (since=None → full set).
    lesson_ids = {lsn["id"] for lsn in body["lessons"]}
    assert lesson_ids == {str(lsn.id) for lsn in gb_lessons}
    # Metadata populated.
    assert {m["id"] for m in body["modules"]} == {str(gb_mod.id)}
    assert str(gb_mod.id) in body["module_levels"]
    assert {lv["id"] for lv in body["module_levels"][str(gb_mod.id)]} == {str(gb_level.id)}
    assert str(gb_level.id) in body["level_lessons"]
    # current_ids mirror the full id sets.
    assert set(body["current_ids"]["lessons"]) == {str(lsn.id) for lsn in gb_lessons}
    assert set(body["current_ids"]["modules"]) == {str(gb_mod.id)}
    assert set(body["current_ids"]["levels"]) == {str(gb_level.id)}


async def test_delta_returns_only_changed_lesson(client, db_session):
    # _seed_market stamps lessons 0 & 2 in the past, lesson 1 in the future.
    gb_mod, gb_level, gb_lessons, _, _ = await _seed_market(db_session)
    await _register_and_login(client, email="delta@example.com", username="deltakid")

    bumped = gb_lessons[1]
    # Pass `since` via params so httpx URL-encodes the "+" in the tz offset
    # (a raw "+" in the query string would decode to a space and fail to parse).
    resp = await client.get("/offline-bundle", params={"since": _BETWEEN})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Only the one lesson with updated_at > since comes back in the delta.
    assert {lsn["id"] for lsn in body["lessons"]} == {str(bumped.id)}
    # Metadata + current_ids stay complete despite the delta.
    assert set(body["current_ids"]["lessons"]) == {str(lsn.id) for lsn in gb_lessons}
    assert {m["id"] for m in body["modules"]} == {str(gb_mod.id)}


async def test_other_market_never_appears(client, db_session):
    gb_mod, _, gb_lessons, us_mod, us_lesson = await _seed_market(db_session)
    await _register_and_login(client, email="scope@example.com", username="scopekid")

    resp = await client.get("/offline-bundle")
    body = resp.json()

    all_lesson_ids = set(body["current_ids"]["lessons"]) | {lsn["id"] for lsn in body["lessons"]}
    assert str(us_lesson.id) not in all_lesson_ids
    assert str(us_mod.id) not in body["current_ids"]["modules"]
    assert str(us_mod.id) not in {m["id"] for m in body["modules"]}


async def test_server_time_is_iso8601(client, db_session):
    await _seed_market(db_session)
    await _register_and_login(client, email="clock@example.com", username="clockkid")

    resp = await client.get("/offline-bundle")
    body = resp.json()
    assert "server_time" in body
    # Parseable as ISO8601 (handle a trailing Z if present).
    parsed = datetime.fromisoformat(body["server_time"].replace("Z", "+00:00"))
    assert parsed is not None


async def test_unauthenticated_returns_401(client):
    resp = await client.get("/offline-bundle")
    assert resp.status_code == 401
