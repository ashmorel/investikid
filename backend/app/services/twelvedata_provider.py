"""Twelve Data market-data provider (PROTOTYPE).

Behind the ``price_provider="twelvedata"`` + ``twelvedata_api_key`` config flags.
Implements the same ``PriceProvider`` Protocol as ``LivePriceProvider`` so it
can be swapped in via the factory in ``app.routers.simulator`` without touching
any consumer.

INERT in prod until an operator sets both env vars.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

import httpx

from app.services import price_cache
from app.services.price_provider import (
    _CACHE_TTL,
    _FEATURED,
    _WARM_TTL,
    REGION_EXCHANGES,
    MarketMover,
    PricePoint,
    PriceQuote,
    TickerNotAvailableError,
    _movers_from_dict,
    _movers_to_dict,
    _normalise_currency,
    _quote_from_dict,
    _quote_to_dict,
)

logger = logging.getLogger(__name__)

_TD_BASE = "https://api.twelvedata.com"
_TD_TIMEOUT = 5.0  # seconds

# Period → outputsize mapping for /time_series (trading-day approximations).
_PERIOD_TO_OUTPUTSIZE: dict[str, int] = {
    "1d": 1,
    "5d": 5,
    "1mo": 22,
    "3mo": 65,
    "6mo": 130,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
    "max": 5000,
}

# Twelve Data uses various casings for GBp; normalise alongside yfinance's GBX.
_PENCE_CURRENCIES = {"GBp", "GBX", "GBx", "gbp_pence"}


def _td_pence(currency: str) -> bool:
    """Return True if the Twelve Data currency string indicates UK pence."""
    return currency in _PENCE_CURRENCIES


def _to_decimal2(value) -> Decimal:
    """Convert a number-like value to Decimal rounded to 2dp."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TwelveDataError(Exception):
    """API-level error returned by Twelve Data (status=='error')."""


class TwelveDataProvider:
    """Live prices from the Twelve Data REST API.

    Uses a sync ``httpx.Client`` to match the sync Protocol contract.  Cache
    behaviour mirrors ``LivePriceProvider``: L2 (Redis) first, then live fetch.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.Client(timeout=_TD_TIMEOUT)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict) -> dict:
        """GET ``endpoint`` with ``params`` + injected apikey.

        Raises ``TwelveDataError`` on API-level errors (``status=='error'``),
        ``httpx.HTTPError`` on network/transport errors.
        """
        params = {**params, "apikey": self._api_key}
        url = f"{_TD_BASE}/{endpoint.lstrip('/')}"
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("status") == "error":
            raise TwelveDataError(data.get("message", "Twelve Data API error"))
        return data

    def _fetch_quote(
        self, ticker: str, exchange: str, *, cache_ttl: int = _CACHE_TTL
    ) -> PriceQuote:
        """Fetch a live quote from /quote, apply pence conversion, write L2."""
        key = (ticker.upper(), exchange.upper())
        rkey = f"mkt:quote:{key[0]}:{key[1]}"
        featured = _FEATURED.get(key)

        try:
            data = self._get("quote", {"symbol": key[0], "exchange": key[1]})
            raw_price = float(data["close"])
            td_currency: str = data.get("currency", "")
            # Use our curated name if available; fall back to Twelve Data name.
            name = featured[0] if featured else (data.get("name") or key[0])
            our_currency = featured[2] if featured else ""
            # _normalise_currency checks for pence via GBp/GBX; Twelve Data also
            # uses these strings (confirmed in their docs) so the helper applies.
            display_currency, is_pence = _normalise_currency(td_currency, our_currency)
            if is_pence:
                raw_price = raw_price / 100
            live_price = _to_decimal2(raw_price)
        except Exception:  # noqa: BLE001
            if featured:
                logger.warning(
                    "twelvedata quote failed for %s:%s, using fallback", ticker, exchange
                )
                name, fallback_price, display_currency, _ = featured
                live_price = fallback_price
            else:
                raise TickerNotAvailableError(
                    f"{ticker} on {exchange} is not available via Twelve Data"
                )

        quote = PriceQuote(
            ticker=key[0], exchange=key[1], name=name,
            price=live_price, currency=display_currency,
        )
        price_cache.set_json(rkey, _quote_to_dict(quote), cache_ttl)
        return quote

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str, exchange: str) -> PriceQuote:
        key = (ticker.upper(), exchange.upper())
        rkey = f"mkt:quote:{key[0]}:{key[1]}"

        l2 = price_cache.get_json(rkey)
        if l2 is not None:
            return _quote_from_dict(l2)

        return self._fetch_quote(ticker, exchange)

    def get_history(
        self, ticker: str, exchange: str, period: str = "1mo"
    ) -> list[PricePoint]:
        outputsize = _PERIOD_TO_OUTPUTSIZE.get(period, 30)
        featured = _FEATURED.get((ticker.upper(), exchange.upper()))

        try:
            data = self._get(
                "time_series",
                {
                    "symbol": ticker.upper(),
                    "exchange": exchange.upper(),
                    "interval": "1day",
                    "outputsize": outputsize,
                },
            )
            values = data.get("values", [])
            # Twelve Data returns newest-first; reverse to oldest-first to match
            # LivePriceProvider's PricePoint list contract.
            points: list[PricePoint] = []
            for row in reversed(values):
                # Pence conversion for UK LSE tickers (same logic as LivePriceProvider).
                divisor = 1.0
                if featured and featured[2] == "GBP":
                    divisor = 100.0
                elif _td_pence(data.get("meta", {}).get("currency", "")):
                    divisor = 100.0

                points.append(
                    PricePoint(
                        date=str(row["datetime"])[:10],
                        open=round(float(row["open"]) / divisor, 2),
                        high=round(float(row["high"]) / divisor, 2),
                        low=round(float(row["low"]) / divisor, 2),
                        close=round(float(row["close"]) / divisor, 2),
                        volume=int(float(row.get("volume") or 0)),
                    )
                )
            return points
        except Exception:  # noqa: BLE001
            logger.warning(
                "twelvedata history failed for %s:%s period=%s", ticker, exchange, period
            )
            return []

    def search(self, query: str) -> list[PriceQuote]:
        q = query.strip()
        if not q:
            # Empty query: return featured quotes from L2 / live.
            out: list[PriceQuote] = []
            for ticker, exchange in _FEATURED:
                try:
                    out.append(self.get_quote(ticker, exchange))
                except Exception:  # noqa: BLE001
                    pass
            return out

        try:
            data = self._get(
                "symbol_search",
                {"symbol": q, "outputsize": 20},
            )
            results = data.get("data", [])
            _allowed_types = {"Common Stock", "ETF"}

            out = []
            seen: set[tuple[str, str]] = set()
            for item in results:
                if item.get("instrument_type") not in _allowed_types:
                    continue
                sym = (item.get("symbol") or "").upper()
                exch = (item.get("exchange") or "").upper()
                if not sym or not exch:
                    continue
                key = (sym, exch)
                if key in seen:
                    continue
                seen.add(key)
                # Return a PriceQuote with price=0 for search rows (consistent
                # with how LivePriceProvider handles search results where live
                # quote fetches fail — callers re-fetch on selection).
                currency = item.get("currency", "USD")
                name = item.get("instrument_name") or sym
                out.append(
                    PriceQuote(
                        ticker=sym,
                        exchange=exch,
                        name=name,
                        price=Decimal("0"),
                        currency=currency,
                    )
                )
            return out
        except Exception:  # noqa: BLE001
            logger.warning(
                "twelvedata search failed for %r, returning featured", q
            )
            # Fallback: filter featured by prefix / name match.
            qu = q.upper()
            return [
                PriceQuote(
                    ticker=t, exchange=e,
                    name=_FEATURED[(t, e)][0],
                    price=_FEATURED[(t, e)][1],
                    currency=_FEATURED[(t, e)][2],
                )
                for (t, e) in _FEATURED
                if t.startswith(qu) or qu in _FEATURED[(t, e)][0].upper()
            ]

    def get_market_movers(
        self, region: str
    ) -> dict[str, dict[str, list[MarketMover]]]:
        """Compute movers by fetching /quote for each _FEATURED ticker in the region.

        Twelve Data has no dedicated movers endpoint; we replicate
        LivePriceProvider's compute-from-featured approach using the
        ``percent_change`` field from /quote (vs previous close).
        """
        rkey = f"mkt:movers:{region}"
        l2 = price_cache.get_json(rkey)
        if l2 is not None:
            return _movers_from_dict(l2)

        return self._fetch_market_movers(region)

    def _fetch_market_movers(
        self, region: str, *, cache_ttl: int = _CACHE_TTL
    ) -> dict[str, dict[str, list[MarketMover]]]:
        rkey = f"mkt:movers:{region}"
        exchanges = REGION_EXCHANGES.get(region, [])
        featured = [
            (ticker, exchange, name, fallback_price, currency)
            for (ticker, exchange), (name, fallback_price, currency, _yf) in _FEATURED.items()
            if exchange in exchanges
        ]

        movers: list[MarketMover] = []
        for ticker, exchange, name, fallback_price, currency in featured:
            try:
                data = self._get("quote", {"symbol": ticker, "exchange": exchange})
                raw_price = float(data["close"])
                td_currency: str = data.get("currency", "")
                display_currency, is_pence = _normalise_currency(td_currency, currency)
                if is_pence:
                    raw_price = raw_price / 100
                price = _to_decimal2(raw_price)
                change_percent = float(data.get("percent_change", 0.0))
            except Exception:  # noqa: BLE001
                logger.warning(
                    "twelvedata movers quote failed for %s:%s", ticker, exchange
                )
                price = fallback_price
                display_currency = currency
                change_percent = 0.0

            movers.append(
                MarketMover(
                    ticker=ticker, exchange=exchange, name=name,
                    price=price, currency=display_currency,
                    change_percent=change_percent,
                )
            )

        result: dict[str, dict[str, list[MarketMover]]] = {}
        for exch in exchanges:
            ex_movers = [m for m in movers if m.exchange == exch]
            winners = sorted(
                [m for m in ex_movers if m.change_percent > 0],
                key=lambda m: m.change_percent,
                reverse=True,
            )[:5]
            losers = sorted(
                [m for m in ex_movers if m.change_percent < 0],
                key=lambda m: m.change_percent,
            )[:5]
            if winners or losers:
                result[exch] = {"winners": winners, "losers": losers}

        price_cache.set_json(rkey, _movers_to_dict(result), cache_ttl)
        return result

    def get_news(self, holdings: list[tuple[str, str]]) -> list:  # -> list[StockNewsItem]
        # Twelve Data does not offer a news/headlines endpoint.  News will be
        # served by a separate provider (Finnhub / Marketaux) once the split is
        # wired.  Return empty to keep the prototype honest; the default yfinance
        # provider continues to serve news until then.
        return []

    def is_free_tier(self, ticker: str, exchange: str) -> bool:
        # Mirror LivePriceProvider: all tickers are treated as free tier.
        # (LivePriceProvider.is_free_tier always returns True.)
        return True

    def warm_region(self, region: str) -> dict:
        """Pre-populate Redis L2 for the region's featured quotes + movers."""
        exchanges = REGION_EXCHANGES.get(region, [])
        featured = [(t, e) for (t, e) in _FEATURED if e in exchanges]
        for t, e in featured:
            try:
                self._fetch_quote(t, e, cache_ttl=_WARM_TTL)
            except Exception:  # noqa: BLE001
                logger.warning("twelvedata warm: quote failed for %s:%s", t, e)
        try:
            self._fetch_market_movers(region, cache_ttl=_WARM_TTL)
            movers_ok = True
        except Exception:  # noqa: BLE001
            logger.warning("twelvedata warm: movers failed for %s", region)
            movers_ok = False
        return {"region": region, "featured": len(featured), "movers": movers_ok}
