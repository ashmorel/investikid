# Penny's Arcade — Phase 1 Implementation Plan (Foundation + Quiz Rush)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a playable "Penny's Arcade" hub reachable from Home, with the **Quiz Rush** 60-second quiz blitz, plus the shared rewards/leaderboard foundation that Phase 2 (MoneyWord) will build on.

**Architecture:** A new `arcade_score` table + per-day `arcade_xp_today` cap columns on `UserProgress` back two reward streams — capped coins/XP into the existing economy (via the canonical `award_xp` seam) and an uncapped **Arcade Points** score feeding a weekly per-market leaderboard + personal bests. Quiz Rush reuses the existing quiz-lesson bank; scoring is server-authoritative. Frontend adds an `/arcade` hub page + a Quiz Rush game page + a Home entry, no new bottom tab.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Alembic (backend); React + Vite + TypeScript + TanStack Query + react-i18next + Tailwind (frontend); pytest + ruff (backend CI); tsc + eslint + vitest + vitest-axe + build (frontend CI).

**Reference spec:** `docs/superpowers/specs/2026-06-23-penny-arcade-design.md`

## Global Constraints

- DB change = hand-written, chained Alembic migration. Current head is **`e7c1a2b3d4f5`**; new migration's `down_revision` must be `e7c1a2b3d4f5` (run `alembic heads` to reconfirm before writing). Migration is **additive** (new table + new nullable/defaulted columns).
- Coins == XP (1 coin per 1 XP). Award coins/XP **only** through the canonical seam `award_xp(session, progress, amount, *, market_code=None, today=None)` in `app/services/market_progress_service.py` (keeps `sum(per-market) == global`). Never mutate `virtual_coins`/`xp` directly.
- **Daily participation-coin cap = 25 XP/day** for arcade play (matches the existing `sim_xp_today` / `revise_xp_today` caps). Arcade Points are **never** capped.
- Quiz Rush content comes from existing `Lesson` rows where `type == "quiz"` and `content_json == {question, choices, answer_index, explanation}`. **Cold-start threshold: if the child's unlocked-concept quiz pool has `< 10` questions, fall back to all published quiz questions in their `active_market_code`.**
- Scoring is **server-authoritative**: `POST /arcade/quiz-rush/score` re-scores from submitted choices; client-side feedback never sets the official score.
- Child-facing endpoints require the existing auth dependency `get_current_user` (`app/routers/users.py`); admin endpoints (none in Phase 1) would use `get_current_admin`.
- Kids' app: no child free-text (Quiz Rush is multiple-choice). WCAG 2.2 AA — touch targets ≥44px, keyboard operable, no colour-only signalling, new UI covered by `vitest-axe`. All user-facing strings localised via i18n (new `src/locales/en/arcade.json`).
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` and the shared `client` / `db_session` fixtures (see `backend/tests/test_video_curation_api.py` for the admin pattern and any existing child-authed API test for the `client` fixture). Never instantiate a raw `AsyncClient` on the app engine.
- Commit messages end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. Commit to `main` (beta).
- iOS-visible (new child screens): after the frontend tasks run `npm run build && npx cap sync ios` (Task 9) so the native shell picks up the new bundle.

---

## File Structure

**Backend (create):**
- `backend/app/models/arcade.py` — `ArcadeScore` model.
- `backend/alembic/versions/<rev>_arcade_foundation.py` — table + `UserProgress` cap columns.
- `backend/app/services/arcade_service.py` — capped coin/XP award, score recording, leaderboard + personal-best queries.
- `backend/app/services/quiz_rush_service.py` — build a question set (unlocked-concept preference + cold-start fallback) and authoritatively score a submission.
- `backend/app/routers/arcade.py` — child endpoints.
- `backend/app/schemas/arcade.py` — Pydantic request/response models.
- `backend/tests/test_arcade_service.py`, `backend/tests/test_quiz_rush_service.py`, `backend/tests/test_arcade_api.py` — tests.

**Backend (modify):**
- `backend/app/models/user.py` — add `arcade_xp_today` / `arcade_xp_date` to `UserProgress`.
- `backend/app/main.py` — `include_router(arcade_router.router)`.

**Frontend (create):**
- `frontend/src/api/arcade.ts` — types + `apiFetch` calls + TanStack hooks.
- `frontend/src/pages/child/Arcade.tsx` — hub page.
- `frontend/src/pages/child/games/QuizRush.tsx` — game page.
- `frontend/src/components/child/home/ArcadeHomeCard.tsx` — Home entry card.
- `frontend/src/locales/en/arcade.json` — strings.
- `frontend/src/pages/child/__tests__/Arcade.test.tsx`, `frontend/src/pages/child/games/__tests__/QuizRush.test.tsx`, `frontend/src/components/child/home/__tests__/ArcadeHomeCard.test.tsx`.

**Frontend (modify):**
- `frontend/src/App.tsx` — add `/arcade` and `/arcade/quiz-rush` routes inside `<Route element={<Shell />}>`.
- `frontend/src/pages/child/Home.tsx` — render `<ArcadeHomeCard />`.
- `frontend/src/i18n.ts` (or wherever namespaces are registered) — register the `arcade` namespace.

---

### Task 1: Arcade data model + migration

**Files:**
- Create: `backend/app/models/arcade.py`
- Modify: `backend/app/models/user.py` (add columns to `UserProgress`)
- Create: `backend/alembic/versions/<rev>_arcade_foundation.py`
- Test: `backend/tests/test_arcade_model.py`

**Interfaces:**
- Produces: `ArcadeScore` model (`__tablename__ = "arcade_scores"`) with `id: UUID`, `user_id: UUID` (FK `users.id`), `game: str`, `points: int`, `market_code: str` (FK `markets.code`), `created_at: datetime`. New `UserProgress.arcade_xp_today: int` (default 0) and `UserProgress.arcade_xp_date: date | None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_arcade_model.py
import pytest
from sqlalchemy import select
from app.models.arcade import ArcadeScore
from app.models.user import UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_arcade_score_persists(db_session, make_user):
    user = await make_user()  # existing helper; if absent, create a User+UserProgress inline as other tests do
    db_session.add(ArcadeScore(user_id=user.id, game="quiz_rush", points=120, market_code="GB"))
    await db_session.flush()
    row = (await db_session.scalars(select(ArcadeScore))).one()
    assert row.game == "quiz_rush" and row.points == 120 and row.market_code == "GB"

async def test_user_progress_has_arcade_cap_columns(db_session):
    cols = UserProgress.__table__.columns.keys()
    assert "arcade_xp_today" in cols and "arcade_xp_date" in cols
```

> If no `make_user` fixture exists, mirror how `backend/tests/test_arcade_service.py` (Task 2) or existing user tests build a `User` + `UserProgress`; keep one shared inline helper.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_arcade_model.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models.arcade` / missing columns.

- [ ] **Step 3: Create the model**

```python
# backend/app/models/arcade.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArcadeScore(Base):
    """One row per completed arcade play. Powers the weekly per-market leaderboard
    (sum/Top-N over a rolling window) and all-time personal bests (max)."""
    __tablename__ = "arcade_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # quiz_rush | moneyword
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    market_code: Mapped[str] = mapped_column(String(2), ForeignKey("markets.code"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 4: Add the cap columns to `UserProgress`**

In `backend/app/models/user.py`, directly after the existing `revise_xp_date` / `revise_xp_today` columns in `class UserProgress`, add (matching the existing `Date` import + `date` typing already used there):

```python
    arcade_xp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    arcade_xp_today: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
```

- [ ] **Step 5: Write the migration**

Confirm head first: `cd backend && alembic heads` → expect `e7c1a2b3d4f5`.

```python
# backend/alembic/versions/f1a2b3c4d5e6_arcade_foundation.py
"""arcade foundation: scores table + user_progress xp cap columns

Revision ID: f1a2b3c4d5e6
Revises: e7c1a2b3d4f5
Create Date: 2026-06-23 19:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e7c1a2b3d4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arcade_scores",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("game", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arcade_scores_user_id", "arcade_scores", ["user_id"])
    op.create_index("ix_arcade_scores_game", "arcade_scores", ["game"])
    op.create_index("ix_arcade_scores_market_code", "arcade_scores", ["market_code"])
    op.add_column("user_progress", sa.Column("arcade_xp_date", sa.Date(), nullable=True))
    op.add_column(
        "user_progress",
        sa.Column("arcade_xp_today", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_progress", "arcade_xp_today")
    op.drop_column("user_progress", "arcade_xp_date")
    op.drop_index("ix_arcade_scores_market_code", table_name="arcade_scores")
    op.drop_index("ix_arcade_scores_game", table_name="arcade_scores")
    op.drop_index("ix_arcade_scores_user_id", table_name="arcade_scores")
    op.drop_table("arcade_scores")
```

> Confirm the `UserProgress` table name is `user_progress` via `python -c "from app.models.user import UserProgress; print(UserProgress.__tablename__)"`; correct the migration's `add_column`/`drop_column` target if it differs.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_arcade_model.py -v`
Expected: PASS (the test DB is created from models; the migration is exercised by CI/prod, not the test fixtures).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/arcade.py backend/app/models/user.py backend/alembic/versions/f1a2b3c4d5e6_arcade_foundation.py backend/tests/test_arcade_model.py
git commit -m "feat(arcade): scores table + user_progress arcade xp-cap columns

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: arcade_service — capped award, score recording, leaderboard, personal best

**Files:**
- Create: `backend/app/services/arcade_service.py`
- Test: `backend/tests/test_arcade_service.py`

**Interfaces:**
- Consumes: `award_xp(session, progress, amount, *, market_code=None, today=None)` from `app/services/market_progress_service.py`; `ArcadeScore` from Task 1.
- Produces:
  - `ARCADE_DAILY_XP_CAP = 25`
  - `async def award_arcade_coins(session, progress, amount, *, market_code, today=None) -> int` — awards `min(amount, remaining cap today)` via `award_xp`, updates `arcade_xp_today`/`arcade_xp_date`, returns the coins actually awarded.
  - `async def record_score(session, *, user_id, game, points, market_code) -> ArcadeScore`
  - `async def weekly_leaderboard(session, *, game, market_code, limit=50) -> list[tuple[str, str, int]]` — `(username, country_code, points_this_week)` since Monday 00:00 UTC, per market, Top-N.
  - `async def personal_best(session, *, user_id, game) -> int` — max points (0 if none).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_arcade_service.py
import pytest
from app.models.user import User, UserProgress
from app.services import arcade_service as svc

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _user(db_session, username="kid", market="GB"):
    u = User(username=username, country_code=market, active_market_code=market)
    db_session.add(u); await db_session.flush()
    p = UserProgress(user_id=u.id)
    db_session.add(p); await db_session.flush()
    return u, p

async def test_award_is_capped_per_day(db_session):
    u, p = await _user(db_session)
    first = await svc.award_arcade_coins(db_session, p, 20, market_code="GB")
    second = await svc.award_arcade_coins(db_session, p, 20, market_code="GB")
    assert first == 20
    assert second == 5            # only 5 of the cap (25) remained
    assert p.arcade_xp_today == 25

async def test_record_score_and_personal_best(db_session):
    u, p = await _user(db_session)
    await svc.record_score(db_session, user_id=u.id, game="quiz_rush", points=80, market_code="GB")
    await svc.record_score(db_session, user_id=u.id, game="quiz_rush", points=140, market_code="GB")
    assert await svc.personal_best(db_session, user_id=u.id, game="quiz_rush") == 140

async def test_leaderboard_is_per_market_and_ranked(db_session):
    u1, p1 = await _user(db_session, "a", "GB")
    u2, p2 = await _user(db_session, "b", "GB")
    u3, p3 = await _user(db_session, "c", "US")
    await svc.record_score(db_session, user_id=u1.id, game="quiz_rush", points=50, market_code="GB")
    await svc.record_score(db_session, user_id=u2.id, game="quiz_rush", points=90, market_code="GB")
    await svc.record_score(db_session, user_id=u3.id, game="quiz_rush", points=200, market_code="US")
    board = await svc.weekly_leaderboard(db_session, game="quiz_rush", market_code="GB")
    assert [r[0] for r in board] == ["b", "a"]   # US child excluded; ranked desc
```

> Build `User`/`UserProgress` exactly as existing tests do — if those models require more non-null fields than shown, copy the construction from an existing test (e.g. a progress/xp test).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_arcade_service.py -v`
Expected: FAIL — `module app.services.arcade_service not found`.

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/arcade_service.py
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.user import User, UserProgress
from app.services.market_progress_service import award_xp

ARCADE_DAILY_XP_CAP = 25


async def award_arcade_coins(
    session: AsyncSession, progress: UserProgress, amount: int, *, market_code: str, today: date | None = None
) -> int:
    """Award up to the remaining daily arcade cap (25 XP=coins). Returns coins actually awarded."""
    today = today or datetime.now(UTC).date()
    if progress.arcade_xp_date != today:
        progress.arcade_xp_date = today
        progress.arcade_xp_today = 0
    remaining = max(0, ARCADE_DAILY_XP_CAP - progress.arcade_xp_today)
    grant = max(0, min(amount, remaining))
    if grant:
        await award_xp(session, progress, grant, market_code=market_code, today=today)
        progress.arcade_xp_today += grant
    return grant


async def record_score(
    session: AsyncSession, *, user_id, game: str, points: int, market_code: str
) -> ArcadeScore:
    row = ArcadeScore(user_id=user_id, game=game, points=points, market_code=market_code)
    session.add(row)
    await session.flush()
    return row


async def personal_best(session: AsyncSession, *, user_id, game: str) -> int:
    best = await session.scalar(
        select(func.max(ArcadeScore.points)).where(
            ArcadeScore.user_id == user_id, ArcadeScore.game == game
        )
    )
    return best or 0


async def weekly_leaderboard(
    session: AsyncSession, *, game: str, market_code: str, limit: int = 50
) -> list[tuple[str, str, int]]:
    now = datetime.now(UTC)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    total = func.sum(ArcadeScore.points).label("pts")
    stmt = (
        select(User.username, User.country_code, total)
        .join(ArcadeScore, ArcadeScore.user_id == User.id)
        .where(
            ArcadeScore.game == game,
            ArcadeScore.market_code == market_code,
            ArcadeScore.created_at >= monday,
        )
        .group_by(User.id, User.username, User.country_code)
        .order_by(total.desc())
        .limit(limit)
    )
    return [(u, c, int(p)) for u, c, p in (await session.execute(stmt)).all()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_arcade_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/arcade_service.py backend/tests/test_arcade_service.py
git commit -m "feat(arcade): capped coin award + score/leaderboard/personal-best service

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: quiz_rush_service — build question set + authoritative scoring

**Files:**
- Create: `backend/app/services/quiz_rush_service.py`
- Test: `backend/tests/test_quiz_rush_service.py`

**Interfaces:**
- Consumes: `Lesson`, `Module`, `LessonCompletion` (from `app/models/content.py`); the child's `active_market_code`.
- Produces:
  - `COLD_START_MIN = 10`
  - `async def build_session(session, user, *, limit=20) -> list[dict]` — each item `{"lesson_id": str, "question": str, "choices": list[str], "answer_index": int}`. Prefers quizzes in modules where the child has a `LessonCompletion` (unlocked concepts) in their active market; if that pool `< COLD_START_MIN`, uses all published quiz lessons in the active market. Shuffled, capped to `limit`.
  - `def score_submission(session_items: list[dict], answers: list[dict]) -> dict` — pure function. `answers` = `[{"lesson_id": str, "choice_index": int}]`. Returns `{"correct": int, "max_combo": int, "points": int}` where `points = correct*10 + max_combo*5` and combo counts consecutive correct answers in submitted order.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_quiz_rush_service.py
import pytest
from app.services.quiz_rush_service import score_submission

pytestmark = pytest.mark.asyncio(loop_scope="session")

def test_score_counts_correct_and_combo():
    items = [
        {"lesson_id": "a", "question": "q", "choices": ["x", "y"], "answer_index": 0},
        {"lesson_id": "b", "question": "q", "choices": ["x", "y"], "answer_index": 1},
        {"lesson_id": "c", "question": "q", "choices": ["x", "y"], "answer_index": 0},
    ]
    answers = [
        {"lesson_id": "a", "choice_index": 0},  # correct
        {"lesson_id": "b", "choice_index": 1},  # correct (combo 2)
        {"lesson_id": "c", "choice_index": 1},  # wrong (combo breaks)
    ]
    result = score_submission(items, answers)
    assert result == {"correct": 2, "max_combo": 2, "points": 2 * 10 + 2 * 5}

def test_score_ignores_unknown_lessons():
    items = [{"lesson_id": "a", "question": "q", "choices": ["x"], "answer_index": 0}]
    answers = [{"lesson_id": "zzz", "choice_index": 0}]
    assert score_submission(items, answers)["correct"] == 0
```

(An async DB test for `build_session` — seeding a module + completed quiz lesson + an unrelated quiz lesson and asserting the unlocked one is preferred — should mirror the seeding style of `backend/tests/test_video_salvage_service.py`. Include it as a third test in this file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_quiz_rush_service.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/quiz_rush_service.py
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.user import User

COLD_START_MIN = 10


def _shuffle(seq: list) -> list:
    items = list(seq)
    for i in range(len(items) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def _to_item(lesson: Lesson) -> dict:
    cj = lesson.content_json or {}
    return {
        "lesson_id": str(lesson.id),
        "question": cj.get("question", ""),
        "choices": list(cj.get("choices", [])),
        "answer_index": int(cj.get("answer_index", 0)),
    }


async def build_session(session: AsyncSession, user: User, *, limit: int = 20) -> list[dict]:
    market = user.active_market_code or "GB"
    unlocked = (await session.scalars(
        select(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(
            LessonCompletion.user_id == user.id,
            Lesson.type == "quiz",
            Module.market_code == market,
            Module.archived_at.is_(None),
            Module.published.is_(True),
        )
        .distinct()
    )).all()
    pool = list(unlocked)
    if len(pool) < COLD_START_MIN:
        pool = (await session.scalars(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.type == "quiz",
                Module.market_code == market,
                Module.archived_at.is_(None),
                Module.published.is_(True),
            )
        )).all()
    return [_to_item(le) for le in _shuffle(list(pool))[:limit]]


def score_submission(session_items: list[dict], answers: list[dict]) -> dict:
    key = {it["lesson_id"]: it["answer_index"] for it in session_items}
    correct = combo = max_combo = 0
    for ans in answers:
        lid = ans.get("lesson_id")
        if lid in key and ans.get("choice_index") == key[lid]:
            correct += 1
            combo += 1
            max_combo = max(max_combo, combo)
        else:
            combo = 0
    return {"correct": correct, "max_combo": max_combo, "points": correct * 10 + max_combo * 5}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_quiz_rush_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/quiz_rush_service.py backend/tests/test_quiz_rush_service.py
git commit -m "feat(arcade): quiz-rush session builder + authoritative scoring

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: arcade router + schemas (child endpoints)

**Files:**
- Create: `backend/app/schemas/arcade.py`
- Create: `backend/app/routers/arcade.py`
- Modify: `backend/app/main.py` (register the router)
- Test: `backend/tests/test_arcade_api.py`

**Interfaces:**
- Consumes: `get_current_user` (`app/routers/users.py`), `get_session` (`app/core/database.py`), `arcade_service`, `quiz_rush_service`, `UserProgress`.
- Produces endpoints:
  - `GET /arcade/quiz-rush/session` → `{"items": [{lesson_id, question, choices, answer_index}]}` (answer keys included for instant client feedback — server re-scores).
  - `POST /arcade/quiz-rush/score` body `{"session_items": [...], "answers": [{lesson_id, choice_index, time_ms}]}` → `{"points", "coins_awarded", "personal_best", "leaderboard_rank"}`.
  - `GET /arcade/leaderboard?game=quiz_rush` → `{"entries": [{username, country_code, points}]}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_arcade_api.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_quiz_rush_session_then_score(client):
    # `client` is the existing authed-child fixture (mirror an existing child-auth API test)
    r = await client.get("/arcade/quiz-rush/session")
    assert r.status_code == 200
    items = r.json()["items"]
    # Score a submission that is correct for whatever items came back (may be empty in a bare test DB)
    answers = [{"lesson_id": it["lesson_id"], "choice_index": it["answer_index"], "time_ms": 800} for it in items]
    r2 = await client.post("/arcade/quiz-rush/score", json={"session_items": items, "answers": answers})
    assert r2.status_code == 200
    body = r2.json()
    assert body["points"] == len(items) * 10 + (len(items) * 5 if items else 0)
    assert body["coins_awarded"] >= 0
    assert "personal_best" in body and "leaderboard_rank" in body

async def test_leaderboard_endpoint(client):
    r = await client.get("/arcade/leaderboard?game=quiz_rush")
    assert r.status_code == 200
    assert isinstance(r.json()["entries"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_arcade_api.py -v`
Expected: FAIL — 404 (router not registered).

- [ ] **Step 3: Implement schemas**

```python
# backend/app/schemas/arcade.py
from pydantic import BaseModel


class QuizItem(BaseModel):
    lesson_id: str
    question: str
    choices: list[str]
    answer_index: int


class QuizSessionOut(BaseModel):
    items: list[QuizItem]


class QuizAnswer(BaseModel):
    lesson_id: str
    choice_index: int
    time_ms: int = 0


class QuizScoreIn(BaseModel):
    session_items: list[QuizItem]
    answers: list[QuizAnswer]


class QuizScoreOut(BaseModel):
    points: int
    coins_awarded: int
    personal_best: int
    leaderboard_rank: int | None


class LeaderboardEntryOut(BaseModel):
    username: str
    country_code: str
    points: int


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntryOut]
```

- [ ] **Step 4: Implement the router**

```python
# backend/app/routers/arcade.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.arcade import (
    LeaderboardEntryOut, LeaderboardOut, QuizScoreIn, QuizScoreOut, QuizSessionOut,
)
from app.services import arcade_service, quiz_rush_service

router = APIRouter(prefix="/arcade", tags=["arcade"])


@router.get("/quiz-rush/session", response_model=QuizSessionOut)
async def quiz_rush_session(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> QuizSessionOut:
    items = await quiz_rush_service.build_session(session, user)
    return QuizSessionOut(items=items)


@router.post("/quiz-rush/score", response_model=QuizScoreOut)
async def quiz_rush_score(
    payload: QuizScoreIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QuizScoreOut:
    items = [it.model_dump() for it in payload.session_items]
    answers = [a.model_dump() for a in payload.answers]
    result = quiz_rush_service.score_submission(items, answers)
    market = user.active_market_code or "GB"
    progress = await session.get(UserProgress, user.id)
    coins = await arcade_service.award_arcade_coins(
        session, progress, result["correct"], market_code=market
    )
    await arcade_service.record_score(
        session, user_id=user.id, game="quiz_rush", points=result["points"], market_code=market
    )
    best = await arcade_service.personal_best(session, user_id=user.id, game="quiz_rush")
    board = await arcade_service.weekly_leaderboard(session, game="quiz_rush", market_code=market)
    rank = next((i + 1 for i, row in enumerate(board) if row[0] == user.username), None)
    await session.commit()
    return QuizScoreOut(points=result["points"], coins_awarded=coins, personal_best=best, leaderboard_rank=rank)


@router.get("/leaderboard", response_model=LeaderboardOut)
async def leaderboard(
    game: str = "quiz_rush",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeaderboardOut:
    market = user.active_market_code or "GB"
    rows = await arcade_service.weekly_leaderboard(session, game=game, market_code=market)
    return LeaderboardOut(
        entries=[LeaderboardEntryOut(username=u, country_code=c, points=p) for u, c, p in rows]
    )
```

- [ ] **Step 5: Register the router**

In `backend/app/main.py`, alongside the other `application.include_router(...)` calls, add:

```python
from app.routers import arcade as arcade_router
...
    application.include_router(arcade_router.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_arcade_api.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/arcade.py backend/app/routers/arcade.py backend/app/main.py backend/tests/test_arcade_api.py
git commit -m "feat(arcade): child endpoints — quiz-rush session/score + leaderboard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Frontend API module

**Files:**
- Create: `frontend/src/api/arcade.ts`
- Test: `frontend/src/api/__tests__/arcade.test.ts`

**Interfaces:**
- Consumes: `apiFetch<T>` from `frontend/src/api/client.ts`.
- Produces: types `QuizItem`, `QuizScoreResult`, `ArcadeLeaderboard`; functions `getQuizRushSession()`, `submitQuizRushScore(body)`, `getArcadeLeaderboard(game)`; hooks `useArcadeLeaderboard(game)`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/api/__tests__/arcade.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { getQuizRushSession, submitQuizRushScore } from '../arcade';

describe('arcade api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('GETs a quiz-rush session', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await getQuizRushSession();
    expect(spy).toHaveBeenCalledWith('/arcade/quiz-rush/session');
  });

  it('POSTs a score submission', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(
      { points: 0, coins_awarded: 0, personal_best: 0, leaderboard_rank: null } as never,
    );
    await submitQuizRushScore({ session_items: [], answers: [] });
    expect(spy).toHaveBeenCalledWith('/arcade/quiz-rush/score', expect.objectContaining({ method: 'POST' }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/__tests__/arcade.test.ts`
Expected: FAIL — `../arcade` not found.

- [ ] **Step 3: Implement the API module**

```typescript
// frontend/src/api/arcade.ts
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type QuizItem = { lesson_id: string; question: string; choices: string[]; answer_index: number };
export type QuizSession = { items: QuizItem[] };
export type QuizAnswer = { lesson_id: string; choice_index: number; time_ms: number };
export type QuizScoreBody = { session_items: QuizItem[]; answers: QuizAnswer[] };
export type QuizScoreResult = {
  points: number; coins_awarded: number; personal_best: number; leaderboard_rank: number | null;
};
export type ArcadeLeaderboard = { entries: { username: string; country_code: string; points: number }[] };

export function getQuizRushSession(): Promise<QuizSession> {
  return apiFetch<QuizSession>('/arcade/quiz-rush/session');
}

export function submitQuizRushScore(body: QuizScoreBody): Promise<QuizScoreResult> {
  return apiFetch<QuizScoreResult>('/arcade/quiz-rush/score', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function getArcadeLeaderboard(game = 'quiz_rush'): Promise<ArcadeLeaderboard> {
  return apiFetch<ArcadeLeaderboard>(`/arcade/leaderboard?game=${encodeURIComponent(game)}`);
}

export function useArcadeLeaderboard(game = 'quiz_rush') {
  return useQuery({ queryKey: ['arcade', 'leaderboard', game], queryFn: () => getArcadeLeaderboard(game) });
}
```

> Confirm the `apiFetch` POST signature matches `frontend/src/api/client.ts` (it accepts a second `RequestInit`-like arg with `method`/`body`); adjust if the helper wraps JSON differently (mirror an existing POST call such as in `frontend/src/api/revise.ts`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/__tests__/arcade.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/arcade.ts frontend/src/api/__tests__/arcade.test.ts
git commit -m "feat(arcade): frontend api module

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: i18n strings + Arcade hub page + routes + Home entry

**Files:**
- Create: `frontend/src/locales/en/arcade.json`
- Create: `frontend/src/pages/child/Arcade.tsx`
- Create: `frontend/src/components/child/home/ArcadeHomeCard.tsx`
- Modify: `frontend/src/App.tsx` (routes), `frontend/src/pages/child/Home.tsx` (render the card), namespace registration (`frontend/src/i18n.ts` or equivalent)
- Test: `frontend/src/pages/child/__tests__/Arcade.test.tsx`, `frontend/src/components/child/home/__tests__/ArcadeHomeCard.test.tsx`

**Interfaces:**
- Consumes: `useTranslation('arcade')`, `react-router-dom` `Link`.
- Produces: default-export `Arcade` page listing games (Quiz Rush now; MoneyWord shown "coming soon" placeholder is **out of scope** — list only Quiz Rush); `ArcadeHomeCard` linking to `/arcade`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/child/home/__tests__/ArcadeHomeCard.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import ArcadeHomeCard from '../ArcadeHomeCard';

describe('ArcadeHomeCard', () => {
  it('links to the arcade hub and is accessible', async () => {
    const { container } = render(<MemoryRouter><ArcadeHomeCard /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /arcade/i })).toHaveAttribute('href', '/arcade');
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

```tsx
// frontend/src/pages/child/__tests__/Arcade.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Arcade from '../Arcade';

describe('Arcade hub', () => {
  it('lists Quiz Rush with a play link', () => {
    render(<MemoryRouter><Arcade /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /quiz rush/i })).toHaveAttribute('href', '/arcade/quiz-rush');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/child/__tests__/Arcade.test.tsx src/components/child/home/__tests__/ArcadeHomeCard.test.tsx`
Expected: FAIL — components not found.

- [ ] **Step 3: Add strings**

```json
// frontend/src/locales/en/arcade.json
{
  "hub": { "title": "Penny's Arcade", "subtitle": "Quick games to test what you've learned." },
  "home": { "cardTitle": "Penny's Arcade", "cardCta": "Play a game" },
  "quizRush": {
    "name": "Quiz Rush",
    "tagline": "Answer as many as you can in 60 seconds!",
    "play": "Play",
    "start": "Start",
    "timeLeft": "Time left",
    "score": "Score",
    "combo": "Combo",
    "results": "Results",
    "personalBest": "Your best",
    "coinsEarned": "Coins earned",
    "playAgain": "Play again",
    "backToArcade": "Back to Arcade",
    "noQuestions": "No questions available yet — finish a lesson first!"
  }
}
```

Register the `arcade` namespace where the others are registered (mirror how `revise`/`home` namespaces are added in `frontend/src/i18n.ts`).

- [ ] **Step 4: Implement `ArcadeHomeCard` and `Arcade`**

```tsx
// frontend/src/components/child/home/ArcadeHomeCard.tsx
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function ArcadeHomeCard() {
  const { t } = useTranslation('arcade');
  return (
    <Link
      to="/arcade"
      className="block rounded-xl border border-line bg-card p-4 min-h-[44px] focus-visible:outline focus-visible:outline-2"
    >
      <div className="text-base font-extrabold text-ink">🎮 {t('home.cardTitle')}</div>
      <div className="text-sm text-muted-foreground">{t('home.cardCta')}</div>
    </Link>
  );
}
```

```tsx
// frontend/src/pages/child/Arcade.tsx
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Arcade() {
  const { t } = useTranslation('arcade');
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-extrabold text-ink">{t('hub.title')}</h1>
      <p className="text-sm text-muted-foreground">{t('hub.subtitle')}</p>
      <ul className="space-y-3">
        <li>
          <Link
            to="/arcade/quiz-rush"
            className="block rounded-xl border border-line bg-card p-4 min-h-[44px]"
          >
            <div className="text-base font-extrabold text-ink">⚡ {t('quizRush.name')}</div>
            <div className="text-sm text-muted-foreground">{t('quizRush.tagline')}</div>
          </Link>
        </li>
      </ul>
    </main>
  );
}
```

- [ ] **Step 5: Wire routes + Home card**

In `frontend/src/App.tsx`, inside `<Route element={<Shell />}>`, add (with lazy import matching the file's existing style):

```tsx
import Arcade from '@/pages/child/Arcade';
import QuizRush from '@/pages/child/games/QuizRush';
...
          <Route path="/arcade" element={<Arcade />} />
          <Route path="/arcade/quiz-rush" element={<QuizRush />} />
```

In `frontend/src/pages/child/Home.tsx`, render `<ArcadeHomeCard />` in the home layout (near the existing quick-links / cards):

```tsx
import ArcadeHomeCard from '@/components/child/home/ArcadeHomeCard';
...
        <ArcadeHomeCard />
```

> `QuizRush` is created in Task 7; the route import will not resolve until then. Sequence Task 7 before running the full app build, or stub the import. (SDD runs tasks in order, so this resolves at Task 7.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/child/__tests__/Arcade.test.tsx src/components/child/home/__tests__/ArcadeHomeCard.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/locales/en/arcade.json frontend/src/pages/child/Arcade.tsx frontend/src/components/child/home/ArcadeHomeCard.tsx frontend/src/App.tsx frontend/src/pages/child/Home.tsx frontend/src/i18n.ts frontend/src/pages/child/__tests__/Arcade.test.tsx frontend/src/components/child/home/__tests__/ArcadeHomeCard.test.tsx
git commit -m "feat(arcade): hub page, Home entry card, routes + i18n

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Quiz Rush game page

**Files:**
- Create: `frontend/src/pages/child/games/QuizRush.tsx`
- Test: `frontend/src/pages/child/games/__tests__/QuizRush.test.tsx`

**Interfaces:**
- Consumes: `getQuizRushSession`, `submitQuizRushScore` (Task 5); `useTranslation('arcade')`.
- Produces: default-export `QuizRush` page. States: idle → playing (60s countdown, one question at a time, instant correct/incorrect feedback using the included `answer_index`, combo counter) → results (final points, coins earned, personal best, play again / back).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/child/games/__tests__/QuizRush.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import QuizRush from '../QuizRush';
import * as api from '@/api/arcade';

vi.mock('@/api/arcade');

beforeEach(() => {
  vi.mocked(api.getQuizRushSession).mockResolvedValue({
    items: [
      { lesson_id: 'a', question: 'What is saving?', choices: ['Keeping money', 'Spending all'], answer_index: 0 },
    ],
  });
  vi.mocked(api.submitQuizRushScore).mockResolvedValue({
    points: 15, coins_awarded: 1, personal_best: 15, leaderboard_rank: 1,
  });
});

describe('QuizRush', () => {
  it('plays a question and reaches results', async () => {
    render(<MemoryRouter><QuizRush /></MemoryRouter>);
    await userEvent.click(await screen.findByRole('button', { name: /start/i }));
    await userEvent.click(await screen.findByRole('button', { name: /keeping money/i }));
    await waitFor(() => expect(screen.getByText(/your best/i)).toBeInTheDocument());
  });

  it('has no axe violations on the start screen', async () => {
    const { container } = render(<MemoryRouter><QuizRush /></MemoryRouter>);
    await screen.findByRole('button', { name: /start/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/child/games/__tests__/QuizRush.test.tsx`
Expected: FAIL — component not found.

- [ ] **Step 3: Implement the game page**

```tsx
// frontend/src/pages/child/games/QuizRush.tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getQuizRushSession, submitQuizRushScore, type QuizItem, type QuizScoreResult } from '@/api/arcade';

const ROUND_SECONDS = 60;
type Phase = 'idle' | 'playing' | 'done';

export default function QuizRush() {
  const { t } = useTranslation('arcade');
  const [phase, setPhase] = useState<Phase>('idle');
  const [items, setItems] = useState<QuizItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [combo, setCombo] = useState(0);
  const [seconds, setSeconds] = useState(ROUND_SECONDS);
  const answers = useRef<{ lesson_id: string; choice_index: number; time_ms: number }[]>([]);
  const [result, setResult] = useState<QuizScoreResult | null>(null);

  const finish = useCallback(async () => {
    setPhase('done');
    const res = await submitQuizRushScore({ session_items: items, answers: answers.current });
    setResult(res);
  }, [items]);

  useEffect(() => {
    if (phase !== 'playing') return;
    if (seconds <= 0) { void finish(); return; }
    const id = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, seconds, finish]);

  async function start() {
    const session = await getQuizRushSession();
    setItems(session.items);
    answers.current = [];
    setIdx(0); setCombo(0); setSeconds(ROUND_SECONDS); setResult(null);
    setPhase('playing');
  }

  function answer(choice: number) {
    const it = items[idx];
    answers.current.push({ lesson_id: it.lesson_id, choice_index: choice, time_ms: 0 });
    setCombo((c) => (choice === it.answer_index ? c + 1 : 0));
    if (idx + 1 >= items.length) void finish();
    else setIdx((i) => i + 1);
  }

  if (phase === 'idle') {
    return (
      <main className="mx-auto max-w-md space-y-4 p-4 text-center">
        <h1 className="text-xl font-extrabold text-ink">⚡ {t('quizRush.name')}</h1>
        <p className="text-sm text-muted-foreground">{t('quizRush.tagline')}</p>
        <button type="button" onClick={start}
          className="min-h-[44px] rounded-md bg-brand-600 px-6 py-2 font-semibold text-white">
          {t('quizRush.start')}
        </button>
      </main>
    );
  }

  if (phase === 'done') {
    return (
      <main className="mx-auto max-w-md space-y-3 p-4 text-center">
        <h2 className="text-lg font-extrabold text-ink">{t('quizRush.results')}</h2>
        <p className="text-3xl font-extrabold text-ink">{result?.points ?? 0}</p>
        <p className="text-sm text-muted-foreground">{t('quizRush.personalBest')}: {result?.personal_best ?? 0}</p>
        <p className="text-sm text-muted-foreground">{t('quizRush.coinsEarned')}: {result?.coins_awarded ?? 0}</p>
        <div className="flex justify-center gap-2">
          <button type="button" onClick={start} className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 font-semibold text-white">
            {t('quizRush.playAgain')}
          </button>
          <Link to="/arcade" className="min-h-[44px] rounded-md border border-line px-4 py-2 font-semibold text-ink">
            {t('quizRush.backToArcade')}
          </Link>
        </div>
      </main>
    );
  }

  const it = items[idx];
  if (!it) return <main className="p-4 text-center text-sm text-muted-foreground">{t('quizRush.noQuestions')}</main>;

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <div className="flex justify-between text-sm font-semibold text-ink" aria-live="polite">
        <span>{t('quizRush.timeLeft')}: {seconds}s</span>
        <span>{t('quizRush.combo')}: {combo}</span>
      </div>
      <h2 className="text-lg font-bold text-ink">{it.question}</h2>
      <ul className="space-y-2">
        {it.choices.map((choice, i) => (
          <li key={i}>
            <button type="button" onClick={() => answer(i)}
              className="block w-full min-h-[44px] rounded-md border border-line bg-card px-4 py-2 text-left text-ink">
              {choice}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/child/games/__tests__/QuizRush.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/games/QuizRush.tsx frontend/src/pages/child/games/__tests__/QuizRush.test.tsx
git commit -m "feat(arcade): Quiz Rush game page

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Full verification + native sync + docs + push

**Files:**
- Modify: `docs/MASTER-BACKLOG.md`, `AGENTS.md` (note the new `/arcade` surface), and any `.cursor` doc that lists child routes.

- [ ] **Step 1: Backend gates**

Run: `cd backend && ruff check . && python -m pytest -q`
Expected: ruff clean; all tests pass (including the new arcade tests).

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run build`
Expected: tsc clean, lint clean, all vitest pass (incl. vitest-axe), build succeeds.

- [ ] **Step 3: iOS bundle sync**

Run: `cd frontend && npx cap sync ios`
Expected: sync completes (the new `/arcade` screens ship in the native bundle on the next device build).

- [ ] **Step 4: Update docs**

Add a `MASTER-BACKLOG.md` entry describing Phase 1 (hub + Quiz Rush + rewards/leaderboard foundation, `arcade_scores` migration `f1a2b3c4d5e6`) and note Phase 2 (MoneyWord) is the next plan. Mention the new child routes in `AGENTS.md`/`.cursor` route lists.

- [ ] **Step 5: Commit + push**

```bash
git add docs/MASTER-BACKLOG.md AGENTS.md
git commit -m "docs: log Penny's Arcade Phase 1 (hub + Quiz Rush)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 6: Deploy reminders (operator)**

- Backend deploys via Railway on green CI (the `f1a2b3c4d5e6` migration runs on deploy). **Per standing rule, ask whether to take a prod DB snapshot before this additive migration is applied.**
- Frontend is a **manual** Vercel prod deploy: `cd frontend && vercel --prod --force --yes` then `vercel alias set <frontend-hash>-investikid.vercel.app app.investikid.ai`.

---

## Self-Review (completed)

- **Spec coverage:** hub (Task 6), Quiz Rush incl. unlocked-concept preference + cold-start fallback (Tasks 3, 7), dual rewards — capped coins via `award_arcade_coins` + Arcade Points via `record_score` (Tasks 2, 4), weekly per-market leaderboard + personal bests (Tasks 2, 4), server-authoritative scoring (Tasks 3, 4), Home daily-return entry (Task 6 — the MoneyWord *daily* card itself is Phase 2), a11y/i18n (Tasks 6, 7), additive migration + 25/day cap + cold-start <10 (Global Constraints, Tasks 1–3). **MoneyWord, the word bank, daily-schedule/daily-completion tables, and the Home *daily* card are intentionally Phase 2** (separate plan) and are not in this plan.
- **Placeholders:** none — every code step contains complete code. The two "confirm X" notes (UserProgress tablename; apiFetch POST shape) are concrete verification instructions pointing at named example files, not deferred work.
- **Type consistency:** `ArcadeScore(game, points, market_code)` consistent across Tasks 1/2/4; `build_session`→items shape `{lesson_id, question, choices, answer_index}` consistent across Tasks 3/4/5/7; `score_submission` return `{correct, max_combo, points}` consistent Tasks 3/4; `award_arcade_coins(...)->int` consistent Tasks 2/4.
