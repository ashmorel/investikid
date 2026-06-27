from datetime import date

import pytest
from sqlalchemy import select

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_group_config_constants():
    from app.services import group_config
    assert group_config.GROUP_SIZE_CAP == 30
    assert group_config.GROUPS_PER_PARENT_CAP == 10
    assert group_config.GROUP_CODE_LENGTH == 8
    assert "O" not in group_config.GROUP_CODE_ALPHABET
    assert "0" not in group_config.GROUP_CODE_ALPHABET


async def test_group_models_roundtrip(db_session):
    from datetime import date

    from app.models.group import GroupMembership, LeaderboardGroup
    from app.models.user import User

    g = LeaderboardGroup(name="Cousins", code="ABCD2345", owner_parent_email="p@example.com")
    db_session.add(g)
    await db_session.flush()
    u = User(username="kidg", password_hash="x", dob=date(2012, 1, 1), country_code="GB", currency_code="GBP")
    db_session.add(u)
    await db_session.flush()
    db_session.add(GroupMembership(group_id=g.id, user_id=u.id, added_by_parent_email="p@example.com"))
    await db_session.flush()

    rows = (await db_session.scalars(select(GroupMembership).where(GroupMembership.group_id == g.id))).all()
    assert len(rows) == 1
    assert rows[0].user_id == u.id


async def _mk_child(db_session, parent_email, suffix, *, handle=None, hidden=False):
    u = User(username=f"kid_{suffix}", display_handle=handle or f"H_{suffix}",
             leaderboard_hidden=hidden, password_hash="x", dob=date(2012, 1, 1),
             country_code="GB", currency_code="GBP", parent_email=parent_email)
    db_session.add(u)
    await db_session.flush()
    return u


async def test_create_group_generates_unique_code_and_enforces_cap(db_session):
    from app.services import group_config, group_service

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    assert len(g.code) == group_config.GROUP_CODE_LENGTH
    assert all(c in group_config.GROUP_CODE_ALPHABET for c in g.code)

    from app.services.group_config import GROUPS_PER_PARENT_CAP
    for i in range(GROUPS_PER_PARENT_CAP - 1):
        await group_service.create_group(db_session, "p@example.com", f"G{i}")
    with pytest.raises(group_service.GroupLimitError):
        await group_service.create_group(db_session, "p@example.com", "TooMany")


async def test_join_child_idempotent_and_capped(db_session):
    from app.models.group import GroupMembership
    from app.services import group_service

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    child = await _mk_child(db_session, "p@example.com", "a")

    await group_service.join_child(db_session, g.code, child, "p@example.com")
    await group_service.join_child(db_session, g.code, child, "p@example.com")  # idempotent
    rows = (await db_session.scalars(select(GroupMembership).where(GroupMembership.group_id == g.id))).all()
    assert len(rows) == 1


async def test_join_unknown_code_raises(db_session):
    from app.services import group_service
    child = await _mk_child(db_session, "p@example.com", "b")
    with pytest.raises(group_service.GroupNotFound):
        await group_service.join_child(db_session, "ZZZZZZZZ", child, "p@example.com")


async def test_join_then_commit_keeps_session_usable(db_session):
    from app.models.group import GroupMembership
    from app.services import group_service

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    child = await _mk_child(db_session, "p@example.com", "commit_ok")
    await group_service.join_child(db_session, g.code, child, "p@example.com")
    # If join poisoned the transaction, this commit (and re-query) would raise.
    await db_session.commit()
    rows = (await db_session.scalars(select(GroupMembership).where(GroupMembership.group_id == g.id))).all()
    assert len(rows) == 1


async def test_group_leaderboard_scopes_to_members_and_marks_me(db_session):
    from datetime import UTC, datetime

    from app.models.content import Lesson, LessonCompletion, Level, Module
    from app.services import group_service

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    a = await _mk_child(db_session, "p@example.com", "lead_a")
    b = await _mk_child(db_session, "p@example.com", "lead_b")
    outsider = await _mk_child(db_session, "p@example.com", "lead_out")
    hidden = await _mk_child(db_session, "p@example.com", "lead_hidden", hidden=True)
    await group_service.join_child(db_session, g.code, a, "p@example.com")
    await group_service.join_child(db_session, g.code, b, "p@example.com")
    await group_service.join_child(db_session, g.code, hidden, "p@example.com")

    mod = Module(title="M", topic="budgeting", icon="💰", order_index=0)
    db_session.add(mod)
    await db_session.flush()
    lvl = Level(module_id=mod.id, order_index=0, title="L1")
    db_session.add(lvl)
    await db_session.flush()
    lesson = Lesson(level_id=lvl.id, module_id=mod.id, type="card", order_index=0, xp_reward=10, content_json={})
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=a.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    db_session.add(LessonCompletion(user_id=outsider.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.flush()

    boards = await group_service.group_leaderboard_for_child(db_session, a.id)
    assert len(boards) == 1
    board = boards[0]
    assert board["group_id"] == g.id
    names = {e["username"] for e in board["entries"]}
    # Board shows the safe display_handle, never the raw username
    assert names == {a.display_handle, b.display_handle}
    assert a.username not in names and b.username not in names
    assert outsider.display_handle not in names      # non-member excluded
    assert hidden.display_handle not in names         # leaderboard_hidden honoured
    by_name = {e["username"]: e for e in board["entries"]}
    assert by_name[a.display_handle]["xp_this_week"] == 10
    assert by_name[b.display_handle]["xp_this_week"] == 0
    assert by_name[a.display_handle]["is_me"] is True
    assert by_name[b.display_handle]["is_me"] is False


async def _sign_in_parent(client, db_session, parent_email="gp@example.com", child_dob="2011-01-01"):
    from datetime import timedelta

    from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "gkid@example.com", "username": "gkid", "password": "SecurePass123!",
        "dob": child_dob, "country_code": "GB", "currency_code": "GBP", "parent_email": parent_email,
    })
    token = await issue_one_time_token(db_session, purpose=PARENT_MAGIC_AUDIENCE,
                                       email=parent_email, subject_id=None, expires_in=timedelta(minutes=15))
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")
    csrf = client.cookies.get("csrf_token")
    from app.models.user import User
    child = await db_session.scalar(select(User).where(User.username == "gkid"))
    return csrf, child.id


async def test_parent_create_and_join_own_child(client, db_session):
    csrf, child_id = await _sign_in_parent(client, db_session)
    r = await client.post("/parent/groups", json={"name": "Cousins"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 8

    r = await client.post("/parent/groups/join", json={"code": code, "child_user_id": str(child_id)},
                          headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200

    r = await client.get("/parent/groups")
    assert r.status_code == 200
    groups = r.json()
    assert any(g["name"] == "Cousins" and any(m["username"] == "gkid" for m in g["members"]) for g in groups)


async def test_parent_cannot_add_another_parents_child(client, db_session):
    csrf, _ = await _sign_in_parent(client, db_session)
    other = await _mk_child(db_session, "other@example.com", "outsider2")
    await db_session.commit()
    r = await client.post("/parent/groups", json={"name": "G"}, headers={"X-CSRF-Token": csrf})
    code = r.json()["code"]
    r = await client.post("/parent/groups/join", json={"code": code, "child_user_id": str(other.id)},
                          headers={"X-CSRF-Token": csrf})
    assert r.status_code == 404  # not this parent's child


async def test_child_group_leaderboard_endpoint(client, db_session):
    await client.post("/auth/register", json={
        "email": "teeng@example.com", "username": "teeng", "password": "SecurePass123!",
        "dob": "2010-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    from app.models.user import User
    me = await db_session.scalar(select(User).where(User.username == "teeng"))
    from app.services import group_service
    g = await group_service.create_group(db_session, "gp2@example.com", "Team")
    await group_service.join_child(db_session, g.code, me, "gp2@example.com")
    await db_session.commit()

    r = await client.get("/groups/leaderboard")
    assert r.status_code == 200
    boards = r.json()
    assert len(boards) == 1
    assert boards[0]["group_name"] == "Team"
    entries = boards[0]["entries"]
    # My row is present and flagged; the raw username is never exposed
    assert any(e["is_me"] for e in entries)
    assert all(e["username"] != "teeng" for e in entries)
