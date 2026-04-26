import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.routers.parent_auth import get_current_parent
from app.schemas.parent import ChildOut, FreezeRequest

router = APIRouter(prefix="/parent", tags=["parent"])


async def _get_owned_child(
    session: AsyncSession, parent_email: str, user_id: uuid.UUID,
) -> User:
    user = await session.scalar(
        select(User).where(
            User.id == user_id,
            User.parent_email == parent_email,
        ).execution_options(include_deleted=True)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return user


@router.get("/children", response_model=list[ChildOut])
async def list_children(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(User).where(User.parent_email == parent_email)
        .execution_options(include_deleted=True)
        .order_by(User.created_at)
    )).all()
    return [
        ChildOut(
            user_id=r.id, username=r.username, country_code=r.country_code,
            is_active=r.is_active,
            parent_consent_given_at=r.parent_consent_given_at,
            consent_declined_at=r.consent_declined_at,
            deleted_at=r.deleted_at,
            deletion_requested_at=r.deletion_requested_at,
        )
        for r in rows
    ]


@router.post("/children/{user_id}/freeze")
async def freeze_child(
    user_id: uuid.UUID,
    payload: FreezeRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    child.is_active = not payload.frozen
    await session.commit()
    return {"status": "ok", "frozen": payload.frozen}


@router.post("/children/{user_id}/erasure")
async def erase_child(
    user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        return {"status": "already_deleted"}
    now = datetime.now(timezone.utc)
    child.deletion_requested_at = now
    child.deleted_at = now
    child.is_active = False
    await session.commit()
    return {"status": "ok"}
