"""Admin endpoints to schedule limited-edition collectable drops (B2)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.routers.admin_auth import get_current_admin
from app.services import collectables_admin_service as svc

router = APIRouter(
    prefix="/admin/collectables",
    tags=["admin-collectables"],
    dependencies=[Depends(get_current_admin)],
)

_CONFLICT_CODES = {
    "not_drop_eligible", "already_scheduled", "not_a_drop",
    "live_locked", "ended_locked", "not_scheduled", "owned_cannot_unschedule",
}


def _raise(e: svc.AdminError) -> NoReturn:
    if e.code == "not_found":
        raise HTTPException(status.HTTP_404_NOT_FOUND, e.code)
    if e.code in _CONFLICT_CODES:
        raise HTTPException(status.HTTP_409_CONFLICT, e.code)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, e.code)


class PoolItemOut(BaseModel):
    item_id: uuid.UUID
    slug: str
    name: str
    emoji: str
    type: str


class DropOut(PoolItemOut):
    rarity: str | None
    unlock_type: str | None
    unlock_threshold: int | None
    available_from: datetime | None
    available_until: datetime | None
    status: str
    owned_count: int


class ScheduleIn(BaseModel):
    item_id: uuid.UUID
    rarity: str
    unlock_type: str
    unlock_threshold: int
    available_from: datetime
    available_until: datetime


class EditIn(BaseModel):
    rarity: str | None = None
    unlock_type: str | None = None
    unlock_threshold: int | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None


def _pool_out(item) -> PoolItemOut:
    return PoolItemOut(item_id=item.id, slug=item.slug, name=item.name, emoji=item.emoji, type=item.type)


def _drop_out(view: svc.DropView) -> DropOut:
    i = view.item
    return DropOut(
        item_id=i.id, slug=i.slug, name=i.name, emoji=i.emoji, type=i.type,
        rarity=i.rarity, unlock_type=i.unlock_type, unlock_threshold=i.unlock_threshold,
        available_from=i.available_from, available_until=i.available_until,
        status=view.status, owned_count=view.owned_count,
    )


@router.get("/pool", response_model=list[PoolItemOut])
async def get_pool(session: AsyncSession = Depends(get_session)) -> list[PoolItemOut]:
    return [_pool_out(i) for i in await svc.list_pool(session)]


@router.get("", response_model=list[DropOut])
async def get_drops(session: AsyncSession = Depends(get_session)) -> list[DropOut]:
    return [_drop_out(v) for v in await svc.list_drops(session, datetime.now(UTC))]


@router.post("", response_model=DropOut)
async def schedule(payload: ScheduleIn, session: AsyncSession = Depends(get_session)) -> DropOut:
    try:
        item = await svc.schedule_drop(
            session, item_id=payload.item_id, rarity=payload.rarity,
            unlock_type=payload.unlock_type, unlock_threshold=payload.unlock_threshold,
            available_from=payload.available_from, available_until=payload.available_until,
        )
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    return _drop_out(svc.DropView(item=item, status=svc.drop_status(item, datetime.now(UTC)),
                                  owned_count=0))


@router.patch("/{item_id}", response_model=DropOut)
async def edit(item_id: uuid.UUID, payload: EditIn, session: AsyncSession = Depends(get_session)) -> DropOut:
    now = datetime.now(UTC)
    try:
        item = await svc.edit_drop(
            session, item_id=item_id, now=now, rarity=payload.rarity,
            unlock_type=payload.unlock_type, unlock_threshold=payload.unlock_threshold,
            available_from=payload.available_from, available_until=payload.available_until,
        )
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    owned = await svc._owned_count(session, item_id)
    return _drop_out(svc.DropView(item=item, status=svc.drop_status(item, now), owned_count=owned))


@router.post("/{item_id}/unschedule", response_model=PoolItemOut)
async def unschedule(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> PoolItemOut:
    try:
        item = await svc.unschedule_drop(session, item_id=item_id, now=datetime.now(UTC))
    except svc.AdminError as e:
        _raise(e)
    await session.commit()
    return _pool_out(item)
