"""First-party product-analytics ingest (M4).

Accepts the small closed set of CLIENT events from authenticated children.
Unknown names / disallowed prop keys are dropped (counted), never 4xx — the
client must never break the app over analytics.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.user import User
from app.routers.users import get_current_user
from app.services import product_analytics_service
from app.services.product_analytics_service import CLIENT_EVENTS

router = APIRouter(prefix="/analytics", tags=["analytics"])

MAX_BATCH = 20


class ClientEvent(BaseModel):
    event_name: str = Field(max_length=50)
    props: dict[str, str | bool | None] | None = None


class IngestRequest(BaseModel):
    events: list[ClientEvent] = Field(min_length=1, max_length=MAX_BATCH)


class IngestResponse(BaseModel):
    accepted: int
    dropped: int


@router.post("/events", response_model=IngestResponse, status_code=202)
@limiter.limit("120/hour")
async def ingest_events(
    request: Request,
    payload: IngestRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    accepted = 0
    dropped = 0
    for event in payload.events:
        if event.event_name not in CLIENT_EVENTS:
            dropped += 1
            continue
        await product_analytics_service.record(
            session,
            event.event_name,
            user=current_user,
            role="child",
            props=event.props,
        )
        accepted += 1
    await session.commit()
    return IngestResponse(accepted=accepted, dropped=dropped)
