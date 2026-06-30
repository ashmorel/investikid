"""Tests for GET /diagnostic/recheck-status (Task 2, A2 Unit 4).

TDD: tests written first, run → fail, then implementation lands.

Coverage:
- active_days below first milestone → due:false
- active_days >= 5, 0 progress checkpoints → due:true, milestone:5
- 1 progress checkpoint + active_days 10 (< 15) → due:false
- 1 progress checkpoint + active_days >= 15 → due:true, milestone:15
- 3 progress checkpoints (all milestones done) → due:false, milestone:null
- submitting a progress session stamps session_count == active_days (server-side)
- submitting a baseline session keeps session_count == 0
- unauth → 401
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.diagnostic import DiagnosticItem
from app.models.mastery import DiagnosticSession, MasteryCheckpoint
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")

_DEFAULT_MARKET = "GB"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, db_session, *, suffix: str = "") -> User:
    """Register a new child user, log them in, return the ORM User row."""
    email = f"rchk{suffix}@example.com"
    username = f"rchkkid{suffix}"
    payload = {
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"rchk_parent{suffix}@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return await db_session.scalar(select(User).where(User.username == username))


def _set_active_days(db_session, user: User, days: int) -> None:
    """Directly set active_days on the user's UserProgress row (or create it)."""
    # We flush lazily — caller must await db_session.flush() after
    # UserProgress may not exist yet; we need to handle both cases in the test
    pass  # implemented inline per test where we need flush control


async def _get_or_create_progress(db_session, user: User, active_days: int) -> UserProgress:
    progress = await db_session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id, active_days=active_days)
        db_session.add(progress)
    else:
        progress.active_days = active_days
    await db_session.flush()
    return progress


async def _add_progress_checkpoint(db_session, user: User) -> MasteryCheckpoint:
    """Insert a kind='progress' MasteryCheckpoint for the user."""
    cp = MasteryCheckpoint(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="progress",
        session_count=0,
        overall_score=0.75,
    )
    db_session.add(cp)
    await db_session.flush()
    return cp


async def _seed_item(db_session) -> DiagnosticItem:
    item = DiagnosticItem(
        market_code=_DEFAULT_MARKET,
        topic="budgeting",
        difficulty_tier=1,
        question="What is budgeting?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="Because reasons.",
        status="approved",
        source="authored",
    )
    db_session.add(item)
    await db_session.flush()
    return item


async def _recheck_status(client) -> dict:
    resp = await client.get("/diagnostic/recheck-status")
    return resp


# ---------------------------------------------------------------------------
# active_days below first milestone → due:false
# ---------------------------------------------------------------------------


async def test_recheck_below_first_milestone(client, db_session):
    """active_days=3 (<5), 0 progress checkpoints → due:false."""
    user = await _register_and_login(client, db_session, suffix="_r1")
    await _get_or_create_progress(db_session, user, active_days=3)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is False
    assert data["completed_checks"] == 0
    assert data["active_days"] == 3
    assert data["milestone"] == 5  # next milestone is still 5


# ---------------------------------------------------------------------------
# active_days >= 5, 0 progress checkpoints → due:true, milestone:5
# ---------------------------------------------------------------------------


async def test_recheck_due_at_first_milestone(client, db_session):
    """active_days=5, 0 progress checkpoints → due:true, milestone:5."""
    user = await _register_and_login(client, db_session, suffix="_r2")
    await _get_or_create_progress(db_session, user, active_days=5)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is True
    assert data["milestone"] == 5
    assert data["active_days"] == 5
    assert data["completed_checks"] == 0


async def test_recheck_due_above_first_milestone(client, db_session):
    """active_days=12 (>5), 0 progress checkpoints → due:true, milestone:5."""
    user = await _register_and_login(client, db_session, suffix="_r2b")
    await _get_or_create_progress(db_session, user, active_days=12)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is True
    assert data["milestone"] == 5


# ---------------------------------------------------------------------------
# 1 progress checkpoint + active_days < 15 → due:false
# ---------------------------------------------------------------------------


async def test_recheck_one_done_below_second_milestone(client, db_session):
    """1 progress checkpoint + active_days=10 (<15) → due:false, milestone:15."""
    user = await _register_and_login(client, db_session, suffix="_r3")
    await _get_or_create_progress(db_session, user, active_days=10)
    await _add_progress_checkpoint(db_session, user)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is False
    assert data["completed_checks"] == 1
    assert data["active_days"] == 10
    assert data["milestone"] == 15


# ---------------------------------------------------------------------------
# 1 progress checkpoint + active_days >= 15 → due:true, milestone:15
# ---------------------------------------------------------------------------


async def test_recheck_one_done_at_second_milestone(client, db_session):
    """1 progress checkpoint + active_days=15 → due:true, milestone:15."""
    user = await _register_and_login(client, db_session, suffix="_r4")
    await _get_or_create_progress(db_session, user, active_days=15)
    await _add_progress_checkpoint(db_session, user)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is True
    assert data["milestone"] == 15
    assert data["completed_checks"] == 1


# ---------------------------------------------------------------------------
# 3 progress checkpoints (all milestones done) → due:false, milestone:null
# ---------------------------------------------------------------------------


async def test_recheck_all_milestones_exhausted(client, db_session):
    """3 progress checkpoints → due:false, milestone:null even with huge active_days."""
    user = await _register_and_login(client, db_session, suffix="_r5")
    await _get_or_create_progress(db_session, user, active_days=999)
    await _add_progress_checkpoint(db_session, user)
    await _add_progress_checkpoint(db_session, user)
    await _add_progress_checkpoint(db_session, user)

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["due"] is False
    assert data["completed_checks"] == 3
    assert data["milestone"] is None


# ---------------------------------------------------------------------------
# submitting a progress session stamps session_count == active_days
# ---------------------------------------------------------------------------


async def test_progress_submit_stamps_session_count(client, db_session):
    """Progress session submit → checkpoint.session_count == user's active_days (server-side)."""
    user = await _register_and_login(client, db_session, suffix="_r6")
    await _get_or_create_progress(db_session, user, active_days=7)

    item = await _seed_item(db_session)

    # Start a progress session directly in the DB (bypassing start endpoint for simplicity)
    diag = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="progress",
        item_ids=[str(item.id)],
    )
    db_session.add(diag)
    await db_session.flush()

    # Submit (server should read active_days=7, ignore any client value)
    resp = await client.post(
        "/diagnostic/submit",
        json={"session_id": str(diag.id), "answers": {str(item.id): 0}},
    )
    assert resp.status_code == 200, resp.text

    checkpoint = await db_session.scalar(
        select(MasteryCheckpoint).where(
            MasteryCheckpoint.user_id == user.id,
            MasteryCheckpoint.kind == "progress",
        )
    )
    assert checkpoint is not None
    assert checkpoint.session_count == 7  # must equal active_days, not client value


# ---------------------------------------------------------------------------
# submitting a baseline session keeps session_count == 0
# ---------------------------------------------------------------------------


async def test_baseline_submit_keeps_session_count_zero(client, db_session):
    """Baseline session submit → checkpoint.session_count == 0 regardless of active_days."""
    user = await _register_and_login(client, db_session, suffix="_r7")
    await _get_or_create_progress(db_session, user, active_days=20)

    item = await _seed_item(db_session)

    diag = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[str(item.id)],
    )
    db_session.add(diag)
    await db_session.flush()

    resp = await client.post(
        "/diagnostic/submit",
        json={"session_id": str(diag.id), "answers": {str(item.id): 0}},
    )
    assert resp.status_code == 200, resp.text

    checkpoint = await db_session.scalar(
        select(MasteryCheckpoint).where(
            MasteryCheckpoint.user_id == user.id,
            MasteryCheckpoint.kind == "baseline",
        )
    )
    assert checkpoint is not None
    assert checkpoint.session_count == 0


# ---------------------------------------------------------------------------
# no progress row → active_days defaults to 0
# ---------------------------------------------------------------------------


async def test_recheck_no_progress_row_defaults_zero(client, db_session):
    """User with no UserProgress row → active_days=0, due:false."""
    user = await _register_and_login(client, db_session, suffix="_r8")
    # Don't create a UserProgress row — registration may or may not create one.
    # If it does, set active_days to 0.
    progress = await db_session.get(UserProgress, user.id)
    if progress is not None:
        progress.active_days = 0
        await db_session.flush()

    resp = await _recheck_status(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["active_days"] == 0
    assert data["due"] is False


# ---------------------------------------------------------------------------
# Unauth → 401
# ---------------------------------------------------------------------------


async def test_recheck_status_unauth(client, db_session):
    """Unauthenticated request → 401."""
    # Log out by clearing cookies
    client.cookies.clear()
    if "X-CSRF-Token" in client.headers:
        del client.headers["X-CSRF-Token"]

    resp = await client.get("/diagnostic/recheck-status")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
