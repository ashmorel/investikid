import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User, UserProgress
from app.services.simulator_service import reset_portfolio, set_portfolio_currency

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user_with_portfolio(db_session, currency="USD"):
    user = User(
        username=f"sim_{currency.lower()}", password_hash="x",
        dob=datetime.date(2014, 1, 1),
        country_code="US", currency_code=currency, parent_email="p@example.com",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code=currency)
    db_session.add(portfolio)
    await db_session.flush()
    return user, portfolio


async def test_set_currency_converts_cash_and_preserves_holdings(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "USD")
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("2"), avg_buy_price=Decimal("100.00")))
    db_session.add(Trade(portfolio_id=portfolio.id, ticker="AAPL",
                         type="buy", shares=Decimal("2"), price=Decimal("100.00")))
    await db_session.flush()

    result = await set_portfolio_currency(db_session, user, "GBP")
    assert result is not None
    assert user.currency_code == "GBP"
    assert result.currency_code == "GBP"
    assert result.virtual_cash == Decimal("787.40")
    holdings = (await db_session.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))).all()
    trades = (await db_session.scalars(select(Trade).where(Trade.portfolio_id == portfolio.id))).all()
    assert len(holdings) == 1 and len(trades) == 1


async def test_set_currency_same_currency_is_noop_value(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "USD")
    result = await set_portfolio_currency(db_session, user, "USD")
    assert result.virtual_cash == Decimal("1000.00")
    assert result.currency_code == "USD"


async def test_set_currency_no_portfolio_returns_none_but_sets_pref(db_session):
    user = User(username="nopf", password_hash="x", dob=datetime.date(2014, 1, 1),
                country_code="US", currency_code="USD", parent_email="p@example.com", is_active=True)
    db_session.add(user)
    await db_session.flush()
    result = await set_portfolio_currency(db_session, user, "GBP")
    assert result is None
    assert user.currency_code == "GBP"


async def test_reset_clears_holdings_trades_resets_cash_preserves_progress(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "GBP")
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="VOD", exchange="LSE",
                           shares=Decimal("3"), avg_buy_price=Decimal("1.00")))
    db_session.add(Trade(portfolio_id=portfolio.id, ticker="VOD",
                         type="buy", shares=Decimal("3"), price=Decimal("1.00")))
    progress = UserProgress(user_id=user.id, xp=500, level=3, virtual_coins=42)
    db_session.add(progress)
    portfolio.virtual_cash = Decimal("10.00")
    await db_session.flush()

    result = await reset_portfolio(db_session, user)
    assert result.currency_code == "GBP"
    assert result.virtual_cash > Decimal("10.00")
    holdings = (await db_session.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))).all()
    trades = (await db_session.scalars(select(Trade).where(Trade.portfolio_id == portfolio.id))).all()
    assert holdings == [] and trades == []
    refreshed = await db_session.get(UserProgress, progress.user_id)
    assert refreshed.xp == 500 and refreshed.virtual_coins == 42
