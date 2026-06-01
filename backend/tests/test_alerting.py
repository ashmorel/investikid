"""Tests for app/services/alerting.py — admin LLM alert feature."""
import pytest
from sqlalchemy import func, select

from app.models.consent import SentEmail
from app.services.alerting import on_all_providers_down, on_provider_degraded, reset_throttle
from app.services.email import LoggingEmailSender

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def _reset_throttle_between_tests():
    """Ensure the in-memory throttle is cleared before every test."""
    reset_throttle()
    yield
    reset_throttle()


@pytest.fixture(autouse=True)
def _set_admin_email(monkeypatch):
    """Point alerts at a test address by default; individual tests may override."""
    from app.core import config
    monkeypatch.setattr(config.settings, "admin_alert_email", "admin@example.com")


async def test_provider_degraded_sends_alert(db_session, monkeypatch):
    """on_provider_degraded sends one admin_llm_alert email."""
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    # Patch async_session_factory to use the test db_session
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_provider_degraded("quota exceeded")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1
    row = await db_session.scalar(select(SentEmail))
    assert row.template == "admin_llm_alert"
    assert row.to_email == "admin@example.com"
    assert "quota exceeded" in row.body
    assert "premium AI provider" in row.body


async def test_provider_degraded_throttled(db_session, monkeypatch):
    """A second immediate call does NOT send another alert (throttled)."""
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_provider_degraded("first call")
    await on_provider_degraded("second call — throttled")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1  # still only one email


async def test_no_send_when_admin_email_empty(db_session, monkeypatch):
    """When admin_alert_email is empty, no email is sent."""
    from app.core import config
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(config.settings, "admin_alert_email", "")
    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_provider_degraded("boom")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 0


async def test_all_providers_down_sends_alert(db_session, monkeypatch):
    """on_all_providers_down sends an alert with the path in the headline."""
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_all_providers_down("all failed", "/api/ai/coach")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1
    row = await db_session.scalar(select(SentEmail))
    assert row.template == "admin_llm_alert"
    assert "/api/ai/coach" in row.body


async def test_all_providers_down_throttled(db_session, monkeypatch):
    """Repeated all-down alerts are throttled independently of degraded alerts."""
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_all_providers_down("first", "/path")
    await on_all_providers_down("second — throttled", "/path")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1


async def test_degraded_and_down_keys_independent(db_session, monkeypatch):
    """Degraded and all-down alerts use different throttle keys — each fires once."""
    from app.services import alerting
    from app.services import email as email_mod

    monkeypatch.setattr(email_mod, "get_email_sender", lambda: LoggingEmailSender())
    from unittest.mock import AsyncMock, MagicMock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(alerting, "async_session_factory", lambda: cm)

    await on_provider_degraded("degraded detail")
    await on_all_providers_down("down detail", "/path")

    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 2
