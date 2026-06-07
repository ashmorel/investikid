from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_notifications_is_csrf_exempt_and_dispatches(client):
    client.cookies.clear()  # no auth, no CSRF token
    with patch("app.routers.billing.apple_billing_service.handle_notification", new=AsyncMock()) as mock:
        r = await client.post("/billing/apple/notifications", json={"signedPayload": "signed-notification"})
    assert r.status_code == 200          # NOT 403 (CSRF) — exempt like the Stripe webhook
    assert r.json()["status"] == "ok"
    mock.assert_awaited_once()


async def test_notifications_missing_payload_400(client):
    client.cookies.clear()
    r = await client.post("/billing/apple/notifications", json={})
    assert r.status_code == 400
