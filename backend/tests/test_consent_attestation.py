import uuid
from datetime import timedelta

import pytest

from app.services.tokens import CONSENT_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_minor(client, email, username):
    payload = {
        "email": email, "username": username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }
    r = await client.post("/auth/register", json=payload)
    return r.json()["user_id"]


async def _make_pending_child_and_token(
    client, db_session, *, email="attest@example.com", username="attestkid",
    return_id=False,
):
    user_id = await _register_minor(client, email=email, username=username)
    token = await issue_one_time_token(
        db_session, purpose=CONSENT_AUDIENCE, email="parent@example.com",
        subject_id=uuid.UUID(user_id), expires_in=timedelta(hours=1),
    )
    await db_session.commit()
    if return_id:
        return token, uuid.UUID(user_id)
    return token


async def test_approve_without_attestation_rejected(client, db_session):
    token = await _make_pending_child_and_token(
        client, db_session, email="a1@example.com", username="a1",
    )
    resp = await client.post(
        f"/consent/decide?token={token}", json={"decision": "approve"}
    )
    assert resp.status_code == 400
    assert "attestation" in resp.json()["detail"].lower()
    # token NOT consumed -> a correct retry still works
    resp2 = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "approve", "attest_guardian": True},
    )
    assert resp2.status_code == 200


async def test_approve_with_attestation_sets_timestamps(client, db_session):
    token, user_id = await _make_pending_child_and_token(
        client, db_session, email="a2@example.com", username="a2", return_id=True,
    )
    resp = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "approve", "attest_guardian": True},
    )
    assert resp.status_code == 200
    from app.models.user import User
    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.parent_consent_given_at is not None
    assert user.guardian_attested_at is not None
    assert user.is_active is True


async def test_decline_does_not_require_attestation(client, db_session):
    token, user_id = await _make_pending_child_and_token(
        client, db_session, email="a3@example.com", username="a3", return_id=True,
    )
    resp = await client.post(
        f"/consent/decide?token={token}", json={"decision": "decline"}
    )
    assert resp.status_code == 200
    from app.models.user import User
    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.consent_declined_at is not None
    assert user.guardian_attested_at is None
    assert user.is_active is False
