"""A07-1: one-time / cross-audience tokens must not be accepted as a session
access token on authenticated endpoints."""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.models.user import User
from app.services.tokens import (
    PASSWORD_RESET_AUDIENCE,
    PASSWORD_RESET_EXPIRY,
    issue_one_time_token,
    issue_parent_session,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user(db_session) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"victim-{suffix}@example.com",
        username=f"victim{suffix}",
        password_hash="x",
        dob=date(2006, 5, 10),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_password_reset_token_rejected_as_access_cookie(client, db_session):
    user = await _make_user(db_session)
    reset_token = await issue_one_time_token(
        db_session,
        purpose=PASSWORD_RESET_AUDIENCE,
        email=user.email,
        subject_id=user.id,
        expires_in=PASSWORD_RESET_EXPIRY,
    )
    client.cookies.set("access_token", reset_token)
    resp = await client.get("/users/me")
    assert resp.status_code == 401, (
        "password-reset one-time token must NOT authenticate a session"
    )


async def test_parent_session_token_rejected_as_access_cookie(client, db_session):
    await _make_user(db_session)
    parent_token = await issue_parent_session(db_session, "victim_parent@example.com")
    client.cookies.set("access_token", parent_token)
    resp = await client.get("/users/me")
    assert resp.status_code == 401, (
        "parent_session token must NOT authenticate a child session"
    )


async def test_typeless_audless_jwt_rejected_as_access_cookie(client, db_session):
    """A JWT signed with the app secret carrying only `sub` (no token `type`,
    no `aud`) must NOT be accepted as a session. `decode_token` must positively
    assert this is an access token rather than accepting any non-refresh JWT."""
    user = await _make_user(db_session)
    forged = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    client.cookies.set("access_token", forged)
    resp = await client.get("/users/me")
    assert resp.status_code == 401, (
        "a typeless/audless claims-only JWT must NOT authenticate a session"
    )
