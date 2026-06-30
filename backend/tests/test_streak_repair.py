"""B6 — `GET /users/me/progress` new fields + `POST /streak/repair`."""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.time import today_utc
from app.models.user import User, UserProgress
from app.services.streak_config import (
    STREAK_MILESTONE,
    STREAK_REPAIR_COST,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {
    "password": "SecurePass123!", "dob": "2006-01-01",
    "country_code": "GB", "currency_code": "GBP",
}


async def _login(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _progress(db_session, email):
    user = await db_session.scalar(select(User).where(User.email == email))
    progress = await db_session.scalar(select(UserProgress).where(UserProgress.user_id == user.id))
    if progress is None:
        progress = UserProgress(user_id=user.id)
        db_session.add(progress)
    return progress


# --- GET /users/me/progress new fields ---------------------------------------

async def test_progress_surfaces_next_freeze_in(client, db_session):
    await _login(client, "b6-prog@example.com", "b6prog")
    progress = await _progress(db_session, "b6-prog@example.com")
    progress.streak_count = 5  # 7 - (5 % 7) = 2
    progress.last_activity_date = today_utc()
    await db_session.flush()

    r = await client.get("/users/me/progress")
    assert r.status_code == 200
    body = r.json()
    assert body["next_freeze_in"] == STREAK_MILESTONE - 5
    assert body["streak_repair_available"] is False
    assert body["streak_repair_cost"] == STREAK_REPAIR_COST


async def test_progress_surfaces_repair_available_for_at_risk_streak(client, db_session):
    await _login(client, "b6-prog-risk@example.com", "b6progrisk")
    progress = await _progress(db_session, "b6-prog-risk@example.com")
    progress.streak_count = 5
    progress.last_activity_date = today_utc() - timedelta(days=2)  # gap 2, no freeze
    progress.streak_freezes = 0
    await db_session.flush()

    r = await client.get("/users/me/progress")
    assert r.status_code == 200
    body = r.json()
    assert body["streak_repair_available"] is True
    assert body["streak_repair_cost"] == STREAK_REPAIR_COST


# --- POST /streak/repair ------------------------------------------------------

async def test_repair_happy_path(client, db_session):
    await _login(client, "b6-repair@example.com", "b6repair")
    progress = await _progress(db_session, "b6-repair@example.com")
    progress.streak_count = 6
    progress.last_activity_date = today_utc() - timedelta(days=2)
    progress.streak_freezes = 0
    progress.virtual_coins = 200
    await db_session.flush()

    r = await client.post("/streak/repair")
    assert r.status_code == 200
    body = r.json()
    assert body["virtual_coins"] == 200 - STREAK_REPAIR_COST
    assert body["streak_count"] == 6  # preserved
    assert body["last_activity_date"] == (today_utc() - timedelta(days=1)).isoformat()
    # repair window is closed now (gap == 1)
    assert body["streak_repair_available"] is False


async def test_repair_insufficient_coins(client, db_session):
    await _login(client, "b6-poor@example.com", "b6poor")
    progress = await _progress(db_session, "b6-poor@example.com")
    progress.streak_count = 6
    progress.last_activity_date = today_utc() - timedelta(days=2)
    progress.streak_freezes = 0
    progress.virtual_coins = STREAK_REPAIR_COST - 1
    await db_session.flush()

    r = await client.post("/streak/repair")
    assert r.status_code == 409
    assert r.json()["detail"] == "not_enough_coins"


async def test_repair_not_eligible(client, db_session):
    await _login(client, "b6-alive@example.com", "b6alive")
    progress = await _progress(db_session, "b6-alive@example.com")
    progress.streak_count = 6
    progress.last_activity_date = today_utc() - timedelta(days=1)  # still alive
    progress.virtual_coins = 200
    await db_session.flush()

    r = await client.post("/streak/repair")
    assert r.status_code == 409
    assert r.json()["detail"] == "streak_not_repairable"


async def test_repair_second_call_is_conflict(client, db_session):
    await _login(client, "b6-twice@example.com", "b6twice")
    progress = await _progress(db_session, "b6-twice@example.com")
    progress.streak_count = 6
    progress.last_activity_date = today_utc() - timedelta(days=2)
    progress.streak_freezes = 0
    progress.virtual_coins = 200
    await db_session.flush()

    first = await client.post("/streak/repair")
    assert first.status_code == 200
    second = await client.post("/streak/repair")
    assert second.status_code == 409
    assert second.json()["detail"] == "streak_not_repairable"


async def test_repair_requires_auth(client):
    """Unauthenticated POST is rejected (401/403), not 404 — the endpoint exists
    and is auth-gated. (No login → no auth cookie.)"""
    r = await client.post("/streak/repair")
    assert r.status_code in (401, 403)
