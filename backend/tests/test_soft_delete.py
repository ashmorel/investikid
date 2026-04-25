from datetime import datetime, timezone

import pytest

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_active(client, email="active@example.com", username="active"):
    await client.post("/auth/register", json={
        "email": email, "username": username, "password": "SecurePass123!",
        "dob": "2008-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_login_pending_consent_returns_403(client, db_session):
    await client.post("/auth/register", json={
        "email": "kid5@example.com", "username": "kid5", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "p@example.com",
    })
    r = await client.post("/auth/login", json={
        "email": "kid5@example.com", "password": "SecurePass123!"
    })
    assert r.status_code == 403
    assert "consent" in r.json()["detail"].lower()


async def test_soft_deleted_user_login_blocked(client, db_session):
    await _register_active(client, email="del@example.com", username="del")
    from sqlalchemy import select
    user = await db_session.scalar(
        select(User).where(User.email == "del@example.com")
        .execution_options(include_deleted=True)
    )
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    client.cookies.clear()
    r = await client.post("/auth/login", json={
        "email": "del@example.com", "password": "SecurePass123!"
    })
    assert r.status_code == 401


async def test_get_current_user_blocks_after_soft_delete(client, db_session):
    await _register_active(client, email="del2@example.com", username="del2")
    from sqlalchemy import select
    user = await db_session.scalar(
        select(User).where(User.email == "del2@example.com")
        .execution_options(include_deleted=True)
    )
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    r = await client.get("/users/me")
    assert r.status_code == 401
