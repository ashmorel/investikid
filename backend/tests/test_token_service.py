import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.consent import OneTimeToken
from app.services.tokens import (
    CONSENT_AUDIENCE, PARENT_MAGIC_AUDIENCE,
    TokenAlreadyUsed, TokenExpired, TokenInvalid,
    consume_one_time_token, decode_parent_session,
    issue_one_time_token, issue_parent_session,
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
