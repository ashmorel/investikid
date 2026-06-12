"""Idempotent cosmetics catalog seed (M8) — upsert by slug.

Coins are EARNED only (1/XP); premium gates catalogue breadth, never sells coins.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cosmetics import CosmeticItem

CATALOG: list[dict] = [
    {"slug": "party_hat", "name": "Party Hat", "emoji": "🥳", "coin_cost": 50, "is_premium": False},
    {"slug": "sunglasses", "name": "Cool Shades", "emoji": "🕶️", "coin_cost": 75, "is_premium": False},
    {"slug": "bow", "name": "Big Bow", "emoji": "🎀", "coin_cost": 75, "is_premium": False},
    {"slug": "headphones", "name": "Headphones", "emoji": "🎧", "coin_cost": 100, "is_premium": False},
    {"slug": "grad_cap", "name": "Graduation Cap", "emoji": "🎓", "coin_cost": 150, "is_premium": False},
    {"slug": "crown", "name": "Golden Crown", "emoji": "👑", "coin_cost": 300, "is_premium": False},
    {"slug": "monocle", "name": "Investor Monocle", "emoji": "🧐", "coin_cost": 200, "is_premium": True},
    {"slug": "top_hat", "name": "Top Hat", "emoji": "🎩", "coin_cost": 500, "is_premium": True},
]


async def seed_cosmetics(session: AsyncSession) -> int:
    """Upsert the catalog by slug; refreshes name/emoji/cost/premium. Returns count."""
    existing = {
        item.slug: item
        for item in (await session.scalars(select(CosmeticItem))).all()
    }
    for spec in CATALOG:
        item = existing.get(spec["slug"])
        if item is None:
            session.add(CosmeticItem(type="accessory", **spec))
        else:
            item.name = spec["name"]
            item.emoji = spec["emoji"]
            item.coin_cost = spec["coin_cost"]
            item.is_premium = spec["is_premium"]
    await session.flush()
    return len(CATALOG)
