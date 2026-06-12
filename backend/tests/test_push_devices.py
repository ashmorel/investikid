"""Push device registry + parent master switch (M7 Task 4)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.push_device import PushDevice
from app.models.user import User
from tests.test_billing import _csrf_headers, _setup_parent
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _login_child(client, db_session, *, push_enabled: bool):
    suffix = uuid.uuid4().hex[:8]
    email = f"pd{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"pd{suffix}")
    child = await db_session.scalar(select(User).where(User.email == email))
    child.push_enabled = push_enabled
    await db_session.commit()
    return child


async def test_register_requires_parent_switch(client, db_session):
    await _login_child(client, db_session, push_enabled=False)
    r = await client.post(
        "/users/me/push-devices",
        json={"platform": "ios", "token": "tok-" + uuid.uuid4().hex},
    )
    assert r.status_code == 403


async def test_register_upserts_and_unregister_deletes(client, db_session):
    child = await _login_child(client, db_session, push_enabled=True)
    token = "tok-" + uuid.uuid4().hex

    r = await client.post(
        "/users/me/push-devices", json={"platform": "ios", "token": token}
    )
    assert r.status_code == 201
    r = await client.post(
        "/users/me/push-devices", json={"platform": "android", "token": token}
    )
    assert r.status_code == 201

    rows = (
        await db_session.execute(select(PushDevice).where(PushDevice.token == token))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].platform == "android"
    assert rows[0].user_id == child.id

    r = await client.delete(f"/users/me/push-devices/{token}")
    assert r.status_code == 200
    remaining = await db_session.scalar(
        select(PushDevice).where(PushDevice.token == token)
    )
    assert remaining is None


async def test_register_requires_auth(client):
    r = await client.post(
        "/users/me/push-devices", json={"platform": "ios", "token": "tok-anon-123"}
    )
    assert r.status_code in (401, 403)


async def test_parent_toggle_flips_child_flag(client, db_session):
    parent = f"pt{uuid.uuid4().hex[:6]}@example.com"
    child_email = f"ptk{uuid.uuid4().hex[:6]}@example.com"
    await _setup_parent(
        client, db_session, parent_email=parent,
        child_email=child_email, child_username=f"ptk{uuid.uuid4().hex[:6]}",
    )
    child = await db_session.scalar(select(User).where(User.email == child_email))
    assert child.push_enabled is False

    r = await client.post(
        f"/parent/children/{child.id}/push",
        json={"enabled": True},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "push_enabled": True}
    await db_session.refresh(child)
    assert child.push_enabled is True

    # IDOR: another parent cannot toggle this child
    other_client_email = f"px{uuid.uuid4().hex[:6]}@example.com"
    await _setup_parent(
        client, db_session, parent_email=other_client_email,
        child_email=f"pxk{uuid.uuid4().hex[:6]}@example.com",
        child_username=f"pxk{uuid.uuid4().hex[:6]}",
    )
    r = await client.post(
        f"/parent/children/{child.id}/push",
        json={"enabled": False},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 404
