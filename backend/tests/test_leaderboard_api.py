"""API-layer tests for leaderboard, handle and visibility endpoints (Task 4).

Extra tests from Task 3 review:
  - test_friends_scope_shows_usernames
  - test_own_row_fallback_when_not_consented
"""
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers (local to this module to avoid cross-module import coupling)
# ---------------------------------------------------------------------------

_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2012-06-01",
    "country_code": "GB",
    "currency_code": "GBP",
}


async def _reg(client, email, username, *, country_code="GB"):
    """Register + login a child user; returns CSRF token."""
    await client.post("/auth/register", json={
        **_USER_BASE, "email": email, "username": username, "country_code": country_code,
    })
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return csrf


async def _mk_user_direct(db_session, email, username, *, market="GB", country="GB",
                          consent=True, hidden=False, handle=None,
                          parent_email=None):
    """Create a User directly in DB (no HTTP round-trip) — for scope/consent tests."""
    from app.models.user import User
    u = User(
        email=email,
        username=username,
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code=country,
        currency_code="GBP",
        active_market_code=market,
        leaderboard_consent=consent,
        leaderboard_hidden=hidden,
        display_handle=handle or f"Handle{username}",
        parent_email=parent_email,
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _add_xp(db_session, user, amount):
    from app.models.content import Lesson, LessonCompletion, Module
    mod = (await db_session.scalars(select(Module).limit(1))).first()
    if mod is None:
        mod = Module(topic="savings", title="Savings", country_codes=[], is_premium=False, order_index=0)
        db_session.add(mod)
        await db_session.flush()
    lesson = Lesson(module_id=mod.id, type="card", xp_reward=amount,
                    order_index=0, content_json={"title": "t", "body": "b"})
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(
        user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC),
    ))
    await db_session.commit()


# ---------------------------------------------------------------------------
# Brief-specified tests
# ---------------------------------------------------------------------------

async def test_leaderboard_requires_auth(client):
    assert (await client.get("/leaderboard")).status_code == 401


async def test_leaderboard_defaults_market_xp(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbapi@example.com", username="lbapi")
    r = await client.get("/leaderboard")               # no params
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_leaderboard_rejects_bad_scope(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbapi2@example.com", username="lbapi2")
    assert (await client.get("/leaderboard?scope=planet")).status_code == 422


async def test_me_handle_generates_and_reroll_changes_it(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbh@example.com", username="lbh")
    r = await client.get("/me/handle")
    h1 = r.json()["handle"]
    assert h1
    # Task 7: GET /me/handle must include hidden field
    assert "hidden" in r.json(), f"Expected 'hidden' in response, got: {r.json()}"
    assert r.json()["hidden"] is False  # default
    h2 = (await client.post("/me/handle/reroll")).json()["handle"]
    assert h2 and h2 != h1


async def test_visibility_toggle(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbvis@example.com", username="lbvis")
    r = await client.patch("/me/leaderboard-visibility", json={"hidden": True})
    assert r.status_code == 200 and r.json()["hidden"] is True


# ---------------------------------------------------------------------------
# Parent consent endpoint
# ---------------------------------------------------------------------------

async def test_parent_consent_endpoint(client, db_session):
    from datetime import timedelta

    from app.models.user import User
    from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

    parent_email = "lbp@example.com"
    child_email = "lbpc@example.com"
    child_username = "lbpc"

    await client.post("/auth/register", json={
        **_USER_BASE,
        "email": child_email,
        "username": child_username,
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE,
        email=parent_email, subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    csrf = client.cookies.get("csrf_token")

    child = await db_session.scalar(select(User).where(User.username == child_username))
    assert child is not None

    r = await client.post(
        f"/parent/children/{child.id}/leaderboard-consent",
        json={"consent": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["leaderboard_consent"] is True

    # Flip back off
    r2 = await client.post(
        f"/parent/children/{child.id}/leaderboard-consent",
        json={"consent": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert r2.status_code == 200
    assert r2.json()["leaderboard_consent"] is False


# ---------------------------------------------------------------------------
# Extra tests from Task 3 review
# ---------------------------------------------------------------------------

async def test_own_row_fallback_when_not_consented(client, db_session):
    """Non-consented viewer still gets exactly one row (their own) with is_me=True.
    Other non-consented users must be absent from the board."""
    from app.models.user import User

    # Register and login the caller (they'll be non-consented via DB direct update)
    viewer_email = "lbnc_viewer@example.com"
    viewer_username = "lbnc_viewer"
    await _reg(client, viewer_email, viewer_username)
    viewer = await db_session.scalar(select(User).where(User.email == viewer_email))
    viewer.leaderboard_consent = False
    viewer.display_handle = "NonConsentedViewer42"
    viewer.active_market_code = "GB"
    await db_session.commit()

    # Create another non-consented user in the same market who should NOT appear
    other = await _mk_user_direct(
        db_session, "lbnc_other@example.com", "lbnc_other",
        market="GB", consent=False, handle="OtherNonConsented99",
    )
    await _add_xp(db_session, other, 100)

    r = await client.get("/leaderboard?scope=global&metric=xp")
    assert r.status_code == 200
    rows = r.json()

    # Viewer's own row must be present
    my_rows = [row for row in rows if row["is_me"]]
    assert len(my_rows) == 1, f"Expected exactly 1 is_me row, got {my_rows}"

    # The other non-consented user must not appear
    names = {row["name"] for row in rows}
    assert other.display_handle not in names, f"Non-consented other appeared in board: {names}"


async def test_friends_scope_shows_usernames(client, db_session):
    """Friends scope returns member usernames (not handles) and marks is_me correctly.

    Setup: one parent creates a group, adds two children. One of them calls the endpoint.
    We verify both children appear (by username) and is_me is set for the caller.
    """
    from datetime import timedelta

    from app.models.user import User
    from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

    parent_email = "lbfp@example.com"
    child_a_email = "lbfa@example.com"
    child_b_email = "lbfb@example.com"

    # Register child A (will be our logged-in viewer)
    await _reg(client, child_a_email, "lbfa")
    child_a = await db_session.scalar(select(User).where(User.email == child_a_email))
    child_a.parent_email = parent_email
    await db_session.flush()

    # Create child B directly (no need to log them in via HTTP)
    child_b = await _mk_user_direct(
        db_session, child_b_email, "lbfb",
        parent_email=parent_email,
    )
    await db_session.commit()

    # Parent sign-in and create group, add both children
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE,
        email=parent_email, subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    parent_csrf = client.cookies.get("csrf_token")

    g_resp = await client.post("/parent/groups", json={"name": "FriendGroup"},
                               headers={"X-CSRF-Token": parent_csrf})
    assert g_resp.status_code == 201, g_resp.text
    code = g_resp.json()["code"]

    for child in (child_a, child_b):
        j = await client.post(
            "/parent/groups/join",
            json={"code": code, "child_user_id": str(child.id)},
            headers={"X-CSRF-Token": parent_csrf},
        )
        assert j.status_code == 200, j.text

    # Now log in as child_a and call /leaderboard?scope=friends
    await _reg(client, child_a_email, "lbfa")  # re-login child_a (replaces parent session)
    r = await client.get("/leaderboard?scope=friends&metric=xp")
    assert r.status_code == 200
    rows = r.json()

    names = {row["name"] for row in rows}
    assert "lbfa" in names, f"child_a username not in friends board: {names}"
    assert "lbfb" in names, f"child_b username not in friends board: {names}"

    my_rows = [row for row in rows if row["is_me"]]
    assert len(my_rows) == 1
    assert my_rows[0]["name"] == "lbfa"
