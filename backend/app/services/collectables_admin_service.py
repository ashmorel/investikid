"""Admin authoring for limited-edition collectable drops (B2).

A "drop" is a CosmeticItem with unlock_type set; B2 lets an admin schedule a
drop over a dev-supplied "pool" item (drop_eligible=True, unlock_type=None).
All guardrails live here so the router stays thin. Never deletes anything —
earned items are immutable.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.services.collectables_service import _EVALUATORS

VALID_UNLOCK_TYPES: frozenset[str] = frozenset(_EVALUATORS.keys())
VALID_RARITIES: frozenset[str] = frozenset({"legendary", "epic", "rare", "common"})


class AdminError(Exception):
    """Carries a stable error code the router maps to an HTTP status."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class DropView:
    item: CosmeticItem
    status: str
    owned_count: int


def drop_status(item: CosmeticItem, now: datetime) -> str:
    if item.available_from is not None and now < item.available_from:
        return "scheduled"
    if item.available_until is not None and now > item.available_until:
        return "ended"
    return "live"


def _validate(rarity, unlock_type, unlock_threshold, available_from, available_until) -> None:
    if unlock_type not in VALID_UNLOCK_TYPES:
        raise AdminError("bad_unlock_type")
    if rarity not in VALID_RARITIES:
        raise AdminError("bad_rarity")
    if not isinstance(unlock_threshold, int) or unlock_threshold <= 0:
        raise AdminError("bad_threshold")
    if available_from is None or available_until is None or available_until <= available_from:
        raise AdminError("bad_window")


async def _owned_count(session: AsyncSession, item_id: uuid.UUID) -> int:
    return int(await session.scalar(
        select(func.count()).select_from(UserCosmetic).where(UserCosmetic.item_id == item_id)
    ) or 0)


async def _get_item(session: AsyncSession, item_id: uuid.UUID) -> CosmeticItem:
    item = await session.get(CosmeticItem, item_id)
    if item is None:
        raise AdminError("not_found")
    return item


async def list_pool(session: AsyncSession) -> list[CosmeticItem]:
    return list((await session.scalars(
        select(CosmeticItem)
        .where(CosmeticItem.drop_eligible.is_(True), CosmeticItem.unlock_type.is_(None))
        .order_by(CosmeticItem.name)
    )).all())


async def list_drops(session: AsyncSession, now: datetime) -> list[DropView]:
    drops = list((await session.scalars(
        select(CosmeticItem)
        .where(CosmeticItem.drop_eligible.is_(True), CosmeticItem.unlock_type.is_not(None))
        .order_by(CosmeticItem.available_from)
    )).all())
    out: list[DropView] = []
    for d in drops:
        out.append(DropView(item=d, status=drop_status(d, now), owned_count=await _owned_count(session, d.id)))
    return out


async def schedule_drop(
    session: AsyncSession, *, item_id: uuid.UUID, rarity: str, unlock_type: str,
    unlock_threshold: int, available_from: datetime, available_until: datetime,
) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if not item.drop_eligible:
        raise AdminError("not_drop_eligible")
    if item.unlock_type is not None:
        raise AdminError("already_scheduled")
    _validate(rarity, unlock_type, unlock_threshold, available_from, available_until)
    item.rarity = rarity
    item.unlock_type = unlock_type
    item.unlock_threshold = unlock_threshold
    item.available_from = available_from
    item.available_until = available_until
    await session.flush()
    return item


async def edit_drop(
    session: AsyncSession, *, item_id: uuid.UUID, now: datetime,
    rarity: str | None = None, unlock_type: str | None = None,
    unlock_threshold: int | None = None, available_from: datetime | None = None,
    available_until: datetime | None = None,
) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if item.unlock_type is None:
        raise AdminError("not_a_drop")
    status = drop_status(item, now)
    if status == "ended":
        raise AdminError("ended_locked")
    if status == "live":
        if any(v is not None for v in (rarity, unlock_type, unlock_threshold, available_from)):
            raise AdminError("live_locked")
        if available_until is None or available_until <= now:
            raise AdminError("bad_window")
        item.available_until = available_until
    else:  # scheduled — full replace, all fields required
        _validate(rarity, unlock_type, unlock_threshold, available_from, available_until)
        item.rarity = rarity
        item.unlock_type = unlock_type
        item.unlock_threshold = unlock_threshold
        item.available_from = available_from
        item.available_until = available_until
    await session.flush()
    return item


async def unschedule_drop(session: AsyncSession, *, item_id: uuid.UUID, now: datetime) -> CosmeticItem:
    item = await _get_item(session, item_id)
    if item.unlock_type is None:
        raise AdminError("not_a_drop")
    if drop_status(item, now) != "scheduled":
        raise AdminError("not_scheduled")  # only not-yet-started drops revert
    if await _owned_count(session, item_id) > 0:
        raise AdminError("owned_cannot_unschedule")
    item.unlock_type = None
    item.unlock_threshold = None
    item.rarity = None
    item.available_from = None
    item.available_until = None
    await session.flush()
    return item
