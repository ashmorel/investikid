# Penny's Arcade — Phase 2 Implementation Plan (MoneyWord + word bank + daily infra)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship **MoneyWord** — a daily Wordle-style finance-term puzzle (the Arcade's daily-return anchor) — plus the LLM-assisted, admin-approved word bank that feeds it and the Home "daily" card.

**Architecture:** Three new tables (`arcade_words` bank, `arcade_daily_schedule` per-day word assignment, `arcade_daily_play` per-child daily progress). A `moneyword_service` handles guess evaluation (classic two-pass Wordle algorithm), lazy no-repeat daily word selection, and play/completion (which reuses the Phase-1 `arcade_service` for capped coins + the shared leaderboard, and `record_daily_activity` for the streak). An `arcade_word_admin_service` proposes finance words + kid-safe definitions via the existing LLM client (moderated), gated behind an admin approval queue. Frontend adds the MoneyWord game page, a Home daily card, and the admin word-bank page. Launch English-only.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic; existing LLM client (`get_llm_client`) + `moderate_output` + `with_generation_framing`; React + Vite + TS + TanStack Query + react-i18next + Tailwind. CI: backend ruff + pytest; frontend tsc + eslint + vitest + vitest-axe + build.

**Reference spec:** `docs/superpowers/specs/2026-06-23-penny-arcade-design.md` (§4 MoneyWord, §5 word bank). Builds on Phase 1 (LIVE): `arcade_scores`, `arcade_service` (`award_arcade_coins`, `record_score`, `weekly_leaderboard`, `personal_best`), the `/arcade` router, and the frontend `/arcade` hub + `arcade.json` namespace.

## Global Constraints

- DB change = hand-written, chained Alembic migration. Current head is **`f1a2b3c4d5e6`** (Phase 1); the new migration's `down_revision` must be `f1a2b3c4d5e6` (run `alembic heads` to reconfirm). Additive only.
- One **MoneyWord** word per **language** per **UTC day** — same word for everyone sharing a language (UTC, matching the app's existing daily mechanics). Launch language = `"en"` only; carry `language` on every relevant row for the future.
- Word constraints: 4–8 letters, uppercase A–Z. **6 guesses.** A guess is validated for length + A–Z only (NOT dictionary membership — kid-friendly, avoids "not a word" frustration; this is a deliberate relaxation of spec §4).
- Guess feedback uses the classic two-pass Wordle algorithm with correct **duplicate-letter** handling: pass 1 marks exact-position `correct` and consumes those answer letters; pass 2 marks `present` only while unconsumed copies of that letter remain in the answer, else `absent`.
- Reward streams reuse Phase 1 exactly: capped coins via `arcade_service.award_arcade_coins(...)` (25/day shared arcade cap); Arcade Points via `arcade_service.record_score(session, user_id=..., game="moneyword", points=..., market_code=...)` so MoneyWord shares the existing weekly per-market leaderboard + personal bests. Points scale **inversely with guesses used** (fewer guesses → more points). Solving credits the daily streak via `record_daily_activity(progress, today)`.
- One play per child per day, server-authoritative: the server tracks guesses; a completed day cannot be replayed. The **answer word is never sent to the client until the puzzle ends** (solved or out of guesses) — then the kid-safe definition is revealed.
- LLM word generation: `get_llm_client("authoring").complete(system_prompt, messages, temperature=0.4, max_tokens=..., response_format="json")`, parse with `extract_json_list(json.loads(raw))`; frame the system prompt with `with_generation_framing(...)` (non-interactive generated text); **every candidate definition passes `moderate_output(text, surface="lesson")`** before it is stored. Only `status="approved"` words ever enter daily rotation.
- Child endpoints require `get_current_user`; admin endpoints require `get_current_admin` (router-level `dependencies=[Depends(get_current_admin)]`, like `app/routers/video_curation.py`). New admin LLM endpoint must be rate-limited (`@limiter.limit`, `request: Request`) like sibling LLM endpoints. New `/internal/*` cron endpoints (none here) would need the CSRF allowlist — N/A this plan.
- Kids' app: no child free-text beyond letter tiles; all definitions LLM-moderated **and** human-approved. WCAG 2.2 AA — letter feedback **not colour-only** (icon/label per state), ≥44px tap targets, keyboard play, screen-reader announcements; new UI gets `vitest-axe`. All strings localised (extend `arcade.json` + a new `arcade` admin section or reuse `admin.json`).
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")`, shared `client` / `admin_client` / `db_session` fixtures (see `backend/tests/test_arcade_api.py`, `backend/tests/test_video_curation_api.py`). Build `User`/`UserProgress`/`Module`/`Lesson` by copying required fields from existing tests — never invent fields.
- Commit to `main` (beta); messages end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. iOS-visible (new child screens) → `npm run build && npx cap sync ios` (Task 11).

---

## File Structure

**Backend create:** `app/models/arcade_word.py` (`ArcadeWord`, `ArcadeDailySchedule`, `ArcadeDailyPlay`); `alembic/versions/<rev>_moneyword.py`; `app/services/moneyword_service.py`; `app/services/arcade_word_admin_service.py`; `app/seed/arcade_words.py` (starter approved words); `app/routers/arcade_words_admin.py`; tests `test_moneyword_eval.py`, `test_moneyword_service.py`, `test_arcade_word_admin_service.py`, `test_arcade_words_admin_api.py`, and additions to `test_arcade_api.py`.
**Backend modify:** `app/models/__init__.py` (register models); `app/routers/arcade.py` (+ `moneyword/today`, `moneyword/guess`); `app/schemas/arcade.py` (+ MoneyWord schemas); `app/main.py` (register admin router); `app/seed/run.py` (call the starter seed).
**Frontend create:** `src/pages/child/games/MoneyWord.tsx`; `src/components/child/home/ArcadeDailyCard.tsx`; `src/components/admin/ArcadeWordBank.tsx`; `src/api/moneyword.ts`; `src/api/arcadeWordsAdmin.ts`; tests alongside each.
**Frontend modify:** `src/api/arcade.ts` (or new module) ; `src/App.tsx` (`/arcade/moneyword` + admin route); `src/pages/child/Arcade.tsx` (MoneyWord hub entry); `src/pages/child/Home.tsx` (render `ArcadeDailyCard`); `src/components/admin/AdminSidebar.tsx` (nav item); `src/locales/en/arcade.json` + `src/locales/en/admin.json`.

---

### Task 1: MoneyWord data model + migration

**Files:** Create `backend/app/models/arcade_word.py`, `backend/alembic/versions/a1b2c3d4e5f6_moneyword.py`; Modify `backend/app/models/__init__.py`; Test `backend/tests/test_moneyword_model.py`.

**Interfaces — Produces:**
- `ArcadeWord` (`arcade_words`): `id: UUID`, `word: str` (4–8, A–Z upper), `definition: str`, `language: str` (default `"en"`), `length: int`, `status: str` (`pending`|`approved`|`rejected`, default `pending`), `source: str` (`llm`|`manual`), `created_at`. Unique `(word, language)`.
- `ArcadeDailySchedule` (`arcade_daily_schedule`): `id: UUID`, `puzzle_date: date`, `language: str`, `word_id: UUID` (FK `arcade_words.id`), `created_at`. Unique `(puzzle_date, language)`.
- `ArcadeDailyPlay` (`arcade_daily_play`): `id: UUID`, `user_id: UUID` (FK `users.id`, CASCADE), `puzzle_date: date`, `language: str`, `guesses: list[str]` (JSON, default `[]`), `solved: bool` (default False), `completed: bool` (default False), `created_at`, `updated_at`. Unique `(user_id, puzzle_date)`.

- [ ] **Step 1: Write the failing test** — `test_moneyword_model.py` asserts each model persists and the unique constraints exist (mirror `backend/tests/test_arcade_model.py` from Phase 1; build a `User` inline for the play row).

```python
import pytest
from sqlalchemy import select
from app.models.arcade_word import ArcadeWord, ArcadeDailySchedule, ArcadeDailyPlay

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_word_persists(db_session):
    db_session.add(ArcadeWord(word="ASSET", definition="Something valuable you own.",
                              language="en", length=5, status="approved", source="manual"))
    await db_session.flush()
    row = (await db_session.scalars(select(ArcadeWord))).first()
    assert row.word == "ASSET" and row.status == "approved" and row.length == 5
```

- [ ] **Step 2: Run** `cd backend && python -m pytest tests/test_moneyword_model.py -v` → FAIL (module missing).
- [ ] **Step 3: Create the models** (mirror the SQLAlchemy style of `app/models/arcade.py` and `app/models/content.py`):

```python
# backend/app/models/arcade_word.py
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArcadeWord(Base):
    __tablename__ = "arcade_words"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word: Mapped[str] = mapped_column(String(8), nullable=False)
    definition: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="en", index=True)
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="pending", index=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False)  # llm | manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("word", "language", name="uq_arcade_word_lang"),)


class ArcadeDailySchedule(Base):
    __tablename__ = "arcade_daily_schedule"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    puzzle_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    word_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("arcade_words.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("puzzle_date", "language", name="uq_arcade_daily_date_lang"),)


class ArcadeDailyPlay(Base):
    __tablename__ = "arcade_daily_play"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    puzzle_date: Mapped[date] = mapped_column(Date, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    guesses: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    solved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "puzzle_date", name="uq_arcade_daily_play_user_date"),)
```

Register all three in `app/models/__init__.py` (import them so `create_all`/Alembic autogen-parity sees them — match how `ArcadeScore` was added in Phase 1).

- [ ] **Step 4: Write the migration** — `down_revision = "f1a2b3c4d5e6"`; `op.create_table` for the three tables with the unique constraints + indexes above; full `downgrade()` dropping them in reverse FK order (`arcade_daily_play`, `arcade_daily_schedule`, `arcade_words`). Mirror `alembic/versions/f1a2b3c4d5e6_arcade_foundation.py`.
- [ ] **Step 5: Run** the model test → PASS.
- [ ] **Step 6: Commit** `feat(moneyword): word bank + daily schedule + daily play models & migration`.

---

### Task 2: Guess evaluation (pure Wordle algorithm)

**Files:** Create `backend/app/services/moneyword_service.py` (start it here); Test `backend/tests/test_moneyword_eval.py`.

**Interfaces — Produces:** `evaluate_guess(answer: str, guess: str) -> list[str]` returning one of `"correct"|"present"|"absent"` per position, two-pass with duplicate handling. `MAX_GUESSES = 6`.

- [ ] **Step 1: Write the failing tests:**

```python
# backend/tests/test_moneyword_eval.py
from app.services.moneyword_service import evaluate_guess

def test_all_correct():
    assert evaluate_guess("ASSET", "ASSET") == ["correct"] * 5

def test_present_and_absent():
    # answer ASSET, guess STEAL: S present, T present, E present, A present, L absent
    assert evaluate_guess("ASSET", "STEAL") == ["present", "present", "present", "present", "absent"]

def test_duplicate_letters_consume_once():
    # answer ROBOT (two O), guess BOOKS: B present, O correct(pos2), O present? — only one O left after the correct
    res = evaluate_guess("ROBOT", "OOOOO")
    # ROBOT has 2 O's at positions 1 and 3 → those two are correct, the other three O's are absent
    assert res == ["absent", "correct", "absent", "correct", "absent"]
```

- [ ] **Step 2: Run** `cd backend && python -m pytest tests/test_moneyword_eval.py -v` → FAIL.
- [ ] **Step 3: Implement:**

```python
# backend/app/services/moneyword_service.py  (module start)
from collections import Counter

MAX_GUESSES = 6


def evaluate_guess(answer: str, guess: str) -> list[str]:
    answer, guess = answer.upper(), guess.upper()
    result = ["absent"] * len(guess)
    remaining = Counter(answer)
    # Pass 1: exact matches consume answer letters.
    for i, ch in enumerate(guess):
        if i < len(answer) and ch == answer[i]:
            result[i] = "correct"
            remaining[ch] -= 1
    # Pass 2: present only while an unconsumed copy remains.
    for i, ch in enumerate(guess):
        if result[i] == "correct":
            continue
        if remaining.get(ch, 0) > 0:
            result[i] = "present"
            remaining[ch] -= 1
    return result
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(moneyword): pure two-pass guess evaluation`.

---

### Task 3: Daily word selection (lazy, no-repeat)

**Files:** Modify `backend/app/services/moneyword_service.py`; Test `backend/tests/test_moneyword_service.py`.

**Interfaces — Consumes:** `ArcadeWord`, `ArcadeDailySchedule` (Task 1). **Produces:** `async def pick_daily_word(session, *, language, today) -> ArcadeWord` — returns the scheduled approved word for `(today, language)`, creating the schedule row on first call: choose the approved word least-recently-scheduled (an approved word with no schedule row yet, else the one whose most-recent schedule is oldest), insert `(today, language)`; on the unique-constraint race, re-read the existing row. Raises `NoApprovedWords` (custom exception) if the bank has zero approved words for the language.

- [ ] **Step 1: Write the failing tests** — seed two approved words; first `pick_daily_word(today=D1)` creates a schedule row and returns a word; calling again for D1 returns the **same** word (idempotent); `pick_daily_word(today=D2)` returns the **other** word (no-repeat) until the bank is exhausted; zero approved words → raises `NoApprovedWords`.

```python
import datetime as dt
import pytest
from app.models.arcade_word import ArcadeWord
from app.services.moneyword_service import pick_daily_word, NoApprovedWords

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _seed_words(db_session, *words):
    for w in words:
        db_session.add(ArcadeWord(word=w, definition=f"def {w}", language="en",
                                  length=len(w), status="approved", source="manual"))
    await db_session.flush()

async def test_no_words_raises(db_session):
    with pytest.raises(NoApprovedWords):
        await pick_daily_word(db_session, language="en", today=dt.date(2026, 7, 1))

async def test_lazy_idempotent_and_no_repeat(db_session):
    await _seed_words(db_session, "ASSET", "BUDGET")
    d1 = dt.date(2026, 7, 2); d2 = dt.date(2026, 7, 3)
    w1 = await pick_daily_word(db_session, language="en", today=d1)
    w1b = await pick_daily_word(db_session, language="en", today=d1)
    assert w1.id == w1b.id                      # idempotent same-day
    w2 = await pick_daily_word(db_session, language="en", today=d2)
    assert w2.id != w1.id                        # no-repeat next day
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (append to `moneyword_service.py`):

```python
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade_word import ArcadeDailySchedule, ArcadeWord


class NoApprovedWords(Exception):
    """No approved MoneyWord words exist for the requested language."""


async def pick_daily_word(session: AsyncSession, *, language: str, today: date) -> ArcadeWord:
    existing = await session.scalar(
        select(ArcadeDailySchedule).where(
            ArcadeDailySchedule.puzzle_date == today, ArcadeDailySchedule.language == language
        )
    )
    if existing is not None:
        return await session.get(ArcadeWord, existing.word_id)

    # Least-recently-scheduled approved word: never-scheduled first (NULL last-scheduled),
    # then oldest most-recent schedule.
    last_sched = (
        select(ArcadeDailySchedule.word_id, func.max(ArcadeDailySchedule.puzzle_date).label("last"))
        .group_by(ArcadeDailySchedule.word_id)
        .subquery()
    )
    word = await session.scalar(
        select(ArcadeWord)
        .outerjoin(last_sched, last_sched.c.word_id == ArcadeWord.id)
        .where(ArcadeWord.status == "approved", ArcadeWord.language == language)
        .order_by(last_sched.c.last.asc().nulls_first(), ArcadeWord.created_at.asc())
        .limit(1)
    )
    if word is None:
        raise NoApprovedWords(language)
    session.add(ArcadeDailySchedule(puzzle_date=today, language=language, word_id=word.id))
    try:
        await session.flush()
    except IntegrityError:
        # Concurrent first-request created the row — re-read the winner.
        await session.rollback()
        existing = await session.scalar(
            select(ArcadeDailySchedule).where(
                ArcadeDailySchedule.puzzle_date == today, ArcadeDailySchedule.language == language
            )
        )
        return await session.get(ArcadeWord, existing.word_id)
    return word
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(moneyword): lazy no-repeat daily word selection`.

---

### Task 4: Play a guess + completion (rewards, streak, idempotent)

**Files:** Modify `backend/app/services/moneyword_service.py`; Test `backend/tests/test_moneyword_play.py`.

**Interfaces — Consumes:** `pick_daily_word`, `evaluate_guess`, `MAX_GUESSES` (this module); `arcade_service.award_arcade_coins`, `arcade_service.record_score` (Phase 1); `record_daily_activity` (`app/services/content_service.py`); `ArcadeDailyPlay`, `UserProgress`, `User`. **Produces:**
- `async def get_today(session, user, *, today) -> dict` → `{"length": int, "max_guesses": MAX_GUESSES, "guesses": [{"word": str, "feedback": [str]}], "completed": bool, "solved": bool, "definition": str | None, "already_played": bool}` (definition only when completed; never leaks the answer mid-game).
- `async def play_guess(session, user, *, guess, today) -> dict` → validates (length == today's word length, A–Z only; 422 via a raised `ValueError` the router maps), rejects if `completed` (raise `AlreadyCompleted`), appends the guess, evaluates, and on completion (solved or `len(guesses) == MAX_GUESSES`) records score+coins+streak and reveals the definition. Returns the same shape as `get_today`. Points = `max(1, (MAX_GUESSES - guesses_used + 1)) * 10` when solved, else `0`. Coins awarded = `5` on solve (capped via `award_arcade_coins`), `0` otherwise.

- [ ] **Step 1: Write the failing tests** — seed one approved word `"ASSET"`; a correct first guess → solved, completed, definition revealed, points > 0, an `arcade_scores` row with `game="moneyword"` exists, streak advanced; a second `play_guess` same day → `AlreadyCompleted`; a wrong guess of wrong length → `ValueError`. Build `User`+`UserProgress` inline as in `test_arcade_service.py`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (append):

```python
from app.models.user import User, UserProgress
from app.services import arcade_service
from app.services.content_service import record_daily_activity


class AlreadyCompleted(Exception):
    pass


async def _load_play(session, user, today, language):
    play = await session.scalar(
        select(ArcadeDailyPlay).where(
            ArcadeDailyPlay.user_id == user.id, ArcadeDailyPlay.puzzle_date == today
        )
    )
    if play is None:
        play = ArcadeDailyPlay(user_id=user.id, puzzle_date=today, language=language, guesses=[])
        session.add(play)
        await session.flush()
    return play


def _state(word: ArcadeWord, play: ArcadeDailyPlay) -> dict:
    return {
        "length": word.length,
        "max_guesses": MAX_GUESSES,
        "guesses": [{"word": g, "feedback": evaluate_guess(word.word, g)} for g in play.guesses],
        "completed": play.completed,
        "solved": play.solved,
        "definition": word.definition if play.completed else None,
        "already_played": play.completed,
    }


async def get_today(session, user, *, today, language: str = "en") -> dict:
    word = await pick_daily_word(session, language=language, today=today)
    play = await session.scalar(
        select(ArcadeDailyPlay).where(
            ArcadeDailyPlay.user_id == user.id, ArcadeDailyPlay.puzzle_date == today
        )
    )
    if play is None:  # no row yet — empty board, don't create until first guess
        return {"length": word.length, "max_guesses": MAX_GUESSES, "guesses": [],
                "completed": False, "solved": False, "definition": None, "already_played": False}
    return _state(word, play)


async def play_guess(session, user, *, guess, today, language: str = "en") -> dict:
    word = await pick_daily_word(session, language=language, today=today)
    g = (guess or "").strip().upper()
    if len(g) != word.length or not g.isalpha():
        raise ValueError("guess must be the right length and letters only")
    play = await _load_play(session, user, today, language)
    if play.completed:
        raise AlreadyCompleted()
    play.guesses = [*play.guesses, g]
    solved = g == word.word
    out_of_guesses = len(play.guesses) >= MAX_GUESSES
    if solved or out_of_guesses:
        play.completed = True
        play.solved = solved
        if solved:
            points = max(1, MAX_GUESSES - len(play.guesses) + 1) * 10
            progress = await session.get(UserProgress, user.id)
            market = user.active_market_code or "GB"
            await arcade_service.award_arcade_coins(session, progress, 5, market_code=market)
            await arcade_service.record_score(session, user_id=user.id, game="moneyword",
                                               points=points, market_code=market)
            record_daily_activity(progress, today)
    await session.flush()
    return _state(word, play)
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(moneyword): play/guess with completion, rewards, streak credit`.

---

### Task 5: Word-bank admin service (LLM suggest + moderation) + starter seed

**Files:** Create `backend/app/services/arcade_word_admin_service.py`, `backend/app/seed/arcade_words.py`; Modify `backend/app/seed/run.py`; Test `backend/tests/test_arcade_word_admin_service.py`.

**Interfaces — Produces:**
- `async def suggest_words(session, *, language="en", count=10) -> dict` → calls the LLM for `count` finance words + kid-safe definitions, validates each (4–8 A–Z, unique per language, definition non-empty ≤180 chars, no proper nouns/answer-leak), runs `moderate_output(definition, surface="lesson")`, inserts surviving ones as `status="pending", source="llm"`. Returns `{"created": int, "skipped": int}`. Idempotent on `(word, language)`.
- `async def seed_arcade_words(session) -> int` → idempotent upsert of ~18 hand-verified approved English starter words (so the daily puzzle works at launch); returns count. Called from `seed/run.py`.

- [ ] **Step 1: Write the failing tests** — for `suggest_words`, inject a fake LLM client (monkeypatch `get_llm_client`) returning a JSON list of `{word, definition}` incl. one invalid (too long) + one duplicate of a seeded word; assert only the valid/new ones are inserted as `pending` and `moderate_output` was applied. For the seed, call `seed_arcade_words` twice and assert no duplicates + all `approved`. (Mirror the LLM-mock style of existing suggester tests, e.g. `test_market_module_suggester.py` if present.)
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the service (LLM call + parse + validate + moderate + insert) and the seed:

```python
# backend/app/services/arcade_word_admin_service.py
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade_word import ArcadeWord
from app.services.guardrails import with_generation_framing
from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.moderation import moderate_output

_SYS = with_generation_framing(
    "You generate short finance vocabulary words for a kids' money-learning word game. "
    "Each item: an UPPERCASE common finance term 4-8 letters A-Z only (no spaces, hyphens, "
    "proper nouns, or plurals of a shorter root), plus a one-sentence kid-friendly definition "
    "(<=180 chars) that does NOT contain the word itself. Return a JSON array of "
    '{"word": "...", "definition": "..."}.'
)


def _valid_word(w: str) -> bool:
    return 4 <= len(w) <= 8 and w.isalpha() and w.isascii()


async def suggest_words(session: AsyncSession, *, language: str = "en", count: int = 10) -> dict:
    raw = await get_llm_client("authoring").complete(
        _SYS, [{"role": "user", "content": f"Generate {count} words."}],
        temperature=0.5, max_tokens=1200, response_format="json",
    )
    items = extract_json_list(json.loads(raw))
    created = skipped = 0
    for it in items:
        word = str(it.get("word", "")).strip().upper()
        definition = str(it.get("definition", "")).strip()
        if not _valid_word(word) or not definition or len(definition) > 180 or word in definition.upper():
            skipped += 1
            continue
        exists = await session.scalar(
            select(ArcadeWord).where(ArcadeWord.word == word, ArcadeWord.language == language)
        )
        if exists is not None:
            skipped += 1
            continue
        mod = await moderate_output(definition, surface="lesson")
        if not mod.allowed:
            skipped += 1
            continue
        session.add(ArcadeWord(word=word, definition=definition, language=language,
                               length=len(word), status="pending", source="llm"))
        created += 1
    await session.flush()
    return {"created": created, "skipped": skipped}
```

> Confirm `moderate_output`'s result attribute name (`.allowed` vs `.is_allowed`/`.flagged`) from `app/services/moderation.py:ModerationResult` and use the real one.

The seed file holds an inline list of ~18 `{word, definition}` (e.g. SAVE, BUDGET, COIN, BANK, DEBT, ASSET, INCOME, SPEND, INVEST, STOCK, INTEREST, PROFIT, WAGES, CASH, CREDIT, REFUND, VALUE, TAXES) inserted/upserted as `status="approved", source="manual", language="en"` (verify each is 4–8 letters). Wire `seed_arcade_words(session)` into `seed/run.py` next to the other seeds.

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(moneyword): LLM word-bank suggester + moderated approval + starter seed`.

---

### Task 6: MoneyWord child endpoints

**Files:** Modify `backend/app/routers/arcade.py`, `backend/app/schemas/arcade.py`; Test add to `backend/tests/test_arcade_api.py`.

**Interfaces — Produces:** `GET /arcade/moneyword/today` → today's state (no answer). `POST /arcade/moneyword/guess` body `{"guess": str}` → state after the guess (definition only on completion). Both `get_current_user`, rate-limited (`@limiter.limit`, `request: Request`): today `60/hour`, guess `60/hour`. `ValueError` from `play_guess` → 422; `AlreadyCompleted` → 409; `NoApprovedWords` → 503 (`{"detail": "no_daily_word"}`).

- [ ] **Step 1: Write failing API tests** (authed `client`): with no approved words, `GET /arcade/moneyword/today` → 503. Then (seed an approved word in the test DB via `db_session`), `GET today` → 200 with `length`, `completed=false`; `POST guess` with the correct word → `solved=true, completed=true, definition` present; a second guess → 409.
- [ ] **Step 2: Run** → FAIL (404). **Step 3:** add schemas (`MoneyWordStateOut`, `MoneyWordGuessIn`) + the two routes (UTC `today = datetime.now(UTC).date()`, `language="en"`), mapping the service exceptions to the status codes above. **Step 4:** Run → PASS. **Step 5:** Commit `feat(moneyword): child today/guess endpoints`.

---

### Task 7: Word-bank admin endpoints

**Files:** Create `backend/app/routers/arcade_words_admin.py`; Modify `backend/app/main.py`; Test `backend/tests/test_arcade_words_admin_api.py`.

**Interfaces — Produces** (router prefix `/admin/arcade-words`, `dependencies=[Depends(get_current_admin)]`): `POST /suggest` (rate-limited `@limiter.limit("5/minute")`, `request: Request`) → `{"created","skipped"}`; `GET ?status=pending` → list of words; `POST /{id}/approve` (optional body to edit word/definition, re-validates 4–8 A–Z) → the approved word; `POST /{id}/reject` → status `rejected`. Only approval flips `status` to `approved`.

- [ ] **Step 1: Write failing API tests** (`admin_client`): seed a `pending` word; `GET ?status=pending` returns it; `approve` flips to `approved`; an over-length edit on approve → 422; `reject` flips to `rejected`. (Mirror `test_video_curation_api.py`.) **Step 2:** Run → FAIL. **Step 3:** implement router + register in `main.py`. **Step 4:** Run → PASS. **Step 5:** Commit `feat(moneyword): admin word-bank suggest/list/approve/reject`.

---

### Task 8: Frontend API modules (MoneyWord + admin word bank)

**Files:** Create `frontend/src/api/moneyword.ts`, `frontend/src/api/arcadeWordsAdmin.ts`; Tests alongside.

**Interfaces — Produces:** `moneyword.ts`: types `MoneyWordState` (`length`, `max_guesses`, `guesses: {word,feedback:string[]}[]`, `completed`, `solved`, `definition: string|null`), `getMoneyWordToday()`, `submitMoneyWordGuess(guess)`. `arcadeWordsAdmin.ts`: `listArcadeWords(status)`, `suggestArcadeWords(count)`, `approveArcadeWord(id, edits?)`, `rejectArcadeWord(id)` + a `useArcadeWords(status)` hook. Mirror Phase-1 `src/api/arcade.ts` exactly (incl. the `T | null` return from `apiFetch` — null-guard in consumers).

- [ ] TDD per the Phase-1 api test pattern (spy on `apiFetch`, assert path+method). Commit `feat(moneyword): frontend api modules`.

---

### Task 9: MoneyWord game page + route + hub entry + i18n

**Files:** Create `frontend/src/pages/child/games/MoneyWord.tsx`; Modify `frontend/src/App.tsx` (`/arcade/moneyword` route), `frontend/src/pages/child/Arcade.tsx` (hub entry), `frontend/src/locales/en/arcade.json`; Test alongside.

**Interfaces — Consumes:** `getMoneyWordToday`, `submitMoneyWordGuess` (Task 8). **Produces:** the game UI — a grid of up to 6 rows × N letter tiles; an on-screen A–Z keyboard (letter buttons, ≥44px); per-letter feedback that is **not colour-only** (each tile carries a state class + an icon/`aria-label`, e.g. ✓ correct / ◐ present / ✕ absent); `aria-live` announcements for each guess result + remaining guesses; on completion, reveal the definition + a "you solved it in N!" + a share button (copies the emoji-grid result) + back-to-arcade. Null-guard the API results.

- [ ] **Step 1: Write the failing test** — mock `@/api/moneyword`; `getMoneyWordToday` returns `{length:5, max_guesses:6, guesses:[], completed:false, solved:false, definition:null}`; type/submit a correct guess (mock `submitMoneyWordGuess` → solved completion with a definition); assert the definition is shown and the grid renders feedback; axe-clean. **Step 2-4:** implement → green; full `tsc + lint + build`. **Step 5:** Commit `feat(moneyword): game page + route + hub entry + i18n`.

---

### Task 10: Home daily card

**Files:** Create `frontend/src/components/child/home/ArcadeDailyCard.tsx`; Modify `frontend/src/pages/child/Home.tsx`, `frontend/src/locales/en/arcade.json`; Test alongside.

**Interfaces — Consumes:** `getMoneyWordToday` (via a `useQuery` hook). **Produces:** a Home card showing today's MoneyWord state — **Play** (not started) / **Continue** (in progress, `guesses.length` shown) / **Done ✓** (completed) — linking to `/arcade/moneyword`. This is the #1 daily-return surface; place it prominently on Home (above the existing `ArcadeHomeCard`/quick-links). Accessible link, ≥44px, axe-clean.

- [ ] TDD (mock the hook for each of the three states; assert the right label + link + axe). Commit `feat(moneyword): Home daily card with play/continue/done state`.

---

### Task 11: Admin word-bank page + nav + verify + native sync + docs + push

**Files:** Create `frontend/src/components/admin/ArcadeWordBank.tsx`; Modify `frontend/src/App.tsx` (admin route), `frontend/src/components/admin/AdminSidebar.tsx` (nav item), `frontend/src/locales/en/admin.json`; Modify `docs/MASTER-BACKLOG.md`, `AGENTS.md`; Test alongside.

**Interfaces — Consumes:** `arcadeWordsAdmin.ts` (Task 8). **Produces:** an admin page listing pending/approved/rejected words with a market-style filter, a **Suggest N** button (calls `suggestArcadeWords`), and per-row **approve** (with inline edit of word/definition) / **reject**. Mirror `src/components/admin/VideoCuration.tsx` structure + the `AdminSidebar` nav pattern.

- [ ] **Step 1:** TDD the admin page (mock the api; assert list renders, suggest calls the api, approve/reject call the api). **Step 2: Verify gates** — backend `ruff check . && pytest -q`; frontend `tsc --noEmit && npm run lint && vitest run && npm run build` (report arcade/moneyword tests distinctly from the known ~70 pre-existing `.env.local` local-only fails). **Step 3:** `npx cap sync ios`. **Step 4:** docs entry for Phase 2 (MoneyWord live, migration `a1b2c3d4e5f6`, new `/arcade/moneyword` + admin word-bank routes; note the operator must run Suggest→approve to grow the bank beyond the starter seed). **Step 5:** Commit docs. **Step 6 (controller, not the implementer):** the push triggers Railway deploy + the additive migration — **ask the user about a prod snapshot first**, then push; then the manual Vercel prod deploy + alias.

---

## Self-Review (completed)

- **Spec coverage (§4–§5):** daily same-word-per-language (Task 3 `pick_daily_word`, UTC in Task 6), 6 guesses + variable 4–8 length + per-letter feedback with duplicate handling (Tasks 1–2, 4), definition-on-finish never-leak-mid-game (Task 4 `_state`), shareable emoji grid (Task 9), lazy no-repeat no-cron selection (Task 3), once-per-day server-authoritative (Task 4 `AlreadyCompleted` + unique `(user_id, puzzle_date)`), rewards reuse Phase-1 coins+leaderboard + streak (Task 4), LLM-assisted + moderated + admin-approved word bank (Tasks 5, 7), launch English-only (`language="en"` throughout), Home daily card (Task 10), admin UI (Task 11), a11y not-colour-only + i18n (Tasks 9–11). Starter seed (Task 5) added so the daily works at launch before the operator grows the bank.
- **Deliberate spec deviations (flagged):** guess validation is length + A–Z only, not dictionary membership (kid-friendly); `arcade_daily_play` supersedes the spec's `arcade_daily_completion` name and also tracks in-progress guesses (for resume + server-authoritative guess limiting).
- **Type/name consistency:** `evaluate_guess`/`MAX_GUESSES`/`pick_daily_word`/`NoApprovedWords`/`AlreadyCompleted`/`get_today`/`play_guess` consistent across Tasks 2–6; `game="moneyword"` into the Phase-1 `arcade_service.record_score`; state shape (`length`,`max_guesses`,`guesses[]`,`completed`,`solved`,`definition`) consistent across Tasks 4/6/8/9/10.
- **Placeholders:** none — the one "confirm `moderate_output` result attribute" note is a concrete verification against a named file, not deferred work.
- **Phase-1 carry-forward hardening** (server-issued/persisted sessions) is *inherently satisfied for MoneyWord*: the answer is server-held and never sent until completion, and guesses are server-tracked — so MoneyWord's Arcade Points are not client-fabricable. (The Quiz Rush anti-spoof item remains a Quiz-Rush-specific follow-up.)
