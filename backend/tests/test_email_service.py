import pytest
from sqlalchemy import select

from app.models.consent import SentEmail
from app.services.email import LoggingEmailSender, _render

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_render_consent_template():
    body = _render("consent_request", {
        "child_username": "kid", "age": 12, "country_code": "GB",
        "link": "http://x/consent?token=abc",
    })
    assert "kid" in body
    assert "http://x/consent?token=abc" in body


def test_render_unknown_template_raises():
    import pytest
    with pytest.raises(ValueError):
        _render("nope", {})


async def test_logging_sender_persists_to_db(db_session):
    sender = LoggingEmailSender()
    await sender.send(db_session, "p@example.com", "parent_magic_link", {"link": "http://x/m?t=1"})
    await db_session.commit()
    rows = (await db_session.scalars(select(SentEmail))).all()
    assert any(r.to_email == "p@example.com" and "http://x/m?t=1" in r.body for r in rows)
