# Leaderboard Scope & Privacy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One leaderboard viewable at three scopes (My Market / Global / Friends) ranked by XP or Arcade Points, made safe for a kids' app with auto-generated handles, parent-granted consent, and a child hide switch.

**Architecture:** A new `leaderboard_service` unifies the three existing ad-hoc queries (gamification global-XP, arcade per-market-points, group friends-XP) behind one `leaderboard(viewer, scope, metric)` call. Public scopes show a non-identifying `display_handle` and include only children whose parent granted consent and who haven't hidden themselves; Friends shows usernames (closed, parent-created groups). Frontend collapses the two Stats boards into one `LeaderboardCard` with scope + metric toggles.

**Tech Stack:** FastAPI + async SQLAlchemy + Alembic (Postgres); React + TypeScript + React Query + react-i18next + Tailwind; pytest (`pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures); vitest + vitest-axe.

## Global Constraints

- **Migrations:** hand-written, chained Alembic. New revision's `down_revision = "a2b3c4d5e6f7"` (current head). Check `alembic heads` first. **Ask the user before running any prod migration whether to snapshot first.**
- **Async tests:** `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient`.
- **Kids' safety / WCAG 2.2 AA:** handle word lists must be kid-safe (no free text). New UI is keyboard-reachable + `vitest-axe`-clean.
- **Public visibility rule (verbatim):** a child appears on **public (market/global)** boards **iff `leaderboard_consent AND NOT leaderboard_hidden`**. Friends scope ignores consent and shows `username`.
- **Identity per scope (verbatim):** friends → `username`; market/global → `display_handle`.
- **Week window:** weekly boards reset Monday 00:00 UTC (matches existing `gamification`/`arcade` queries).
- **Commit to `main`**; end messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. Backend deploys on green CI (5 jobs); web is a manual two-step Vercel deploy.
- **Frozen-emoji rule N/A here.** Reuse `countryFlag` from `frontend/src/lib/country.ts`.

---

### Task 1: Migration + User columns

**Files:**
- Create: `backend/alembic/versions/b3c4d5e6f7a8_leaderboard_handle_and_consent.py`
- Modify: `backend/app/models/user.py` (add 3 columns to `User`)
- Test: `backend/tests/test_leaderboard_columns.py`

**Interfaces:**
- Produces: `User.display_handle: str | None`, `User.leaderboard_consent: bool`, `User.leaderboard_hidden: bool`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_leaderboard_columns.py
import pytest
from sqlalchemy import select
from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_user_has_leaderboard_columns(client, db_session):
    await _register_and_login(client, email="lb1@example.com", username="lb1")
    user = await db_session.scalar(select(User).where(User.email == "lb1@example.com"))
    assert user.display_handle is None          # not generated yet
    assert user.leaderboard_consent is False     # default off
    assert user.leaderboard_hidden is False       # default off
```

- [ ] **Step 2: Run it — expect FAIL** (`AttributeError: 'User' object has no attribute 'display_handle'`)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_leaderboard_columns.py -q`

- [ ] **Step 3: Add columns to the model**

In `backend/app/models/user.py`, inside `class User`, after the existing columns add:

```python
    display_handle: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    leaderboard_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    leaderboard_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
```

Ensure the file imports `Boolean` from `sqlalchemy` and `sqlalchemy as sa` (check existing imports; add only what's missing).

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/b3c4d5e6f7a8_leaderboard_handle_and_consent.py
"""leaderboard: display_handle + consent + hidden on users

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-06-24 12:00:00.000000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("users", sa.Column("display_handle", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("leaderboard_consent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("leaderboard_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_users_display_handle", "users", ["display_handle"])

def downgrade() -> None:
    op.drop_constraint("uq_users_display_handle", "users", type_="unique")
    op.drop_column("users", "leaderboard_hidden")
    op.drop_column("users", "leaderboard_consent")
    op.drop_column("users", "display_handle")
```

- [ ] **Step 5: Verify migration chains & tests pass**

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && alembic heads` — expect single head `b3c4d5e6f7a8`.
Run: `python -m pytest tests/test_leaderboard_columns.py -q` — expect PASS.
Run: `python -m ruff check app/models/user.py alembic/versions/b3c4d5e6f7a8_leaderboard_handle_and_consent.py`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user.py backend/alembic/versions/b3c4d5e6f7a8_leaderboard_handle_and_consent.py backend/tests/test_leaderboard_columns.py
git commit -m "feat(leaderboard): add display_handle + consent + hidden to users"
```

---

### Task 2: Handle generator service

**Files:**
- Create: `backend/app/services/handles.py`
- Test: `backend/tests/test_handles.py`

**Interfaces:**
- Consumes: `User.display_handle` (Task 1).
- Produces:
  - `generate_handle() -> str` — e.g. `"CleverOtter42"`.
  - `async ensure_handle(session, user: User) -> str` — assigns+persists a unique handle if missing; returns it.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_handles.py
import re
import pytest
from sqlalchemy import select
from app.models.user import User
from app.services.handles import generate_handle, ensure_handle, ADJECTIVES, ANIMALS
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")
HANDLE_RE = re.compile(r"^[A-Z][a-z]+[A-Z][a-z]+\d{2}$")

def test_generate_handle_shape():
    for _ in range(50):
        h = generate_handle()
        assert HANDLE_RE.match(h), h
        assert any(h.startswith(a) for a in ADJECTIVES)
        assert any(an in h for an in ANIMALS)

async def test_ensure_handle_assigns_and_persists(client, db_session):
    await _register_and_login(client, email="h1@example.com", username="h1")
    user = await db_session.scalar(select(User).where(User.email == "h1@example.com"))
    assert user.display_handle is None
    handle = await ensure_handle(db_session, user)
    await db_session.commit()
    assert HANDLE_RE.match(handle)
    await db_session.refresh(user)
    assert user.display_handle == handle
    # idempotent: returns the same handle, does not regenerate
    assert await ensure_handle(db_session, user) == handle
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: app.services.handles`)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_handles.py -q`

- [ ] **Step 3: Implement the generator**

```python
# backend/app/services/handles.py
"""Non-identifying display handles for public leaderboards (kids' safety).
Format: <Adjective><Animal><2 digits>, e.g. "CleverOtter42". Curated word
lists only — zero free text, so no moderation surface."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

ADJECTIVES = [
    "Clever", "Brave", "Sunny", "Swift", "Lucky", "Mighty", "Jolly", "Bright",
    "Cosmic", "Nimble", "Bouncy", "Cheery", "Dandy", "Epic", "Fuzzy", "Golden",
    "Happy", "Kind", "Lively", "Merry", "Noble", "Plucky", "Quick", "Rapid",
    "Snazzy", "Trusty", "Witty", "Zippy", "Breezy", "Curious",
]
ANIMALS = [
    "Otter", "Fox", "Panda", "Koala", "Tiger", "Falcon", "Dolphin", "Lynx",
    "Beaver", "Robin", "Badger", "Gecko", "Heron", "Ibis", "Jaguar", "Kestrel",
    "Llama", "Meerkat", "Newt", "Owl", "Puffin", "Quokka", "Raccoon", "Seal",
    "Toucan", "Urchin", "Vole", "Walrus", "Yak", "Zebra",
]

def generate_handle() -> str:
    adj = secrets.choice(ADJECTIVES)
    animal = secrets.choice(ANIMALS)
    num = secrets.randbelow(90) + 10  # 10..99 — always 2 digits
    return f"{adj}{animal}{num}"

async def _handle_taken(session: AsyncSession, handle: str) -> bool:
    return (await session.scalar(select(User.id).where(User.display_handle == handle))) is not None

async def ensure_handle(session: AsyncSession, user: User) -> str:
    """Assign a unique handle if the user has none; return the current handle.
    Caller commits."""
    if user.display_handle:
        return user.display_handle
    for _ in range(20):
        candidate = generate_handle()
        if not await _handle_taken(session, candidate):
            user.display_handle = candidate
            await session.flush()
            return candidate
    raise RuntimeError("could not allocate a unique handle")
```

Note: `generate_handle` uses `secrets` (allowed; not `random`). Tests vary by iteration, not by seeding.

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_handles.py -q`

- [ ] **Step 5: Lint + commit**

```bash
cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app/services/handles.py tests/test_handles.py
git add backend/app/services/handles.py backend/tests/test_handles.py
git commit -m "feat(leaderboard): kid-safe display-handle generator"
```

---

### Task 3: Unified leaderboard service

**Files:**
- Create: `backend/app/services/leaderboard_service.py`
- Test: `backend/tests/test_leaderboard_service.py`

**Interfaces:**
- Consumes: `ensure_handle` (Task 2); `User`, `Lesson`, `LessonCompletion`, `ArcadeScore`, `GroupMembership`, `LeaderboardGroup` models; `group_service` patterns.
- Produces:
  ```python
  @dataclass
  class LeaderboardRow:
      rank: int
      name: str                 # display_handle (public) or username (friends)
      country_code: str | None
      points: int
      is_me: bool

  async def leaderboard(
      session, *, viewer: User,
      scope: Literal["market", "global", "friends"],
      metric: Literal["xp", "arcade"],
      limit: int = 50,
  ) -> list[LeaderboardRow]
  ```

- [ ] **Step 1: Write the failing tests** (covers scope × metric, visibility, identity, is_me)

```python
# backend/tests/test_leaderboard_service.py
import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from app.models.user import User, UserProgress
from app.models.content import Lesson, LessonCompletion
from app.models.arcade import ArcadeScore
from app.services.leaderboard_service import leaderboard
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _mk_user(client, db_session, email, *, market="GB", country="GB",
                   consent=True, hidden=False, handle=None):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    u.active_market_code = market
    u.country_code = country
    u.leaderboard_consent = consent
    u.leaderboard_hidden = hidden
    u.display_handle = handle or f"Handle{email.split('@')[0]}"
    await db_session.commit()
    return u

async def _add_xp(db_session, user, amount):
    # one lesson completion worth `amount` xp, this week
    lesson = (await db_session.scalars(select(Lesson).limit(1))).first()
    lesson.xp_reward = amount
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.commit()

async def _add_arcade(db_session, user, points, market="GB"):
    db_session.add(ArcadeScore(user_id=user.id, game="quiz_rush", points=points,
                               market_code=market, created_at=datetime.now(UTC)))
    await db_session.commit()

async def test_market_scope_filters_by_market_and_uses_handle(client, db_session):
    me = await _mk_user(client, db_session, "lbm_me@example.com", market="GB")
    other_gb = await _mk_user(client, db_session, "lbm_gb@example.com", market="GB")
    other_us = await _mk_user(client, db_session, "lbm_us@example.com", market="US")
    await _add_xp(db_session, me, 30)
    await _add_xp(db_session, other_gb, 50)
    await _add_xp(db_session, other_us, 99)

    rows = await leaderboard(db_session, viewer=me, scope="market", metric="xp")
    names = [r.name for r in rows]
    assert me.display_handle in names and other_gb.display_handle in names
    assert other_us.display_handle not in names         # different market excluded
    assert all(not r.name.startswith("lbm_") for r in rows)  # handle, never username
    assert any(r.is_me for r in rows)

async def test_public_excludes_non_consented_and_hidden(client, db_session):
    me = await _mk_user(client, db_session, "lbv_me@example.com")
    noconsent = await _mk_user(client, db_session, "lbv_nc@example.com", consent=False)
    hidden = await _mk_user(client, db_session, "lbv_h@example.com", hidden=True)
    for u in (me, noconsent, hidden):
        await _add_xp(db_session, u, 40)

    rows = await leaderboard(db_session, viewer=me, scope="global", metric="xp")
    names = {r.name for r in rows}
    assert noconsent.display_handle not in names
    assert hidden.display_handle not in names
    assert me.display_handle in names

async def test_arcade_metric_uses_arcade_points(client, db_session):
    me = await _mk_user(client, db_session, "lba_me@example.com", market="GB")
    await _add_xp(db_session, me, 5)        # xp present but should be ignored
    await _add_arcade(db_session, me, 250, market="GB")
    rows = await leaderboard(db_session, viewer=me, scope="market", metric="arcade")
    mine = next(r for r in rows if r.is_me)
    assert mine.points == 250
```

(Friends-scope identity is covered by an integration check in Task 4's endpoint tests, where group fixtures already exist.)

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError`)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_leaderboard_service.py -q`

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/leaderboard_service.py
"""Unified weekly leaderboard: scope (market/global/friends) × metric (xp/arcade).
Public scopes show display_handle and only consented, non-hidden children.
Friends shows usernames for all group members (closed, parent-created)."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.content import Lesson, LessonCompletion
from app.models.group import GroupMembership
from app.models.user import User

Scope = Literal["market", "global", "friends"]
Metric = Literal["xp", "arcade"]

@dataclass
class LeaderboardRow:
    rank: int
    name: str
    country_code: str | None
    points: int
    is_me: bool

def _monday(now: datetime) -> datetime:
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

def _metric_join(stmt, metric: Metric, since: datetime):
    """Attach the metric's sum + time filter to a select over User."""
    if metric == "xp":
        total = func.coalesce(func.sum(Lesson.xp_reward), 0)
        stmt = (
            stmt.outerjoin(LessonCompletion,
                           and_(LessonCompletion.user_id == User.id,
                                LessonCompletion.completed_at >= since))
                .outerjoin(Lesson, Lesson.id == LessonCompletion.lesson_id)
        )
    else:
        total = func.coalesce(func.sum(ArcadeScore.points), 0)
        stmt = stmt.outerjoin(ArcadeScore,
                              and_(ArcadeScore.user_id == User.id,
                                   ArcadeScore.created_at >= since))
    return stmt, total

async def leaderboard(session: AsyncSession, *, viewer: User, scope: Scope,
                      metric: Metric, limit: int = 50) -> list[LeaderboardRow]:
    since = _monday(datetime.now(UTC))

    if scope == "friends":
        return await _friends(session, viewer=viewer, metric=metric, since=since)

    # public (market/global): handle identity, consent-gated population
    base = select(User.id, User.display_handle, User.country_code)
    base, total = _metric_join(base, metric, since)
    base = base.where(User.leaderboard_consent.is_(True), User.leaderboard_hidden.is_(False))
    if scope == "market":
        base = base.where(User.active_market_code == viewer.active_market_code)
    base = base.group_by(User.id, User.display_handle, User.country_code)
    base = base.order_by(total.desc(), User.display_handle.asc()).limit(limit)

    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    out = [
        LeaderboardRow(rank=i + 1, name=handle or "—", country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id))
        for i, (uid, handle, cc, pts) in enumerate(rows)
    ]
    # Ensure the viewer always sees their own row (even if not public / outside top-N).
    if not any(r.is_me for r in out):
        out.append(await _own_row(session, viewer=viewer, scope=scope, metric=metric, since=since))
    return out

async def _own_row(session, *, viewer, scope, metric, since) -> LeaderboardRow:
    mine = select(User.id)
    mine, total = _metric_join(mine, metric, since)
    mine = mine.where(User.id == viewer.id).group_by(User.id)
    pts = (await session.execute(mine.add_columns(total.label("pts")))).first()
    points = int(pts.pts) if pts else 0
    # rank = how many public users beat me + 1 (cheap COUNT over the same population)
    pop = select(User.id)
    pop, ptotal = _metric_join(pop, metric, since)
    pop = pop.where(User.leaderboard_consent.is_(True), User.leaderboard_hidden.is_(False))
    if scope == "market":
        pop = pop.where(User.active_market_code == viewer.active_market_code)
    pop = pop.group_by(User.id).having(ptotal > points)
    ahead = len((await session.execute(pop)).all())
    return LeaderboardRow(rank=ahead + 1, name=viewer.display_handle or "—",
                          country_code=viewer.country_code, points=points, is_me=True)

async def _friends(session, *, viewer, metric, since) -> list[LeaderboardRow]:
    group_ids = (await session.scalars(
        select(GroupMembership.group_id).where(GroupMembership.user_id == viewer.id))).all()
    if not group_ids:
        return []
    base = select(User.id, User.username, User.country_code)
    base, total = _metric_join(base, metric, since)
    base = (base.join(GroupMembership, GroupMembership.user_id == User.id)
                .where(GroupMembership.group_id.in_(group_ids))
                .group_by(User.id, User.username, User.country_code)
                .order_by(total.desc(), User.username.asc()))
    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    return [
        LeaderboardRow(rank=i + 1, name=uname, country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id))
        for i, (uid, uname, cc, pts) in enumerate(rows)
    ]
```

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_leaderboard_service.py -q`

- [ ] **Step 5: Lint + commit**

```bash
cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app/services/leaderboard_service.py tests/test_leaderboard_service.py
git add backend/app/services/leaderboard_service.py backend/tests/test_leaderboard_service.py
git commit -m "feat(leaderboard): unified scope×metric leaderboard service"
```

---

### Task 4: Schemas + endpoints (leaderboard, handle, visibility, parent consent)

**Files:**
- Modify: `backend/app/schemas/gamification.py` (add `LeaderboardRowOut`)
- Modify: `backend/app/routers/gamification.py` (rewrite `GET /leaderboard`; add `GET /me/handle`, `POST /me/handle/reroll`, `PATCH /me/leaderboard-visibility`)
- Modify: `backend/app/routers/parent.py` (add `POST /parent/children/{user_id}/leaderboard-consent`)
- Test: `backend/tests/test_leaderboard_api.py`

**Interfaces:**
- Consumes: `leaderboard`, `LeaderboardRow` (Task 3); `ensure_handle` (Task 2); the parent `_get_owned_child` + `get_current_parent` patterns (`parent.py`); `get_current_user`.
- Produces: `LeaderboardRowOut {rank, name, country_code, points, is_me}`; the four endpoints below.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_leaderboard_api.py
import pytest
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_leaderboard_requires_auth(client):
    assert (await client.get("/leaderboard")).status_code == 401

async def test_leaderboard_defaults_market_xp(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbapi@example.com", username="lbapi")
    r = await client.get("/leaderboard")               # no params
    assert r.status_code == 200
    assert isinstance(r.json(), list)

async def test_leaderboard_rejects_bad_scope(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbapi2@example.com", username="lbapi2")
    assert (await client.get("/leaderboard?scope=planet")).status_code == 422

async def test_me_handle_generates_and_reroll_changes_it(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbh@example.com", username="lbh")
    h1 = (await client.get("/me/handle")).json()["handle"]
    assert h1
    h2 = (await client.post("/me/handle/reroll")).json()["handle"]
    assert h2 and h2 != h1

async def test_visibility_toggle(client):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="lbvis@example.com", username="lbvis")
    r = await client.patch("/me/leaderboard-visibility", json={"hidden": True})
    assert r.status_code == 200 and r.json()["hidden"] is True
```

- [ ] **Step 2: Run — expect FAIL** (404/422/405 mismatches)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_leaderboard_api.py -q`

- [ ] **Step 3: Add the schema**

In `backend/app/schemas/gamification.py` add:

```python
class LeaderboardRowOut(BaseModel):
    rank: int
    name: str
    country_code: str | None = None
    points: int
    is_me: bool
```

- [ ] **Step 4: Rewrite the leaderboard endpoint + add child endpoints**

In `backend/app/routers/gamification.py`: replace the existing `weekly_leaderboard` function. Update imports: `from typing import Literal`, `from fastapi import Query`, `from pydantic import BaseModel` (for the visibility body), `from app.services.leaderboard_service import leaderboard`, `from app.services.handles import ensure_handle, generate_handle`, `from app.schemas.gamification import LeaderboardRowOut`. Keep existing imports.

```python
@router.get("/leaderboard", response_model=list[LeaderboardRowOut])
async def weekly_leaderboard(
    scope: Literal["market", "global", "friends"] = Query("market"),
    metric: Literal["xp", "arcade"] = Query("xp"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not current_user.display_handle:
        await ensure_handle(session, current_user)
        await session.commit()
    rows = await leaderboard(session, viewer=current_user, scope=scope, metric=metric)
    return [LeaderboardRowOut(rank=r.rank, name=r.name, country_code=r.country_code,
                              points=r.points, is_me=r.is_me) for r in rows]

@router.get("/me/handle")
async def get_my_handle(current_user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    handle = await ensure_handle(session, current_user)
    await session.commit()
    return {"handle": handle}

@router.post("/me/handle/reroll")
async def reroll_my_handle(current_user: User = Depends(get_current_user),
                           session: AsyncSession = Depends(get_session)):
    from app.services.handles import _handle_taken  # local import; small helper
    for _ in range(20):
        candidate = generate_handle()
        if candidate != current_user.display_handle and not await _handle_taken(session, candidate):
            current_user.display_handle = candidate
            await session.commit()
            return {"handle": candidate}
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "handle_unavailable")

class VisibilityRequest(BaseModel):
    hidden: bool

@router.patch("/me/leaderboard-visibility")
async def set_my_visibility(payload: VisibilityRequest,
                            current_user: User = Depends(get_current_user),
                            session: AsyncSession = Depends(get_session)):
    current_user.leaderboard_hidden = payload.hidden
    await session.commit()
    return {"hidden": current_user.leaderboard_hidden}
```

Add `from fastapi import HTTPException, status` if not already imported.

- [ ] **Step 5: Add the parent consent endpoint**

In `backend/app/routers/parent.py`, following the `set_child_push` pattern, add a request model near the other request models and the endpoint:

```python
class LeaderboardConsentRequest(BaseModel):
    consent: bool

@router.post("/children/{user_id}/leaderboard-consent")
async def set_child_leaderboard_consent(
    user_id: uuid.UUID,
    payload: LeaderboardConsentRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    """Parent consent for showing the child on public (market/global) boards."""
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    child.leaderboard_consent = payload.consent
    session.add(AuditLog(
        user_id=child.id,
        event_type="leaderboard_consent_on" if payload.consent else "leaderboard_consent_off",
        metadata_json={"actor": f"parent:{parent_email}"},
    ))
    await session.commit()
    return {"status": "ok", "leaderboard_consent": payload.consent}
```

Reuse the existing `BaseModel`, `AuditLog`, `HTTPException`, `status`, `uuid` imports already in `parent.py` (verify; add only if missing).

- [ ] **Step 6: Run — expect PASS** (`python -m pytest tests/test_leaderboard_api.py -q`)

- [ ] **Step 6b: Rate-limit the read endpoint**

The spec calls for rate-limiting public board reads. Check how `app/routers/arcade.py`'s `/arcade/leaderboard` applies its limit (it rate-limits leaderboard reads at 60/h). Apply the **same** limiter dependency/decorator to this `GET /leaderboard`. If the gamification router currently has no limiter wired, import and apply arcade's exactly as arcade does — do not invent a new limiter. Verify with the existing rate-limit test pattern if one exists; otherwise a manual check that the dependency is attached is sufficient.

- [ ] **Step 7: CSRF allowlist check**

The new POST/PATCH endpoints (`/me/handle/reroll`, `/me/leaderboard-visibility`, `/parent/children/*/leaderboard-consent`) are authed user actions, not cron, so they go through normal CSRF like the existing `/parent/children/*/push`. No `_DEFAULT_EXEMPT_PATHS` change needed (those are for `/internal/*` cron only). Confirm by running the parent/consent tests below.

- [ ] **Step 8: Run broader regressions + lint + commit**

Run: `python -m pytest tests/test_leaderboard_api.py tests/test_gamification*.py tests/test_parent*.py -q`
Run: `python -m ruff check app/routers/gamification.py app/routers/parent.py app/schemas/gamification.py tests/test_leaderboard_api.py`

```bash
git add backend/app/routers/gamification.py backend/app/routers/parent.py backend/app/schemas/gamification.py backend/tests/test_leaderboard_api.py
git commit -m "feat(leaderboard): scope/metric endpoint + handle/visibility/consent endpoints"
```

---

### Task 5: Frontend API client + hooks

**Files:**
- Modify: `frontend/src/api/gamification.ts` (`getLeaderboard(scope, metric)` + new types; handle/visibility fns)
- Modify: `frontend/src/api/parent.ts` (consent fn) — locate the parent api module; if parent calls live elsewhere, follow that file's pattern.
- Modify: `frontend/src/hooks/useLeaderboard.ts`
- Create: `frontend/src/hooks/useLeaderboardControls.ts` (optional small hook for scope/metric state) — only if it reduces duplication; otherwise keep state in the component.
- Test: `frontend/src/api/__tests__/leaderboard.test.ts`

**Interfaces:**
- Consumes: endpoints from Task 4.
- Produces:
  - `type LeaderboardRow = { rank: number; name: string; country_code: string | null; points: number; is_me: boolean }`
  - `gamificationApi.getLeaderboard(scope: Scope, metric: Metric): Promise<LeaderboardRow[]>`
  - `gamificationApi.getHandle()`, `rerollHandle()`, `setLeaderboardVisibility(hidden)`
  - `useLeaderboard(scope, metric)` keyed `['leaderboard', scope, metric]`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/api/__tests__/leaderboard.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { gamificationApi } from '../gamification';

describe('gamificationApi.getLeaderboard', () => {
  beforeEach(() => vi.restoreAllMocks());
  it('passes scope + metric as query params', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([]);
    await gamificationApi.getLeaderboard('global', 'arcade');
    expect(spy).toHaveBeenCalledWith('/leaderboard?scope=global&metric=arcade');
  });
  it('reroll posts to /me/handle/reroll', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ handle: 'X' });
    await gamificationApi.rerollHandle();
    expect(spy).toHaveBeenCalledWith('/me/handle/reroll', { method: 'POST' });
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (`cd frontend && npx vitest run src/api/__tests__/leaderboard.test.ts`)

- [ ] **Step 3: Implement the client fns**

In `frontend/src/api/gamification.ts`:

```ts
export type LeaderboardScope = 'market' | 'global' | 'friends';
export type LeaderboardMetric = 'xp' | 'arcade';
export type LeaderboardRow = {
  rank: number; name: string; country_code: string | null; points: number; is_me: boolean;
};

// inside the gamificationApi object:
  getLeaderboard: (scope: LeaderboardScope, metric: LeaderboardMetric) =>
    apiFetch<LeaderboardRow[]>(`/leaderboard?scope=${scope}&metric=${metric}`),
  getHandle: () => apiFetch<{ handle: string }>('/me/handle'),
  rerollHandle: () => apiFetch<{ handle: string }>('/me/handle/reroll', { method: 'POST' }),
  setLeaderboardVisibility: (hidden: boolean) =>
    apiFetch<{ hidden: boolean }>('/me/leaderboard-visibility', { method: 'PATCH', body: JSON.stringify({ hidden }) }),
```

Remove the old `LeaderboardEntry` `getLeaderboard()` (no-arg) — update its only caller (`useLeaderboard`). Keep `LeaderboardEntry` type only if other code still imports it; otherwise delete.

Update `frontend/src/hooks/useLeaderboard.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type LeaderboardRow, type LeaderboardScope, type LeaderboardMetric } from '@/api/gamification';

export function useLeaderboard(scope: LeaderboardScope, metric: LeaderboardMetric) {
  return useQuery<LeaderboardRow[] | null>({
    queryKey: ['leaderboard', scope, metric],
    queryFn: () => gamificationApi.getLeaderboard(scope, metric),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
```

Add the parent consent call in the parent api module (match its existing fns):

```ts
  setChildLeaderboardConsent: (childId: string, consent: boolean) =>
    apiFetch(`/parent/children/${childId}/leaderboard-consent`, { method: 'POST', body: JSON.stringify({ consent }) }),
```

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd frontend && npx vitest run src/api/__tests__/leaderboard.test.ts && npx tsc --noEmit`
(tsc will flag the old `useLeaderboard()` callers — fix them in Task 6.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/gamification.ts frontend/src/hooks/useLeaderboard.ts frontend/src/api/parent.ts frontend/src/api/__tests__/leaderboard.test.ts
git commit -m "feat(leaderboard): client api + hook for scope/metric + handle/visibility"
```

---

### Task 6: LeaderboardCard UI + Stats integration

**Files:**
- Create: `frontend/src/components/child/stats/LeaderboardCard.tsx`
- Modify: `frontend/src/pages/child/Stats.tsx` (replace the two separate boards with `LeaderboardCard`)
- Modify: `frontend/src/components/child/stats/LeaderboardTable.tsx` (accept `rows: LeaderboardRow[]` + a `pointsLabel`; render `name`, flag, points, highlight `is_me`)
- Modify: `frontend/src/locales/en/child.json` (`leaderboard.*` strings: scope/metric labels, colName, friendsEmpty)
- Test: `frontend/src/components/child/stats/__tests__/LeaderboardCard.test.tsx`

**Interfaces:**
- Consumes: `useLeaderboard(scope, metric)`, `useGroupLeaderboard` (existing, for Friends fallback if you keep group rendering), `LeaderboardRow` (Task 5).
- Produces: `<LeaderboardCard currentName={string} />`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/child/stats/__tests__/LeaderboardCard.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LeaderboardCard } from '../LeaderboardCard';

const getLeaderboard = vi.fn();
vi.mock('@/api/gamification', () => ({
  gamificationApi: { getLeaderboard: (...a: unknown[]) => getLeaderboard(...a) },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  getLeaderboard.mockReset();
  getLeaderboard.mockResolvedValue([
    { rank: 1, name: 'CleverOtter42', country_code: 'GB', points: 120, is_me: false },
    { rank: 2, name: 'You', country_code: 'GB', points: 90, is_me: true },
  ]);
});

describe('LeaderboardCard', () => {
  it('defaults to Market + XP and renders rows', async () => {
    wrap(<LeaderboardCard currentName="You" />);
    await waitFor(() => expect(getLeaderboard).toHaveBeenCalledWith('market', 'xp'));
    expect(await screen.findByText('CleverOtter42')).toBeInTheDocument();
  });

  it('switching scope to Global refetches with global', async () => {
    wrap(<LeaderboardCard currentName="You" />);
    await screen.findByText('CleverOtter42');
    fireEvent.click(screen.getByRole('tab', { name: /global/i }));
    await waitFor(() => expect(getLeaderboard).toHaveBeenCalledWith('global', 'xp'));
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<LeaderboardCard currentName="You" />);
    await screen.findByText('CleverOtter42');
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (`cd frontend && npx vitest run src/components/child/stats/__tests__/LeaderboardCard.test.tsx`)

- [ ] **Step 3: Implement `LeaderboardCard`**

```tsx
// frontend/src/components/child/stats/LeaderboardCard.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import type { LeaderboardScope, LeaderboardMetric } from '@/api/gamification';
import { LeaderboardTable } from './LeaderboardTable';

const SCOPES: LeaderboardScope[] = ['market', 'global', 'friends'];
const METRICS: LeaderboardMetric[] = ['xp', 'arcade'];

export function LeaderboardCard({ currentName }: { currentName: string }) {
  const { t } = useTranslation('child');
  const [scope, setScope] = useState<LeaderboardScope>('market');
  const [metric, setMetric] = useState<LeaderboardMetric>('xp');
  const { data, isLoading, isError } = useLeaderboard(scope, metric);

  return (
    <section aria-labelledby="lb-heading">
      <h2 id="lb-heading" className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">
        {t('leaderboard.title')}
      </h2>
      <div role="tablist" aria-label={t('leaderboard.scopeLabel')} className="mb-2 flex gap-1 rounded-2xl border border-brand-200 bg-brand-50 p-1">
        {SCOPES.map((s) => (
          <button key={s} role="tab" type="button" aria-selected={scope === s}
            onClick={() => setScope(s)}
            className={`min-h-[44px] flex-1 rounded-xl px-3 text-sm font-bold ${scope === s ? 'bg-white text-brand-800 shadow-sm' : 'text-brand-600'}`}>
            {t(`leaderboard.scope.${s}`)}
          </button>
        ))}
      </div>
      <div role="tablist" aria-label={t('leaderboard.metricLabel')} className="mb-3 flex gap-1">
        {METRICS.map((m) => (
          <button key={m} role="tab" type="button" aria-selected={metric === m}
            onClick={() => setMetric(m)}
            className={`min-h-[36px] rounded-full px-3 text-xs font-bold ${metric === m ? 'bg-brand-600 text-white' : 'bg-brand-100 text-brand-700'}`}>
            {t(`leaderboard.metric.${m}`)}
          </button>
        ))}
      </div>
      {isLoading && <p className="py-6 text-center text-sm text-muted-foreground">{t('leaderboard.loading')}</p>}
      {isError && <p role="alert" className="py-6 text-center text-sm text-red-700">{t('leaderboard.error')}</p>}
      {data && (
        data.length === 0
          ? <p className="py-8 text-center text-muted-foreground">{scope === 'friends' ? t('leaderboard.friendsEmpty') : t('leaderboard.empty')}</p>
          : <LeaderboardTable rows={data} currentName={currentName}
              pointsLabel={metric === 'xp' ? t('leaderboard.colXp') : t('leaderboard.colPoints')} />
      )}
    </section>
  );
}
```

Refactor `LeaderboardTable.tsx` to the new shape:

```tsx
import { useTranslation } from 'react-i18next';
import type { LeaderboardRow } from '@/api/gamification';
import { countryFlag } from '@/lib/country';
import { cn } from '@/lib/utils';

type Props = { rows: LeaderboardRow[]; currentName: string; pointsLabel: string };

export function LeaderboardTable({ rows, pointsLabel }: Props) {
  const { t } = useTranslation('child');
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colRank')}</th>
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colName')}</th>
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colCountry')}</th>
            <th className="px-4 py-3 text-right font-medium">{pointsLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.rank}-${r.name}`} className={cn('border-b last:border-b-0', r.is_me && 'bg-brand-50 font-bold')}>
              <td className="px-4 py-3">{r.rank}</td>
              <td className="px-4 py-3">{r.name}</td>
              <td className="px-4 py-3" aria-hidden="true">{r.country_code ? countryFlag(r.country_code) : ''}</td>
              <td className="px-4 py-3 text-right">{r.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

In `Stats.tsx`: remove the separate `LeaderboardTable` + `GroupLeaderboard` leaderboard block and the `useLeaderboard()`/`useGroupLeaderboard()` wiring for it; render `<LeaderboardCard currentName={session?.username ?? ''} />` in that slot. (Keep `GroupLeaderboard` import only if still used elsewhere; the Friends scope now renders through the unified card, so the old `GroupLeaderboard` standalone block is removed.) Add the i18n keys: `leaderboard.title`, `scopeLabel`, `metricLabel`, `scope.market/global/friends`, `metric.xp/arcade`, `colName`, `colPoints`, `loading`, `friendsEmpty` (keep existing `colRank/colCountry/colXp/empty`).

- [ ] **Step 4: Run — expect PASS** + tsc + lint

Run: `cd frontend && npx vitest run src/components/child/stats && npx tsc --noEmit && npm run lint`
Fix any remaining `useLeaderboard()` no-arg callers tsc surfaces.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/stats/ frontend/src/pages/child/Stats.tsx frontend/src/locales/en/child.json
git commit -m "feat(leaderboard): unified Market/Global/Friends card with XP/Arcade toggle"
```

---

### Task 7: Parent consent toggle + child handle/hide UI

**Files:**
- Modify: the parent child-controls card (same component hosting the push/biometric toggles — find via `grep -rl "biometric" frontend/src/components/parent`), add a "Show on public leaderboards" toggle calling `setChildLeaderboardConsent`.
- Modify: `frontend/src/components/child/ProfileMenu.tsx` — add a handle row (show handle + "New name" reroll) and a "Hide me from public leaderboards" switch (calls `setLeaderboardVisibility`).
- Modify: `frontend/src/locales/en/settings.json` (handle + hide labels) and parent locale.
- Test: extend the relevant parent card test + a `ProfileMenu` handle test.

**Interfaces:**
- Consumes: `setChildLeaderboardConsent` (Task 5), `gamificationApi.getHandle/rerollHandle/setLeaderboardVisibility` (Task 5).

- [ ] **Step 1: Write failing tests** — (a) toggling the parent consent switch calls `setChildLeaderboardConsent(childId, true)`; (b) clicking "New name" in ProfileMenu calls `rerollHandle` and shows the new handle. Mirror the existing `ProfileMenu.biometric.test.tsx` mocking style.

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement** the parent consent `Switch` (copy the push/biometric toggle markup + handler in the same card) and the ProfileMenu handle row + hide switch (a `useState` seeded from `getHandle()`; reroll updates it; hide switch calls `setLeaderboardVisibility`). Keep controls ≥44px touch target, labelled, axe-clean.

- [ ] **Step 4: Run — expect PASS** + tsc + lint + `vitest-axe` on touched components.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/parent/ frontend/src/components/child/ProfileMenu.tsx frontend/src/locales/
git commit -m "feat(leaderboard): parent consent toggle + child handle/hide controls"
```

---

### Task 8: Full verification + ship

**Files:** none (verify/deploy).

- [ ] **Step 1: Backend gate**

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app tests && python -m pytest tests/test_leaderboard_columns.py tests/test_handles.py tests/test_leaderboard_service.py tests/test_leaderboard_api.py tests/test_parent_api.py tests/test_gamification_api.py -q`
Expected: all pass, ruff clean. (If the local DB hangs ~90s, it's environmental — rely on CI.)

- [ ] **Step 2: Frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/api/__tests__/leaderboard.test.ts src/components/child/stats src/components/child/__tests__/ProfileMenu* && npm run build`
Expected: tsc 0, lint 0 errors, targeted tests pass, build clean. (The session's known ~68 local base-URL vitest failures are env-only and pass in CI; confirm no NEW failures and zero unhandled errors.)

- [ ] **Step 3: Migration snapshot gate (STANDING RULE)**

Before the prod migration, **ask the user whether to take a DB snapshot/backup first.** Do not promote without an answer.

- [ ] **Step 4: Commit any verification fixes, push, watch CI**

```bash
git push origin main
gh run watch "$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```
Expected: CI green (5 jobs). Railway applies migration `b3c4d5e6f7a8` + deploys backend.

- [ ] **Step 5: Manual web deploy + alias**

```bash
cd frontend && vercel --prod --force --yes
vercel alias set <printed-hash>-investikid.vercel.app app.investikid.ai
```

- [ ] **Step 6: `cap sync ios`** (Stats UI changed)

Run: `cd frontend && npx cap sync ios`

- [ ] **Step 7: Verify live** in the user's Chrome: `/stats` shows the unified card; Market default; toggling Global/Friends + XP/Arcade refetches; own row highlighted; ProfileMenu shows handle + hide switch.

- [ ] **Step 8: Update docs/memory** — MASTER-BACKLOG + `project_arcade`/leaderboard memory note (scopes, handle, consent, migration id, live status).

---

## Notes for the implementer

- **Privacy is the point.** Never emit `username` on market/global scopes — only `display_handle`. The service is the single choke point; keep it that way (don't re-add a username path in the endpoint).
- **Default off.** `leaderboard_consent` defaults false — a fresh child is NOT on public boards until a parent opts in. Tests must assert this.
- **Reuse, don't fork.** The week-window + sum logic mirrors existing `gamification`/`arcade`/`group` queries; the new service consolidates them — after this lands, the old `arcade_service.weekly_leaderboard` and the group board can stay (still used by `/arcade/leaderboard` and group challenges) or be pointed at the new service in a later cleanup (out of scope here).
