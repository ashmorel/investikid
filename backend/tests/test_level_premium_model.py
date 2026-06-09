from datetime import date

import pytest

from app.core.security import hash_password
from app.models.user import User, UserProgress
from app.services.level_service import premium_for_position

_asyncio = pytest.mark.asyncio(loop_scope="session")


def test_premium_for_position():
    assert premium_for_position(0) is False
    assert premium_for_position(1) is False
    assert premium_for_position(2) is True
    assert premium_for_position(5) is True


async def _make_module(admin_client):
    r = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Premium LV Mod", "icon": "📈", "order_index": 0,
    })
    assert r.status_code == 200
    return r.json()["id"]


@_asyncio
async def test_create_level_premium_derived_from_position(admin_client):
    module_id = await _make_module(admin_client)

    # Client lies: order_index 0 with is_premium=True → forced False.
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Free L1", "order_index": 0, "is_premium": True, "pass_threshold": 0.7,
    })
    assert r.status_code == 200
    assert r.json()["is_premium"] is False

    # order_index 2 with is_premium=False → forced True.
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Premium L3", "order_index": 2, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200
    assert r.json()["is_premium"] is True


@_asyncio
async def test_update_level_premium_recomputed_from_order_index(admin_client):
    module_id = await _make_module(admin_client)
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Movable", "order_index": 1, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200 and r.json()["is_premium"] is False
    level_id = r.json()["id"]

    # Move to order_index 2 → premium, even though client sends is_premium False.
    r = await admin_client.put(f"/admin/levels/{level_id}", json={
        "order_index": 2, "is_premium": False,
    })
    assert r.status_code == 200 and r.json()["is_premium"] is True

    # Move back to order_index 0 → free, even though client sends is_premium True.
    r = await admin_client.put(f"/admin/levels/{level_id}", json={
        "order_index": 0, "is_premium": True,
    })
    assert r.status_code == 200 and r.json()["is_premium"] is False


async def _login_as(client, db_session, *, email, username, premium):
    user = User(
        email=email,
        username=username,
        password_hash=hash_password("SecurePass123!"),
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_premium=premium,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    await db_session.flush()

    r = await client.post(
        "/auth/login", json={"email": email, "password": "SecurePass123!"}
    )
    assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


@_asyncio
async def test_level3_premium_gate_end_to_end(admin_client, db_session):
    # admin_client is the shared client (logged in as admin). Build a module and
    # a Level at order_index 2 → premium by the position rule (Task 1).
    module_id = await _make_module(admin_client)
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 3", "order_index": 2, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200 and r.json()["is_premium"] is True
    level_id = r.json()["id"]

    def _find(levels):
        return next(lv for lv in levels if lv["id"] == level_id)

    # Non-premium child: the Level 3 is premium-locked.
    client = await _login_as(
        admin_client, db_session,
        email="free_child@example.com", username="freechild", premium=False,
    )
    r = await client.get(f"/modules/{module_id}/levels")
    assert r.status_code == 200
    lv = _find(r.json())
    assert lv["is_premium"] is True
    assert lv["state"] == "locked"
    assert lv["locked_reason"] == "premium"

    # Premium child: same level is NOT premium-blocked (may be progression-locked).
    client = await _login_as(
        admin_client, db_session,
        email="premium_child@example.com", username="premiumchild", premium=True,
    )
    r = await client.get(f"/modules/{module_id}/levels")
    assert r.status_code == 200
    lv = _find(r.json())
    assert lv["locked_reason"] != "premium"
