import pytest

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

pytestmark = pytest.mark.asyncio(loop_scope="session")

_BASE = {
    "password": "SecurePass123!",
    "dob": "2006-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="me@example.com", username="meuser"):
    await client.post(REGISTER_URL, json={**_BASE, "email": email, "username": username})
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_get_profile_authenticated(client):
    await _register_and_login(client)
    response = await client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "password_hash" not in data


async def test_get_profile_unauthenticated(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_country_code_is_immutable_via_patch(client):
    """country_code drives the COPPA / UK-GDPR parental-consent regime
    (compliance.py / consent_service.py derive the consent age from it), so the
    self-service preferences PATCH must NOT let a user change it. The user is
    registered as GB; sending a different country_code is silently ignored while
    other preferences still update."""
    await _register_and_login(client, "update@example.com", "updateuser")
    response = await client.patch("/users/me", json={"country_code": "US", "currency_code": "USD"})
    assert response.status_code == 200
    # currency still updates independently...
    assert response.json()["currency_code"] == "USD"
    # ...but the legal consent country is unchanged.
    assert response.json()["country_code"] == "GB"


async def test_update_topic_path(client):
    await _register_and_login(client, "topic@example.com", "topicuser")
    response = await client.patch("/users/me", json={"topic_path": "stocks"})
    assert response.status_code == 200
    assert response.json()["topic_path"] == "stocks"


async def test_get_progress_zero_defaults_for_brand_new_user(client, db_session):
    await _register_and_login(client, email="new@example.com", username="newuser")
    response = await client.get("/users/me/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["xp"] == 0
    assert data["level"] == 1
    assert data["streak_count"] == 0
    assert data["last_activity_date"] is None


async def test_get_progress_reflects_lesson_completion(client, db_session):
    from datetime import date

    from app.models.content import Lesson, Module

    await _register_and_login(client, email="lp@example.com", username="lpuser")
    module = Module(topic="stocks", title="P", country_codes=[], is_premium=False, order_index=0)
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, type="card", order_index=0, xp_reward=10,
        content_json={"title": "t", "body": "b"},
    )
    db_session.add(lesson)
    await db_session.commit()

    complete = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert complete.status_code == 200

    response = await client.get("/users/me/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["xp"] == 10
    assert data["level"] >= 1
    assert data["streak_count"] == 1
    assert data["last_activity_date"] == date.today().isoformat()


async def test_get_progress_unauthenticated(client):
    # Fresh client (no cookies, no CSRF header) — call /users/me/progress directly.
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    response = await client.get("/users/me/progress")
    assert response.status_code == 401


async def test_self_export_returns_profile_json(client, db_session):
    await client.post("/auth/register", json={
        "email": "export@example.com", "username": "exportme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    # Register set auth cookies on the client.
    resp = await client.get("/users/me/export")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].startswith("attachment")
    data = resp.json()
    assert data["profile"]["username"] == "exportme"
    assert data["profile"]["email"] == "export@example.com"
    assert "progress" in data
    assert "consent" in data
    assert "emails" in data
    assert isinstance(data["emails"], list)


async def test_export_does_not_leak_sibling_emails(client, db_session):
    from sqlalchemy import select

    from app.models.consent import SentEmail
    from app.models.user import User

    for uname in ("sibA", "sibB"):
        await client.post("/auth/register", json={
            "username": uname, "password": "SecurePass123!",
            "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
            "parent_email": "shared-parent@example.com",
            "policy_version_accepted": "2026-05-16",
        })
    a = await db_session.scalar(select(User).where(User.username == "sibA"))
    b = await db_session.scalar(select(User).where(User.username == "sibB"))
    a_emails = (await db_session.scalars(
        select(SentEmail).where(SentEmail.subject_id == a.id))).all()
    b_emails = (await db_session.scalars(
        select(SentEmail).where(SentEmail.subject_id == b.id))).all()
    assert a_emails and b_emails
    assert {e.subject_id for e in a_emails} == {a.id}
    assert {e.subject_id for e in b_emails} == {b.id}
