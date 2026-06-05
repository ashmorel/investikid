import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_parent_session_row_roundtrips(db_session):
    from app.models.parent_session import ParentSession

    jti = uuid.uuid4()
    db_session.add(ParentSession(
        jti=jti,
        parent_email="dad@example.com",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    ))
    await db_session.flush()

    row = await db_session.scalar(select(ParentSession).where(ParentSession.jti == jti))
    assert row is not None
    assert row.parent_email == "dad@example.com"
    assert row.revoked_at is None
    assert row.id is not None
    assert row.created_at is not None


async def test_parent_session_jti_unique(db_session):
    import uuid as _uuid

    import sqlalchemy.exc

    from app.models.parent_session import ParentSession

    jti = _uuid.uuid4()
    db_session.add(ParentSession(
        jti=jti, parent_email="a@example.com",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    ))
    await db_session.flush()
    db_session.add(ParentSession(
        jti=jti, parent_email="b@example.com",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    ))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await db_session.flush()


async def test_issue_parent_session_persists_row_and_jti(db_session):
    import uuid as _uuid

    from app.models.parent_session import ParentSession
    from app.services.tokens import decode_parent_session, issue_parent_session

    token = await issue_parent_session(db_session, "mum@example.com")
    await db_session.flush()

    email, jti = decode_parent_session(token)
    assert email == "mum@example.com"
    assert isinstance(jti, _uuid.UUID)

    row = await db_session.scalar(
        select(ParentSession).where(ParentSession.jti == jti)
    )
    assert row is not None
    assert row.parent_email == "mum@example.com"
    assert row.revoked_at is None


async def test_revoke_parent_session_sets_revoked_at(db_session):
    from app.models.parent_session import ParentSession
    from app.services.tokens import (
        decode_parent_session,
        issue_parent_session,
        revoke_parent_session,
    )

    token = await issue_parent_session(db_session, "mum@example.com")
    await db_session.flush()
    _email, jti = decode_parent_session(token)

    await revoke_parent_session(db_session, jti)
    await db_session.flush()

    row = await db_session.scalar(
        select(ParentSession).where(ParentSession.jti == jti)
    )
    assert row.revoked_at is not None


def test_decode_parent_session_rejects_missing_or_bad_jti():
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings
    from app.services.tokens import (
        PARENT_SESSION_AUDIENCE,
        TokenInvalid,
        decode_parent_session,
    )

    now = datetime.now(UTC)
    base = {
        "sub": "x@example.com",
        "aud": PARENT_SESSION_AUDIENCE,
        "exp": now + timedelta(days=7),
        "iat": now,
    }
    no_jti = jwt.encode(base, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    bad_jti = jwt.encode({**base, "jti": "not-a-uuid"}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    import pytest
    with pytest.raises(TokenInvalid):
        decode_parent_session(no_jti)
    with pytest.raises(TokenInvalid):
        decode_parent_session(bad_jti)


async def _sign_in_parent(client, db_session, parent_email="dad@example.com"):
    """Register a kid (so the parent email is known) and sign the parent in via magic link.
    Returns the csrf token for CSRF-protected POSTs."""
    from datetime import timedelta

    from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "kid_rev@example.com", "username": "kid_rev", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    return client.cookies.get("csrf_token")


async def test_logout_revokes_session_server_side(client, db_session):
    csrf = await _sign_in_parent(client, db_session)
    # Authenticated route works before logout
    r = await client.get("/parent/children")
    assert r.status_code == 200

    # Capture the cookie, log out, then replay the SAME cookie
    cookie = client.cookies.get("parent_session")
    r = await client.post("/parent/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200

    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={cookie}"})
    assert r.status_code == 401, "a logged-out (revoked) parent cookie must not authenticate"


async def test_logout_emits_cookie_clear(client, db_session):
    csrf = await _sign_in_parent(client, db_session)
    r = await client.post("/parent/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert "parent_session=" in set_cookie
    assert "path=/" in set_cookie.lower()
    # A real clear sets an immediate expiry / Max-Age=0
    assert ("max-age=0" in set_cookie.lower()) or ("expires=" in set_cookie.lower())


async def test_revoked_row_rejected(client, db_session):
    from app.models.parent_session import ParentSession  # noqa: F401
    from app.services.tokens import decode_parent_session, revoke_parent_session

    await _sign_in_parent(client, db_session)
    cookie = client.cookies.get("parent_session")
    _email, jti = decode_parent_session(cookie)
    await revoke_parent_session(db_session, jti)
    await db_session.commit()

    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={cookie}"})
    assert r.status_code == 401


async def test_unknown_jti_rejected(client, db_session):
    # A validly-signed parent JWT whose jti has no row must be rejected.
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings
    from app.services.tokens import PARENT_SESSION_AUDIENCE

    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": "ghost@example.com",
            "aud": PARENT_SESSION_AUDIENCE,
            "jti": str(_uuid.uuid4()),
            "exp": now + timedelta(days=7),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={forged}"})
    assert r.status_code == 401


async def test_expired_row_rejected(client, db_session):
    # JWT exp is valid but the DB row is expired -> defence-in-depth 401.
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings
    from app.models.parent_session import ParentSession
    from app.services.tokens import PARENT_SESSION_AUDIENCE

    jti = _uuid.uuid4()
    db_session.add(ParentSession(
        jti=jti,
        parent_email="stale@example.com",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    ))
    await db_session.commit()

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "stale@example.com",
            "aud": PARENT_SESSION_AUDIENCE,
            "jti": str(jti),
            "exp": now + timedelta(days=7),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = await client.get("/parent/children", headers={"Cookie": f"parent_session={token}"})
    assert r.status_code == 401
