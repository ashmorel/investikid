import logging
import time
from datetime import UTC, datetime

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.email import get_email_sender

logger = logging.getLogger(__name__)
_last_sent: dict[str, float] = {}


async def _send_alert(key: str, headline: str, detail: str) -> None:
    """Throttled admin alert. Never raises (fire-and-forget safe)."""
    try:
        if not settings.admin_alert_email:
            return
        now = time.monotonic()
        last = _last_sent.get(key)
        if last is not None and (now - last) < settings.llm_alert_cooldown_seconds:
            return
        _last_sent[key] = now
        async with async_session_factory() as session:
            await get_email_sender().send(
                session,
                to=settings.admin_alert_email,
                template="admin_llm_alert",
                context={
                    "headline": headline,
                    "detail": detail,
                    "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                },
            )
            await session.commit()
    except Exception:  # never break the caller
        logger.exception("Failed to send admin alert %s", key)


async def on_provider_degraded(detail: str) -> None:
    await _send_alert(
        "llm_degraded",
        "A premium AI provider is failing; Coach Eddie is using the fallback provider. "
        "If this is OpenAI 'insufficient_quota', top up the account.",
        detail,
    )


async def on_all_providers_down(detail: str, path: str) -> None:
    await _send_alert(
        "llm_down",
        f"All AI providers are unavailable — Coach Eddie is down (path: {path}).",
        detail,
    )


def reset_throttle() -> None:  # for tests
    _last_sent.clear()
