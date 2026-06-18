from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.market import Market
from app.models.market_progress import UserMarketProgress
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.services.content_service import compute_level
from app.services.market_progress_service import ensure_enrolled

router = APIRouter(tags=["markets"])


class MarketOut(BaseModel):
    code: str
    name: str
    currency_code: str
    has_content: bool
    enrolled: bool
    is_active: bool


class SwitchMarketRequest(BaseModel):
    market_code: str


@router.get("/markets", response_model=list[MarketOut])
async def list_markets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    markets = (
        await session.scalars(
            select(Market).where(Market.is_active.is_(True)).order_by(Market.code)
        )
    ).all()
    enrolled = set(
        (
            await session.scalars(
                select(UserMarketProgress.market_code).where(
                    UserMarketProgress.user_id == current_user.id
                )
            )
        ).all()
    )
    return [
        MarketOut(
            code=m.code,
            name=m.name,
            currency_code=m.currency_code,
            has_content=m.has_content,
            enrolled=m.code in enrolled,
            is_active=m.code == current_user.active_market_code,
        )
        for m in markets
    ]


@router.post("/me/active-market")
async def switch_active_market(
    payload: SwitchMarketRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, payload.market_code)
    if market is None or not market.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown market")
    current_user.active_market_code = payload.market_code
    await ensure_enrolled(session, current_user.id, payload.market_code)
    await session.commit()
    return {"active_market_code": current_user.active_market_code}


class MarketProgressOut(BaseModel):
    market_code: str
    xp: int


class MarketsProgressEnvelope(BaseModel):
    markets: list[MarketProgressOut]
    total_xp: int
    level: int


@router.get("/me/markets", response_model=MarketsProgressEnvelope)
async def my_market_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.scalars(
            select(UserMarketProgress).where(
                UserMarketProgress.user_id == current_user.id
            )
        )
    ).all()
    progress = await session.get(UserProgress, current_user.id)
    total = progress.xp if progress else 0
    return MarketsProgressEnvelope(
        markets=[
            MarketProgressOut(market_code=r.market_code, xp=r.xp) for r in rows
        ],
        total_xp=total,
        level=compute_level(total),
    )
