from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.consent import SentEmail
from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.premium import PremiumRequestIn, PremiumRequestResult
from app.services.email import get_email_sender
from app.services.premium_config import PREMIUM_BENEFITS, PREMIUM_REQUEST_COOLDOWN_HOURS

router = APIRouter(prefix="/premium", tags=["premium"])


@router.post("/request", response_model=PremiumRequestResult)
async def request_premium(
    payload: PremiumRequestIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    parent_email = current_user.parent_email
    if not parent_email:
        return PremiumRequestResult(status="no_parent")

    session.add(PremiumRequest(
        child_user_id=current_user.id, parent_email=parent_email,
        context_kind=payload.kind, context_label=payload.label,
    ))

    cutoff = datetime.now(UTC) - timedelta(hours=PREMIUM_REQUEST_COOLDOWN_HOURS)
    recent = await session.scalar(
        select(SentEmail.id).where(
            SentEmail.to_email == parent_email,
            SentEmail.template == "premium_request",
            SentEmail.sent_at > cutoff,
        ).limit(1)
    )
    if recent is not None:
        await session.commit()
        return PremiumRequestResult(status="already_sent")

    await get_email_sender().send(
        session, parent_email, "premium_request",
        {"child_username": current_user.username, "context_label": payload.label,
         "benefits": list(PREMIUM_BENEFITS)},
        subject_id=current_user.id,
    )
    await session.commit()
    return PremiumRequestResult(status="sent")
