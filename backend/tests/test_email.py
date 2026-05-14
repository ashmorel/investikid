import pytest
from unittest.mock import AsyncMock, patch

from app.services.email import _render_html

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_render_html_consent_request():
    context = {
        "child_username": "alice",
        "age": 13,
        "country_code": "GB",
        "link": "http://localhost:5173/consent/verify?token=abc123",
    }
    html = _render_html("consent_request", context)

    assert "alice" in html
    assert "13" in html
    assert "GB" in html
    assert 'href="http://localhost:5173/consent/verify?token=abc123"' in html
    assert "Approve Account" in html
    assert "24 hours" in html
    assert "<html" in html


def test_render_html_parent_magic_link():
    context = {
        "link": "http://localhost:5173/parent/auth/callback?token=xyz789",
    }
    html = _render_html("parent_magic_link", context)

    assert 'href="http://localhost:5173/parent/auth/callback?token=xyz789"' in html
    assert "Sign In" in html
    assert "15 minutes" in html
    assert "<html" in html


def test_render_html_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        _render_html("nonexistent", {})


from app.services.email import ResendEmailSender


async def test_resend_sender_calls_api_and_persists(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "child_username": "bob",
        "age": 12,
        "country_code": "GB",
        "link": "http://localhost:5173/consent/verify?token=tok123",
    }

    with patch("app.services.email.resend") as mock_resend:
        mock_resend.Emails.send_async = AsyncMock(return_value={"id": "msg_123"})

        await sender.send(db_session, "parent@example.com", "consent_request", context)

        # Verify resend was called once with correct params
        mock_resend.Emails.send_async.assert_called_once()
        call_params = mock_resend.Emails.send_async.call_args[0][0]
        assert call_params["from"] == "test@example.com"
        assert call_params["to"] == ["parent@example.com"]
        assert call_params["subject"] == "Approve your child's Invest-Ed account"
        assert "bob" in call_params["html"]
        assert "bob" in call_params["text"]

    # Verify SentEmail record was created
    from sqlalchemy import select, func
    from app.models.consent import SentEmail
    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1

    row = await db_session.scalar(select(SentEmail))
    assert row.to_email == "parent@example.com"
    assert row.template == "consent_request"
    assert "bob" in row.body


async def test_resend_sender_raises_on_api_error(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "link": "http://localhost:5173/parent/auth/callback?token=tok456",
    }

    with patch("app.services.email.resend") as mock_resend:
        mock_resend.Emails.send_async = AsyncMock(
            side_effect=Exception("Resend API error")
        )

        with pytest.raises(Exception, match="Resend API error"):
            await sender.send(
                db_session, "parent@example.com", "parent_magic_link", context
            )
