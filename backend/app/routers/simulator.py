from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.simulator import (
    HoldingOut,
    PortfolioOut,
    PortfolioSnapshot,
    PricePointOut,
    QuoteOut,
    TradeOut,
    TradeRequest,
)
from app.services.gamification_service import (
    evaluate_and_award_badges,
    update_challenge_progress,
)
from app.services.price_provider import (
    LivePriceProvider,
    TickerNotAvailableError,
)
from app.services.simulator_service import (
    InsufficientFundsError,
    InsufficientSharesError,
    execute_trade,
    get_or_create_portfolio,
)

router = APIRouter(tags=["simulator"])

_price_provider = LivePriceProvider()


def get_price_provider():
    """Dependency so tests can override with a fake provider."""
    return _price_provider


@router.get("/market/search", response_model=list[QuoteOut])
async def search_market(
    q: str,
    refresh: bool = False,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if refresh and hasattr(provider, "clear_cache"):
        provider.clear_cache()
    results = provider.search(q)
    return [
        QuoteOut(ticker=r.ticker, exchange=r.exchange, name=r.name, price=r.price, currency=r.currency)
        for r in results
    ]


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


@router.get("/market/history/{exchange}/{ticker}", response_model=list[PricePointOut])
async def get_stock_history(
    exchange: str,
    ticker: str,
    period: str = "1mo",
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_history"):
        return []
    points = provider.get_history(ticker, exchange, period)
    return [
        PricePointOut(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume)
        for p in points
    ]


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


@router.get("/portfolio/history", response_model=list[PortfolioSnapshot])
async def portfolio_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    if not portfolio:
        return []

    trades = (
        await session.scalars(
            select(Trade)
            .where(Trade.portfolio_id == portfolio.id)
            .order_by(Trade.executed_at.asc())
        )
    ).all()

    if not trades:
        return []

    # Build ticker→exchange map from holdings
    all_holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()
    ticker_exchange: dict[str, str] = {h.ticker: h.exchange for h in all_holdings}

    shares_held: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    cash = portfolio.virtual_cash
    # Reconstruct starting cash by reversing all trades
    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash += cost
        else:
            cash -= cost

    snapshots: list[PortfolioSnapshot] = []
    seen_dates: set[str] = set()

    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash -= cost
            shares_held[t.ticker] += t.shares
        else:
            cash += cost
            shares_held[t.ticker] -= t.shares

        date_str = t.executed_at.date().isoformat()
        holding_value = Decimal("0")
        for ticker, qty in shares_held.items():
            if qty <= 0:
                continue
            exchange = ticker_exchange.get(ticker, "")
            try:
                q = provider.get_quote(ticker, exchange)
                holding_value += q.price * qty
            except Exception:
                holding_value += t.price * qty

        snapshot = PortfolioSnapshot(
            date=date_str, value=float((cash + holding_value).quantize(Decimal("0.01")))
        )
        if date_str in seen_dates:
            snapshots[-1] = snapshot
        else:
            seen_dates.add(date_str)
            snapshots.append(snapshot)

    return snapshots
