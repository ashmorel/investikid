import logging
import time
from datetime import UTC, datetime

from app.core.database import async_session_factory
from app.services.email import get_email_sender

logger = logging.getLogger(__name__)
_last_sent: dict[str, float] = {}


async def _send_alert(key: str, headline: str, detail: str) -> None:
    """Throttled admin alert. Never raises (fire-and-forget safe)."""
    try:
        from app.services.app_settings import get_alert_emails

        now = time.monotonic()
        last = _last_sent.get(key)
        if last is not None and (now - last) < _get_cooldown():
            return
        async with async_session_factory() as session:
            recipients = await get_alert_emails(session)
            if not recipients:
                return
            _last_sent[key] = now
            context = {
                "headline": headline,
                "detail": detail,
                "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            for addr in recipients:
                await get_email_sender().send(
                    session,
                    to=addr,
                    template="admin_llm_alert",
                    context=context,
                )
            await session.commit()
    except Exception:  # never break the caller
        logger.exception("Failed to send admin alert %s", key)


def _get_cooldown() -> int:
    from app.core.config import settings
    return settings.llm_alert_cooldown_seconds


async def on_provider_degraded(detail: str) -> None:
    await _send_alert(
        "llm_degraded",
        "The primary AI provider is failing, so AI replies (including Coach Penny) are "
        "coming from the fallback provider. Most likely a quota or rate limit on the "
        "primary provider — e.g. a free-tier daily cap — so check that provider's "
        "quota/billing. The provider's error is in the detail below.",
        detail,
    )


async def on_all_providers_down(detail: str, path: str) -> None:
    await _send_alert(
        "llm_down",
        f"All AI providers are unavailable — Coach Penny is down (path: {path}).",
        detail,
    )


def reset_throttle() -> None:  # for tests
    _last_sent.clear()
