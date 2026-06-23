"""Idempotent cosmetics catalog seed (M8) — upsert by slug.

Coins are EARNED only (1/XP); premium gates catalogue breadth, never sells coins.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cosmetics import CosmeticItem

CATALOG: list[dict] = [
    # ── Accessories ──────────────────────────────────────────────────────────
    {"slug": "party_hat", "name": "Party Hat", "emoji": "🥳", "coin_cost": 50, "is_premium": False, "type": "accessory"},
    {"slug": "sunglasses", "name": "Cool Shades", "emoji": "🕶️", "coin_cost": 75, "is_premium": False, "type": "accessory"},
    {"slug": "bow", "name": "Big Bow", "emoji": "🎀", "coin_cost": 75, "is_premium": False, "type": "accessory"},
    {"slug": "headphones", "name": "Headphones", "emoji": "🎧", "coin_cost": 100, "is_premium": False, "type": "accessory"},
    {"slug": "grad_cap", "name": "Graduation Cap", "emoji": "🎓", "coin_cost": 150, "is_premium": False, "type": "accessory"},
    {"slug": "crown", "name": "Golden Crown", "emoji": "👑", "coin_cost": 300, "is_premium": False, "type": "accessory"},
    {"slug": "monocle", "name": "Investor Monocle", "emoji": "🧐", "coin_cost": 200, "is_premium": True, "type": "accessory"},
    {"slug": "top_hat", "name": "Top Hat", "emoji": "🎩", "coin_cost": 500, "is_premium": True, "type": "accessory"},
    # ── Backgrounds ──────────────────────────────────────────────────────────
    {"slug": "bg_beach", "name": "Beach Day", "emoji": "🏖️", "coin_cost": 120, "is_premium": False, "type": "background"},
    {"slug": "bg_forest", "name": "Forest", "emoji": "🌲", "coin_cost": 120, "is_premium": False, "type": "background"},
    {"slug": "bg_city", "name": "City Lights", "emoji": "🏙️", "coin_cost": 180, "is_premium": False, "type": "background"},
    {"slug": "bg_space", "name": "Outer Space", "emoji": "🚀", "coin_cost": 250, "is_premium": False, "type": "background"},
    {"slug": "bg_vault", "name": "Money Vault", "emoji": "🏦", "coin_cost": 400, "is_premium": True, "type": "background"},
    # ── Skins ─────────────────────────────────────────────────────────────────
    {"slug": "skin_pink", "name": "Pink", "emoji": "🩷", "coin_cost": 60, "is_premium": False, "type": "skin"},
    {"slug": "skin_sky", "name": "Sky Blue", "emoji": "🔵", "coin_cost": 60, "is_premium": False, "type": "skin"},
    {"slug": "skin_mint", "name": "Mint", "emoji": "🟢", "coin_cost": 90, "is_premium": False, "type": "skin"},
    {"slug": "skin_gold", "name": "Gold", "emoji": "🟡", "coin_cost": 300, "is_premium": False, "type": "skin"},
    {"slug": "skin_lavender", "name": "Lavender", "emoji": "🟣", "coin_cost": 250, "is_premium": True, "type": "skin"},
]


async def seed_cosmetics(session: AsyncSession) -> int:
    """Upsert the catalog by slug; refreshes name/emoji/cost/premium/type. Returns count."""
    existing = {
        item.slug: item
        for item in (await session.scalars(select(CosmeticItem))).all()
    }
    for spec in CATALOG:
        item = existing.get(spec["slug"])
        if item is None:
            session.add(CosmeticItem(**spec))
        else:
            item.name = spec["name"]
            item.emoji = spec["emoji"]
            item.coin_cost = spec["coin_cost"]
            item.is_premium = spec["is_premium"]
            item.type = spec["type"]
    await session.flush()
    return len(CATALOG)
