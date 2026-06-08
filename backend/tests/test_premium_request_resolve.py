import datetime as dt
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.services.webhook_service import resolve_premium_requests

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _child(parent_email: str) -> User:
    return User(
        username=f"c{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=dt.date(2015, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent_email,
    )


async def test_resolve_marks_open_requests(db_session):
    pe = "resolve@example.com"
    c1, c2, c3 = _child(pe), _child(pe), _child("other@example.com")
    db_session.add_all([c1, c2, c3])
    await db_session.flush()

    db_session.add(PremiumRequest(child_user_id=c1.id, parent_email=pe,
                                  context_kind="level", context_label="X"))
    db_session.add(PremiumRequest(child_user_id=c2.id, parent_email=pe,
                                  context_kind="module", context_label="Y",
                                  resolved_at=datetime.now(UTC)))
    # a different parent's open request must NOT be resolved
    db_session.add(PremiumRequest(child_user_id=c3.id, parent_email="other@example.com",
                                  context_kind="level", context_label="Z"))
    await db_session.flush()
    await resolve_premium_requests(db_session, pe)
    mine = (await db_session.execute(
        select(PremiumRequest).where(PremiumRequest.parent_email == pe))).scalars().all()
    assert all(r.resolved_at is not None for r in mine)
    other = await db_session.scalar(
        select(PremiumRequest).where(PremiumRequest.parent_email == "other@example.com"))
    assert other.resolved_at is None
