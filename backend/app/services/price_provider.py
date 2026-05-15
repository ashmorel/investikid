import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import yfinance as yf

logger = logging.getLogger(__name__)


class TickerNotAvailableError(Exception):
    """Raised when the requested ticker is not supported."""


@dataclass(frozen=True)
class PriceQuote:
    ticker: str
    exchange: str
    name: str
    price: Decimal
    currency: str


@dataclass(frozen=True)
class PricePoint:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class MarketMover:
    ticker: str
    exchange: str
    name: str
    price: Decimal
    currency: str
    change_percent: float


@dataclass(frozen=True)
class StockNewsItem:
    title: str
    summary: str
    publisher: str
    url: str
    published: str
    thumbnail: str
    related_ticker: str
    related_exchange: str


class PriceProvider(Protocol):
    def get_quote(self, ticker: str, exchange: str) -> PriceQuote: ...
    def search(self, query: str) -> list[PriceQuote]: ...
    def is_free_tier(self, ticker: str, exchange: str) -> bool: ...


# Yahoo exchange suffix → our display exchange name
_SUFFIX_TO_EXCHANGE: dict[str, str] = {
    "": "NASDAQ",
    ".L": "LSE",
    ".HK": "HKEX",
    ".T": "TSE",
    ".PA": "EPA",
    ".DE": "XETRA",
    ".AS": "AMS",
    ".TO": "TSX",
    ".AX": "ASX",
    ".SI": "SGX",
    ".SS": "SSE",
    ".SZ": "SZSE",
    ".KS": "KRX",
    ".NS": "NSE",
    ".BO": "BSE",
}

# Reverse: our exchange → Yahoo suffix
_EXCHANGE_TO_SUFFIX: dict[str, str] = {v: k for k, v in _SUFFIX_TO_EXCHANGE.items()}
# US exchanges all use no suffix
for _us in ("NYSE", "NASDAQ", "AMEX", "NMS", "NYQ", "NGM", "NCM", "PCX"):
    _EXCHANGE_TO_SUFFIX[_us] = ""

# Yahoo exchange codes → our display names
_YAHOO_EXCHANGE_MAP: dict[str, str] = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ",
    "NYQ": "NYSE", "PCX": "NYSE",
    "LSE": "LSE", "IOB": "LSE",
    "HKG": "HKEX",
    "JPX": "TSE", "TYO": "TSE",
    "PAR": "EPA",
    "GER": "XETRA", "FRA": "XETRA",
    "AMS": "AMS",
    "TOR": "TSX",
    "ASX": "ASX",
    "SES": "SGX",
    "SHH": "SSE",
    "SHZ": "SZSE",
    "KSC": "KRX", "KOE": "KRX",
    "NSI": "NSE",
    "BOM": "BSE",
}

# Featured tickers: (display_ticker, exchange) → (name, fallback_price, currency, yahoo_symbol)
_FEATURED: dict[tuple[str, str], tuple[str, Decimal, str, str]] = {
    ("AAPL", "NASDAQ"): ("Apple Inc.", Decimal("190.50"), "USD", "AAPL"),
    ("MSFT", "NASDAQ"): ("Microsoft Corp.", Decimal("410.25"), "USD", "MSFT"),
    ("GOOGL", "NASDAQ"): ("Alphabet Inc.", Decimal("145.80"), "USD", "GOOGL"),
    ("AMZN", "NASDAQ"): ("Amazon.com Inc.", Decimal("175.10"), "USD", "AMZN"),
    ("TSLA", "NASDAQ"): ("Tesla Inc.", Decimal("245.00"), "USD", "TSLA"),
    ("NVDA", "NASDAQ"): ("NVIDIA Corp.", Decimal("525.40"), "USD", "NVDA"),
    ("VOD", "LSE"): ("Vodafone Group", Decimal("0.72"), "GBP", "VOD.L"),
    ("BP", "LSE"): ("BP plc", Decimal("4.85"), "GBP", "BP.L"),
    ("HSBA", "LSE"): ("HSBC Holdings", Decimal("6.40"), "GBP", "HSBA.L"),
    ("TSCO", "LSE"): ("Tesco plc", Decimal("2.95"), "GBP", "TSCO.L"),
    ("0700", "HKEX"): ("Tencent Holdings", Decimal("320.00"), "HKD", "0700.HK"),
    ("0005", "HKEX"): ("HSBC Holdings HK", Decimal("62.50"), "HKD", "0005.HK"),
}

_CACHE_TTL = 300  # 5 minutes
_HISTORY_CACHE_TTL = 600  # 10 minutes


def _to_yahoo_symbol(ticker: str, exchange: str) -> str:
    featured = _FEATURED.get((ticker.upper(), exchange.upper()))
    if featured:
        return featured[3]
    suffix = _EXCHANGE_TO_SUFFIX.get(exchange.upper(), "")
    return f"{ticker.upper()}{suffix}"


def _normalise_currency(yf_currency: str, our_currency: str) -> tuple[str, bool]:
    """Returns (display_currency, needs_pence_conversion)."""
    if yf_currency in ("GBp", "GBX"):
        return "GBP", True
    if yf_currency in ("ILA", "ILa"):
        return "ILS", True
    return our_currency or yf_currency or "USD", False


def _parse_exchange(yahoo_exchange: str, symbol: str) -> str:
    if yahoo_exchange in _YAHOO_EXCHANGE_MAP:
        return _YAHOO_EXCHANGE_MAP[yahoo_exchange]
    for suffix, exch in _SUFFIX_TO_EXCHANGE.items():
        if suffix and symbol.endswith(suffix):
            return exch
    return yahoo_exchange or "NYSE"


class StaticPriceProvider:
    """Hardcoded in-memory provider for tests."""

    def get_quote(self, ticker: str, exchange: str) -> PriceQuote:
        key = (ticker.upper(), exchange.upper())
        data = _FEATURED.get(key)
        if data is None:
            raise TickerNotAvailableError(f"{ticker} on {exchange} is not available")
        name, fallback_price, currency, _yf = data
        return PriceQuote(ticker=key[0], exchange=key[1], name=name, price=fallback_price, currency=currency)

    def search(self, query: str) -> list[PriceQuote]:
        q = query.upper().strip()
        out: list[PriceQuote] = []
        for (ticker, exchange), (name, fallback_price, currency, _yf) in _FEATURED.items():
            if not q or ticker.startswith(q) or q in name.upper():
                out.append(
                    PriceQuote(
                        ticker=ticker, exchange=exchange, name=name,
                        price=fallback_price, currency=currency,
                    )
                )
        return out

    def is_free_tier(self, ticker: str, exchange: str) -> bool:
        return True

    def get_history(self, ticker: str, exchange: str, period: str = "1mo") -> list[PricePoint]:
        return []

    def get_market_movers(self) -> dict[str, dict[str, list[MarketMover]]]:
        return {}

    def get_news(self, holdings: list[tuple[str, str]]) -> list[StockNewsItem]:
        return []


class LivePriceProvider:
    """Fetches live prices via yfinance with an in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], tuple[PriceQuote, float]] = {}
        self._history_cache: dict[str, tuple[list[PricePoint], float]] = {}

    def clear_cache(self) -> None:
        self._cache.clear()
        self._history_cache.clear()

    def get_quote(self, ticker: str, exchange: str) -> PriceQuote:
        key = (ticker.upper(), exchange.upper())

        cached = self._cache.get(key)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

        yf_symbol = _to_yahoo_symbol(ticker, exchange)
        featured = _FEATURED.get(key)

        try:
            info = yf.Ticker(yf_symbol).fast_info
            raw_price = info["lastPrice"]
            yf_currency = str(info.get("currency", ""))
            name = featured[0] if featured else (str(info.get("shortName", "")) or ticker.upper())
            our_currency = featured[2] if featured else ""
            display_currency, pence = _normalise_currency(yf_currency, our_currency)
            if pence:
                raw_price = raw_price / 100
            live_price = Decimal(str(round(raw_price, 2)))
        except Exception:
            if featured:
                logger.warning("yfinance lookup failed for %s, using fallback", yf_symbol)
                name, fallback_price, display_currency, _ = featured
                live_price = fallback_price
            else:
                raise TickerNotAvailableError(f"{ticker} on {exchange} is not available")

        quote = PriceQuote(
            ticker=key[0], exchange=key[1], name=name,
            price=live_price, currency=display_currency,
        )
        self._cache[key] = (quote, time.monotonic())
        return quote

    def search(self, query: str) -> list[PriceQuote]:
        q = query.strip()
        if not q:
            # Empty query: return featured stocks with live prices
            out: list[PriceQuote] = []
            for (ticker, exchange) in _FEATURED:
                try:
                    out.append(self.get_quote(ticker, exchange))
                except Exception:
                    pass
            return out

        # Search Yahoo Finance for any stock
        try:
            results = yf.Search(q)
            quotes = results.quotes[:15]
        except Exception:
            logger.warning("Yahoo search failed for %r, falling back to featured", q)
            quotes = []

        seen: set[tuple[str, str]] = set()
        out = []

        for item in quotes:
            if item.get("quoteType") not in ("EQUITY", "ETF"):
                continue
            symbol = item.get("symbol", "")
            yahoo_exchange = item.get("exchange", "")
            exchange = _parse_exchange(yahoo_exchange, symbol)

            # Strip suffix to get display ticker
            display_ticker = symbol
            for suffix in sorted(_SUFFIX_TO_EXCHANGE.keys(), key=len, reverse=True):
                if suffix and symbol.endswith(suffix):
                    display_ticker = symbol[: -len(suffix)]
                    break

            key = (display_ticker.upper(), exchange)
            if key in seen:
                continue
            seen.add(key)

            try:
                quote = self.get_quote(display_ticker, exchange)
                out.append(quote)
            except Exception:
                pass

        # Also include matching featured stocks not already in results
        qu = q.upper()
        for (ticker, exchange) in _FEATURED:
            key = (ticker, exchange)
            if key in seen:
                continue
            featured_name = _FEATURED[key][0]
            if ticker.startswith(qu) or qu in featured_name.upper():
                seen.add(key)
                try:
                    out.append(self.get_quote(ticker, exchange))
                except Exception:
                    pass

        return out

    def is_free_tier(self, ticker: str, exchange: str) -> bool:
        return True

    def get_history(self, ticker: str, exchange: str, period: str = "1mo") -> list[PricePoint]:
        allowed = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
        if period not in allowed:
            period = "1mo"

        cache_key = f"{ticker}:{exchange}:{period}"
        cached = self._history_cache.get(cache_key)
        if cached and (time.monotonic() - cached[1]) < _HISTORY_CACHE_TTL:
            return cached[0]

        yf_symbol = _to_yahoo_symbol(ticker, exchange)
        featured = _FEATURED.get((ticker.upper(), exchange.upper()))

        try:
            hist = yf.Ticker(yf_symbol).history(period=period)
        except Exception:
            logger.warning("yfinance history failed for %s", yf_symbol)
            return []

        if hist.empty:
            return []

        # Check if pence conversion needed
        pence_convert = False
        if featured and featured[2] == "GBP":
            pence_convert = True
        elif not featured:
            try:
                info = yf.Ticker(yf_symbol).fast_info
                yf_currency = str(info.get("currency", ""))
                if yf_currency in ("GBp", "GBX"):
                    pence_convert = True
            except Exception:
                pass

        divisor = 100.0 if pence_convert else 1.0
        points: list[PricePoint] = []
        for dt, row in hist.iterrows():
            points.append(PricePoint(
                date=dt.strftime("%Y-%m-%d"),
                open=round(row["Open"] / divisor, 2),
                high=round(row["High"] / divisor, 2),
                low=round(row["Low"] / divisor, 2),
                close=round(row["Close"] / divisor, 2),
                volume=int(row["Volume"]),
            ))

        self._history_cache[cache_key] = (points, time.monotonic())
        return points

    def get_market_movers(self) -> dict[str, dict[str, list[MarketMover]]]:
        cache_key = "_movers"
        cached = self._history_cache.get(cache_key)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

        result: dict[str, dict[str, list[MarketMover]]] = {}

        for screener_key, label in [("day_gainers", "winners"), ("day_losers", "losers")]:
            try:
                data = yf.screen(screener_key, count=25)
                quotes = data.get("quotes", [])
            except Exception:
                logger.warning("yfinance screener %s failed", screener_key)
                continue

            by_exchange: dict[str, list[MarketMover]] = {}
            for item in quotes:
                symbol = item.get("symbol", "")
                raw_exchange = item.get("exchange", "")
                exchange = _parse_exchange(raw_exchange, symbol)
                name = item.get("shortName") or item.get("longName") or symbol
                price_val = item.get("regularMarketPrice", 0)
                change_pct = item.get("regularMarketChangePercent", 0)
                currency = item.get("currency", "USD")
                if currency in ("GBp", "GBX"):
                    price_val = price_val / 100
                    currency = "GBP"

                display_ticker = symbol
                for suffix in sorted(_SUFFIX_TO_EXCHANGE.keys(), key=len, reverse=True):
                    if suffix and symbol.endswith(suffix):
                        display_ticker = symbol[: -len(suffix)]
                        break

                mover = MarketMover(
                    ticker=display_ticker,
                    exchange=exchange,
                    name=name,
                    price=Decimal(str(round(price_val, 2))),
                    currency=currency,
                    change_percent=round(change_pct, 2),
                )
                by_exchange.setdefault(exchange, []).append(mover)

            for exchange, movers in by_exchange.items():
                result.setdefault(exchange, {})[label] = movers[:5]

        self._history_cache[cache_key] = (result, time.monotonic())
        return result

    def get_news(self, holdings: list[tuple[str, str]]) -> list[StockNewsItem]:
        cache_key = "_news:" + ",".join(f"{t}:{e}" for t, e in sorted(holdings))
        cached = self._history_cache.get(cache_key)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

        items: list[StockNewsItem] = []
        seen_titles: set[str] = set()

        for ticker, exchange in holdings:
            yf_symbol = _to_yahoo_symbol(ticker, exchange)
            try:
                news = yf.Ticker(yf_symbol).news or []
            except Exception:
                logger.warning("yfinance news failed for %s", yf_symbol)
                continue

            for article in news[:5]:
                content = article.get("content", {})
                title = content.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                thumbnail_url = ""
                thumb = content.get("thumbnail")
                if thumb and thumb.get("resolutions"):
                    thumbnail_url = thumb["resolutions"][0].get("url", "")

                provider = content.get("provider", {})
                publisher = provider.get("displayName", "") if isinstance(provider, dict) else ""
                canonical = content.get("canonicalUrl", {})
                url = canonical.get("url", "") if isinstance(canonical, dict) else ""

                items.append(StockNewsItem(
                    title=title,
                    summary=content.get("summary", "")[:200],
                    publisher=publisher,
                    url=url,
                    published=content.get("pubDate", ""),
                    thumbnail=thumbnail_url,
                    related_ticker=ticker,
                    related_exchange=exchange,
                ))

        items.sort(key=lambda x: x.published, reverse=True)
        self._history_cache[cache_key] = (items[:20], time.monotonic())
        return items[:20]
