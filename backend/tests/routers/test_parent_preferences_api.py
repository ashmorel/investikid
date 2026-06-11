import pytest

from tests.routers.test_apple_billing import _csrf_headers, _setup_parent

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_get_preferences_requires_auth(client):
    client.cookies.clear()
    resp = await client.get("/parent/preferences")
    assert resp.status_code in (401, 403)


async def test_get_defaults_false_then_patch_roundtrip(client, db_session):
    await _setup_parent(
        client, db_session,
        parent_email="pref-parent@example.com",
        child_email="prefkid@example.com",
        child_username="prefkid",
    )

    got = await client.get("/parent/preferences")
    assert got.status_code == 200
    assert got.json() == {
        "trial_reminder_opt_out": False,
        "weekly_digest_opt_out": False,
    }

    patched = await client.patch(
        "/parent/preferences",
        json={"trial_reminder_opt_out": True},
        headers=_csrf_headers(client),
    )
    assert patched.status_code == 200
    assert patched.json() == {
        "trial_reminder_opt_out": True,
        "weekly_digest_opt_out": False,
    }

    again = await client.get("/parent/preferences")
    assert again.json() == {
        "trial_reminder_opt_out": True,
        "weekly_digest_opt_out": False,
    }

    off = await client.patch(
        "/parent/preferences",
        json={"trial_reminder_opt_out": False},
        headers=_csrf_headers(client),
    )
    assert off.json() == {
        "trial_reminder_opt_out": False,
        "weekly_digest_opt_out": False,
    }


async def test_weekly_digest_opt_out_patch_roundtrip(client, db_session):
    await _setup_parent(
        client, db_session,
        parent_email="digest-pref-parent@example.com",
        child_email="digestprefkid@example.com",
        child_username="digestprefkid",
    )

    # Row is created on first PATCH; only the digest field is sent.
    patched = await client.patch(
        "/parent/preferences",
        json={"weekly_digest_opt_out": True},
        headers=_csrf_headers(client),
    )
    assert patched.status_code == 200
    assert patched.json() == {
        "trial_reminder_opt_out": False,
        "weekly_digest_opt_out": True,
    }

    got = await client.get("/parent/preferences")
    assert got.json() == {
        "trial_reminder_opt_out": False,
        "weekly_digest_opt_out": True,
    }

    # Partial update of the other field must not clobber the digest opt-out.
    other = await client.patch(
        "/parent/preferences",
        json={"trial_reminder_opt_out": True},
        headers=_csrf_headers(client),
    )
    assert other.json() == {
        "trial_reminder_opt_out": True,
        "weekly_digest_opt_out": True,
    }

    back = await client.patch(
        "/parent/preferences",
        json={"weekly_digest_opt_out": False},
        headers=_csrf_headers(client),
    )
    assert back.json() == {
        "trial_reminder_opt_out": True,
        "weekly_digest_opt_out": False,
    }
