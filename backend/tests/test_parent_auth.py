from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.consent import OneTimeToken, SentEmail
from app.services.tokens import (
    PARENT_MAGIC_AUDIENCE, issue_one_time_token,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_kid_with_parent(client, parent_email="dad@example.com"):
    await client.post("/auth/register", json={
        "email": "kid6@example.com", "username": "kid6", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })


async def test_magic_request_unknown_email_returns_202(client):
    r = await client.post("/parent/auth/request", json={"email": "noone@example.com"})
    assert r.status_code == 202


async def test_magic_request_known_email_sends(client, db_session):
    await _register_kid_with_parent(client)
    r = await client.post("/parent/auth/request", json={"email": "dad@example.com"})
    assert r.status_code == 202
    sent = (await db_session.scalars(select(SentEmail).where(SentEmail.template == "parent_magic_link"))).all()
    assert any(s.to_email == "dad@example.com" for s in sent)


async def test_magic_callback_sets_cookie(client, db_session):
    await _register_kid_with_parent(client)
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email="dad@example.com",
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    r = await client.get(f"/parent/auth/callback?token={token}")
    assert r.status_code == 200
    assert client.cookies.get("parent_session") is not None


async def test_magic_callback_replay_410(client, db_session):
    await _register_kid_with_parent(client)
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email="dad@example.com",
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    r = await client.get(f"/parent/auth/callback?token={token}")
    assert r.status_code == 410


async def test_logout_clears_cookie(client, db_session):
    await _register_kid_with_parent(client)
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email="dad@example.com",
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    r = await client.post("/parent/auth/logout")
    assert r.status_code == 200
    assert not client.cookies.get("parent_session")
