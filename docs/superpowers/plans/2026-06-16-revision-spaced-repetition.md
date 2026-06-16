# Revision / spaced-repetition ("Revise") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-facing "Revise" loop — a home card + a Revise tab/hub + a capped-5 session — that resurfaces due weak concepts (weak-first) and mastered-concept refreshers, records each answer through the existing SM-2 engine, and awards XP toward the daily goal/streak.

**Architecture:** A new stateless `revise_service.py` selects up to 5 concepts and re-derives answer correctness server-side; a `revise` router exposes `GET /revise/modules`, `GET /revise/session`, `POST /revise/answer`. It reuses `get_due_items`, `record_review`, `generate_practice_quiz` (cached + moderated), `record_xp`/`record_daily_activity`. Frontend adds a client lib, a home card, a hub page, a session page, a nav tab, and two routes. **No DB migration.**

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, pytest + pytest-asyncio (`loop_scope="session"`), React 18 + Vite 7 + TanStack Query + Tailwind v4, vitest + vitest-axe.

**Spec:** [docs/superpowers/specs/2026-06-16-revision-spaced-repetition-design.md](../specs/2026-06-16-revision-spaced-repetition-design.md)

**Conventions:**
- Backend tests from `/Users/leeashmore/investikid/backend` with `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`.
- Async DB tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `db_session` fixture; patch `app.services.<module>.<fn>`.
- Frontend from `/Users/leeashmore/investikid/frontend`: `npm test`, `npx tsc -b`, `npm run lint`, `npm run build`. New UI gets a `vitest-axe` test.
- Branch `testing`. End commits with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `backend/app/services/revise_service.py` | Session selection, answer recording, revisable-modules listing, `ref` codec, concept→lesson resolver | **Create** |
| `backend/app/schemas/revise.py` | Pydantic request/response models | **Create** |
| `backend/app/routers/revise.py` | `GET /revise/modules`, `GET /revise/session`, `POST /revise/answer` | **Create** |
| `backend/app/main.py` | Register the revise router | Modify |
| `backend/tests/test_revise_service.py` | Service unit tests | **Create** |
| `backend/tests/test_revise_endpoints.py` | Endpoint tests (auth, rate-limit, shape) | **Create** |
| `frontend/src/api/revise.ts` | Client lib + types + hooks | **Create** |
| `frontend/src/components/child/home/ReviseCard.tsx` | Home card | **Create** |
| `frontend/src/pages/child/Home.tsx` | Mount the card | Modify |
| `frontend/src/pages/child/Revise.tsx` | Hub page (modules + Daily revise) | **Create** |
| `frontend/src/pages/child/ReviseSession.tsx` | One-at-a-time session flow | **Create** |
| `frontend/src/components/child/BottomTabBar.tsx` | Add Revise tab | Modify |
| `frontend/src/App.tsx` | Add `/revise` + `/revise/session` routes | Modify |
| `frontend/src/**/__tests__/*` | vitest + vitest-axe for card/hub/session | **Create** |

---

## Task 1: `ref` codec + concept→lesson resolver

**Files:**
- Create: `backend/app/services/revise_service.py`
- Test: `backend/tests/test_revise_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_revise_service.py`:

```python
import uuid

import pytest

from app.services.revise_service import decode_ref, encode_ref

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_ref_roundtrip():
    lesson_id = uuid.uuid4()
    wc_id = uuid.uuid4()
    ref = encode_ref(kind="weak", topic="stocks", lesson_id=lesson_id,
                     concept="What is a stock?", weak_concept_id=wc_id)
    out = decode_ref(ref)
    assert out == {
        "kind": "weak", "topic": "stocks", "lesson_id": str(lesson_id),
        "concept": "What is a stock?", "weak_concept_id": str(wc_id),
    }


def test_ref_refresher_has_no_weak_id():
    lesson_id = uuid.uuid4()
    ref = encode_ref(kind="refresher", topic="saving", lesson_id=lesson_id,
                     concept="Why save?", weak_concept_id=None)
    out = decode_ref(ref)
    assert out["kind"] == "refresher"
    assert out["weak_concept_id"] is None


def test_decode_ref_rejects_garbage():
    with pytest.raises(ValueError):
        decode_ref("not-a-real-ref")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k ref -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.revise_service'`.

- [ ] **Step 3: Implement**

Create `backend/app/services/revise_service.py`:

```python
from __future__ import annotations

import base64
import json
import logging
import uuid

from app.models.content import Lesson, Module

logger = logging.getLogger(__name__)

SESSION_CAP = 5
XP_PER_CORRECT = 5


def _concept_of(lesson: Lesson) -> str:
    """Same derivation the practice flow uses (ai.py practice_quiz)."""
    c = lesson.content_json or {}
    return c.get("question") or c.get("title") or c.get("prompt") or "general"


def encode_ref(
    *,
    kind: str,
    topic: str,
    lesson_id: uuid.UUID,
    concept: str,
    weak_concept_id: uuid.UUID | None,
) -> str:
    payload = {
        "kind": kind,
        "topic": topic,
        "lesson_id": str(lesson_id),
        "concept": concept,
        "weak_concept_id": str(weak_concept_id) if weak_concept_id else None,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_ref(ref: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(ref.encode())
        data = json.loads(raw)
        if data.get("kind") not in ("weak", "refresher") or "lesson_id" not in data:
            raise ValueError("bad ref payload")
        return data
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid ref") from exc
```

- [ ] **Step 4: Run to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k ref -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid/backend
git add app/services/revise_service.py tests/test_revise_service.py
git commit -m "feat(revise): ref codec + concept derivation helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `build_session` — weak-first selection + refresher top-up to cap 5

**Files:**
- Modify: `backend/app/services/revise_service.py`
- Test: `backend/tests/test_revise_service.py`

Reference (verify before coding): `get_due_items(session, user_id) -> list[SpacedRepetitionItem]` and `record_review(session, user_id, weak_concept_id, *, correct)` in `app/services/spaced_repetition_service.py`; `generate_practice_quiz(session, lesson, *, user, topic, concept, premium, wrong_answer_index=None) -> dict` (returns `{question, choices, answer_index, explanation, variant_rung}`) in `app/services/ai_content_service.py`; `WeakConcept(user_id, topic, concept, resolved, ...)` and `SpacedRepetitionItem(weak_concept_id, next_review_at, ...)` in `app/models/skill_profile.py`; `Module(id, topic, title, icon)`, `Lesson(id, module_id, content_json)`, `LessonCompletion(user_id, lesson_id, completed_at)` in `app/models/content.py`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_revise_service.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User
from app.services.revise_service import build_session


async def _seed_user(db_session):
    user = User(email="rev@example.com", username="revkid", password_hash="x",
                dob=datetime(2012, 1, 1).date(), country_code="GB", currency_code="GBP")
    db_session.add(user)
    module = Module(topic="stocks", title="Stocks", country_codes=[],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    return user, module


def _quiz_payload(q):
    return {"question": q, "choices": ["a", "b", "c"], "answer_index": 1,
            "explanation": "because", "variant_rung": "core"}


async def test_build_session_is_weak_first_then_refreshers_capped_5(db_session):
    user, module = await _seed_user(db_session)
    # 2 due weak concepts (each tied to a lesson via concept string)
    weak_lessons = []
    for i in range(2):
        q = f"Weak concept {i}?"
        lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=i,
                        content_json={"question": q, "choices": ["a", "b"], "answer_index": 0})
        db_session.add(lesson)
        weak_lessons.append((q, lesson))
        wc = WeakConcept(user_id=user.id, topic="stocks", concept=q, resolved=False)
        db_session.add(wc)
        await db_session.flush()
        db_session.add(SpacedRepetitionItem(
            user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5,
            interval_days=1, repetition_count=0,
            next_review_at=datetime.now(UTC) - timedelta(days=1)))
    # 5 completed (mastered) lessons available as refreshers
    for i in range(5):
        q = f"Mastered {i}?"
        lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=10 + i,
                        content_json={"question": q, "choices": ["a", "b"], "answer_index": 0})
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=None)

    assert len(session) == 5
    assert session[0]["kind"] == "weak" and session[1]["kind"] == "weak"
    assert all(s["kind"] == "refresher" for s in session[2:])
    # session items expose question/choices but NOT the answer
    assert "answer_index" not in session[0]
    assert set(session[0]) >= {"ref", "kind", "module_id", "lesson_id", "concept",
                               "question", "choices"}


async def test_build_session_module_filter(db_session):
    user, module = await _seed_user(db_session)
    other = Module(topic="saving", title="Saving", country_codes=[],
                   is_premium=False, order_index=1, icon="🐷")
    db_session.add(other)
    await db_session.flush()
    lesson = Lesson(module_id=other.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Save?", "choices": ["a"], "answer_index": 0})
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        session = await build_session(db_session, user, module_id=other.id)

    assert all(s["module_id"] == str(other.id) for s in session)
    assert len(session) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k build_session -v`
Expected: FAIL — `ImportError: cannot import name 'build_session'`.

- [ ] **Step 3: Implement**

Append to `backend/app/services/revise_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User
from app.services.ai_content_service import generate_practice_quiz
from app.services.entitlements import is_premium
from app.services.spaced_repetition_service import get_due_items


async def _lesson_for_concept(
    session: AsyncSession, *, topic: str, concept: str
) -> tuple[Lesson, Module] | None:
    """Find a lesson in `topic` whose derived concept equals `concept`."""
    rows = await session.execute(
        select(Lesson, Module).join(Module, Module.id == Lesson.module_id)
        .where(Module.topic == topic)
    )
    for lesson, module in rows.all():
        if _concept_of(lesson) == concept:
            return lesson, module
    return None


async def _build_item(session, user, *, kind, lesson, module, concept) -> dict | None:
    try:
        quiz = await generate_practice_quiz(
            session, lesson, user=user, topic=module.topic,
            concept=concept, premium=is_premium(user),
        )
    except Exception:  # noqa: BLE001
        logger.warning("revise: quiz generation failed for %s", lesson.id)
        return None
    wc_id = None
    if kind == "weak":
        wc = await session.scalar(
            select(WeakConcept).where(
                WeakConcept.user_id == user.id,
                WeakConcept.topic == module.topic,
                WeakConcept.concept == concept,
            )
        )
        wc_id = wc.id if wc else None
    return {
        "ref": encode_ref(kind=kind, topic=module.topic, lesson_id=lesson.id,
                          concept=concept, weak_concept_id=wc_id),
        "kind": kind,
        "module_id": str(module.id),
        "lesson_id": str(lesson.id),
        "concept": concept,
        "question": quiz["question"],
        "choices": quiz["choices"],
    }


async def build_session(
    session: AsyncSession, user: User, *, module_id: uuid.UUID | None
) -> list[dict]:
    items: list[dict] = []
    seen_concepts: set[tuple[str, str]] = set()

    # 1) Weak-first: due SR items -> weak concepts (already ordered by due-ness).
    due = await get_due_items(session, user.id)
    weak_ids = [d.weak_concept_id for d in due]
    if weak_ids:
        weaks = (await session.scalars(
            select(WeakConcept).where(WeakConcept.id.in_(weak_ids))
        )).all()
        by_id = {w.id: w for w in weaks}
        for d in due:  # preserve due order
            w = by_id.get(d.weak_concept_id)
            if not w:
                continue
            resolved = await _lesson_for_concept(session, topic=w.topic, concept=w.concept)
            if not resolved:
                continue
            lesson, module = resolved
            if module_id and module.id != module_id:
                continue
            item = await _build_item(session, user, kind="weak", lesson=lesson,
                                     module=module, concept=w.concept)
            if item:
                items.append(item)
                seen_concepts.add((module.topic, w.concept))
            if len(items) >= SESSION_CAP:
                return items

    # 2) Refresher top-up: completed lessons not already weak/seen.
    comp_q = (
        select(Lesson, Module, LessonCompletion.completed_at)
        .join(Module, Module.id == Lesson.module_id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user.id)
        .order_by(LessonCompletion.completed_at.asc())  # stable rotation; oldest first
    )
    if module_id:
        comp_q = comp_q.where(Module.id == module_id)
    for lesson, module, _ in (await session.execute(comp_q)).all():
        concept = _concept_of(lesson)
        if (module.topic, concept) in seen_concepts:
            continue
        # skip if it's a current unresolved weak concept
        is_weak = await session.scalar(
            select(WeakConcept.id).where(
                WeakConcept.user_id == user.id, WeakConcept.topic == module.topic,
                WeakConcept.concept == concept, WeakConcept.resolved == False,  # noqa: E712
            )
        )
        if is_weak:
            continue
        item = await _build_item(session, user, kind="refresher", lesson=lesson,
                                 module=module, concept=concept)
        if item:
            items.append(item)
            seen_concepts.add((module.topic, concept))
        if len(items) >= SESSION_CAP:
            break
    return items
```

- [ ] **Step 4: Run to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k build_session -v`
Expected: PASS (2 tests). Then `ruff check app/services/revise_service.py` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid/backend
git add app/services/revise_service.py tests/test_revise_service.py
git commit -m "feat(revise): build_session weak-first selection + refresher top-up

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `record_answer` — SM-2 update + XP + wrong-refresher creates weak concept

**Files:**
- Modify: `backend/app/services/revise_service.py`
- Test: `backend/tests/test_revise_service.py`

Reference: `record_xp(progress, amount, *, today=None) -> XpResult(awarded, goal_met_now, goal_met_today)` in `app/services/xp_service.py`; `record_daily_activity(progress, today_local) -> bool` in `app/services/content_service.py`; `UserProgress` loaded via `await session.get(UserProgress, user.id)` then created if `None` (see `app/routers/content.py:324`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_revise_service.py`:

```python
from app.models.user import UserProgress
from app.services.revise_service import record_answer


async def _progress(db_session, user):
    p = UserProgress(user_id=user.id)
    db_session.add(p)
    await db_session.flush()
    return p


async def test_record_answer_weak_correct_awards_xp_and_advances(db_session):
    user, module = await _seed_user(db_session)
    await _progress(db_session, user)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Q?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    wc = WeakConcept(user_id=user.id, topic="stocks", concept="Q?", resolved=False)
    db_session.add(wc)
    await db_session.flush()
    from app.services.revise_service import encode_ref
    ref = encode_ref(kind="weak", topic="stocks", lesson_id=lesson.id,
                     concept="Q?", weak_concept_id=wc.id)

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload("Q?"))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        # _quiz_payload answer_index is 1 -> selecting 1 is correct
        result = await record_answer(db_session, user, ref, selected_index=1)

    assert result["correct"] is True
    assert result["answer_index"] == 1
    assert result["xp_awarded"] == 5
    sr = await db_session.scalar(
        select(SpacedRepetitionItem).where(SpacedRepetitionItem.weak_concept_id == wc.id))
    assert sr is not None and sr.repetition_count >= 1  # advanced


async def test_record_answer_wrong_refresher_creates_weak_concept(db_session):
    user, module = await _seed_user(db_session)
    await _progress(db_session, user)
    lesson = Lesson(module_id=module.id, type="quiz", xp_reward=10, order_index=0,
                    content_json={"question": "Fresh?", "choices": ["a", "b"], "answer_index": 0})
    db_session.add(lesson)
    await db_session.flush()
    from app.services.revise_service import encode_ref
    ref = encode_ref(kind="refresher", topic="stocks", lesson_id=lesson.id,
                     concept="Fresh?", weak_concept_id=None)

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload("Fresh?"))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        result = await record_answer(db_session, user, ref, selected_index=0)  # wrong (ans=1)

    assert result["correct"] is False
    assert result["xp_awarded"] == 0
    wc = await db_session.scalar(
        select(WeakConcept).where(WeakConcept.user_id == user.id,
                                  WeakConcept.concept == "Fresh?"))
    assert wc is not None  # missed refresher re-enters the SR loop
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k record_answer -v`
Expected: FAIL — `ImportError: cannot import name 'record_answer'`.

- [ ] **Step 3: Implement**

Append to `backend/app/services/revise_service.py`:

```python
from datetime import UTC, datetime

from app.models.user import UserProgress
from app.services.content_service import record_daily_activity
from app.services.spaced_repetition_service import record_review
from app.services.xp_service import record_xp


async def record_answer(
    session: AsyncSession, user: User, ref: str, selected_index: int
) -> dict:
    data = decode_ref(ref)
    lesson = await session.get(Lesson, uuid.UUID(data["lesson_id"]))
    if lesson is None:
        raise ValueError("lesson not found")
    module = await session.get(Module, lesson.module_id)
    quiz = await generate_practice_quiz(
        session, lesson, user=user, topic=data["topic"],
        concept=data["concept"], premium=is_premium(user),
    )
    answer_index = quiz["answer_index"]
    correct = selected_index == answer_index

    if data["kind"] == "weak" and data.get("weak_concept_id"):
        await record_review(session, user.id,
                            uuid.UUID(data["weak_concept_id"]), correct=correct)
    elif data["kind"] == "refresher" and not correct:
        wc = await session.scalar(
            select(WeakConcept).where(
                WeakConcept.user_id == user.id, WeakConcept.topic == data["topic"],
                WeakConcept.concept == data["concept"],
            )
        )
        if wc is None:
            wc = WeakConcept(user_id=user.id, topic=data["topic"], concept=data["concept"])
            session.add(wc)
            await session.flush()
        await record_review(session, user.id, wc.id, correct=False)

    xp_awarded = 0
    goal_met = False
    if correct:
        progress = await session.get(UserProgress, user.id)
        if progress is None:
            progress = UserProgress(user_id=user.id)
            session.add(progress)
            await session.flush()
        today = datetime.now(UTC).date()
        xp = record_xp(progress, XP_PER_CORRECT, today=today)
        record_daily_activity(progress, today)
        xp_awarded = xp.awarded
        goal_met = xp.goal_met_today

    await session.commit()
    return {
        "correct": correct,
        "answer_index": answer_index,
        "explanation": quiz.get("explanation", ""),
        "xp_awarded": xp_awarded,
        "goal_met": goal_met,
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k record_answer -v`
Expected: PASS (2 tests). `ruff check app/services/revise_service.py` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid/backend
git add app/services/revise_service.py tests/test_revise_service.py
git commit -m "feat(revise): record_answer SM-2 update + XP + wrong-refresher reentry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `list_revisable_modules` (weak-first) + schemas + router

**Files:**
- Modify: `backend/app/services/revise_service.py`
- Create: `backend/app/schemas/revise.py`, `backend/app/routers/revise.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_revise_service.py`, `backend/tests/test_revise_endpoints.py`

- [ ] **Step 1: Write the failing service test**

Append to `backend/tests/test_revise_service.py`:

```python
from app.services.revise_service import list_revisable_modules


async def test_list_modules_weak_first(db_session):
    user, module = await _seed_user(db_session)  # stocks
    saving = Module(topic="saving", title="Saving", country_codes=[],
                    is_premium=False, order_index=1, icon="🐷")
    db_session.add(saving)
    await db_session.flush()
    # complete one lesson in each module
    for m in (module, saving):
        lesson = Lesson(module_id=m.id, type="quiz", xp_reward=10, order_index=0,
                        content_json={"question": f"{m.topic}?", "choices": ["a"], "answer_index": 0})
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))
    # one due weak concept in `saving`
    wc = WeakConcept(user_id=user.id, topic="saving", concept="saving?", resolved=False)
    db_session.add(wc)
    await db_session.flush()
    db_session.add(SpacedRepetitionItem(
        user_id=user.id, weak_concept_id=wc.id, ease_factor=2.5, interval_days=1,
        repetition_count=0, next_review_at=datetime.now(UTC) - timedelta(days=1)))
    await db_session.flush()

    mods = await list_revisable_modules(db_session, user)
    assert mods[0]["topic"] == "saving"  # weak-first
    assert mods[0]["due_weak_count"] == 1
    assert {m["topic"] for m in mods} == {"stocks", "saving"}
```

- [ ] **Step 2: Run → fail, then implement**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py -k list_modules -v` → FAIL.

Append to `backend/app/services/revise_service.py`:

```python
from sqlalchemy import func


async def list_revisable_modules(session: AsyncSession, user: User) -> list[dict]:
    # completed module ids
    comp_modules = (await session.scalars(
        select(Module.id).distinct()
        .join(Lesson, Lesson.module_id == Module.id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user.id)
    )).all()
    if not comp_modules:
        return []
    modules = (await session.scalars(
        select(Module).where(Module.id.in_(comp_modules))
    )).all()
    # due weak counts per topic
    rows = (await session.execute(
        select(WeakConcept.topic, func.count(SpacedRepetitionItem.id))
        .join(SpacedRepetitionItem, SpacedRepetitionItem.weak_concept_id == WeakConcept.id)
        .where(
            SpacedRepetitionItem.user_id == user.id,
            SpacedRepetitionItem.next_review_at <= func.now(),
            WeakConcept.resolved == False,  # noqa: E712
        )
        .group_by(WeakConcept.topic)
    )).all()
    due_by_topic = {t: int(c) for t, c in rows}
    out = [{
        "module_id": str(m.id), "title": m.title, "icon": m.icon,
        "topic": m.topic, "due_weak_count": due_by_topic.get(m.topic, 0),
    } for m in modules]
    out.sort(key=lambda d: (-d["due_weak_count"], d["title"]))  # weak-first
    return out
```

Run the test → PASS.

- [ ] **Step 3: Create schemas**

Create `backend/app/schemas/revise.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


class ReviseQuestion(BaseModel):
    ref: str
    kind: str  # "weak" | "refresher"
    module_id: str
    lesson_id: str
    concept: str
    question: str
    choices: list[str]


class ReviseSession(BaseModel):
    items: list[ReviseQuestion]


class ReviseModule(BaseModel):
    module_id: str
    title: str
    icon: str
    topic: str
    due_weak_count: int


class ReviseAnswerIn(BaseModel):
    ref: str
    selected_index: int


class ReviseAnswerResult(BaseModel):
    correct: bool
    answer_index: int
    explanation: str
    xp_awarded: int
    goal_met: bool
```

- [ ] **Step 4: Write the failing endpoint test**

Create `backend/tests/test_revise_endpoints.py` (mirror an existing endpoint test that uses the `client` fixture + an authenticated child; check `tests/test_coach_endpoint.py` for the exact auth-fixture name and login helper, and reuse it):

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_revise_modules_requires_auth(client):
    resp = await client.get("/revise/modules")
    assert resp.status_code in (401, 403)


async def test_revise_modules_empty_for_new_user(client, child_auth):
    # child_auth: reuse whatever authenticated-child fixture the suite provides
    resp = await client.get("/revise/modules", headers=child_auth)
    assert resp.status_code == 200
    assert resp.json() == []
```

> If the suite's authenticated-child fixture has a different name/shape, adapt these two tests to it (do not invent a new auth mechanism). The behavioural assertions (401/403 unauthenticated; `[]` for a user with no completions) must stay.

- [ ] **Step 5: Create the router + register it**

Create `backend/app/routers/revise.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db import get_session
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.revise import (
    ReviseAnswerIn,
    ReviseAnswerResult,
    ReviseModule,
    ReviseSession,
)
from app.services import revise_service

router = APIRouter(tags=["revise"])


@router.get("/revise/modules", response_model=list[ReviseModule])
async def revise_modules(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await revise_service.list_revisable_modules(session, current_user)


@router.get("/revise/session", response_model=ReviseSession)
@limiter.limit("20/hour")
async def revise_session(
    request: Request,
    module_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    items = await revise_service.build_session(session, current_user, module_id=module_id)
    return {"items": items}


@router.post("/revise/answer", response_model=ReviseAnswerResult)
@limiter.limit("120/hour")
async def revise_answer(
    request: Request,
    payload: ReviseAnswerIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await revise_service.record_answer(
            session, current_user, payload.ref, payload.selected_index)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
```

> Verify the exact import paths for `limiter`, `get_session`, and `get_current_user` against an existing router (e.g. `app/routers/ai.py`) and match them — names above are the expected ones but confirm before running.

Register in `backend/app/main.py` next to the other `app.include_router(...)` calls:

```python
from app.routers import revise
app.include_router(revise.router)
```

(Match the existing include style — if other routers use a prefix like `/ai`, the revise router defines full paths itself, so include it **without** an extra prefix.)

- [ ] **Step 6: Run all backend revise tests + lint**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_revise_service.py tests/test_revise_endpoints.py -v`
Expected: all PASS.
Run: `/Users/leeashmore/Local Repo/.venv/bin/ruff check app/services/revise_service.py app/routers/revise.py app/schemas/revise.py` → clean.

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid/backend
git add app/services/revise_service.py app/schemas/revise.py app/routers/revise.py app/main.py tests/test_revise_service.py tests/test_revise_endpoints.py
git commit -m "feat(revise): revisable-modules + schemas + /revise endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Frontend client lib `revise.ts`

**Files:**
- Create: `frontend/src/api/revise.ts`
- Test: `frontend/src/api/__tests__/revise.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/__tests__/revise.test.ts` (mirror an existing `src/api/__tests__/*.test.ts` for the `apiFetch` mock pattern):

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { reviseApi } from '../revise';

describe('reviseApi', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('getSession passes module_id when provided', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await reviseApi.getSession('m1');
    expect(spy).toHaveBeenCalledWith('/revise/session?module_id=m1');
  });

  it('getSession omits module_id when absent', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await reviseApi.getSession();
    expect(spy).toHaveBeenCalledWith('/revise/session');
  });

  it('postAnswer posts ref + selected_index', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({} as never);
    await reviseApi.postAnswer('REF', 2);
    expect(spy).toHaveBeenCalledWith('/revise/answer', {
      method: 'POST',
      body: JSON.stringify({ ref: 'REF', selected_index: 2 }),
    });
  });
});
```

- [ ] **Step 2: Run → fail**

Run: `cd /Users/leeashmore/investikid/frontend && npx vitest run src/api/__tests__/revise.test.ts`
Expected: FAIL — cannot find `../revise`.

- [ ] **Step 3: Implement**

Create `frontend/src/api/revise.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type ReviseQuestion = {
  ref: string;
  kind: 'weak' | 'refresher';
  module_id: string;
  lesson_id: string;
  concept: string;
  question: string;
  choices: string[];
};
export type ReviseSession = { items: ReviseQuestion[] };

export type ReviseModule = {
  module_id: string;
  title: string;
  icon: string;
  topic: string;
  due_weak_count: number;
};

export type ReviseAnswerResult = {
  correct: boolean;
  answer_index: number;
  explanation: string;
  xp_awarded: number;
  goal_met: boolean;
};

export const reviseApi = {
  getModules: () => apiFetch<ReviseModule[]>('/revise/modules'),
  getSession: (moduleId?: string) =>
    apiFetch<ReviseSession>(
      moduleId ? `/revise/session?module_id=${moduleId}` : '/revise/session',
    ),
  postAnswer: (ref: string, selectedIndex: number) =>
    apiFetch<ReviseAnswerResult>('/revise/answer', {
      method: 'POST',
      body: JSON.stringify({ ref, selected_index: selectedIndex }),
    }),
};

export function useRevisableModules() {
  return useQuery({
    queryKey: ['revise-modules'],
    queryFn: () => reviseApi.getModules(),
    retry: false,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 4: Run → pass, then commit**

Run: `npx vitest run src/api/__tests__/revise.test.ts` → PASS.
```bash
cd /Users/leeashmore/investikid
git add frontend/src/api/revise.ts frontend/src/api/__tests__/revise.test.ts
git commit -m "feat(revise): frontend client lib + hooks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `ReviseCard` on Home

**Files:**
- Create: `frontend/src/components/child/home/ReviseCard.tsx`
- Modify: `frontend/src/pages/child/Home.tsx`
- Test: `frontend/src/components/child/home/__tests__/ReviseCard.test.tsx`

The card shows whenever there's anything revisable (≥1 module). Copy leads with the total due-weak count across modules when > 0, else a "keep fresh" message. Links to `/revise/session` (daily smart session).

- [ ] **Step 1: Write the failing test (render + axe + copy variants)**

Create `frontend/src/components/child/home/__tests__/ReviseCard.test.tsx` (mirror an existing home-card test for the QueryClient/render wrapper; use `axe` like other `vitest-axe` tests in the repo):

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { ReviseCard } from '../ReviseCard';

vi.mock('@/api/revise', () => ({
  useRevisableModules: vi.fn(),
}));
import { useRevisableModules } from '@/api/revise';

function renderCard() {
  return render(<MemoryRouter><ReviseCard /></MemoryRouter>);
}

it('hides when nothing is revisable', () => {
  (useRevisableModules as unknown as vi.Mock).mockReturnValue({ data: [] });
  const { container } = renderCard();
  expect(container).toBeEmptyDOMElement();
});

it('leads with the weak count when due, and is accessible', async () => {
  (useRevisableModules as unknown as vi.Mock).mockReturnValue({
    data: [{ module_id: 'm', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 2 }],
  });
  const { container } = renderCard();
  expect(screen.getByText(/2 .*practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();
});

it('shows a keep-fresh message when nothing weak is due', () => {
  (useRevisableModules as unknown as vi.Mock).mockReturnValue({
    data: [{ module_id: 'm', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 0 }],
  });
  renderCard();
  expect(screen.getByText(/fresh/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run → fail**

Run: `npx vitest run src/components/child/home/__tests__/ReviseCard.test.tsx` → FAIL (no `../ReviseCard`).

- [ ] **Step 3: Implement**

Create `frontend/src/components/child/home/ReviseCard.tsx` (match the visual style of sibling cards like `QuickLinksRow`/`StatsCard` — rounded-2xl, border, brand colours; keep touch targets ≥44px):

```tsx
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useRevisableModules } from '@/api/revise';

export function ReviseCard() {
  const { data: modules } = useRevisableModules();
  if (!modules || modules.length === 0) return null;

  const dueWeak = modules.reduce((n, m) => n + m.due_weak_count, 0);
  const headline =
    dueWeak > 0
      ? `${dueWeak} concept${dueWeak === 1 ? '' : 's'} to practice`
      : 'Keep your learning fresh';
  const sub =
    dueWeak > 0 ? 'A quick 5-question revision keeps your streak going.' : 'Revise a few things you’ve learned.';

  return (
    <Link
      to="/revise/session"
      className="mt-4 flex items-center gap-3 rounded-2xl border border-brand-200 bg-brand-50 p-4 shadow-sm transition-colors hover:bg-brand-100 min-h-[44px]"
      aria-label={`Revise: ${headline}`}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-white">
        <Sparkles className="h-5 w-5" aria-hidden="true" />
      </span>
      <span className="flex flex-col">
        <span className="font-semibold text-brand-900">{headline}</span>
        <span className="text-sm text-brand-700">{sub}</span>
      </span>
    </Link>
  );
}
```

Mount it in `frontend/src/pages/child/Home.tsx` — add the import and place `<ReviseCard />` directly after the `StatsCard` block:

```tsx
import { ReviseCard } from '@/components/child/home/ReviseCard';
// ...inside the returned JSX, after the StatsCard's wrapping <div>:
<ReviseCard />
```

- [ ] **Step 4: Run → pass + a11y**

Run: `npx vitest run src/components/child/home/__tests__/ReviseCard.test.tsx` → PASS (3 tests incl. axe).

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/components/child/home/ReviseCard.tsx frontend/src/pages/child/Home.tsx frontend/src/components/child/home/__tests__/ReviseCard.test.tsx
git commit -m "feat(revise): home ReviseCard (weak-count-led, always-available)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Revise hub page + nav tab + route

**Files:**
- Create: `frontend/src/pages/child/Revise.tsx`
- Modify: `frontend/src/components/child/BottomTabBar.tsx`, `frontend/src/App.tsx`
- Test: `frontend/src/pages/child/__tests__/Revise.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/child/__tests__/Revise.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import Revise from '../Revise';

vi.mock('@/api/revise', () => ({ useRevisableModules: vi.fn() }));
import { useRevisableModules } from '@/api/revise';

function renderPage() {
  return render(<MemoryRouter><Revise /></MemoryRouter>);
}

it('shows Daily revise + weak-first module list and is accessible', async () => {
  (useRevisableModules as unknown as vi.Mock).mockReturnValue({
    data: [
      { module_id: 'a', title: 'Saving', icon: '🐷', topic: 'saving', due_weak_count: 2 },
      { module_id: 'b', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 0 },
    ],
    isLoading: false,
  });
  const { container } = renderPage();
  expect(screen.getByRole('link', { name: /daily revise/i })).toBeInTheDocument();
  expect(screen.getByText(/2 to practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();
});

it('shows an empty state when nothing is revisable', () => {
  (useRevisableModules as unknown as vi.Mock).mockReturnValue({ data: [], isLoading: false });
  renderPage();
  expect(screen.getByText(/complete a lesson/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run → fail**

Run: `npx vitest run src/pages/child/__tests__/Revise.test.tsx` → FAIL.

- [ ] **Step 3: Implement the hub page**

Create `frontend/src/pages/child/Revise.tsx` (mirror the container/spacing of other child pages, e.g. `max-w-3xl px-4 py-4 sm:px-6 sm:py-6`):

```tsx
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useRevisableModules } from '@/api/revise';

export default function Revise() {
  const { data: modules, isLoading } = useRevisableModules();

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-bold">Revise</h1>
      <Link
        to="/revise/session"
        className="mt-4 flex items-center gap-3 rounded-2xl border border-brand-200 bg-brand-600 p-4 text-white shadow-sm min-h-[44px]"
      >
        <Sparkles className="h-5 w-5" aria-hidden="true" />
        <span className="font-semibold">Daily revise</span>
        <span className="ml-auto text-sm text-brand-100">Up to 5 questions</span>
      </Link>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading…</p>
      ) : !modules || modules.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          Complete a lesson first, then come back to revise it!
        </p>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {modules.map((m) => (
            <li key={m.module_id}>
              <Link
                to={`/revise/session?module=${m.module_id}`}
                className="flex items-center gap-3 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm transition-colors hover:bg-brand-50 min-h-[44px]"
              >
                <span className="text-2xl" aria-hidden="true">{m.icon}</span>
                <span className="font-semibold">{m.title}</span>
                {m.due_weak_count > 0 ? (
                  <span className="ml-auto rounded-full bg-danger-100 px-2 py-0.5 text-sm font-semibold text-danger-700">
                    {m.due_weak_count} to practice
                  </span>
                ) : (
                  <span className="ml-auto text-sm text-muted-foreground">Refresh</span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Add the route + nav tab**

In `frontend/src/App.tsx`, add the import and two routes inside the `<Route element={<Shell />}>` block:

```tsx
import Revise from '@/pages/child/Revise';
const ReviseSession = lazy(() => import('@/pages/child/ReviseSession'));
// ...
<Route path="/revise" element={<Revise />} />
<Route path="/revise/session" element={<Suspense fallback={null}><ReviseSession /></Suspense>} />
```

In `frontend/src/components/child/BottomTabBar.tsx`, add a Revise tab to `TABS` (import the `RefreshCw` icon from `lucide-react`):

```tsx
import { Home, BookOpen, RefreshCw, TrendingUp, BarChart3, Target } from 'lucide-react';
// in TABS, after Learn:
{ to: '/revise', label: 'Revise', Icon: RefreshCw },
```

(Six tabs fit the existing flex-around row; verify on a 360px viewport in the Responsive CI job. If too tight, drop the least-used existing tab to a secondary menu — but default to adding the 6th.)

- [ ] **Step 5: Run → pass**

Run: `npx vitest run src/pages/child/__tests__/Revise.test.tsx` → PASS (2 tests incl. axe). Also run the existing `BottomTabBar` test: `npx vitest run src/components/child/__tests__/BottomTabBar.test.tsx` and update its expected tab count if it asserts a fixed number.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/pages/child/Revise.tsx frontend/src/App.tsx frontend/src/components/child/BottomTabBar.tsx frontend/src/pages/child/__tests__/Revise.test.tsx
git commit -m "feat(revise): hub page + Revise nav tab + routes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Revise session page (one-at-a-time flow)

**Files:**
- Create: `frontend/src/pages/child/ReviseSession.tsx`
- Test: `frontend/src/pages/child/__tests__/ReviseSession.test.tsx`

Reads `?module=<id>`, fetches the session, presents one question at a time with weak/refresher badges, posts each answer, shows correct/explanation + XP, ends on a summary.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/child/__tests__/ReviseSession.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import ReviseSession from '../ReviseSession';

const session = {
  items: [
    { ref: 'r1', kind: 'weak', module_id: 'm', lesson_id: 'l', concept: 'Stocks?',
      question: 'What is a stock?', choices: ['A loan', 'A slice of a company'] },
  ],
};
vi.mock('@/api/revise', () => ({
  reviseApi: {
    getSession: vi.fn(() => Promise.resolve(session)),
    postAnswer: vi.fn(() => Promise.resolve({
      correct: true, answer_index: 1, explanation: 'A tiny piece.',
      xp_awarded: 5, goal_met: false,
    })),
  },
}));
import { reviseApi } from '@/api/revise';

function renderPage() {
  return render(<MemoryRouter initialEntries={['/revise/session']}><ReviseSession /></MemoryRouter>);
}

it('shows a weak badge, records an answer, then a summary', async () => {
  const { container } = renderPage();
  await screen.findByText('What is a stock?');
  expect(screen.getByText(/needs practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();

  fireEvent.click(screen.getByRole('button', { name: 'A slice of a company' }));
  await waitFor(() => expect(reviseApi.postAnswer).toHaveBeenCalledWith('r1', 1));
  await screen.findByText(/A tiny piece\./i); // explanation shown

  fireEvent.click(screen.getByRole('button', { name: /next|finish|done/i }));
  await screen.findByText(/1.*\/.*1|all done|great revising/i); // summary
});

it('shows an empty state when nothing is due', async () => {
  (reviseApi.getSession as unknown as vi.Mock).mockResolvedValueOnce({ items: [] });
  renderPage();
  await screen.findByText(/nothing to revise|all caught up/i);
});
```

- [ ] **Step 2: Run → fail**

Run: `npx vitest run src/pages/child/__tests__/ReviseSession.test.tsx` → FAIL.

- [ ] **Step 3: Implement the session page**

Create `frontend/src/pages/child/ReviseSession.tsx`. Use local state for the index, the per-question answer result, and a running correct count. Reuse button styling consistent with `PracticeQuiz.tsx` (read it for the choice-button + correct/incorrect colour pattern). Use `aria-live="polite"` for the feedback region.

```tsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { reviseApi, type ReviseQuestion, type ReviseAnswerResult } from '@/api/revise';
import { Button } from '@/components/ui/button';

export default function ReviseSession() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const moduleId = params.get('module') ?? undefined;

  const [items, setItems] = useState<ReviseQuestion[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [result, setResult] = useState<ReviseAnswerResult | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    reviseApi.getSession(moduleId).then((s) => setItems(s.items));
  }, [moduleId]);

  if (items === null) {
    return <div className="mx-auto max-w-3xl px-4 py-6"><p className="text-sm text-muted-foreground">Loading…</p></div>;
  }
  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">All caught up! 🎉</p>
        <p className="mt-1 text-sm text-muted-foreground">Nothing to revise right now.</p>
        <Button className="mt-4" onClick={() => navigate('/home')}>Back to home</Button>
      </div>
    );
  }
  if (done) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">Great revising! 🌟</p>
        <p className="mt-1 text-sm text-muted-foreground">{correctCount} / {items.length} correct</p>
        <Button className="mt-4" onClick={() => navigate('/home')}>Done</Button>
      </div>
    );
  }

  const q = items[idx];

  async function choose(i: number) {
    if (submitting || result) return;
    setSubmitting(true);
    try {
      const r = await reviseApi.postAnswer(q.ref, i);
      setResult(r);
      if (r.correct) setCorrectCount((c) => c + 1);
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    setResult(null);
    if (idx + 1 >= items.length) setDone(true);
    else setIdx((n) => n + 1);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-2 flex items-center justify-between text-sm text-muted-foreground">
        <span>{idx + 1} of {items.length}</span>
        <span className={q.kind === 'weak'
          ? 'rounded-full bg-danger-100 px-2 py-0.5 font-semibold text-danger-700'
          : 'rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-700'}>
          {q.kind === 'weak' ? 'Needs practice' : 'Quick refresher'}
        </span>
      </div>
      <h1 className="text-xl font-semibold">{q.question}</h1>
      <div className="mt-4 flex flex-col gap-2">
        {q.choices.map((c, i) => {
          const isAnswer = result && i === result.answer_index;
          const isChosenWrong = result && !result.correct && i !== result.answer_index;
          return (
            <Button
              key={i}
              variant="outline"
              disabled={!!result || submitting}
              onClick={() => choose(i)}
              className={[
                'justify-start text-left min-h-[44px]',
                isAnswer ? 'border-success-500 bg-success-50' : '',
                isChosenWrong ? 'opacity-60' : '',
              ].join(' ')}
            >
              {c}
            </Button>
          );
        })}
      </div>
      <div aria-live="polite" className="mt-4">
        {result && (
          <div className="rounded-xl border border-brand-100 bg-brand-50 p-3">
            <p className="font-semibold">{result.correct ? 'Correct! ' : 'Not quite. '}
              {result.xp_awarded > 0 && <span>+{result.xp_awarded} XP</span>}
              {result.goal_met && <span> · 🔥 streak kept!</span>}
            </p>
            {result.explanation && <p className="mt-1 text-sm text-brand-800">{result.explanation}</p>}
            <Button className="mt-3" onClick={next}>
              {idx + 1 >= items.length ? 'Finish' : 'Next'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run → pass + a11y**

Run: `npx vitest run src/pages/child/__tests__/ReviseSession.test.tsx` → PASS (incl. axe). Adjust the summary/empty regex in the test only if your final copy differs — keep the behavioural flow (answer → explanation → summary) intact.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/pages/child/ReviseSession.tsx frontend/src/pages/child/__tests__/ReviseSession.test.tsx
git commit -m "feat(revise): one-at-a-time session page with weak/refresher badges + XP feedback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Full verification + backlog + push

**Files:**
- Modify: `docs/MASTER-BACKLOG.md`

- [ ] **Step 1: Backend gate**

Run from `/Users/leeashmore/investikid/backend`:
`/Users/leeashmore/Local Repo/.venv/bin/ruff check .` → clean;
`/Users/leeashmore/Local Repo/.venv/bin/pytest -q` → all pass (existing + new revise tests). If the local Postgres hangs >90s on a DB test, it's the known env issue — rely on CI.

- [ ] **Step 2: Frontend gate**

Run from `/Users/leeashmore/investikid/frontend`:
`npm run lint` → 0 errors; `npx tsc -b` → exit 0; `npm test` → all pass; `npm run build` → succeeds. Confirm the iOS guard still holds: `grep -c crossorigin dist/index.html` → `0`.

- [ ] **Step 3: Update the backlog**

In `docs/MASTER-BACKLOG.md`, remove the **Revision / spaced-repetition** row from 🟡 Soon and add to the ✅ Live-in-prod context (after promotion):
`- **Revision / spaced-repetition ("Revise")** — ✅ shipped (home card + Revise tab/hub + capped-5 weak-first sessions w/ refreshers; per-correct XP feeds goal/streak; reuses SR engine + cached/moderated quiz gen; no migration).`

- [ ] **Step 4: Commit + push**

```bash
cd /Users/leeashmore/investikid
git add docs/MASTER-BACKLOG.md
git commit -m "docs(backlog): mark Revise feature shipped

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin testing
```

- [ ] **Step 5: Green CI, then promote**

Watch `testing` CI (all 6 jobs). On green, promote `testing → staging → main` (stash the uncommitted iOS pbxproj first, restore after), watch `main` CI, then **redeploy the frontend to Vercel prod** (the bundle changed). No DB migration → no snapshot needed. Backend deploys on green `main` CI via Railway.

---

## Self-Review

**1. Spec coverage:**
- Hybrid weak-first + refreshers → Task 2 (`build_session`). ✅
- LLM questions (cached + moderated) → reuses `generate_practice_quiz` (Tasks 2/3). ✅
- Cap 5, weak-first → Task 2 (`SESSION_CAP`, ordering). ✅
- Per-correct XP → goal/streak → Task 3 (`record_xp` + `record_daily_activity`). ✅
- Wrong-refresher creates weak concept → Task 3 (tested). ✅
- Always-available card + weak-count-led copy → Task 6. ✅
- Revise tab/hub + module pick + weak-first sort/badges → Tasks 4 (`list_revisable_modules`) + 7. ✅
- Session one-at-a-time + weak/refresher badges + XP feedback + summary → Task 8. ✅
- A11y (vitest-axe) → Tasks 6/7/8. ✅
- No migration → confirmed (reuses existing tables). ✅
- Server-authoritative correctness (re-derive via cache) → Task 3. ✅

**2. Placeholder scan:** No TBD/TODO. The two "verify against an existing file" notes (auth-fixture name in Task 4; `limiter`/`get_session`/`get_current_user` import paths) are correctness guards for real-but-unconfirmed names, not placeholders — every code block is complete.

**3. Type/name consistency:** `encode_ref`/`decode_ref`, `build_session(session, user, *, module_id)`, `record_answer(session, user, ref, selected_index)`, `list_revisable_modules(session, user)`, `SESSION_CAP=5`, `XP_PER_CORRECT=5`, item keys `{ref, kind, module_id, lesson_id, concept, question, choices}`, `ReviseQuestion`/`ReviseSession`/`ReviseModule`/`ReviseAnswerIn`/`ReviseAnswerResult`, `reviseApi.{getModules,getSession,postAnswer}` — used identically across backend, schemas, client, and pages. Answer result keys `{correct, answer_index, explanation, xp_awarded, goal_met}` match between `record_answer`, the schema, and the session page.
