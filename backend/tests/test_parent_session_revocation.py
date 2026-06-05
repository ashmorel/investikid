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
