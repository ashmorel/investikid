import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_setting import AppSetting

_ALERT_EMAILS_KEY = "alert_emails"

_STARTING_CASH_KEY = "simulator.starting_cash"
_DEFAULT_STARTING_CASH: dict[str, Decimal] = {
    "GBP": Decimal("1000.00"),
    "USD": Decimal("1000.00"),
    "HKD": Decimal("10000.00"),
    "EUR": Decimal("1000.00"),
}


async def get_setting(session: AsyncSession, key: str) -> str | None:
    row = await session.get(AppSetting, key)
    return row.value if row is not None else None


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=value)
        session.add(row)
    else:
        row.value = value


async def get_alert_emails(session: AsyncSession) -> list[str]:
    raw = await get_setting(session, _ALERT_EMAILS_KEY)
    if raw:
        try:
            vals = json.loads(raw)
            if isinstance(vals, list) and vals:
                return [str(v) for v in vals]
        except (ValueError, TypeError):
            pass
    # env fallback
    return [settings.admin_alert_email] if settings.admin_alert_email else []


async def set_alert_emails(session: AsyncSession, emails: list[str]) -> None:
    await set_setting(session, _ALERT_EMAILS_KEY, json.dumps(emails))


async def get_starting_cash(session: AsyncSession) -> dict[str, Decimal]:
    merged = dict(_DEFAULT_STARTING_CASH)
    raw = await get_setting(session, _STARTING_CASH_KEY)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    merged[str(k)] = Decimal(str(v))
        except (ValueError, TypeError, ArithmeticError):
            # Corrupt/hand-edited setting -> fall back to defaults rather than crash.
            pass
    return merged


async def set_starting_cash(session: AsyncSession, mapping: dict[str, Decimal]) -> None:
    await set_setting(
        session, _STARTING_CASH_KEY, json.dumps({k: str(v) for k, v in mapping.items()})
    )
