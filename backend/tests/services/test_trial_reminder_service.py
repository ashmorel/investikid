import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.consent import SentEmail
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User
from app.services import trial_reminder_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _sub(parent_email, *, provider="stripe", status="trialing", days=1):
    return Subscription(
        parent_email=parent_email,
        provider=provider,
        external_id=f"ext-{uuid.uuid4()}",
        status=status,
        current_period_end=datetime.now(UTC) + timedelta(days=days),
    )


async def _count_emails(db_session, to_email):
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.to_email == to_email)
    )).all()
    return len(rows)


async def test_sends_for_in_window_stripe_trial(db_session):
    db_session.add(_sub("a@example.com", days=1))
    db_session.add(User(username="kid_a", password_hash="x", dob=date(2014, 1, 1),
                        country_code="GB", currency_code="GBP", parent_email="a@example.com"))
    await db_session.flush()

    result = await trial_reminder_service.run(db_session)

    assert result["sent"] == 1
    assert await _count_emails(db_session, "a@example.com") == 1


async def test_dedupes_on_second_run(db_session):
    db_session.add(_sub("b@example.com", days=1))
    await db_session.flush()

    first = await trial_reminder_service.run(db_session)
    second = await trial_reminder_service.run(db_session)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert await _count_emails(db_session, "b@example.com") == 1


async def test_skips_opted_out_parent(db_session):
    db_session.add(_sub("c@example.com", days=1))
    db_session.add(ParentPreferences(parent_email="c@example.com", trial_reminder_opt_out=True))
    await db_session.flush()

    result = await trial_reminder_service.run(db_session)

    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert await _count_emails(db_session, "c@example.com") == 0


async def test_ignores_non_stripe(db_session):
    db_session.add(_sub("d@example.com", provider="apple", days=1))
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_ignores_non_trialing(db_session):
    db_session.add(_sub("e@example.com", status="active", days=1))
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_ignores_out_of_window(db_session):
    db_session.add(_sub("f@example.com", days=10))   # too far out
    db_session.add(_sub("g@example.com", days=-1))   # already past
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_child_label_fallback(db_session):
    db_session.add(_sub("h@example.com", days=1))  # no User rows for this parent
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 1
    row = await db_session.scalar(
        select(SentEmail).where(SentEmail.to_email == "h@example.com")
    )
    assert "your child" in row.body
