from decimal import Decimal

import pytest

from app.services.app_settings import (
    _STARTING_CASH_KEY,
    get_starting_cash,
    set_setting,
    set_starting_cash,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.parametrize("bad", ["[1, 2, 3]", '"hello"', "123", '{"GBP": "abc"}'])
async def test_malformed_setting_falls_back_to_defaults(db_session, bad):
    await set_setting(db_session, _STARTING_CASH_KEY, bad)
    cash = await get_starting_cash(db_session)  # must not raise
    assert cash["GBP"] == Decimal("1000.00")
    assert cash["HKD"] == Decimal("10000.00")


async def test_default_when_unset(db_session):
    cash = await get_starting_cash(db_session)
    assert cash["GBP"] == Decimal("1000.00")
    assert cash["HKD"] == Decimal("10000.00")


async def test_set_then_get_roundtrip(db_session):
    await set_starting_cash(db_session, {"GBP": Decimal("2000.00"), "USD": Decimal("1500.00")})
    cash = await get_starting_cash(db_session)
    assert cash["GBP"] == Decimal("2000.00")
    assert cash["USD"] == Decimal("1500.00")
    assert cash["EUR"] == Decimal("1000.00")  # default for non-overridden


async def test_admin_settings_endpoint_roundtrip(admin_client):
    put = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": [], "starting_cash": {"GBP": "1800.00"}},
    )
    assert put.status_code == 200
    assert put.json()["starting_cash"]["GBP"] == "1800.00"
    get = await admin_client.get("/admin/settings")
    assert get.json()["starting_cash"]["GBP"] == "1800.00"
