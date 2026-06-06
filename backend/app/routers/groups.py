from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.group import GroupLeaderboardEntry, GroupLeaderboardOut
from app.services.group_service import group_leaderboard_for_child

router = APIRouter(tags=["groups"])


@router.get("/groups/leaderboard", response_model=list[GroupLeaderboardOut])
async def my_group_leaderboards(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    boards = await group_leaderboard_for_child(session, current_user.id)
    return [
        GroupLeaderboardOut(
            group_id=b["group_id"],
            group_name=b["group_name"],
            entries=[GroupLeaderboardEntry(**e) for e in b["entries"]],
        )
        for b in boards
    ]
