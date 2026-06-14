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
