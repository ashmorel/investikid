from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User
from app.services import fx
from app.services.price_provider import PriceQuote


class InsufficientFundsError(Exception):
    pass


class InsufficientSharesError(Exception):
    pass


async def get_or_create_portfolio(session: AsyncSession, user: User) -> Portfolio:
    from app.services.app_settings import get_starting_cash

    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    if portfolio:
        return portfolio
    cash_map = await get_starting_cash(session)
    starting = cash_map.get(user.currency_code, Decimal("1000.00"))
    portfolio = Portfolio(user_id=user.id, virtual_cash=starting, currency_code=user.currency_code)
    session.add(portfolio)
    await session.flush()
    return portfolio


async def set_portfolio_currency(
    session: AsyncSession, user: User, new_currency: str
) -> Portfolio | None:
    user.currency_code = new_currency
    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    if portfolio is None:
        return None
    if portfolio.currency_code != new_currency:
        portfolio.virtual_cash = fx.convert(
            portfolio.virtual_cash, portfolio.currency_code, new_currency
        )
        portfolio.currency_code = new_currency
    await session.flush()
    return portfolio


async def reset_portfolio(session: AsyncSession, user: User) -> Portfolio:
    from app.services.app_settings import get_starting_cash

    portfolio = await get_or_create_portfolio(session, user)
    await session.execute(delete(Holding).where(Holding.portfolio_id == portfolio.id))
    await session.execute(delete(Trade).where(Trade.portfolio_id == portfolio.id))
    cash_map = await get_starting_cash(session)
    portfolio.virtual_cash = cash_map.get(user.currency_code, Decimal("1000.00"))
    portfolio.currency_code = user.currency_code
    await session.flush()
    return portfolio


async def _get_holding(session: AsyncSession, portfolio_id, ticker: str, exchange: str) -> Holding | None:
    return await session.scalar(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id,
            Holding.ticker == ticker,
            Holding.exchange == exchange,
        )
    )


async def execute_trade(
    session: AsyncSession,
    portfolio: Portfolio,
    quote: PriceQuote,
    trade_type: str,
    shares: Decimal,
) -> Trade:
    """Execute a buy or sell. Caller commits."""
    cost = (quote.price * shares).quantize(Decimal("0.01"))
    holding = await _get_holding(session, portfolio.id, quote.ticker, quote.exchange)

    if trade_type == "buy":
        if portfolio.virtual_cash < cost:
            raise InsufficientFundsError("Not enough virtual cash")
        portfolio.virtual_cash = portfolio.virtual_cash - cost
        if holding is None:
            holding = Holding(
                portfolio_id=portfolio.id, ticker=quote.ticker, exchange=quote.exchange,
                shares=shares, avg_buy_price=quote.price,
            )
            session.add(holding)
        else:
            total_cost = holding.avg_buy_price * holding.shares + cost
            new_shares = holding.shares + shares
            holding.avg_buy_price = (total_cost / new_shares).quantize(Decimal("0.0001"))
            holding.shares = new_shares
    elif trade_type == "sell":
        if holding is None or holding.shares < shares:
            raise InsufficientSharesError("Not enough shares to sell")
        portfolio.virtual_cash = portfolio.virtual_cash + cost
        holding.shares = holding.shares - shares
        if holding.shares == 0:
            await session.delete(holding)
    else:
        raise ValueError(f"Unknown trade type: {trade_type}")

    trade = Trade(
        portfolio_id=portfolio.id, ticker=quote.ticker, type=trade_type,
        shares=shares, price=quote.price,
    )
    session.add(trade)
    await session.flush()
    return trade
