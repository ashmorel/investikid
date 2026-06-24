"""Limited-Edition Collectables (B1): child-facing GET /collectables endpoint.

Returns active drops with per-user progress and a list of owned drops.
A drop is a CosmeticItem with unlock_type set; active iff now is within its window.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.collectables import CollectablesResponse, DropOut, GoalOut, OwnedOut
from app.services.collectables_service import is_drop_active, progress_for

router = APIRouter(prefix="/collectables", tags=["collectables"])


@router.get("", response_model=CollectablesResponse)
async def list_collectables(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(UTC)
    progress = await session.get(UserProgress, current_user.id) or UserProgress(
        user_id=current_user.id, streak_count=0
    )
    owned_rows = {
        r.item_id: r
        for r in (
            await session.scalars(
                select(UserCosmetic).where(UserCosmetic.user_id == current_user.id)
            )
        ).all()
    }
    drops = (
        await session.scalars(
            select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None))
        )
    ).all()

    active = []
    for d in drops:
        if not is_drop_active(d, now):
            continue
        active.append(
            DropOut(
                slug=d.slug,
                name=d.name,
                emoji=d.emoji,
                type=d.type,
                rarity=d.rarity,
                ends_at=d.available_until.isoformat() if d.available_until else None,
                goal=GoalOut(
                    type=d.unlock_type,
                    threshold=d.unlock_threshold or 0,
                    current=await progress_for(session, progress, d),
                ),
                earned=d.id in owned_rows,
            )
        )
    owned = [
        OwnedOut(
            slug=d.slug,
            name=d.name,
            emoji=d.emoji,
            type=d.type,
            rarity=d.rarity,
            equipped=bool(owned_rows.get(d.id) and owned_rows[d.id].equipped),
        )
        for d in drops
        if d.id in owned_rows
    ]
    return CollectablesResponse(active=active, owned=owned)
