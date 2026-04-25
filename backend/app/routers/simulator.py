from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.simulator import Portfolio, Holding, Trade
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.simulator import (
    QuoteOut, PortfolioOut, HoldingOut, TradeRequest, TradeOut,
)
from app.services.gamification_service import (
    evaluate_and_award_badges, update_challenge_progress,
)
from app.services.price_provider import (
    StaticPriceProvider, TickerNotAvailableError,
)
from app.services.simulator_service import (
    get_or_create_portfolio, execute_trade,
    InsufficientFundsError, InsufficientSharesError,
)

router = APIRouter(tags=["simulator"])

_price_provider = StaticPriceProvider()


def get_price_provider():
    """Dependency so tests can override with a fake provider."""
    return _price_provider


@router.get("/market/search", response_model=list[QuoteOut])
async def search_market(
    q: str,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    results = provider.search(q)
    return [QuoteOut(ticker=r.ticker, exchange=r.exchange, name=r.name, price=r.price, currency=r.currency) for r in results]


@router.get("/market/quote/{exchange}/{ticker}", response_model=QuoteOut)
async def get_quote(
    exchange: str,
    ticker: str,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    try:
        q = provider.get_quote(ticker, exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")
    return QuoteOut(ticker=q.ticker, exchange=q.exchange, name=q.name, price=q.price, currency=q.currency)


@router.get("/portfolio", response_model=PortfolioOut)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    portfolio = await get_or_create_portfolio(session, current_user)
    await session.commit()

    holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()

    holding_out: list[HoldingOut] = []
    total_market_value = Decimal("0.00")
    for h in holdings:
        try:
            q = provider.get_quote(h.ticker, h.exchange)
            current_price = q.price
        except TickerNotAvailableError:
            current_price = h.avg_buy_price  # fall back
        market_value = (current_price * h.shares).quantize(Decimal("0.01"))
        unrealized = (market_value - (h.avg_buy_price * h.shares)).quantize(Decimal("0.01"))
        total_market_value += market_value
        holding_out.append(HoldingOut(
            ticker=h.ticker, exchange=h.exchange, shares=h.shares,
            avg_buy_price=h.avg_buy_price, current_price=current_price,
            market_value=market_value, unrealized_pl=unrealized,
        ))

    return PortfolioOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
        total_value=(portfolio.virtual_cash + total_market_value).quantize(Decimal("0.01")),
        holdings=holding_out,
    )


@router.post("/portfolio/trades", response_model=TradeOut, status_code=201)
async def place_trade(
    payload: TradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    if not current_user.is_premium and not provider.is_free_tier(payload.ticker, payload.exchange):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ticker not available on free tier")
    try:
        quote = provider.get_quote(payload.ticker, payload.exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")

    portfolio = await get_or_create_portfolio(session, current_user)

    try:
        trade = await execute_trade(session, portfolio, quote, payload.type, payload.shares)
    except InsufficientFundsError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient virtual cash")
    except InsufficientSharesError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient shares")

    # Gamification hooks
    await update_challenge_progress(session, current_user.id, "trades_executed", increment=1)
    progress = await session.get(UserProgress, current_user.id)
    if progress is None:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()
    await evaluate_and_award_badges(session, current_user.id, progress)

    await session.commit()
    await session.refresh(trade)
    return trade


@router.get("/portfolio/trades", response_model=list[TradeOut])
async def list_trades(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == current_user.id))
    if not portfolio:
        return []
    trades = (await session.scalars(
        select(Trade).where(Trade.portfolio_id == portfolio.id).order_by(Trade.executed_at.desc())
    )).all()
    return list(trades)
