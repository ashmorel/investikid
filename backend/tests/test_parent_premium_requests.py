from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup_parent(client, db_session, parent_email, child_email, child_username):
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2010-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email})
    token = await issue_one_time_token(db_session, purpose=PARENT_MAGIC_AUDIENCE,
                                       email=parent_email, subject_id=None,
                                       expires_in=timedelta(minutes=15))
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


async def test_lists_unresolved_for_this_parent_only(client, db_session):
    await _setup_parent(client, db_session, "ppr@example.com", "pprk@example.com", "pprk")
    child = await db_session.scalar(select(User).where(User.email == "pprk@example.com"))
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="ppr@example.com",
                                  context_kind="level", context_label="Investing Basics"))
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="ppr@example.com",
                                  context_kind="module", context_label="Taxes",
                                  resolved_at=datetime.now(UTC)))
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="other@example.com",
                                  context_kind="level", context_label="Other"))
    await db_session.commit()
    resp = await client.get("/parent/premium-requests")
    assert resp.status_code == 200
    data = resp.json()
    labels = [d["context_label"] for d in data]
    assert "Investing Basics" in labels
    assert "Taxes" not in labels  # resolved excluded
    assert "Other" not in labels  # other parent excluded
    assert data[0]["child_username"] == "pprk"
