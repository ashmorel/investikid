import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.models.subscription import Subscription
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_subscription_has_provider_and_external_id(db_session):
    sub = Subscription(
        parent_email="p@example.com", provider="apple",
        external_id="apple-orig-tx-1", status="active",
    )
    db_session.add(sub)
    await db_session.flush()
    got = await db_session.scalar(select(Subscription).where(Subscription.external_id == "apple-orig-tx-1"))
    assert got.provider == "apple"
    assert got.stripe_customer_id is None


async def test_premium_request_has_declined_at(db_session):
    user = User(
        username=f"c{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x", dob=dt.date(2015, 1, 1), country_code="GB",
        currency_code="GBP", parent_email="p@example.com",
    )
    db_session.add(user)
    await db_session.flush()
    pr = PremiumRequest(
        child_user_id=user.id, parent_email="p@example.com",
        context_kind="module", context_label="Investing Basics",
    )
    db_session.add(pr)
    await db_session.flush()
    assert pr.declined_at is None
