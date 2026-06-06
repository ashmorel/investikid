import datetime as dt
import uuid
from datetime import datetime

import pytest

from app.models.premium_request import PremiumRequest
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_premium_request_persists(db_session):
    user = User(username=f"c{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@x.test",
                password_hash="x", dob=dt.date(2015, 1, 1), country_code="GB",
                currency_code="GBP", parent_email="p@x.test")
    db_session.add(user)
    await db_session.flush()
    req = PremiumRequest(child_user_id=user.id, parent_email="p@x.test",
                         context_kind="level", context_label="Investing Basics")
    db_session.add(req)
    await db_session.flush()
    assert req.id is not None
    assert req.resolved_at is None
    assert isinstance(req.created_at, datetime)
