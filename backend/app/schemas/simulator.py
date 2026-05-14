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
