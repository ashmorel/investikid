import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.tokens import CONSENT_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_minor(client, email="kid@example.com", username="kid"):
    payload = {
        "email": email, "username": username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }
    r = await client.post("/auth/register", json=payload)
    return r.json()["user_id"]


async def test_verify_returns_child_summary(client, db_session):
    user_id = await _register_minor(client)
    new_token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="parent@example.com",
        subject_id=uuid.UUID(user_id), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    r = await client.get(f"/consent/verify?token={new_token}")
    assert r.status_code == 200
    assert r.json()["username"] == "kid"


async def test_decide_approve_activates_user(client, db_session):
    user_id = await _register_minor(client, email="k2@example.com", username="k2")
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="parent@example.com",
        subject_id=uuid.UUID(user_id), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    r = await client.post(f"/consent/decide?token={token}", json={"decision": "approve"})
    assert r.status_code == 200

    user = await db_session.get(User, uuid.UUID(user_id))
    await db_session.refresh(user)
    assert user.is_active is True
    assert user.parent_consent_given_at is not None


async def test_decide_decline_keeps_inactive(client, db_session):
    user_id = await _register_minor(client, email="k3@example.com", username="k3")
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="parent@example.com",
        subject_id=uuid.UUID(user_id), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    r = await client.post(f"/consent/decide?token={token}", json={"decision": "decline"})
    assert r.status_code == 200
    user = await db_session.get(User, uuid.UUID(user_id))
    await db_session.refresh(user)
    assert user.is_active is False
    assert user.consent_declined_at is not None


async def test_decide_replay_returns_410(client, db_session):
    user_id = await _register_minor(client, email="k4@example.com", username="k4")
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="parent@example.com",
        subject_id=uuid.UUID(user_id), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    await client.post(f"/consent/decide?token={token}", json={"decision": "approve"})
    r = await client.post(f"/consent/decide?token={token}", json={"decision": "approve"})
    assert r.status_code == 410


async def test_decide_garbage_token_returns_410(client):
    r = await client.post("/consent/decide?token=not-a-jwt", json={"decision": "approve"})
    assert r.status_code == 410


async def test_request_consent_email_for_unknown_user_returns_202(client):
    fake = str(uuid.uuid4())
    r = await client.post(f"/consent/request/{fake}")
    assert r.status_code == 202
