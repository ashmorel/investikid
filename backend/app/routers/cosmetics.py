"""Penny's Shop (M8): cosmetics catalog, buy with learning coins, equip.

Coins are earned only (1/XP). Premium gates catalogue breadth — coins are
never purchasable, so there is no real-money crossover anywhere here.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.services.entitlements import is_premium

router = APIRouter(prefix="/cosmetics", tags=["cosmetics"])


class CosmeticOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    emoji: str
    type: str
    coin_cost: int
    is_premium: bool
    owned: bool
    equipped: bool
    can_buy: bool


class ShopResponse(BaseModel):
    coins: int
    items: list[CosmeticOut]


class BuyResponse(BaseModel):
    status: str
    coins: int


async def _shop_state(session: AsyncSession, user: User) -> ShopResponse:
    progress = await session.get(UserProgress, user.id)
    coins = (progress.virtual_coins or 0) if progress else 0
    items = (
        await session.scalars(select(CosmeticItem).order_by(CosmeticItem.coin_cost))
    ).all()
    owned_rows = {
        row.item_id: row
        for row in (
            await session.scalars(
                select(UserCosmetic).where(UserCosmetic.user_id == user.id)
            )
        ).all()
    }
    premium = is_premium(user)
    return ShopResponse(
        coins=coins,
        items=[
            CosmeticOut(
                id=item.id,
                slug=item.slug,
                name=item.name,
                emoji=item.emoji,
                type=item.type,
                coin_cost=item.coin_cost,
                is_premium=item.is_premium,
                owned=item.id in owned_rows,
                equipped=bool(owned_rows.get(item.id) and owned_rows[item.id].equipped),
                can_buy=(
                    item.id not in owned_rows
                    and coins >= item.coin_cost
                    and (premium or not item.is_premium)
                ),
            )
            for item in items
        ],
    )


@router.get("", response_model=ShopResponse)
async def get_shop(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _shop_state(session, current_user)


@router.post("/{item_id}/buy", response_model=BuyResponse)
async def buy_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(CosmeticItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if item.is_premium and not is_premium(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "premium_item")

    progress = await session.get(UserProgress, current_user.id)
    coins = (progress.virtual_coins or 0) if progress else 0
    already = await session.scalar(
        select(UserCosmetic).where(
            UserCosmetic.user_id == current_user.id, UserCosmetic.item_id == item_id
        )
    )
    if already is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_owned")
    if progress is None or coins < item.coin_cost:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not_enough_coins")

    # SAVEPOINT: a racing duplicate insert rolls back without poisoning the txn
    # (same pattern as apply-mission completions).
    try:
        async with session.begin_nested():
            session.add(
                UserCosmetic(
                    user_id=current_user.id,
                    item_id=item_id,
                    unlocked_at=datetime.now(UTC),
                )
            )
            progress.virtual_coins = coins - item.coin_cost
            await session.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_owned") from None
    await session.commit()
    return BuyResponse(status="ok", coins=progress.virtual_coins)


@router.post("/{item_id}/equip")
async def equip_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    owned = await session.scalar(
        select(UserCosmetic).where(
            UserCosmetic.user_id == current_user.id, UserCosmetic.item_id == item_id
        )
    )
    if owned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_owned")
    target = await session.get(CosmeticItem, item_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    # One equipped per category: unequip only the user's SAME-TYPE items.
    await session.execute(
        update(UserCosmetic)
        .where(
            UserCosmetic.user_id == current_user.id,
            UserCosmetic.item_id.in_(
                select(CosmeticItem.id).where(CosmeticItem.type == target.type)
            ),
        )
        .values(equipped=False)
    )
    owned.equipped = True
    await session.commit()
    return {"status": "ok"}


@router.post("/unequip")
async def unequip_type(
    type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(UserCosmetic)
        .where(
            UserCosmetic.user_id == current_user.id,
            UserCosmetic.item_id.in_(
                select(CosmeticItem.id).where(CosmeticItem.type == type)
            ),
        )
        .values(equipped=False)
    )
    await session.commit()
    return {"status": "ok"}
