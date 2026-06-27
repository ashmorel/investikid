import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.feedback import Feedback
from app.models.user import User
from app.routers.admin_auth import get_current_admin
from app.routers.parent_auth import get_current_parent
from app.routers.users import get_current_user
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackCreateResponse,
    FeedbackListResponse,
    FeedbackOut,
    FeedbackType,
)
from app.services.feedback_service import create_feedback, notify_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackCreateResponse, status_code=201)
@limiter.limit("5/hour")
async def submit_feedback(
    request: Request,
    payload: Annotated[FeedbackCreate, Body()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    fb = await create_feedback(
        session,
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        user_id=current_user.id,
        parent_email=None,
        submitter_role="child",
    )
    await session.commit()
    await notify_feedback(
        submitter=current_user.username,
        submitter_role="child",
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        screenshot=payload.screenshot,
    )
    return FeedbackCreateResponse(id=fb.id)


parent_feedback_router = APIRouter(prefix="/parent", tags=["parent"])


@parent_feedback_router.post(
    "/feedback", response_model=FeedbackCreateResponse, status_code=201
)
@limiter.limit("5/hour")
async def submit_parent_feedback(
    request: Request,
    payload: Annotated[FeedbackCreate, Body()],
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    fb = await create_feedback(
        session,
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        user_id=None,
        parent_email=parent_email,
        submitter_role="parent",
    )
    await session.commit()
    await notify_feedback(
        submitter=parent_email,
        submitter_role="parent",
        feedback_type=payload.feedback_type,
        message=payload.message,
        page_url=payload.page_url,
        screenshot=payload.screenshot,
    )
    return FeedbackCreateResponse(id=fb.id)


admin_router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)]
)


@admin_router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    session: AsyncSession = Depends(get_session),
    feedback_type: FeedbackType | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    base = select(Feedback)
    count_q = select(func.count()).select_from(Feedback)
    if feedback_type:
        base = base.where(Feedback.feedback_type == feedback_type)
        count_q = count_q.where(Feedback.feedback_type == feedback_type)

    total = await session.scalar(count_q) or 0

    rows = (
        await session.execute(
            base.order_by(Feedback.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    user_ids = [r.user_id for r in rows if r.user_id is not None]
    usernames: dict[uuid.UUID, str] = {}
    if user_ids:
        user_rows = (
            await session.execute(
                select(User.id, User.username).where(User.id.in_(user_ids))
            )
        ).all()
        usernames = {uid: uname for uid, uname in user_rows}

    items = [
        FeedbackOut(
            id=r.id,
            submitter=(
                usernames.get(r.user_id, "(deleted user)")
                if r.submitter_role == "child"
                else (r.parent_email or "(unknown)")
            ),
            submitter_role=r.submitter_role,
            feedback_type=r.feedback_type,
            message=r.message,
            page_url=r.page_url,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return FeedbackListResponse(items=items, total=total, page=page, per_page=per_page)
