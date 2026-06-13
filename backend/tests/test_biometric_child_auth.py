"""Child biometric enroll / exchange / unenroll (SP-Bio Task 2)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _login_allowed(client, db_session, *, allowed=True) -> User:
    suffix = uuid.uuid4().hex[:8]
    email = f"bio{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"bio{suffix}")
    user = await db_session.scalar(select(User).where(User.email == email))
    user.biometric_allowed = allowed
    await db_session.commit()
    return user


async def test_enroll_requires_consent(client, db_session):
    await _login_allowed(client, db_session, allowed=False)
    r = await client.post("/auth/biometric/enroll", json={"device_id": "device-aaaa", "label": "kid"}, headers=_csrf(client))
    assert r.status_code == 403


async def test_enroll_then_exchange_roundtrip(client, db_session):
    await _login_allowed(client, db_session, allowed=True)
    r = await client.post("/auth/biometric/enroll", json={"device_id": "device-bbbb", "label": "kid"}, headers=_csrf(client))
    assert r.status_code == 200
    secret = r.json()["secret"]

    client.cookies.clear()  # simulate a returning device with no live session
    r2 = await client.post("/auth/biometric/exchange", json={"device_id": "device-bbbb", "secret": secret})
    assert r2.status_code == 200
    rotated = r2.json()["secret"]
    assert rotated and rotated != secret
    assert (await client.get("/users/me")).status_code == 200

    # old secret no longer works
    client.cookies.clear()
    assert (await client.post("/auth/biometric/exchange", json={"device_id": "device-bbbb", "secret": secret})).status_code == 401
    # rotated secret does
    assert (await client.post("/auth/biometric/exchange", json={"device_id": "device-bbbb", "secret": rotated})).status_code == 200

    # each successful exchange writes an audit row for forensic parity with login
    logins = await db_session.scalars(
        select(AuditLog).where(AuditLog.event_type == "biometric_login")
    )
    assert len(logins.all()) >= 1


async def test_exchange_rejects_implausibly_short_secret(client, db_session):
    await _login_allowed(client, db_session, allowed=True)
    r = await client.post("/auth/biometric/exchange", json={"device_id": "device-shrt", "secret": "tooshort"})
    assert r.status_code == 422  # rejected by schema before any hash comparison


async def test_exchange_rejected_when_frozen(client, db_session):
    user = await _login_allowed(client, db_session, allowed=True)
    r = await client.post("/auth/biometric/enroll", json={"device_id": "device-cccc", "label": "kid"}, headers=_csrf(client))
    secret = r.json()["secret"]
    user.is_active = False
    await db_session.commit()
    client.cookies.clear()
    assert (await client.post("/auth/biometric/exchange", json={"device_id": "device-cccc", "secret": secret})).status_code == 401


async def test_unenroll_revokes(client, db_session):
    await _login_allowed(client, db_session, allowed=True)
    r = await client.post("/auth/biometric/enroll", json={"device_id": "device-dddd", "label": "kid"}, headers=_csrf(client))
    secret = r.json()["secret"]
    d = await client.delete("/auth/biometric/devices/device-dddd", headers=_csrf(client))
    assert d.status_code == 200
    client.cookies.clear()
    assert (await client.post("/auth/biometric/exchange", json={"device_id": "device-dddd", "secret": secret})).status_code == 401


async def test_me_exposes_biometric_allowed(client, db_session):
    await _login_allowed(client, db_session, allowed=True)
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["biometric_allowed"] is True
