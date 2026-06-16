import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.revise import (
    ReviseAnswerIn,
    ReviseAnswerResult,
    ReviseModule,
    ReviseSession,
)
from app.services import revise_service

router = APIRouter(tags=["revise"])


@router.get("/revise/modules", response_model=list[ReviseModule])
async def revise_modules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await revise_service.list_revisable_modules(session, current_user)


@router.get("/revise/session", response_model=ReviseSession)
@limiter.limit("20/hour")
async def revise_session(
    request: Request,
    module_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    items = await revise_service.build_session(session, current_user, module_id=module_id)
    return {"items": items}


@router.post("/revise/answer", response_model=ReviseAnswerResult)
@limiter.limit("120/hour")
async def revise_answer(
    request: Request,
    payload: ReviseAnswerIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await revise_service.record_answer(
            session, current_user, payload.ref, payload.selected_index)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
