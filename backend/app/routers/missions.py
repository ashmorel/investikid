from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.mission import ActiveMissionOut

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/active", response_model=list[ActiveMissionOut])
async def active_missions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    completed = select(ApplyMissionCompletion.mission_id).where(
        ApplyMissionCompletion.user_id == current_user.id
    )
    rows = (
        await session.execute(
            select(ApplyMission).where(ApplyMission.id.not_in(completed))
        )
    ).scalars().all()
    return rows
