import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_setting import AppSetting

_ALERT_EMAILS_KEY = "alert_emails"

_STARTING_CASH_KEY = "simulator.starting_cash"
_TRADE_COMMISSION_PCT_KEY = "simulator.trade_commission_pct"
_DEFAULT_TRADE_COMMISSION_PCT = Decimal("1.0")

_MARKET_ENROLL_BONUS_KEY = "market.enroll_bonus_coins"
_MARKET_COMPLETION_BONUS_KEY = "market.completion_bonus_coins"
_DEFAULT_MARKET_ENROLL_BONUS = 25
_DEFAULT_MARKET_COMPLETION_BONUS = 250
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


async def _get_int_setting(session: AsyncSession, key: str, default: int) -> int:
    raw = await get_setting(session, key)
    if raw is not None:
        try:
            val = int(raw)
            if val >= 0:
                return val
        except (TypeError, ValueError):
            pass
    return default


async def get_market_enroll_bonus_coins(session: AsyncSession) -> int:
    return await _get_int_setting(session, _MARKET_ENROLL_BONUS_KEY, _DEFAULT_MARKET_ENROLL_BONUS)


async def set_market_enroll_bonus_coins(session: AsyncSession, coins: int) -> None:
    if coins < 0:
        raise ValueError("enroll bonus coins must be >= 0")
    await set_setting(session, _MARKET_ENROLL_BONUS_KEY, str(coins))


async def get_market_completion_bonus_coins(session: AsyncSession) -> int:
    return await _get_int_setting(
        session, _MARKET_COMPLETION_BONUS_KEY, _DEFAULT_MARKET_COMPLETION_BONUS
    )


async def set_market_completion_bonus_coins(session: AsyncSession, coins: int) -> None:
    if coins < 0:
        raise ValueError("completion bonus coins must be >= 0")
    await set_setting(session, _MARKET_COMPLETION_BONUS_KEY, str(coins))


async def get_trade_commission_pct(session: AsyncSession) -> Decimal:
    raw = await get_setting(session, _TRADE_COMMISSION_PCT_KEY)
    if raw:
        try:
            pct = Decimal(raw)
            if Decimal("0") <= pct <= Decimal("10"):
                return pct
        except ArithmeticError:
            # Corrupt/hand-edited setting -> fall back to default rather than crash.
            pass
    return _DEFAULT_TRADE_COMMISSION_PCT


async def set_trade_commission_pct(session: AsyncSession, pct: Decimal) -> None:
    if not Decimal("0") <= pct <= Decimal("10"):
        raise ValueError("trade_commission_pct must be between 0 and 10")
    await set_setting(session, _TRADE_COMMISSION_PCT_KEY, str(pct))
