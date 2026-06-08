import pytest
from sqlalchemy import select

from app.models.consent import SentEmail
from app.services.email import LoggingEmailSender

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_premium_request_email_renders_and_logs(db_session):
    await LoggingEmailSender().send(
        db_session, "parent@x.test", "premium_request",
        {"child_username": "ava", "context_label": "Investing Basics",
         "benefits": ["Coach Penny", "Premium lessons"]},
    )
    row = (await db_session.execute(
        select(SentEmail).where(SentEmail.template == "premium_request")
    )).scalars().first()
    assert row is not None
    assert "ava" in row.body
    assert "Investing Basics" in row.body
    assert "Coach Penny" in row.body
