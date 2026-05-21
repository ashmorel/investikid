import uuid
from unittest.mock import patch

import pytest

from app.services.email import ResendEmailSender, _render_html

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


async def test_resend_sender_calls_api_and_persists(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "child_username": "bob",
        "age": 12,
        "country_code": "GB",
        "link": "http://localhost:5173/consent/verify?token=tok123",
    }

    sid = uuid.uuid4()
    with patch("app.services.email.asyncio.to_thread", return_value={"id": "msg_123"}) as mock_to_thread:
        await sender.send(db_session, "parent@example.com", "consent_request", context, subject_id=sid)

        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args
        assert call_args[0][0].__name__ == "send"
        call_params = call_args[0][1]
        assert call_params["from"] == "test@example.com"
        assert call_params["to"] == ["parent@example.com"]
        assert call_params["subject"] == "Approve your child's Invest-Ed account"
        assert "bob" in call_params["html"]
        assert "bob" in call_params["text"]

    from sqlalchemy import func, select

    from app.models.consent import SentEmail
    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1

    row = await db_session.scalar(select(SentEmail))
    assert row.to_email == "parent@example.com"
    assert row.template == "consent_request"
    assert "bob" in row.body
    assert row.subject_id == sid


async def test_resend_sender_raises_on_api_error(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "link": "http://localhost:5173/parent/auth/callback?token=tok456",
    }

    sid = uuid.uuid4()
    with patch(
        "app.services.email.asyncio.to_thread",
        side_effect=Exception("Resend API error"),
    ):
        with pytest.raises(Exception, match="Resend API error"):
            await sender.send(
                db_session, "parent@example.com", "parent_magic_link", context, subject_id=sid
            )


async def test_verify_email_and_reset_templates_render(db_session):
    from sqlalchemy import select

    from app.models.consent import SentEmail
    from app.services.email import LoggingEmailSender

    sender = LoggingEmailSender()
    sid_verify = uuid.uuid4()
    sid_reset = uuid.uuid4()
    await sender.send(db_session, "kid@example.com", "verify_email",
                      {"username": "kiddo", "link": "https://x/y?token=abc"},
                      subject_id=sid_verify)
    await sender.send(db_session, "kid@example.com", "password_reset",
                      {"link": "https://x/reset?token=def"},
                      subject_id=sid_reset)
    rows = (await db_session.scalars(select(SentEmail))).all()
    templates = {r.template for r in rows}
    assert "verify_email" in templates
    assert "password_reset" in templates
    bodies = "\n".join(r.body for r in rows)
    assert "https://x/y?token=abc" in bodies
    assert "https://x/reset?token=def" in bodies
    subject_ids = {r.subject_id for r in rows}
    assert sid_verify in subject_ids
    assert sid_reset in subject_ids
