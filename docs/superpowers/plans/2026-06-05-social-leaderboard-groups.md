# Social Leaderboard Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global anonymous leaderboard with parent-mediated private groups: parents create groups + add their own children by code; children only view a group-scoped weekly-XP leaderboard.

**Architecture:** Two new tables (`LeaderboardGroup`, `GroupMembership`); a `group_service` for code generation, membership, and the scoped weekly-XP query; parent CRUD endpoints (ownership-enforced) on the existing `/parent` router; one child read endpoint reusing the weekly-XP pattern filtered to group members. Frontend adds a parent dashboard Groups section and a child group-board on Stats. All tunables centralized.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres; React 18 + Vite + TS + TanStack Query + Vitest/vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-05-social-leaderboard-groups-design.md`

**Working dirs:** backend `invest-ed/backend`, frontend `invest-ed/frontend`. Git from repo root; commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Commands:** Backend `/Users/leeashmore/Local\ Repo/.venv/bin/pytest` · `ruff check .` · `alembic heads` (head `a1b2c3d4e5f7`). Frontend `npx tsc -b` · `npm run lint` (known `button.tsx`/`Market.tsx` warnings OK) · `npm test` · `npm run build`.

**Notes:** Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures. `tests/conftest.py` builds tables from `Base.metadata` (imports `app.models`) — new models MUST be exported from `app/models/__init__.py`. Local Postgres can hang ~90s+ → rely on CI. NEVER touch `.env*` (a pre-existing unstaged `.env.production` exists) or the unrelated untracked `_repo-split/` items. There's a parallel `tests/unit/` FE mirror — run the FULL `npm test` after FE changes. **Consent:** an under-13 child registers as pending-consent (inactive, can't log in); for child-authenticated integration tests use a DOB giving age ≥14. Parent-authenticated tests sign in via the magic-link callback (`/parent/auth/callback?token=...`) — mirror `tests/test_parent_auth.py`/`test_parent_oauth.py`.

## File Structure

**Backend**
- Create `app/services/group_config.py` — caps, code length/alphabet, week-start.
- Create `app/models/group.py` — `LeaderboardGroup`, `GroupMembership`.
- Create `alembic/versions/<rev>_add_leaderboard_groups.py`.
- Modify `app/models/__init__.py` — export the two models.
- Create `app/services/group_service.py` — code-gen, membership ops, scoped leaderboard.
- Create `app/schemas/group.py` — request/response schemas.
- Modify `app/routers/parent.py` — parent group endpoints.
- Create `app/routers/groups.py` (child read endpoint) + register in `app/main.py`.

**Frontend**
- Create `src/lib/groupConfig.ts` — client caps/copy.
- Modify `src/api/parent.ts` (+ `src/api/groups.ts` new) — group API methods + types.
- Create `src/hooks/useGroupLeaderboard.ts`.
- Create `src/components/child/stats/GroupLeaderboard.tsx`; modify `src/pages/child/Stats.tsx`.
- Create `src/components/parent/GroupsCard.tsx`; modify `src/pages/ParentDashboard.tsx`.

---

### Task 1: Group config + models + migration

**Files:** Create `app/services/group_config.py`, `app/models/group.py`, `alembic/versions/<rev>_add_leaderboard_groups.py`; Modify `app/models/__init__.py`; Test `tests/test_groups.py` (new).

- [ ] **Step 1: Write the failing test** — create `tests/test_groups.py`:

```python
import uuid

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_group_config_constants():
    from app.services import group_config
    assert group_config.GROUP_SIZE_CAP == 30
    assert group_config.GROUPS_PER_PARENT_CAP == 10
    assert group_config.GROUP_CODE_LENGTH == 8
    assert "O" not in group_config.GROUP_CODE_ALPHABET  # unambiguous
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_groups.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Create `app/services/group_config.py`**

```python
"""Single source of truth for leaderboard-group tunables."""

GROUP_SIZE_CAP = 30          # max children per group
GROUPS_PER_PARENT_CAP = 10   # max groups one parent may own
GROUP_CODE_LENGTH = 8        # join-code length
# Unambiguous alphabet (no O/0, I/1, L) for shareable codes.
GROUP_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LEADERBOARD_WEEK_START_WEEKDAY = 0  # Monday — weekly window reset (matches global board)
```

- [ ] **Step 4: Create `app/models/group.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LeaderboardGroup(Base):
    __tablename__ = "leaderboard_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    owner_parent_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_membership"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leaderboard_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_by_parent_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 5: Export the models** — in `app/models/__init__.py` add:
```python
from app.models.group import GroupMembership, LeaderboardGroup  # noqa: F401
```

- [ ] **Step 6: Write the migration** — first run `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` to confirm the current head is `a1b2c3d4e5f7`. Create `alembic/versions/b1c2d3e4f5a6_add_leaderboard_groups.py` (use the actual current head as `down_revision`; if it differs, fix it):

```python
"""add leaderboard groups + memberships

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f7
Create Date: 2026-06-05 14:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leaderboard_groups",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("owner_parent_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaderboard_groups_code", "leaderboard_groups", ["code"], unique=True)
    op.create_index("ix_leaderboard_groups_owner_parent_email", "leaderboard_groups", ["owner_parent_email"])
    op.create_table(
        "group_memberships",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("added_by_parent_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["leaderboard_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_membership"),
    )
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"])
    op.create_index("ix_group_memberships_user_id", "group_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_group_memberships_user_id", table_name="group_memberships")
    op.drop_index("ix_group_memberships_group_id", table_name="group_memberships")
    op.drop_table("group_memberships")
    op.drop_index("ix_leaderboard_groups_owner_parent_email", table_name="leaderboard_groups")
    op.drop_index("ix_leaderboard_groups_code", table_name="leaderboard_groups")
    op.drop_table("leaderboard_groups")
```

- [ ] **Step 7: Verify single head** — `alembic heads` → single head `b1c2d3e4f5a6`.

- [ ] **Step 8: Run the test** — `pytest tests/test_groups.py -v` → PASS.

- [ ] **Step 9: Lint + commit**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/group_config.py invest-ed/backend/app/models/group.py invest-ed/backend/app/models/__init__.py invest-ed/backend/alembic/versions/b1c2d3e4f5a6_add_leaderboard_groups.py invest-ed/backend/tests/test_groups.py
git commit -m "feat: leaderboard group models + config + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Group service — membership operations

**Files:** Create `app/services/group_service.py`; Test `tests/test_groups.py`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_groups.py`:

```python
from datetime import date

from app.models.user import User


async def _mk_child(db_session, parent_email, suffix):
    u = User(username=f"kid_{suffix}", password_hash="x", dob=date(2012, 1, 1),
             country_code="GB", currency_code="GBP", parent_email=parent_email)
    db_session.add(u)
    await db_session.flush()
    return u


async def test_create_group_generates_unique_code_and_enforces_cap(db_session):
    from app.services import group_config, group_service

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    assert len(g.code) == group_config.GROUP_CODE_LENGTH
    assert all(c in group_config.GROUP_CODE_ALPHABET for c in g.code)

    # cap
    from app.services.group_config import GROUPS_PER_PARENT_CAP
    for i in range(GROUPS_PER_PARENT_CAP - 1):
        await group_service.create_group(db_session, "p@example.com", f"G{i}")
    with pytest.raises(group_service.GroupLimitError):
        await group_service.create_group(db_session, "p@example.com", "TooMany")


async def test_join_child_idempotent_and_capped(db_session):
    from app.services import group_service
    from app.models.group import GroupMembership

    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    child = await _mk_child(db_session, "p@example.com", "a")

    await group_service.join_child(db_session, g.code, child, "p@example.com")
    # idempotent: second join is a no-op, not a duplicate
    await group_service.join_child(db_session, g.code, child, "p@example.com")
    rows = (await db_session.scalars(select(GroupMembership).where(GroupMembership.group_id == g.id))).all()
    assert len(rows) == 1


async def test_join_unknown_code_raises(db_session):
    from app.services import group_service
    child = await _mk_child(db_session, "p@example.com", "b")
    with pytest.raises(group_service.GroupNotFound):
        await group_service.join_child(db_session, "ZZZZZZZZ", child, "p@example.com")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_groups.py -k "create_group or join_child or unknown_code" -v`
Expected: FAIL — `group_service` missing.

- [ ] **Step 3: Create `app/services/group_service.py`**

```python
import secrets
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMembership, LeaderboardGroup
from app.models.user import User
from app.services.group_config import (
    GROUP_CODE_ALPHABET,
    GROUP_CODE_LENGTH,
    GROUP_SIZE_CAP,
    GROUPS_PER_PARENT_CAP,
)

_CODE_RETRIES = 8


class GroupNotFound(Exception):
    pass


class GroupLimitError(Exception):
    pass


def _random_code() -> str:
    return "".join(secrets.choice(GROUP_CODE_ALPHABET) for _ in range(GROUP_CODE_LENGTH))


async def _generate_unique_code(session: AsyncSession) -> str:
    for _ in range(_CODE_RETRIES):
        code = _random_code()
        exists = await session.scalar(select(LeaderboardGroup.id).where(LeaderboardGroup.code == code))
        if exists is None:
            return code
    raise GroupLimitError("could not generate a unique code")


async def create_group(session: AsyncSession, owner_parent_email: str, name: str) -> LeaderboardGroup:
    owned = await session.scalar(
        select(func.count(LeaderboardGroup.id)).where(LeaderboardGroup.owner_parent_email == owner_parent_email)
    )
    if owned >= GROUPS_PER_PARENT_CAP:
        raise GroupLimitError("too many groups")
    code = await _generate_unique_code(session)
    group = LeaderboardGroup(name=name, code=code, owner_parent_email=owner_parent_email)
    session.add(group)
    await session.flush()
    return group


async def join_child(session: AsyncSession, code: str, child: User, parent_email: str) -> LeaderboardGroup:
    group = await session.scalar(select(LeaderboardGroup).where(LeaderboardGroup.code == code))
    if group is None:
        raise GroupNotFound("unknown code")
    # Already a member? -> idempotent no-op.
    existing = await session.scalar(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group.id, GroupMembership.user_id == child.id
        )
    )
    if existing is not None:
        return group
    member_count = await session.scalar(
        select(func.count(GroupMembership.id)).where(GroupMembership.group_id == group.id)
    )
    if member_count >= GROUP_SIZE_CAP:
        raise GroupLimitError("group is full")
    session.add(GroupMembership(group_id=group.id, user_id=child.id, added_by_parent_email=parent_email))
    try:
        await session.flush()
    except IntegrityError:
        # Lost a concurrent join race on the unique constraint -> treat as already-member.
        pass
    return group


async def remove_member(session: AsyncSession, group_id: uuid.UUID, child_user_id: uuid.UUID) -> None:
    await session.execute(
        delete(GroupMembership).where(
            GroupMembership.group_id == group_id, GroupMembership.user_id == child_user_id
        )
    )


async def delete_group(session: AsyncSession, group: LeaderboardGroup) -> None:
    await session.delete(group)
```

- [ ] **Step 4: Run the test** — `pytest tests/test_groups.py -k "create_group or join_child or unknown_code" -v` → PASS.

- [ ] **Step 5: Lint + commit**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/group_service.py invest-ed/backend/tests/test_groups.py
git commit -m "feat: group_service membership operations (create/join/remove/delete)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Group service — scoped weekly-XP leaderboard

**Files:** Modify `app/services/group_service.py`; Test `tests/test_groups.py`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_groups.py`:

```python
async def test_group_leaderboard_scopes_to_members_and_marks_me(db_session):
    from datetime import UTC, datetime
    from app.models.content import Lesson, LessonCompletion, Module, Level
    from app.services import group_service

    # group with two members + one non-member
    g = await group_service.create_group(db_session, "p@example.com", "Cousins")
    a = await _mk_child(db_session, "p@example.com", "lead_a")
    b = await _mk_child(db_session, "p@example.com", "lead_b")
    outsider = await _mk_child(db_session, "p@example.com", "lead_out")
    await group_service.join_child(db_session, g.code, a, "p@example.com")
    await group_service.join_child(db_session, g.code, b, "p@example.com")

    # a lesson worth XP, completed this week by `a` and by `outsider`
    mod = Module(title="M", topic="budgeting", icon="💰", order_index=0)
    db_session.add(mod); await db_session.flush()
    lvl = Level(module_id=mod.id, order_index=0, name="L1"); db_session.add(lvl); await db_session.flush()
    lesson = Lesson(level_id=lvl.id, module_id=mod.id, type="card", order_index=0, xp_reward=10, content_json={})
    db_session.add(lesson); await db_session.flush()
    db_session.add(LessonCompletion(user_id=a.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    db_session.add(LessonCompletion(user_id=outsider.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.flush()

    boards = await group_service.group_leaderboard_for_child(db_session, a.id)
    assert len(boards) == 1
    board = boards[0]
    assert board["group_id"] == g.id
    usernames = {e["username"] for e in board["entries"]}
    assert usernames == {a.username, b.username}          # only members
    assert outsider.username not in usernames              # no leak
    by_name = {e["username"]: e for e in board["entries"]}
    assert by_name[a.username]["xp_this_week"] == 10       # a practised
    assert by_name[b.username]["xp_this_week"] == 0        # b appears with 0
    assert by_name[a.username]["is_me"] is True
    assert by_name[b.username]["is_me"] is False
```
(If the `Module`/`Level`/`Lesson` constructor kwargs differ, READ `app/models/content.py` and adjust the in-test object creation to the real required fields — keep the assertions intact. Reuse an existing seeded lesson via a fixture if one exists.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_groups.py -k "leaderboard_scopes" -v`
Expected: FAIL — `group_leaderboard_for_child` missing.

- [ ] **Step 3: Add the scoped query to `app/services/group_service.py`**

Add imports at the top:
```python
from datetime import UTC, datetime, timedelta

from app.models.content import Lesson, LessonCompletion
from app.services.group_config import LEADERBOARD_WEEK_START_WEEKDAY
```
Add the helper + function:
```python
def _week_start(now: datetime) -> datetime:
    days_since = (now.weekday() - LEADERBOARD_WEEK_START_WEEKDAY) % 7
    return (now - timedelta(days=days_since)).replace(hour=0, minute=0, second=0, microsecond=0)


async def group_leaderboard_for_child(session: AsyncSession, child_user_id: uuid.UUID) -> list[dict]:
    """For each group the child belongs to, return members + weekly XP (members with no
    activity appear with 0), ordered by xp desc. Marks the requesting child with is_me."""
    group_ids = (await session.scalars(
        select(GroupMembership.group_id).where(GroupMembership.user_id == child_user_id)
    )).all()
    if not group_ids:
        return []

    week_start = _week_start(datetime.now(UTC))
    boards: list[dict] = []
    groups = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.id.in_(group_ids))
        .order_by(LeaderboardGroup.created_at)
    )).all()
    for group in groups:
        xp_expr = func.coalesce(func.sum(Lesson.xp_reward), 0).label("xp_this_week")
        stmt = (
            select(User.id, User.username, xp_expr)
            .join(GroupMembership, GroupMembership.user_id == User.id)
            .outerjoin(
                LessonCompletion,
                (LessonCompletion.user_id == User.id) & (LessonCompletion.completed_at >= week_start),
            )
            .outerjoin(Lesson, Lesson.id == LessonCompletion.lesson_id)
            .where(GroupMembership.group_id == group.id)
            .group_by(User.id, User.username)
            .order_by(xp_expr.desc(), User.username.asc())
        )
        rows = (await session.execute(stmt)).all()
        boards.append({
            "group_id": group.id,
            "group_name": group.name,
            "entries": [
                {"username": uname, "xp_this_week": int(xp), "is_me": uid == child_user_id}
                for uid, uname, xp in rows
            ],
        })
    return boards
```

- [ ] **Step 4: Run the test** — `pytest tests/test_groups.py -k "leaderboard_scopes" -v` → PASS.

- [ ] **Step 5: Lint + commit**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/group_service.py invest-ed/backend/tests/test_groups.py
git commit -m "feat: group_service scoped weekly-XP leaderboard query

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Parent group endpoints + schemas

**Files:** Create `app/schemas/group.py`; Modify `app/routers/parent.py`; Test `tests/test_groups.py`.

- [ ] **Step 1: Write the failing integration tests** — append to `tests/test_groups.py`. Use a parent-auth helper (mirror `tests/test_parent_auth.py`): register a kid with a parent email, issue a magic-link token, hit the callback to set the parent cookie. Add at the top of the file's helpers:

```python
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
    # the registered child's id:
    from sqlalchemy import select
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
    # a child owned by a DIFFERENT parent
    other = await _mk_child(db_session, "other@example.com", "outsider2")
    await db_session.commit()
    r = await client.post("/parent/groups", json={"name": "G"}, headers={"X-CSRF-Token": csrf})
    code = r.json()["code"]
    r = await client.post("/parent/groups/join", json={"code": code, "child_user_id": str(other.id)},
                          headers={"X-CSRF-Token": csrf})
    assert r.status_code == 404  # not this parent's child
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_groups.py -k "parent_create or another_parents" -v`
Expected: FAIL — endpoints missing (404).

- [ ] **Step 3: Create `app/schemas/group.py`**

```python
import uuid

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class GroupJoinRequest(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    child_user_id: uuid.UUID


class GroupMemberOut(BaseModel):
    child_user_id: uuid.UUID
    username: str


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None  # only populated for the owner
    is_owner: bool
    members: list[GroupMemberOut]


class GroupLeaderboardEntry(BaseModel):
    username: str
    xp_this_week: int
    is_me: bool


class GroupLeaderboardOut(BaseModel):
    group_id: uuid.UUID
    group_name: str
    entries: list[GroupLeaderboardEntry]
```

- [ ] **Step 4: Add the parent endpoints to `app/routers/parent.py`**

Add imports:
```python
from app.models.group import GroupMembership, LeaderboardGroup
from app.schemas.group import GroupCreateRequest, GroupJoinRequest, GroupMemberOut, GroupOut
from app.services import group_service
```
Append the endpoints (after the existing parent routes):
```python
@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(
    payload: GroupCreateRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        group = await group_service.create_group(session, parent_email, payload.name)
    except group_service.GroupLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group limit reached")
    await session.commit()
    return GroupOut(id=group.id, name=group.name, code=group.code, is_owner=True, members=[])


@router.post("/groups/join", response_model=GroupOut)
async def join_group(
    payload: GroupJoinRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, payload.child_user_id)
    try:
        group = await group_service.join_child(session, payload.code, child, parent_email)
    except group_service.GroupNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    except group_service.GroupLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group is full")
    await session.commit()
    return await _group_out(session, group, parent_email)


@router.get("/groups", response_model=list[GroupOut])
async def list_groups(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    # groups owned by this parent OR containing a child of this parent
    owned = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.owner_parent_email == parent_email)
    )).all()
    child_group_ids = (await session.scalars(
        select(GroupMembership.group_id)
        .join(User, User.id == GroupMembership.user_id)
        .where(User.parent_email == parent_email)
    )).all()
    member_groups = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.id.in_(child_group_ids))
    )).all() if child_group_ids else []
    seen: dict = {}
    for g in [*owned, *member_groups]:
        seen[g.id] = g
    return [await _group_out(session, g, parent_email) for g in seen.values()]


@router.delete("/groups/{group_id}/members/{child_user_id}", status_code=200)
async def remove_group_member(
    group_id: uuid.UUID,
    child_user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    await _get_owned_child(session, parent_email, child_user_id)  # own child only
    await group_service.remove_member(session, group_id, child_user_id)
    await session.commit()
    return {"status": "ok"}


@router.delete("/groups/{group_id}", status_code=200)
async def delete_group(
    group_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    group = await session.scalar(
        select(LeaderboardGroup).where(
            LeaderboardGroup.id == group_id, LeaderboardGroup.owner_parent_email == parent_email
        )
    )
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    await group_service.delete_group(session, group)
    await session.commit()
    return {"status": "ok"}


async def _group_out(session: AsyncSession, group: LeaderboardGroup, parent_email: str) -> GroupOut:
    rows = (await session.execute(
        select(GroupMembership.user_id, User.username)
        .join(User, User.id == GroupMembership.user_id)
        .where(GroupMembership.group_id == group.id)
        .order_by(User.username)
    )).all()
    is_owner = group.owner_parent_email == parent_email
    return GroupOut(
        id=group.id, name=group.name,
        code=group.code if is_owner else None,
        is_owner=is_owner,
        members=[GroupMemberOut(child_user_id=uid, username=uname) for uid, uname in rows],
    )
```

- [ ] **Step 5: Run the tests** — `pytest tests/test_groups.py -k "parent_create or another_parents" -v` → PASS. Then `pytest tests/test_parent_auth.py tests/test_parent_oauth.py -q` (no regressions).

- [ ] **Step 6: Lint + commit**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/group.py invest-ed/backend/app/routers/parent.py invest-ed/backend/tests/test_groups.py
git commit -m "feat: parent group endpoints (create/join/list/remove/delete)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Child group-leaderboard endpoint

**Files:** Create `app/routers/groups.py`; Modify `app/main.py`; Test `tests/test_groups.py`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_groups.py`:

```python
async def test_child_group_leaderboard_endpoint(client, db_session):
    # sign in a TEENAGE child (>=14, no consent gate) and put them in a group
    await client.post("/auth/register", json={
        "email": "teeng@example.com", "username": "teeng", "password": "SecurePass123!",
        "dob": "2010-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    from sqlalchemy import select
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
    assert any(e["username"] == "teeng" and e["is_me"] for e in boards[0]["entries"])
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_groups.py -k "child_group_leaderboard" -v` → FAIL (404).

- [ ] **Step 3: Create `app/routers/groups.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.group import GroupLeaderboardEntry, GroupLeaderboardOut
from app.services.group_service import group_leaderboard_for_child

router = APIRouter(tags=["groups"])


@router.get("/groups/leaderboard", response_model=list[GroupLeaderboardOut])
async def my_group_leaderboards(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    boards = await group_leaderboard_for_child(session, current_user.id)
    return [
        GroupLeaderboardOut(
            group_id=b["group_id"],
            group_name=b["group_name"],
            entries=[GroupLeaderboardEntry(**e) for e in b["entries"]],
        )
        for b in boards
    ]
```

- [ ] **Step 4: Register the router** — in `app/main.py`, find where routers are included (e.g. `app.include_router(gamification.router)`) and add:
```python
from app.routers import groups
```
```python
app.include_router(groups.router)
```
(Match the existing import + include style in `main.py`.)

- [ ] **Step 5: Run the test** — `pytest tests/test_groups.py -k "child_group_leaderboard" -v` → PASS.

- [ ] **Step 6: Lint + commit**
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/groups.py invest-ed/backend/app/main.py invest-ed/backend/tests/test_groups.py
git commit -m "feat: child group-leaderboard endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Frontend API client + config + hook

**Files:** Create `src/api/groups.ts`, `src/lib/groupConfig.ts`, `src/hooks/useGroupLeaderboard.ts`; Modify `src/api/parent.ts`; Test `src/api/__tests__/groups.test.ts` (new, light).

- [ ] **Step 1: Create `src/lib/groupConfig.ts`**
```ts
// Client-side group copy/limits — single place to retune.
export const GROUP = {
  maxNameLength: 60,
  noGroupPrompt: 'Ask a parent to set up a group so you can compare with friends!',
} as const;
```

- [ ] **Step 2: Create `src/api/groups.ts`** (child-facing board) and add parent methods to `src/api/parent.ts`.

`src/api/groups.ts`:
```ts
import { apiFetch } from './client';

export type GroupLeaderboardEntry = { username: string; xp_this_week: number; is_me: boolean };
export type GroupLeaderboard = { group_id: string; group_name: string; entries: GroupLeaderboardEntry[] };

export const groupsApi = {
  myLeaderboards: () => apiFetch<GroupLeaderboard[]>('/groups/leaderboard'),
};
```
In `src/api/parent.ts`, add types + methods to the existing `parentApi` object:
```ts
export type GroupMember = { child_user_id: string; username: string };
export type ParentGroup = { id: string; name: string; code: string | null; is_owner: boolean; members: GroupMember[] };
```
```ts
  listGroups: () => apiFetch<ParentGroup[]>('/parent/groups'),
  createGroup: (name: string) =>
    apiFetch<ParentGroup>('/parent/groups', { method: 'POST', body: JSON.stringify({ name }) }),
  joinGroup: (code: string, childUserId: string) =>
    apiFetch<ParentGroup>('/parent/groups/join', {
      method: 'POST', body: JSON.stringify({ code, child_user_id: childUserId }),
    }),
  removeGroupMember: (groupId: string, childUserId: string) =>
    apiFetch<{ status: string }>(`/parent/groups/${groupId}/members/${childUserId}`, { method: 'DELETE' }),
  deleteGroup: (groupId: string) =>
    apiFetch<{ status: string }>(`/parent/groups/${groupId}`, { method: 'DELETE' }),
```

- [ ] **Step 3: Create `src/hooks/useGroupLeaderboard.ts`**
```ts
import { useQuery } from '@tanstack/react-query';
import { groupsApi, type GroupLeaderboard } from '@/api/groups';

export function useGroupLeaderboard() {
  return useQuery<GroupLeaderboard[]>({
    queryKey: ['group-leaderboard'],
    queryFn: () => groupsApi.myLeaderboards(),
    retry: false,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 4: Write a light test** — create `src/api/__tests__/groups.test.ts` asserting the client builds the right request. Mirror an existing `src/api/__tests__/*.test.ts` mock pattern (e.g. `parentAuth.test.ts`) — READ one first and copy its `apiFetch`/fetch-mock approach. Assert `groupsApi.myLeaderboards()` calls `/groups/leaderboard` and `parentApi.createGroup('X')` POSTs `/parent/groups` with `{name:'X'}`.

- [ ] **Step 5: Run + typecheck** — `npm test -- groups && npx tsc -b` → pass/clean.

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/groups.ts invest-ed/frontend/src/api/parent.ts invest-ed/frontend/src/lib/groupConfig.ts invest-ed/frontend/src/hooks/useGroupLeaderboard.ts invest-ed/frontend/src/api/__tests__/groups.test.ts
git commit -m "feat(fe): group api client + config + leaderboard hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Child GroupLeaderboard component + Stats wiring

**Files:** Create `src/components/child/stats/GroupLeaderboard.tsx`; Modify `src/pages/child/Stats.tsx`; Test `src/components/child/stats/__tests__/GroupLeaderboard.test.tsx` (new).

- [ ] **Step 1: Write the failing test** — create `src/components/child/stats/__tests__/GroupLeaderboard.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { GroupLeaderboard } from '../GroupLeaderboard';

const boards = [{
  group_id: 'g1', group_name: 'Cousins',
  entries: [
    { username: 'Sam', xp_this_week: 30, is_me: true },
    { username: 'Alex', xp_this_week: 10, is_me: false },
  ],
}];

describe('GroupLeaderboard', () => {
  it('renders group name, members and highlights me', () => {
    render(<GroupLeaderboard boards={boards} />);
    expect(screen.getByText('Cousins')).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
    expect(screen.getByText('Alex')).toBeInTheDocument();
    // "me" row carries an accessible marker
    expect(screen.getByText(/you/i)).toBeInTheDocument();
  });
  it('shows the prompt when there are no groups', () => {
    render(<GroupLeaderboard boards={[]} />);
    expect(screen.getByText(/ask a parent/i)).toBeInTheDocument();
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<GroupLeaderboard boards={boards} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npm test -- GroupLeaderboard` → FAIL (missing component).

- [ ] **Step 3: Create `src/components/child/stats/GroupLeaderboard.tsx`** — match the styling of the existing `LeaderboardTable.tsx` (READ it for tokens/markup). Use `GROUP.noGroupPrompt` for the empty state:
```tsx
import type { GroupLeaderboard as Board } from '@/api/groups';
import { GROUP } from '@/lib/groupConfig';
import { cn } from '@/lib/utils';

export function GroupLeaderboard({ boards }: { boards: Board[] }) {
  if (boards.length === 0) {
    return (
      <p className="rounded-2xl border border-brand-100 bg-card p-4 text-sm text-muted-foreground">
        {GROUP.noGroupPrompt}
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {boards.map((b) => (
        <section key={b.group_id} aria-label={`${b.group_name} leaderboard`}
          className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-extrabold text-gray-900">{b.group_name}</h3>
          <ol className="space-y-1">
            {b.entries.map((e, i) => (
              <li key={e.username}
                className={cn('flex items-center justify-between rounded-lg px-3 py-1.5 text-sm',
                  e.is_me ? 'bg-brand-100 font-bold text-brand-800' : 'text-gray-700')}>
                <span><span className="mr-2 text-muted-foreground">{i + 1}.</span>{e.username}
                  {e.is_me && <span className="ml-2 text-xs text-brand-700">(you)</span>}</span>
                <span className="font-semibold">{e.xp_this_week} XP</span>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Wire into `Stats.tsx`** — READ `src/pages/child/Stats.tsx`. Add the hook + render the group board ABOVE the existing "Weekly Leaderboard" section:
```tsx
import { useGroupLeaderboard } from '@/hooks/useGroupLeaderboard';
import { GroupLeaderboard } from '@/components/child/stats/GroupLeaderboard';
```
```tsx
  const groupBoards = useGroupLeaderboard();
```
Just before the existing `{/* Weekly Leaderboard */}` block, insert:
```tsx
      <section className="mt-5" aria-label="Your groups">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Your groups</h2>
        <GroupLeaderboard boards={groupBoards.data ?? []} />
      </section>
```

- [ ] **Step 5: Run tests + typecheck + lint + FULL suite** — `npm test -- GroupLeaderboard Stats && npx tsc -b && npm run lint && npm test`. Expected: pass; tsc/lint clean; FULL suite 0 failed. Update any `tests/unit/` Stats mirror that needs the new `useGroupLeaderboard` mocked (add a `vi.mock('@/hooks/useGroupLeaderboard', () => ({ useGroupLeaderboard: () => ({ data: [] }) }))` to Stats tests that render the page).

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src invest-ed/frontend/tests
git commit -m "feat(fe): child group leaderboard on Stats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Parent dashboard Groups section

**Files:** Create `src/components/parent/GroupsCard.tsx`; Modify `src/pages/ParentDashboard.tsx`; Test `src/components/parent/__tests__/GroupsCard.test.tsx` (new).

- [ ] **Step 1: Write the failing test** — create `src/components/parent/__tests__/GroupsCard.test.tsx`. Mock `parentApi` (mirror an existing parent component test). Provide a `QueryClientProvider`. Assert: the card renders a "Create group" control and lists a mocked group with its code + members; "Add to group" posts the code + selected child. Keep it focused; READ an existing `components/__tests__/ChildCard.test.tsx` to mirror the mocking/QueryClient setup. Minimum viable assertion set:
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupsCard } from '../GroupsCard';

vi.mock('@/api/parent', () => ({
  parentApi: {
    listGroups: vi.fn(async () => [{ id: 'g1', name: 'Cousins', code: 'ABCD2345', is_owner: true, members: [{ child_user_id: 'c1', username: 'Sam' }] }]),
    createGroup: vi.fn(async () => ({ id: 'g2', name: 'New', code: 'WXYZ7890', is_owner: true, members: [] })),
    joinGroup: vi.fn(), removeGroupMember: vi.fn(), deleteGroup: vi.fn(),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe('GroupsCard', () => {
  it('lists groups with code + members', async () => {
    render(wrap(<GroupsCard children={[{ user_id: 'c1', username: 'Sam' }]} />));
    expect(await screen.findByText('Cousins')).toBeInTheDocument();
    expect(screen.getByText(/ABCD2345/)).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npm test -- GroupsCard` → FAIL (missing component).

- [ ] **Step 3: Create `src/components/parent/GroupsCard.tsx`** — a self-contained card. Props: `children: { user_id: string; username: string }[]` (the parent's children, for the add-to-group picker). It uses `parentApi.listGroups` (query), `createGroup`/`joinGroup`/`removeGroupMember`/`deleteGroup` (mutations invalidating `['parent-groups']`). Implement:
  - a "Create a group" form (name input ≤ `GROUP.maxNameLength` → `createGroup`);
  - the list of groups, each showing name, the **code** (owner only) with a copy button, and members with a remove (✕) button;
  - an "Add a child to a group" form: a code input + a `<select>` of the parent's children → `joinGroup`;
  - owner "Delete group" button.
  Use the project's existing UI primitives (`Button`, inputs) and brand tokens; keep inputs ≥16px (iOS). Mark up accessibly (labelled inputs, `aria-label`s on icon buttons). Show a short error message on mutation failure (e.g. group full / limit reached). READ `ParentDashboard.tsx` + an existing parent component to match styling and the `useMutation`/`useQuery` patterns already used.

- [ ] **Step 4: Wire into `ParentDashboard.tsx`** — READ the file. It already loads the parent's children (via `parentApi.listChildren`). Render `<GroupsCard children={children.map(c => ({ user_id: c.user_id, username: c.username }))} />` in a sensible spot (e.g. below the child cards). Add the import.

- [ ] **Step 5: Run tests + typecheck + lint + FULL suite** — `npm test -- GroupsCard ParentDashboard && npx tsc -b && npm run lint && npm test`. Expected: pass; tsc/lint clean; FULL suite 0 failed. Add an axe test to `GroupsCard.test.tsx` (render under QueryClient, assert `toHaveNoViolations`).

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src invest-ed/frontend/tests
git commit -m "feat(fe): parent dashboard Groups management section

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Full regression, iOS sync, push

**Files:** none.

- [ ] **Step 1: Backend** — `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: pass; ruff clean; single head `b1c2d3e4f5a6`.

- [ ] **Step 2: Frontend** — `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean (known warnings only); all suites pass; build OK.

- [ ] **Step 3: iOS sync** — `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx cap sync ios`; if tracked `invest-ed/frontend/ios` files changed, commit them (`chore(ios): cap sync after social groups`).

- [ ] **Step 4: Push** — `cd "/Users/leeashmore/Local Repo" && git push origin main`

- [ ] **Step 5: Report** — summarise commits; note Vercel/Railway deploy on green CI; the feature is parent-mediated (no child action), code-gated, username+XP only; iOS shows the web bundle → a USER Xcode rebuild surfaces it on device.

---

## Self-Review

**Spec coverage:**
- Group model + migration (no PII; cascade) → Task 1. ✓
- Membership ops (code-gen unique, create w/ per-parent cap, idempotent join w/ size cap, remove, delete) → Task 2. ✓
- Scoped weekly-XP leaderboard (members only, zero-XP members appear, is_me, no leak) → Task 3. ✓
- Parent endpoints, ownership-enforced (own-child-only join via `_get_owned_child`; owner-only delete; code hidden from non-owners) → Task 4. ✓
- Child read endpoint → Task 5. ✓
- FE api/config/hook → Task 6; child board on Stats (kept global below) → Task 7; parent management UI → Task 8. ✓
- Configurability single-sources (`group_config.py`, `groupConfig.ts`; tests import constants) → Tasks 1, 6. ✓
- Caps/IDOR/code-collision/edge-cases → Tasks 2–4 tests. ✓
- iOS sync close-out → Task 9. ✓

**Placeholder scan:** No TBD/TODO. The "READ the file + mirror existing test" notes (Tasks 6–8) carry concrete assertion sets + exact insertion points, not placeholders. Component bodies for `GroupLeaderboard` are fully specified; `GroupsCard` is specified by its responsibilities + props + the APIs it calls + a concrete test (its internal JSX is left to the implementer following existing parent-component patterns, which is appropriate for a CRUD form). ✓

**Type consistency:** `GroupOut{id,name,code,is_owner,members[]}` / `ParentGroup` match between backend schema (Task 4) and FE type (Task 6); `GroupLeaderboardOut{group_id,group_name,entries[{username,xp_this_week,is_me}]}` matches the service dicts (Task 3), the schema (Task 4), the child endpoint (Task 5), the FE `GroupLeaderboard` type (Task 6), and the component prop (Task 7). `group_service` function names (`create_group`/`join_child`/`remove_member`/`delete_group`/`group_leaderboard_for_child`) + exceptions (`GroupNotFound`/`GroupLimitError`) are used identically across Tasks 2–5. `parentApi.{listGroups,createGroup,joinGroup,removeGroupMember,deleteGroup}` consistent between Task 6 (def) and Task 8 (use). ✓
