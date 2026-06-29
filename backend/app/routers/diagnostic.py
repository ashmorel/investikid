"""Diagnostic router — child-facing assessment endpoints.

Task 2: POST /diagnostic/start — item selection + session creation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.diagnostic_session import DiagnosticStartResponse
from app.services import diagnostic_service

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.post("/start", response_model=DiagnosticStartResponse)
@limiter.limit("20/hour")
async def start_diagnostic(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DiagnosticStartResponse:
    """Select approved diagnostic items and open a DiagnosticSession.

    Returns the session id and the item list (no answer_index, no
    explanation).  On empty bank returns session with items=[].
    """
    diag_session, items = await diagnostic_service.start_diagnostic(session, user)
    await session.commit()
    return DiagnosticStartResponse(
        session_id=diag_session.id,
        items=items,
    )
