from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Module
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
    """Idempotent upsert of the market catalog. Safe to run repeatedly.

    NOTE: ``has_content`` is set ONLY on initial insert. It is runtime state —
    flipped True by the publish pipeline (curriculum_publish_service) and the
    admin toggle once a market's content goes live — so re-seeding must NOT
    overwrite it, or every redeploy would silently un-publish markets whose
    content was added after the initial seed. See reconcile_market_content.
    """
    existing = {c for c in (await session.scalars(select(Market.code))).all()}
    for m in MARKETS:
        if m["code"] in existing:
            row = await session.get(Market, m["code"])
            row.name = m["name"]
            row.currency_code = m["currency_code"]
            row.default_language = m["default_language"]
            row.is_active = True
        else:
            session.add(Market(**m, is_active=True))
    await session.flush()


async def reconcile_market_content(session: AsyncSession) -> None:
    """Self-heal ``has_content``: promote a market to True when it actually has
    at least one published, non-archived module.

    Runs at startup after content seeding so a market whose content was
    published after the initial seed (or had its flag clobbered by an older
    seed) is correctly marked live without manual DB surgery. Promote-only — it
    never demotes, so it can't hide a market that an operator has live.
    """
    markets = (await session.scalars(select(Market))).all()
    for market in markets:
        if market.has_content:
            continue
        has_live_module = await session.scalar(
            select(
                exists().where(
                    Module.market_code == market.code,
                    Module.published.is_(True),
                    Module.archived_at.is_(None),
                )
            )
        )
        if has_live_module:
            market.has_content = True
    await session.flush()
