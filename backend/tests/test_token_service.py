import uuid
from datetime import timedelta

import pytest

from app.services.tokens import (
    CONSENT_AUDIENCE,
    PARENT_MAGIC_AUDIENCE,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    consume_one_time_token,
    decode_parent_session,
    issue_one_time_token,
    issue_parent_session,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_issue_and_consume_once(db_session):
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="p@example.com",
        subject_id=uuid.uuid4(), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    row = await consume_one_time_token(db_session, token, CONSENT_AUDIENCE)
    await db_session.commit()
    assert row.consumed_at is not None


async def test_replay_rejected(db_session):
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="p@example.com",
        subject_id=uuid.uuid4(), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    await consume_one_time_token(db_session, token, CONSENT_AUDIENCE)
    await db_session.commit()
    with pytest.raises(TokenAlreadyUsed):
        await consume_one_time_token(db_session, token, CONSENT_AUDIENCE)


async def test_wrong_audience_rejected(db_session):
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="p@example.com",
        subject_id=uuid.uuid4(), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    with pytest.raises(TokenInvalid):
        await consume_one_time_token(db_session, token, PARENT_MAGIC_AUDIENCE)


async def test_expired_rejected(db_session):
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="p@example.com",
        subject_id=uuid.uuid4(), expires_in=timedelta(seconds=-1),
    )
    await db_session.commit()
    with pytest.raises((TokenInvalid, TokenExpired)):
        await consume_one_time_token(db_session, token, CONSENT_AUDIENCE)


async def test_garbage_token_rejected(db_session):
    with pytest.raises(TokenInvalid):
        await consume_one_time_token(db_session, "not-a-jwt", CONSENT_AUDIENCE)


def test_parent_session_roundtrip():
    token = issue_parent_session("p@example.com")
    assert decode_parent_session(token) == "p@example.com"


def test_parent_session_invalid_rejected():
    with pytest.raises(TokenInvalid):
        decode_parent_session("garbage")


async def test_verify_email_and_reset_token_roundtrip(db_session):
    import uuid

    from app.services.tokens import (
        PASSWORD_RESET_AUDIENCE,
        PASSWORD_RESET_EXPIRY,
        VERIFY_EMAIL_AUDIENCE,
        VERIFY_EMAIL_EXPIRY,
        consume_one_time_token,
        issue_one_time_token,
    )
    uid = uuid.uuid4()
    vt = await issue_one_time_token(
        db_session, purpose=VERIFY_EMAIL_AUDIENCE, email="t@example.com",
        subject_id=uid, expires_in=VERIFY_EMAIL_EXPIRY,
    )
    row = await consume_one_time_token(db_session, vt, VERIFY_EMAIL_AUDIENCE)
    assert row.subject_id == uid

    rt = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email="t@example.com",
        subject_id=uid, expires_in=PASSWORD_RESET_EXPIRY,
    )
    row2 = await consume_one_time_token(db_session, rt, PASSWORD_RESET_AUDIENCE)
    assert row2.subject_id == uid
