from datetime import date

import pytest

from app.core.config import settings
from app.models.user import User
from app.services.feedback_service import create_feedback

pytestmark = pytest.mark.asyncio(loop_scope="session")

_ADMIN_HEADERS = {"Authorization": f"Bearer {settings.admin_token}"}

_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"


async def _register_and_login(client, email: str, username: str) -> None:
    """Register a child user and log in, setting the CSRF header on the client."""
    await client.post(_REGISTER_URL, json={
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2010-06-15",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"parent_{username}@example.com",
    })
    await client.post(_LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _make_user(db_session, *, email: str) -> User:
    """Create and flush a minimal User row for FK compliance."""
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_feedback_child(db_session):
    user = await _make_user(db_session, email="fb_child@example.com")

    fb = await create_feedback(
        db_session,
        feedback_type="bug",
        message="quiz timer broken",
        page_url="/lessons/1",
        user_id=user.id,
        parent_email=None,
        submitter_role="child",
    )
    assert fb.id is not None
    assert fb.submitter_role == "child"
    assert fb.feedback_type == "bug"
    assert fb.parent_email is None


async def test_create_feedback_parent(db_session):
    fb = await create_feedback(
        db_session,
        feedback_type="feature",
        message="please add dark mode",
        page_url=None,
        user_id=None,
        parent_email="mum@example.com",
        submitter_role="parent",
    )
    assert fb.parent_email == "mum@example.com"
    assert fb.user_id is None
    assert fb.submitter_role == "parent"


async def test_notify_feedback_never_raises(monkeypatch):
    from app.core.config import settings
    from app.services import feedback_service

    monkeypatch.setattr(settings, "email_backend", "resend")
    monkeypatch.setattr(settings, "feedback_notify_email", "admin@example.com")

    def _boom(*args, **kwargs):
        raise RuntimeError("resend down")

    monkeypatch.setattr(feedback_service.resend.Emails, "send", _boom)

    # Must NOT raise despite the send failing
    await feedback_service.notify_feedback(
        submitter="alex",
        submitter_role="child",
        feedback_type="bug",
        message="x",
        page_url=None,
    )


async def test_notify_feedback_skips_when_not_resend(monkeypatch):
    from app.core.config import settings
    from app.services import feedback_service

    monkeypatch.setattr(settings, "email_backend", "logging")
    monkeypatch.setattr(settings, "feedback_notify_email", "admin@example.com")

    called = False

    def _track(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(feedback_service.resend.Emails, "send", _track)

    await feedback_service.notify_feedback(
        submitter="alex",
        submitter_role="child",
        feedback_type="bug",
        message="x",
        page_url=None,
    )
    assert called is False


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

async def test_child_submit_feedback_endpoint(client):
    await _register_and_login(client, "fb_ep_child@example.com", "fb_ep_child")
    r = await client.post("/feedback", json={
        "feedback_type": "bug",
        "message": "timer broke",
        "page_url": "/lessons/1",
    })
    assert r.status_code == 201
    body = r.json()
    assert "id" in body


async def test_submit_feedback_rejects_blank_message(client):
    await _register_and_login(client, "fb_blank@example.com", "fb_blank")
    r = await client.post("/feedback", json={
        "feedback_type": "bug",
        "message": "",
        "page_url": "/lessons/1",
    })
    assert r.status_code == 422


async def test_submit_feedback_rejects_bad_type(client):
    await _register_and_login(client, "fb_badtype@example.com", "fb_badtype")
    r = await client.post("/feedback", json={
        "feedback_type": "spam",
        "message": "this is not a valid type",
    })
    assert r.status_code == 422


async def test_submit_feedback_requires_auth(client):
    client.cookies.clear()
    r = await client.post("/feedback", json={
        "feedback_type": "bug",
        "message": "unauthenticated attempt",
    })
    assert r.status_code in (401, 403)


async def test_admin_list_feedback(client):
    await _register_and_login(client, "fb_admin_list@example.com", "fb_admin_list")
    submit = await client.post("/feedback", json={
        "feedback_type": "bug",
        "message": "admin list test",
        "page_url": "/lessons/2",
    })
    assert submit.status_code == 201

    r = await client.get("/admin/feedback", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    item = body["items"][0]
    assert "submitter" in item
    assert item["feedback_type"] in ("bug", "feature", "general")


async def test_admin_list_feedback_filters_by_type(client):
    await _register_and_login(client, "fb_filter@example.com", "fb_filter")
    submit = await client.post("/feedback", json={
        "feedback_type": "bug",
        "message": "filter test bug report",
        "page_url": "/lessons/3",
    })
    assert submit.status_code == 201

    r = await client.get("/admin/feedback?type=bug", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["feedback_type"] == "bug"
