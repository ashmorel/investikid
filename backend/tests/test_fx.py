from decimal import Decimal

from app.services import fx


def test_identity_returns_same_amount():
    assert fx.convert(Decimal("1000.00"), "USD", "USD") == Decimal("1000.00")


def test_usd_to_gbp_and_back_roundtrips_close():
    gbp = fx.convert(Decimal("1000.00"), "USD", "GBP")
    assert gbp == Decimal("787.40")
    back = fx.convert(gbp, "GBP", "USD")
    assert abs(back - Decimal("1000.00")) <= Decimal("0.01")


def test_usd_to_hkd():
    assert fx.convert(Decimal("1000.00"), "USD", "HKD") == Decimal("7812.50")


def test_unknown_currency_treated_as_usd_parity():
    assert fx.convert(Decimal("100.00"), "ZZZ", "USD") == Decimal("100.00")
