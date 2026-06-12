import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.audit import AuditLog
from app.models.consent import OneTimeToken
from app.models.feedback import Feedback
from app.models.group import GroupMembership, LeaderboardGroup
from app.models.parent_identity import ParentIdentity
from app.models.parent_preferences import ParentPreferences
from app.models.parent_session import ParentSession
from app.models.premium_request import PremiumRequest
from app.models.subscription import Subscription
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


async def _register_child(client, parent_email, child_email, child_username):
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email,
    })


async def _sign_in_parent(client, db_session, parent_email):
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


async def _seed_parent_data(db_session, parent_email, child_id):
    """Add the full constellation of parent-keyed rows for assertions."""
    db_session.add(ParentPreferences(parent_email=parent_email, weekly_digest_opt_out=True))
    db_session.add(ParentIdentity(
        id=uuid.uuid4(), provider="google", provider_subject=f"sub-{parent_email}",
        parent_email=parent_email, created_at=datetime.now(UTC),
    ))
    db_session.add(Subscription(parent_email=parent_email, provider="stripe", status="active"))
    db_session.add(PremiumRequest(
        child_user_id=child_id, parent_email=parent_email,
        context_kind="lesson", context_label="A lesson",
    ))
    db_session.add(Feedback(
        user_id=None, parent_email=parent_email, submitter_role="parent",
        feedback_type="bug", message="hi",
    ))
    await db_session.commit()


async def test_wrong_confirm_email_rejected(client, db_session):
    parent_email = "wrongconfirm@example.com"
    await _register_child(client, parent_email, "wc-kid@example.com", "wckid")
    await _sign_in_parent(client, db_session, parent_email)

    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": "typo@example.com"},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 400

    # Nothing deleted: the child is still present and not soft-deleted.
    child = await db_session.scalar(
        select(User).where(User.parent_email == parent_email)
        .execution_options(include_deleted=True)
    )
    assert child is not None
    assert child.deleted_at is None


async def test_delete_account_cascades(client, db_session):
    parent_email = "delete-me@example.com"
    await _register_child(client, parent_email, "dm-kid@example.com", "dmkid")
    await _sign_in_parent(client, db_session, parent_email)

    child = await db_session.scalar(
        select(User).where(User.parent_email == parent_email)
    )
    await _seed_parent_data(db_session, parent_email, child.id)

    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": "  Delete-Me@Example.com "},  # case/space-insensitive
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "children_deleted": 1}

    # Child soft-deleted.
    refreshed = await db_session.scalar(
        select(User).where(User.id == child.id).execution_options(include_deleted=True)
    )
    await db_session.refresh(refreshed)
    assert refreshed.deleted_at is not None
    assert refreshed.deletion_requested_at is not None
    assert refreshed.is_active is False

    # Hard-deleted rows gone.
    assert (await db_session.scalar(
        select(func.count(ParentSession.id)).where(ParentSession.parent_email == parent_email)
    )) == 0
    assert (await db_session.scalar(
        select(func.count(ParentIdentity.id)).where(ParentIdentity.parent_email == parent_email)
    )) == 0
    assert (await db_session.get(ParentPreferences, parent_email)) is None
    assert (await db_session.scalar(
        select(func.count(Subscription.id)).where(Subscription.parent_email == parent_email)
    )) == 0
    assert (await db_session.scalar(
        select(func.count(PremiumRequest.id)).where(PremiumRequest.parent_email == parent_email)
    )) == 0
    assert (await db_session.scalar(
        select(func.count(Feedback.id)).where(Feedback.parent_email == parent_email)
    )) == 0

    # Audit row written.
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "parent_account_deleted")
    )
    assert audit is not None

    # Session cookie cleared on the response.
    set_cookie = r.headers.get("set-cookie", "")
    assert "parent_session=" in set_cookie


async def test_delete_does_not_touch_other_parent(client, db_session):
    victim = "keep-me@example.com"
    await _register_child(client, victim, "km-kid@example.com", "kmkid")
    victim_child = await db_session.scalar(
        select(User).where(User.parent_email == victim)
    )
    await _seed_parent_data(db_session, victim, victim_child.id)

    deleter = "goodbye@example.com"
    await _register_child(client, deleter, "gb-kid@example.com", "gbkid")
    await _sign_in_parent(client, db_session, deleter)

    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": deleter},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200

    # Victim untouched.
    refreshed = await db_session.scalar(
        select(User).where(User.id == victim_child.id).execution_options(include_deleted=True)
    )
    await db_session.refresh(refreshed)
    assert refreshed.deleted_at is None
    assert (await db_session.get(ParentPreferences, victim)) is not None
    assert (await db_session.scalar(
        select(func.count(Subscription.id)).where(Subscription.parent_email == victim)
    )) == 1
    assert (await db_session.scalar(
        select(func.count(Feedback.id)).where(Feedback.parent_email == victim)
    )) == 1


async def test_delete_account_unauthenticated(client):
    client.cookies.clear()
    # x-capacitor-app marks native-app traffic, which bypasses the CSRF
    # double-submit check — so the request reaches the auth dependency and
    # fails there (401) rather than at the CSRF gate (403).
    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": "x@example.com"},
        headers={"x-capacitor-app": "1"},
    )
    assert r.status_code == 401


async def test_owned_group_deleted_other_group_untouched(client, db_session):
    # Parent who will delete: owns a group, child is a member.
    deleter = "groupowner@example.com"
    await _register_child(client, deleter, "go-kid@example.com", "gokid")
    deleter_child = await db_session.scalar(select(User).where(User.parent_email == deleter))

    owned = LeaderboardGroup(name="Mine", code="OWNEDCODE", owner_parent_email=deleter)
    db_session.add(owned)
    await db_session.flush()
    db_session.add(GroupMembership(
        group_id=owned.id, user_id=deleter_child.id, added_by_parent_email=deleter,
    ))

    # Different parent's group — must survive.
    other = LeaderboardGroup(name="Theirs", code="OTHERCODE", owner_parent_email="other@example.com")
    db_session.add(other)
    await db_session.commit()
    owned_id, other_id = owned.id, other.id

    await _sign_in_parent(client, db_session, deleter)
    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": deleter},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200

    assert (await db_session.get(LeaderboardGroup, owned_id)) is None
    assert (await db_session.scalar(
        select(func.count(GroupMembership.id)).where(GroupMembership.group_id == owned_id)
    )) == 0
    assert (await db_session.get(LeaderboardGroup, other_id)) is not None


async def test_delete_purges_magic_link_tokens(client, db_session):
    """A magic link issued just before deletion must not re-authenticate."""
    parent_email = "purge-tokens@example.com"
    await _register_child(client, parent_email, "pt-kid@example.com", "ptkid")
    await _sign_in_parent(client, db_session, parent_email)

    # A second, still-valid magic-link token issued shortly before deletion
    # that the parent has NOT yet clicked.
    pending_token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email=parent_email,
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()

    r = await client.post(
        "/parent/account/delete",
        json={"confirm_email": parent_email},
        headers=_csrf_headers(client),
    )
    assert r.status_code == 200

    # (a) No OneTimeToken rows survive for the deleted email.
    assert (await db_session.scalar(
        select(func.count(OneTimeToken.id)).where(OneTimeToken.email == parent_email)
    )) == 0

    # (b) Redeeming the pre-issued token does NOT yield a working session.
    client.cookies.clear()
    callback = await client.get(f"/parent/auth/callback?token={pending_token}")
    assert callback.status_code >= 400
    assert "parent_session" not in callback.headers.get("set-cookie", "")
