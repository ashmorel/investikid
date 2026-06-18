from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Market

# 10 target markets. has_content=True only for GB at C1; others seeded-but-empty
# until Sub-project E. default_language uses BCP-47 codes (see app/core/languages.py).
MARKETS: list[dict] = [
    {"code": "GB", "name": "United Kingdom", "currency_code": "GBP", "default_language": "en", "has_content": True},
    {"code": "US", "name": "United States", "currency_code": "USD", "default_language": "en", "has_content": False},
    {"code": "AU", "name": "Australia", "currency_code": "AUD", "default_language": "en", "has_content": False},
    {"code": "CA", "name": "Canada", "currency_code": "CAD", "default_language": "en", "has_content": False},
    {"code": "IE", "name": "Ireland", "currency_code": "EUR", "default_language": "en", "has_content": False},
    {"code": "ES", "name": "Spain", "currency_code": "EUR", "default_language": "es", "has_content": False},
    {"code": "FR", "name": "France", "currency_code": "EUR", "default_language": "fr", "has_content": False},
    {"code": "DE", "name": "Germany", "currency_code": "EUR", "default_language": "de", "has_content": False},
    {"code": "HK", "name": "Hong Kong", "currency_code": "HKD", "default_language": "en", "has_content": False},
    {"code": "SG", "name": "Singapore", "currency_code": "SGD", "default_language": "en", "has_content": False},
]


async def seed_markets(session: AsyncSession) -> None:
    """Idempotent upsert of the market catalog. Safe to run repeatedly."""
    existing = {c for c in (await session.scalars(select(Market.code))).all()}
    for m in MARKETS:
        if m["code"] in existing:
            row = await session.get(Market, m["code"])
            row.name = m["name"]
            row.currency_code = m["currency_code"]
            row.default_language = m["default_language"]
            row.has_content = m["has_content"]
        else:
            session.add(Market(**m, is_active=True))
    await session.flush()
