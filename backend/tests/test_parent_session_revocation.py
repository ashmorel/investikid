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
