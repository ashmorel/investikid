import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_admin_settings_roundtrip_market_bonuses(admin_client):
    r = await admin_client.get("/admin/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["market_enroll_bonus_coins"] == 25
    assert body["market_completion_bonus_coins"] == 250

    upd = await admin_client.put("/admin/settings", json={
        "alert_emails": body["alert_emails"],
        "market_enroll_bonus_coins": 40,
        "market_completion_bonus_coins": 500,
    })
    assert upd.status_code == 200
    assert upd.json()["market_enroll_bonus_coins"] == 40
    assert upd.json()["market_completion_bonus_coins"] == 500
