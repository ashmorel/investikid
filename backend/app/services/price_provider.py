from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class TickerNotAvailableError(Exception):
    """Raised when the requested ticker is not supported for this user tier."""


@dataclass(frozen=True)
class PriceQuote:
    ticker: str
    exchange: str
    name: str
    price: Decimal
    currency: str


class PriceProvider(Protocol):
    def get_quote(self, ticker: str, exchange: str) -> PriceQuote: ...
    def search(self, query: str) -> list[PriceQuote]: ...
    def is_free_tier(self, ticker: str, exchange: str) -> bool: ...


_TICKERS: dict[tuple[str, str], tuple[str, Decimal, str]] = {
    ("AAPL", "NASDAQ"): ("Apple Inc.", Decimal("190.50"), "USD"),
    ("MSFT", "NASDAQ"): ("Microsoft Corp.", Decimal("410.25"), "USD"),
    ("GOOGL", "NASDAQ"): ("Alphabet Inc.", Decimal("145.80"), "USD"),
    ("AMZN", "NASDAQ"): ("Amazon.com Inc.", Decimal("175.10"), "USD"),
    ("TSLA", "NASDAQ"): ("Tesla Inc.", Decimal("245.00"), "USD"),
    ("NVDA", "NASDAQ"): ("NVIDIA Corp.", Decimal("525.40"), "USD"),
    ("VOD", "LSE"): ("Vodafone Group", Decimal("0.72"), "GBP"),
    ("BP", "LSE"): ("BP plc", Decimal("4.85"), "GBP"),
    ("HSBA", "LSE"): ("HSBC Holdings", Decimal("6.40"), "GBP"),
    ("TSCO", "LSE"): ("Tesco plc", Decimal("2.95"), "GBP"),
    ("0700", "HKEX"): ("Tencent Holdings", Decimal("320.00"), "HKD"),
    ("0005", "HKEX"): ("HSBC Holdings HK", Decimal("62.50"), "HKD"),
}


class StaticPriceProvider:
    """Hardcoded in-memory provider. Deterministic prices for v1."""

    def get_quote(self, ticker: str, exchange: str) -> PriceQuote:
        key = (ticker.upper(), exchange.upper())
        data = _TICKERS.get(key)
        if data is None:
            raise TickerNotAvailableError(f"{ticker} on {exchange} is not available")
        name, price, currency = data
        return PriceQuote(ticker=key[0], exchange=key[1], name=name, price=price, currency=currency)

    def search(self, query: str) -> list[PriceQuote]:
        q = query.upper().strip()
        if not q:
            return []
        out: list[PriceQuote] = []
        for (ticker, exchange), (name, price, currency) in _TICKERS.items():
            if ticker.startswith(q) or q in name.upper():
                out.append(PriceQuote(ticker=ticker, exchange=exchange, name=name, price=price, currency=currency))
        return out

    def is_free_tier(self, ticker: str, exchange: str) -> bool:
        return (ticker.upper(), exchange.upper()) in _TICKERS
