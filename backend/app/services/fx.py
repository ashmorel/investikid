"""Approximate play-money FX for the simulator. Not real rates — preserves the
relative VALUE of the child's virtual cash when their practice currency changes."""
from decimal import Decimal

# USD value of one unit of each currency (moved verbatim from the simulator router).
APPROX_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "GBP": 1.27,
    "HKD": 0.128,
    "EUR": 1.08,
    "JPY": 0.0067,
    "CAD": 0.73,
    "AUD": 0.65,
}

_CENTS = Decimal("0.01")


def convert(amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
    if from_ccy == to_ccy:
        return amount.quantize(_CENTS)
    from_rate = Decimal(str(APPROX_USD_RATES.get(from_ccy, 1.0)))
    to_rate = Decimal(str(APPROX_USD_RATES.get(to_ccy, 1.0)))
    usd = amount * from_rate
    return (usd / to_rate).quantize(_CENTS)
