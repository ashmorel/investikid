import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_parent_user(client, db_session, *, verified=True):
    """Register a normal user, optionally mark email verified, and link a child
    whose parent_email is this user's email. Returns the user's email."""
    suffix = uuid.uuid4().hex[:8]
    email = f"par{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"par{suffix}")
    user = await db_session.scalar(select(User).where(User.email == email))
    user.email_verified_at = datetime.now(UTC) if verified else None
    # a child that lists this user as its parent
    child = User(
        username=f"kid{suffix}", email=None, password_hash="x",
        dob=date(2010, 1, 1),
        country_code="GB", currency_code="GBP", parent_email=email, is_active=True,
    )
    db_session.add(child)
    await db_session.commit()
    return email


async def test_me_is_parent_true_for_verified_parent(client, db_session):
    await _make_parent_user(client, db_session, verified=True)
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["is_parent"] is True


async def test_me_is_parent_false_when_email_unverified(client, db_session):
    await _make_parent_user(client, db_session, verified=False)
    r = await client.get("/users/me")
    assert r.json()["is_parent"] is False


async def test_me_is_parent_false_for_non_parent(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"np{suffix}@example.com", username=f"np{suffix}")
    r = await client.get("/users/me")
    assert r.json()["is_parent"] is False


# ---------------------------------------------------------------------------
# Task 2: POST /parent/auth/from-session
# ---------------------------------------------------------------------------
from tests.test_billing import _csrf_headers  # noqa: E402


async def test_from_session_mints_parent_session(client, db_session):
    await _make_parent_user(client, db_session, verified=True)
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 200
    # the minted parent_session now authorizes the dashboard
    assert (await client.get("/parent/children")).status_code == 200


async def test_from_session_403_when_unverified(client, db_session):
    await _make_parent_user(client, db_session, verified=False)
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 403


async def test_from_session_403_for_non_parent(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"np{suffix}@example.com", username=f"np{suffix}")
    # mark verified so we isolate the "no child" branch
    u = await db_session.scalar(select(User).where(User.email == f"np{suffix}@example.com"))
    u.email_verified_at = datetime.now(UTC)
    await db_session.commit()
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Task 3: consent approve mints a parent session (Door 2)
# ---------------------------------------------------------------------------
from app.services.tokens import CONSENT_AUDIENCE, CONSENT_EXPIRY, issue_one_time_token  # noqa: E402


async def test_consent_approve_sets_parent_session_cookie(client, db_session):
    # create an inactive child needing consent, with our email as parent
    suffix = uuid.uuid4().hex[:8]
    pemail = f"cap{suffix}@example.com"
    child = User(
        username=f"ckid{suffix}", email=None, password_hash="x",
        dob=date(2010, 1, 1),
        country_code="GB", currency_code="GBP", parent_email=pemail, is_active=False,
    )
    db_session.add(child)
    await db_session.commit()
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email=pemail,
        subject_id=child.id, expires_in=CONSENT_EXPIRY,
    )
    await db_session.commit()

    client.cookies.clear()
    r = await client.post(f"/consent/decide?token={token}", json={"decision": "approve", "attest_guardian": True})
    assert r.status_code == 200
    assert "parent_session" in r.cookies
    # the cookie authorizes the dashboard for this parent_email
    assert (await client.get("/parent/children")).status_code == 200
