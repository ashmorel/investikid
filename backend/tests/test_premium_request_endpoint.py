import pytest
from sqlalchemy import func, select

from app.models.consent import SentEmail
from app.models.premium_request import PremiumRequest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REG = {"password": "SecurePass123!", "dob": "2010-05-10", "country_code": "GB",
       "currency_code": "GBP", "parent_email": "pr-parent@example.com"}


async def _login_child(client, email="pr-child@example.com", username="prchild"):
    await client.post("/auth/register", json={**REG, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_request_sends_email_then_caps(client, db_session):
    await _login_child(client)
    r1 = await client.post("/premium/request", json={"kind": "level", "label": "Investing Basics"})
    assert r1.status_code == 200 and r1.json()["status"] == "sent"
    r2 = await client.post("/premium/request", json={"kind": "level", "label": "Investing Basics"})
    assert r2.json()["status"] == "already_sent"
    emails = await db_session.scalar(
        select(func.count(SentEmail.id)).where(SentEmail.template == "premium_request"))
    assert emails == 1  # capped — only one email
    reqs = await db_session.scalar(
        select(func.count(PremiumRequest.id)).where(PremiumRequest.parent_email == "pr-parent@example.com"))
    assert reqs == 2  # both interest rows recorded
