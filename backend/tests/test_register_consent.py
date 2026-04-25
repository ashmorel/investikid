import pytest
from sqlalchemy import select

from app.models.consent import OneTimeToken, SentEmail
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
_BASE = {
    "password": "SecurePass123!",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def test_under_threshold_creates_inactive_user(client, db_session):
    payload = {**_BASE, "email": "kid@example.com", "username": "kid", "dob": "2015-01-01"}
    r = await client.post(REGISTER_URL, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending_consent"
    user = await db_session.scalar(select(User).where(User.email == "kid@example.com"))
    assert user is not None
    assert user.is_active is False
    assert user.parent_consent_given_at is None


async def test_under_threshold_sends_email_and_token(client, db_session):
    payload = {**_BASE, "email": "kid2@example.com", "username": "kid2", "dob": "2015-01-01"}
    await client.post(REGISTER_URL, json=payload)
    sent = (await db_session.scalars(select(SentEmail))).all()
    assert any(s.to_email == "parent@example.com" and s.template == "consent_request" for s in sent)
    tokens = (await db_session.scalars(select(OneTimeToken).where(OneTimeToken.purpose == "consent"))).all()
    assert len(tokens) >= 1


async def test_over_threshold_uk_no_consent(client, db_session):
    payload = {**_BASE, "email": "teen@example.com", "username": "teen", "dob": "2008-01-01"}
    r = await client.post(REGISTER_URL, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body.get("status") != "pending_consent"
    assert body["email"] == "teen@example.com"


async def test_eu_threshold_15_blocks(client, db_session):
    payload = {**_BASE, "email": "ie@example.com", "username": "ieteen",
               "country_code": "IE", "currency_code": "EUR", "dob": "2011-01-01"}
    r = await client.post(REGISTER_URL, json=payload)
    assert r.status_code == 201
    assert r.json()["status"] == "pending_consent"


async def test_under_threshold_without_parent_email_rejected(client):
    payload = {"password": "SecurePass123!", "country_code": "GB", "currency_code": "GBP",
               "email": "noparent@example.com", "username": "noparent", "dob": "2015-01-01"}
    r = await client.post(REGISTER_URL, json=payload)
    assert r.status_code in (400, 422)
