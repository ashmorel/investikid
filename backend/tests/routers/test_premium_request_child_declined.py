from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"


async def _login(client, email, username, parent_email):
    await client.post(REGISTER_URL, json={
        "email": email, "username": username, "password": "SecurePass123!",
        "dob": "2010-05-10", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_declined_child_sees_declined_state(client, db_session):
    parent_email = "cdecline-parent@example.com"
    await _login(client, "cdecline-kid@example.com", "cdeclinekid", parent_email)

    child = await db_session.scalar(
        select(User).where(User.email == "cdecline-kid@example.com"))

    # Simulate a prior, parent-declined request within the cooldown window.
    db_session.add(PremiumRequest(
        child_user_id=child.id, parent_email=parent_email,
        context_kind="lesson", context_label="Compound Interest",
        declined_at=datetime.now(UTC),
    ))
    await db_session.commit()

    r = await client.post("/premium/request", json={"kind": "lesson", "label": "Compound Interest"})
    assert r.status_code == 200
    assert r.json() == {"status": "declined"}
