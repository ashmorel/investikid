import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TradeType = Literal["buy", "sell"]


class QuoteOut(BaseModel):
    ticker: str
    exchange: str
    name: str
    price: Decimal
    currency: str


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ticker: str
    exchange: str
    shares: Decimal
    avg_buy_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal


class PortfolioOut(BaseModel):
    id: uuid.UUID
    virtual_cash: Decimal
    currency_code: str
    total_value: Decimal
    holdings: list[HoldingOut]


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(min_length=1, max_length=20)
    type: TradeType
    shares: Decimal = Field(gt=Decimal("0"))


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticker: str
    type: TradeType
    shares: Decimal
    price: Decimal
    executed_at: datetime


class PortfolioSnapshot(BaseModel):
    date: str
    value: float


class PricePointOut(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketMoverOut(BaseModel):
    ticker: str
    exchange: str
    name: str
    price: Decimal
    currency: str
    change_percent: float


class ExchangeMoversOut(BaseModel):
    winners: list[MarketMoverOut] = []
    losers: list[MarketMoverOut] = []


class StockNewsOut(BaseModel):
    title: str
    summary: str
    publisher: str
    url: str
    published: str
    thumbnail: str
    related_ticker: str
    related_exchange: str


class NewsSummaryOut(BaseModel):
    summary: str
    tickers_mentioned: list[str]


class ChartCoachRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(min_length=1, max_length=20)
    period: str = Field(min_length=1, max_length=10)
    message: str = Field(min_length=1, max_length=200)
    conversation_id: uuid.UUID | None = None


class TimeMachinePeriod(BaseModel):
    years_ago: int
    invested: str
    current_value: str
    return_pct: float
    currency: str
    usd_equivalent: str | None = None


class TimeMachineOut(BaseModel):
    ticker: str
    periods: list[TimeMachinePeriod]
    fun_fact: str
