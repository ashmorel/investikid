import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _setup_parent(client, db_session, parent_email, child_email, child_username):
    """Create child + parent magic-link session (mirrors test_apple_billing)."""
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    child = await db_session.scalar(select(User).where(User.email == child_email))
    return child


async def _make_request(db_session, child, parent_email):
    req = PremiumRequest(
        child_user_id=child.id, parent_email=parent_email,
        context_kind="lesson", context_label="Compound Interest",
    )
    db_session.add(req)
    await db_session.commit()
    return req.id


async def test_decline_sets_declined_at_and_hides_from_list(client, db_session):
    parent_email = "decline-parent@example.com"
    child = await _setup_parent(
        client, db_session, parent_email, "decline-kid@example.com", "declinekid")
    req_id = await _make_request(db_session, child, parent_email)

    # Visible before decline.
    r = await client.get("/parent/premium-requests")
    assert r.status_code == 200
    assert any(item["id"] == str(req_id) for item in r.json())

    # Decline it.
    r = await client.post(
        f"/parent/premium-requests/{req_id}/decline", headers=_csrf_headers(client))
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    db_session.expire_all()
    refreshed = await db_session.scalar(
        select(PremiumRequest).where(PremiumRequest.id == req_id))
    assert refreshed.declined_at is not None

    # Gone from the list.
    r = await client.get("/parent/premium-requests")
    assert r.status_code == 200
    assert all(item["id"] != str(req_id) for item in r.json())


async def test_decline_other_parents_request_is_404(client, db_session):
    # Request owned by a different parent.
    other_child = await _setup_parent(
        client, db_session, "other-parent@example.com",
        "other-kid@example.com", "otherkid")
    other_req_id = await _make_request(db_session, other_child, "other-parent@example.com")

    # Now authenticate as the attacker parent.
    client.cookies.clear()
    await _setup_parent(
        client, db_session, "attacker-parent@example.com",
        "attacker-kid@example.com", "attackerkid")

    r = await client.post(
        f"/parent/premium-requests/{other_req_id}/decline", headers=_csrf_headers(client))
    assert r.status_code == 404

    # Unknown id is also 404.
    r = await client.post(
        f"/parent/premium-requests/{uuid.uuid4()}/decline", headers=_csrf_headers(client))
    assert r.status_code == 404
