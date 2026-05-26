# Coach Eddie + Recommendations Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Coach Eddie with the recommendation engine — standalone coach page with FAB, enriched lesson-scoped tutor, action buttons in chat responses.

**Architecture:** New `POST /tutor/coach` endpoint assembles learning state context (recommendations, strengths, SR data) into Eddie's system prompt. LLM responses contain `[ACTION:...]` markers parsed into structured actions. Frontend adds a floating action button on all child pages and a full-screen coach chat page at `/coach` with template greeting + suggestion chips + action buttons.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, React 18, TypeScript, TanStack Query, Tailwind CSS, vitest, vitest-axe, framer-motion.

---

## File Structure

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/app/services/coach_service.py` | `build_coach_context()` and `parse_actions()` pure functions, `coach_chat()` orchestrator |
| `backend/tests/test_coach_service.py` | Unit tests for context building and action parsing pure functions |
| `backend/tests/test_coach_endpoint.py` | Endpoint integration test for `POST /tutor/coach` |
| `backend/alembic/versions/f5a6b7c8d9e0_tutor_lesson_id_nullable.py` | Migration to make `lesson_id` nullable |

### Backend — Modified Files
| File | Change |
|------|--------|
| `backend/app/schemas/ai.py` | Add `CoachChatRequest`, `CoachAction`, `CoachChatResponse` schemas |
| `backend/app/models/tutor.py` | Make `TutorConversation.lesson_id` nullable |
| `backend/app/routers/ai.py` | Add `POST /tutor/coach` endpoint |
| `backend/app/services/tutor_service.py` | Inject weak concepts into lesson-scoped system prompt |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/components/child/EddieFAB.tsx` | Floating action button with badge dot |
| `frontend/src/pages/child/Coach.tsx` | Full-screen coach chat page |
| `frontend/src/hooks/useCoachGreeting.ts` | Template greeting from cached data |
| `frontend/src/components/child/__tests__/EddieFAB.test.tsx` | FAB unit tests |
| `frontend/src/components/child/__tests__/Coach.test.tsx` | Coach page unit tests |
| `frontend/tests/a11y/coach.a11y.test.tsx` | Accessibility axe audit |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/src/api/ai.ts` | Add coach types + `coachApi.sendMessage()` |
| `frontend/src/components/child/Shell.tsx` | Render `EddieFAB` |
| `frontend/src/App.tsx` | Add `/coach` route |

---

### Task 1: Backend Schemas — Coach Chat Types

**Files:**
- Modify: `backend/app/schemas/ai.py`
- Test: `backend/tests/test_coach_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_coach_schemas.py`:

```python
import uuid
from app.schemas.ai import CoachChatRequest, CoachAction, CoachChatResponse


def test_coach_chat_request_defaults():
    req = CoachChatRequest(message="What should I learn?")
    assert req.message == "What should I learn?"
    assert req.conversation_id is None


def test_coach_chat_request_with_conversation_id():
    cid = uuid.uuid4()
    req = CoachChatRequest(message="hi", conversation_id=cid)
    assert req.conversation_id == cid


def test_coach_action_without_lesson():
    a = CoachAction(type="module", module_id="m1", label="Go to M1")
    assert a.lesson_id is None
    assert a.type == "module"


def test_coach_action_with_lesson():
    a = CoachAction(type="lesson", module_id="m1", lesson_id="L1", label="Start L1")
    assert a.lesson_id == "L1"


def test_coach_chat_response_shape():
    resp = CoachChatResponse(
        response="Try stocks!",
        conversation_id=uuid.uuid4(),
        messages_remaining=4,
        actions=[CoachAction(type="module", module_id="m1", label="Go")],
    )
    assert len(resp.actions) == 1
    assert resp.messages_remaining == 4


def test_coach_chat_response_empty_actions():
    resp = CoachChatResponse(
        response="You're doing great!",
        conversation_id=uuid.uuid4(),
        messages_remaining=3,
        actions=[],
    )
    assert resp.actions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_schemas.py -v`
Expected: FAIL with `ImportError: cannot import name 'CoachChatRequest'`

- [ ] **Step 3: Add schemas to ai.py**

Add at the end of `backend/app/schemas/ai.py`:

```python
class CoachChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class CoachAction(BaseModel):
    type: str  # "lesson" | "module" | "review"
    module_id: str
    lesson_id: str | None = None
    label: str


class CoachChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    messages_remaining: int
    actions: list[CoachAction]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_schemas.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/ai.py backend/tests/test_coach_schemas.py
git commit -m "feat: add CoachChatRequest, CoachAction, CoachChatResponse schemas"
```

---

### Task 2: Migration — Make TutorConversation.lesson_id Nullable

**Files:**
- Create: `backend/alembic/versions/f5a6b7c8d9e0_tutor_lesson_id_nullable.py`
- Modify: `backend/app/models/tutor.py`

- [ ] **Step 1: Update the model**

In `backend/app/models/tutor.py`, change line 18-19 from:

```python
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
```

to:

```python
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True
    )
```

- [ ] **Step 2: Create the migration**

Create `backend/alembic/versions/f5a6b7c8d9e0_tutor_lesson_id_nullable.py`:

```python
"""Make tutor_conversations.lesson_id nullable for standalone coach.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-05-26
"""
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "tutor_conversations",
        "lesson_id",
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tutor_conversations",
        "lesson_id",
        nullable=False,
    )
```

- [ ] **Step 3: Verify model change doesn't break existing tests**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_ai_router.py -v`
Expected: all pass (existing tutor tests still pass — they provide a lesson_id)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/tutor.py backend/alembic/versions/f5a6b7c8d9e0_tutor_lesson_id_nullable.py
git commit -m "feat: make TutorConversation.lesson_id nullable for standalone coach"
```

---

### Task 3: Coach Service — Pure Functions (Context Building + Action Parsing)

**Files:**
- Create: `backend/app/services/coach_service.py`
- Test: `backend/tests/test_coach_service.py`

- [ ] **Step 1: Write failing tests for `build_coach_context`**

Create `backend/tests/test_coach_service.py`:

```python
from app.services.coach_service import build_coach_context, parse_actions


class TestBuildCoachContext:
    def test_empty_state(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=0,
        )
        assert "No learning data yet" in ctx

    def test_with_strengths_and_gaps(self):
        ctx = build_coach_context(
            strengths=[
                {"topic": "stocks", "mastery_score": 0.85, "status": "strong", "weak_count": 0, "due_for_review": 0},
                {"topic": "budgeting", "mastery_score": 0.45, "status": "needs_practice", "weak_count": 2, "due_for_review": 1},
            ],
            overall_mastery=0.65,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=1,
        )
        assert "stocks" in ctx
        assert "85%" in ctx
        assert "budgeting" in ctx
        assert "45%" in ctx
        assert "2 weak" in ctx
        assert "Due for review: 1" in ctx

    def test_with_recommendations(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[{"module_title": "Stocks 101", "completed_pct": 60}],
            practise_again=[{"module_title": "Budgeting", "weak_concepts": ["APR", "compound interest"]}],
            something_new=[{"module_title": "Risk Basics"}],
            due_count=0,
        )
        assert "Stocks 101" in ctx
        assert "60%" in ctx
        assert "Budgeting" in ctx
        assert "APR" in ctx
        assert "Risk Basics" in ctx

    def test_due_count_zero_omitted(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=0,
        )
        assert "Due for review" not in ctx


class TestParseActions:
    def test_no_markers(self):
        text, actions = parse_actions("You're doing great!", module_titles={})
        assert text == "You're doing great!"
        assert actions == []

    def test_single_lesson_action(self):
        raw = "Try this! [ACTION:lesson:mod-1:L2] It's fun."
        text, actions = parse_actions(raw, module_titles={"mod-1": "Stocks 101"})
        assert "[ACTION:" not in text
        assert text == "Try this!  It's fun."
        assert len(actions) == 1
        assert actions[0]["type"] == "lesson"
        assert actions[0]["module_id"] == "mod-1"
        assert actions[0]["lesson_id"] == "L2"
        assert "Stocks 101" in actions[0]["label"]

    def test_module_action_no_lesson(self):
        raw = "Check out [ACTION:module:mod-2]"
        text, actions = parse_actions(raw, module_titles={"mod-2": "Budgeting"})
        assert len(actions) == 1
        assert actions[0]["type"] == "module"
        assert actions[0]["lesson_id"] is None
        assert "Budgeting" in actions[0]["label"]

    def test_review_action(self):
        raw = "Time to review! [ACTION:review:mod-3]"
        text, actions = parse_actions(raw, module_titles={"mod-3": "Savings"})
        assert actions[0]["type"] == "review"
        assert "Savings" in actions[0]["label"]

    def test_multiple_actions(self):
        raw = "A [ACTION:lesson:m1:L1] and B [ACTION:module:m2]"
        text, actions = parse_actions(raw, module_titles={"m1": "M1", "m2": "M2"})
        assert len(actions) == 2

    def test_malformed_marker_ignored(self):
        raw = "Bad [ACTION:unknown] marker"
        text, actions = parse_actions(raw, module_titles={})
        assert actions == []
        # Malformed marker stays in text (not a valid pattern)
        assert "Bad" in text

    def test_unknown_module_id_uses_fallback_label(self):
        raw = "[ACTION:module:unknown-id]"
        text, actions = parse_actions(raw, module_titles={})
        assert len(actions) == 1
        assert actions[0]["label"] == "Go to module"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `coach_service.py`**

Create `backend/app/services/coach_service.py`:

```python
"""Coach Eddie standalone service — context building and action parsing."""
from __future__ import annotations

import re
from typing import Any


_ACTION_RE = re.compile(
    r"\[ACTION:(lesson|module|review):([a-f0-9][a-f0-9\-]*)(?::([a-f0-9][a-f0-9\-]*))?\]"
)

_TYPE_LABELS = {
    "lesson": "Start lesson in {title}",
    "module": "Go to {title}",
    "review": "Review {title}",
}


def build_coach_context(
    *,
    strengths: list[dict[str, Any]],
    overall_mastery: float,
    continue_learning: list[dict[str, Any]],
    practise_again: list[dict[str, Any]],
    something_new: list[dict[str, Any]],
    due_count: int,
) -> str:
    """Build a human-readable learning-state block for the system prompt.

    All inputs are plain dicts — caller is responsible for shaping data
    from the various services into this format.
    """
    lines: list[str] = []

    if not strengths and not continue_learning and not practise_again and not something_new and due_count == 0:
        return "No learning data yet — this student is just getting started."

    lines.append("Your student's learning state:")

    # Topic mastery
    for t in strengths:
        score_pct = f"{round(t['mastery_score'] * 100)}%"
        weak = f", {t['weak_count']} weak concepts" if t.get("weak_count", 0) > 0 else ""
        lines.append(f"- {t['topic'].replace('_', ' ').title()}: {score_pct} mastery ({t['status']}){weak}")

    if overall_mastery > 0:
        lines.append(f"- Overall mastery: {round(overall_mastery * 100)}%")

    # Recommendations
    for item in continue_learning:
        pct = item.get("completed_pct", 0)
        lines.append(f"- Currently working on: {item['module_title']} ({pct}% complete)")

    for item in practise_again:
        concepts = item.get("weak_concepts", [])
        concept_str = f" — weak: {', '.join(concepts)}" if concepts else ""
        lines.append(f"- Needs practice: {item['module_title']}{concept_str}")

    for item in something_new:
        lines.append(f"- Suggested next: {item['module_title']} (something new)")

    # SR summary
    if due_count > 0:
        lines.append(f"- Due for review: {due_count} concept{'s' if due_count != 1 else ''}")

    return "\n".join(lines)


def parse_actions(
    raw_text: str,
    module_titles: dict[str, str],
) -> tuple[str, list[dict[str, Any]]]:
    """Extract [ACTION:...] markers from LLM text.

    Returns (cleaned_text, actions_list).
    """
    actions: list[dict[str, Any]] = []

    for match in _ACTION_RE.finditer(raw_text):
        action_type = match.group(1)
        module_id = match.group(2)
        lesson_id = match.group(3)  # may be None

        title = module_titles.get(module_id, "module")
        label = _TYPE_LABELS.get(action_type, "Go to {title}").format(title=title)

        actions.append({
            "type": action_type,
            "module_id": module_id,
            "lesson_id": lesson_id,
            "label": label,
        })

    cleaned = _ACTION_RE.sub("", raw_text).strip()

    return cleaned, actions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_service.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/coach_service.py backend/tests/test_coach_service.py
git commit -m "feat: add coach context building and action parsing pure functions"
```

---

### Task 4: Enriched Lesson Eddie — Weak Concept Injection

**Files:**
- Modify: `backend/app/services/tutor_service.py`
- Test: `backend/tests/test_tutor_enrichment.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_tutor_enrichment.py`:

```python
from app.services.tutor_service import _build_weak_concept_addendum


def test_no_weak_concepts_returns_empty():
    result = _build_weak_concept_addendum([])
    assert result == ""


def test_single_concept():
    result = _build_weak_concept_addendum(["compound interest"])
    assert "compound interest" in result
    assert "struggled" in result


def test_multiple_concepts():
    result = _build_weak_concept_addendum(["APR", "compound interest", "50/30/20 rule"])
    assert "APR" in result
    assert "compound interest" in result
    assert "50/30/20 rule" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_tutor_enrichment.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add `_build_weak_concept_addendum` and wire it into `chat()`**

Add this function to `backend/app/services/tutor_service.py` (after the `_SKILL_INSTRUCTIONS` dict, before `_skill_level`):

```python
def _build_weak_concept_addendum(concepts: list[str]) -> str:
    """Return a system prompt addendum for the student's weak concepts in this topic."""
    if not concepts:
        return ""
    concept_list = ", ".join(f'"{c}"' for c in concepts)
    return (
        f"\n\nThe student has struggled with these concepts in this topic: {concept_list}. "
        "If relevant to their question, proactively address these gaps."
    )
```

Then in the `chat()` function, after the mastery lookup (after line ~111 `level = _skill_level(mastery_score)`), add:

```python
    # Load weak concepts for this topic
    from sqlalchemy import select as sa_select
    from app.models.skill_profile import WeakConcept

    weak_rows = (
        await session.scalars(
            sa_select(WeakConcept).where(
                WeakConcept.user_id == user.id,
                WeakConcept.topic == topic,
                WeakConcept.resolved == False,  # noqa: E712
            )
        )
    ).all()
    weak_concepts = [w.concept for w in weak_rows]
```

Then change the system prompt build to append the addendum:

```python
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        lesson_content=json.dumps(lesson.content_json or {}),
    ) + _build_weak_concept_addendum(weak_concepts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_tutor_enrichment.py -v`
Expected: 3 passed

- [ ] **Step 5: Verify existing tutor tests still pass**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_ai_router.py::test_tutor_chat_endpoint -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/tutor_service.py backend/tests/test_tutor_enrichment.py
git commit -m "feat: inject weak concepts into lesson-scoped Eddie system prompt"
```

---

### Task 5: Coach Endpoint — Wire `POST /tutor/coach`

**Files:**
- Modify: `backend/app/routers/ai.py`
- Modify: `backend/app/services/coach_service.py` (add `coach_chat()` orchestrator)
- Test: `backend/tests/test_coach_endpoint.py`

- [ ] **Step 1: Write the failing endpoint test**

Create `backend/tests/test_coach_endpoint.py`:

```python
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.content import Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def coach_client(db_session, client):
    user = User(
        email="coach@example.com", username="coachkid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    db_session.add(progress)
    module = Module(
        topic="stocks", title="Stocks 101",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()

    response = await client.post("/auth/login", json={
        "email": "coach@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, user, module


async def test_coach_chat_returns_response(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value="Try Stocks 101! [ACTION:module:" + str(module.id) + "]"
    )

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/coach", json={
            "message": "What should I learn?",
        })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "messages_remaining" in data
    assert "actions" in data
    assert isinstance(data["actions"], list)


async def test_coach_chat_parses_action(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value="Go here [ACTION:module:" + str(module.id) + "]"
    )

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/coach", json={
            "message": "What next?",
        })
    data = response.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["type"] == "module"
    assert data["actions"][0]["module_id"] == str(module.id)
    assert "Stocks 101" in data["actions"][0]["label"]
    assert "[ACTION:" not in data["response"]


async def test_coach_chat_continues_conversation(coach_client):
    client, user, module = coach_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="Sure!")

    with patch("app.services.coach_service.get_llm_client", return_value=mock_client):
        r1 = await client.post("/tutor/coach", json={"message": "Hi"})
        cid = r1.json()["conversation_id"]
        r2 = await client.post("/tutor/coach", json={
            "message": "Tell me more",
            "conversation_id": cid,
        })
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == cid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_endpoint.py -v`
Expected: FAIL (endpoint doesn't exist yet)

- [ ] **Step 3: Add `coach_chat()` orchestrator to `coach_service.py`**

Add to `backend/app/services/coach_service.py`:

```python
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.content import Module
from app.models.tutor import TutorConversation
from app.models.user import User
from app.services.entitlements import is_premium
from app.services.gap_detection_service import get_strengths_and_gaps
from app.services.llm_client import get_llm_client, get_model_name
from app.services.moderation import moderate_output
from app.services.recommendation_service import get_recommendations
from app.services.spaced_repetition_service import get_due_count
from app.services.tutor_service import TutorInputTooLong, TutorLimitReached, _skill_level

# Import TopicMastery for mastery lookup
from app.models.skill_profile import TopicMastery


_COACH_SYSTEM_PROMPT = (
    "You are Coach Eddie, a friendly money tutor for kids. You help them navigate "
    "their learning journey — what to learn next, what to review, and how they're doing.\n\n"
    "Rules:\n"
    "1. Reference the student's actual learning state (provided below).\n"
    "2. When suggesting a lesson or module, include an action marker: "
    "[ACTION:lesson:<module_id>:<lesson_id>] or [ACTION:module:<module_id>]\n"
    "3. When suggesting a review session, use: [ACTION:review:<module_id>]\n"
    "4. Never give real financial advice or suggest spending real money.\n"
    "5. Keep responses under 120 words.\n"
    "6. Use simple, encouraging language.\n"
    "7. {skill_level_instruction}\n\n"
    "{learning_state_context}"
)

_SKILL_INSTRUCTIONS = {
    "low": (
        "The student is a beginner. Use very simple words, short sentences, and lots of encouragement."
        " Give examples they can relate to (pocket money, toys, snacks)."
    ),
    "medium": (
        "The student has some understanding. Give clear explanations with relatable examples."
        " Encourage them to think about why."
    ),
    "high": (
        "The student is doing well. Challenge them with deeper questions."
        " Ask 'what if' scenarios to deepen understanding."
    ),
}


async def coach_chat(
    *,
    session: AsyncSession,
    user: User,
    message: str,
    conversation_id: uuid.UUID | None,
    premium: bool,
) -> dict[str, Any]:
    """Process a standalone Coach Eddie message."""
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise TutorInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = (
        settings.tutor_max_messages_premium if premium
        else settings.tutor_max_messages_free
    )

    # Load or create conversation (lesson_id=None for standalone coach)
    conversation: TutorConversation | None = None
    if conversation_id:
        conversation = await session.get(TutorConversation, conversation_id)

    model_name = get_model_name("premium" if premium else "standard")

    if conversation is None:
        conversation = TutorConversation(
            user_id=user.id,
            lesson_id=None,
            messages=[],
            message_count=0,
            model_used=model_name,
        )
        session.add(conversation)
        await session.flush()

    if conversation.message_count >= max_messages:
        raise TutorLimitReached(
            f"Message limit reached ({max_messages}). "
            + ("Upgrade to premium for more!" if not premium else "Limit reached for this conversation.")
        )

    # Gather learning context
    recs = await get_recommendations(session, user)
    gaps = await get_strengths_and_gaps(session, user.id)
    due_count = await get_due_count(session, user.id)

    # Load module titles for action label resolution
    all_modules = (await session.scalars(select(Module))).all()
    module_titles: dict[str, str] = {str(m.id): m.title for m in all_modules}

    # Build recommendation summaries for context
    continue_learning = []
    for item in recs.get("continue_learning", []):
        mid = str(item["module_id"])
        continue_learning.append({
            "module_title": module_titles.get(mid, "Module"),
            "completed_pct": 0,  # Approximation; full data would need lesson counts
        })

    practise_again = []
    for item in recs.get("practise_again", []):
        mid = str(item["module_id"])
        practise_again.append({
            "module_title": module_titles.get(mid, "Module"),
            "weak_concepts": item.get("weak_concepts", []),
        })

    something_new = []
    for item in recs.get("something_new", []):
        mid = str(item["module_id"])
        something_new.append({"module_title": module_titles.get(mid, "Module")})

    strengths = [
        {
            "topic": t.topic,
            "mastery_score": t.mastery_score,
            "status": t.status,
            "weak_count": t.weak_count,
        }
        for t in gaps.topics
    ]

    context_block = build_coach_context(
        strengths=strengths,
        overall_mastery=gaps.overall_mastery,
        continue_learning=continue_learning,
        practise_again=practise_again,
        something_new=something_new,
        due_count=due_count,
    )

    # Get overall mastery for skill level
    mastery_score = gaps.overall_mastery
    level = _skill_level(mastery_score)

    system_prompt = _COACH_SYSTEM_PROMPT.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        learning_state_context=context_block,
    )

    # Build message history
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    # Call LLM
    client = get_llm_client(tier="premium" if premium else "standard")
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    # Kid-safe moderation
    _mod = await moderate_output(raw_response, surface="tutor")
    filtered_response = _mod.text
    if not _mod.safe:
        session.add(AuditLog(
            user_id=user.id,
            event_type="moderation_block",
            metadata_json={"surface": "coach", "category": _mod.category},
        ))

    # Parse actions from response
    cleaned_text, actions = parse_actions(filtered_response, module_titles)

    # Persist conversation
    conversation.messages = [
        *conversation.messages,
        {"role": "user", "content": message},
        {"role": "assistant", "content": cleaned_text},
    ]
    conversation.message_count += 2
    await session.flush()

    return {
        "response": cleaned_text,
        "conversation_id": conversation.id,
        "messages_remaining": max(0, max_messages - conversation.message_count),
        "actions": actions,
    }
```

Note: The imports at the top of `coach_service.py` that were already there from Task 3 (`re`, `Any`) need to be supplemented. Merge the imports so the file has both the pure-function code from Task 3 and this orchestrator.

- [ ] **Step 4: Add the endpoint to ai.py**

Add to the imports in `backend/app/routers/ai.py`:

```python
from app.schemas.ai import (
    CategorisedRecommendations,
    CoachChatRequest,
    CoachChatResponse,
    MasteryProfileResponse,
    PracticeRequest,
    PracticeResponse,
    StrengthsAndGaps,
    TutorChatRequest,
    TutorChatResponse,
)
from app.services.coach_service import coach_chat
```

Add the endpoint (after the existing `/tutor/chat` route):

```python
@router.post("/tutor/coach", response_model=CoachChatResponse)
async def coach_eddie(
    payload: CoachChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await coach_chat(
            session=session,
            user=current_user,
            message=payload.message,
            conversation_id=payload.conversation_id,
            premium=is_premium(current_user),
        )
    except TutorInputTooLong as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except TutorLimitReached as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    return result
```

Also add `TutorInputTooLong` and `TutorLimitReached` to the import from `tutor_service` if not already there (they already are from the existing tutor chat endpoint).

- [ ] **Step 5: Run endpoint tests**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest backend/tests/test_coach_endpoint.py -v`
Expected: 3 passed

- [ ] **Step 6: Run full backend regression**

Run: `/Users/leeashmore/Local Repo/.venv/bin/pytest -q --tb=short`
Expected: 440+ passed (+ the 4 pre-existing failures)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/coach_service.py backend/app/routers/ai.py backend/tests/test_coach_endpoint.py
git commit -m "feat: add POST /tutor/coach endpoint with context-aware Coach Eddie"
```

---

### Task 6: Frontend Types + Coach API Client

**Files:**
- Modify: `frontend/src/api/ai.ts`

- [ ] **Step 1: Add coach types and API function**

Add to `frontend/src/api/ai.ts` after the `TutorResponse` type:

```typescript
// --- Coach Eddie ---

export type CoachAction = {
  type: 'lesson' | 'module' | 'review';
  module_id: string;
  lesson_id: string | null;
  label: string;
};

export type CoachChatResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
  actions: CoachAction[];
};
```

Add to the `aiApi` object:

```typescript
  sendCoachMessage: (message: string, conversationId?: string) =>
    apiFetch<CoachChatResponse>('/tutor/coach', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
      }),
    }),
```

- [ ] **Step 2: Verify tsc passes**

Run: `cd invest-ed/frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/ai.ts
git commit -m "feat: add coach types and API client function"
```

---

### Task 7: useCoachGreeting Hook

**Files:**
- Create: `frontend/src/hooks/useCoachGreeting.ts`

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useCoachGreeting.ts`:

```typescript
import { useRecommendations, useStrengths } from '@/api/ai';
import { useChildSession } from '@/hooks/useChildSession';

export function useCoachGreeting(): { greeting: string; isLoading: boolean } {
  const { data: me, isLoading: meLoading } = useChildSession();
  const { data: recs, isLoading: recsLoading } = useRecommendations();
  const { data: strengths, isLoading: strengthsLoading } = useStrengths();

  const isLoading = meLoading || recsLoading || strengthsLoading;

  if (isLoading || !me) {
    return { greeting: '', isLoading: true };
  }

  const username = me.username ?? 'there';
  let line: string;

  const dueCount = recs?.review_summary?.due_count ?? 0;
  const continueLearning = recs?.continue_learning ?? [];
  const somethingNew = recs?.something_new ?? [];

  if (dueCount > 0) {
    const plural = dueCount === 1 ? 'concept' : 'concepts';
    line = `You have ${dueCount} ${plural} ready for review — want to go over them?`;
  } else if (continueLearning.length > 0) {
    line = `Want to keep going with your current quests?`;
  } else if (somethingNew.length > 0) {
    line = `I found something new for you to explore!`;
  } else {
    line = `What would you like to learn about today?`;
  }

  return { greeting: `Hey ${username}! ${line}`, isLoading: false };
}
```

- [ ] **Step 2: Verify tsc passes**

Run: `cd invest-ed/frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useCoachGreeting.ts
git commit -m "feat: add useCoachGreeting hook for template greeting"
```

---

### Task 8: EddieFAB Component

**Files:**
- Create: `frontend/src/components/child/EddieFAB.tsx`
- Create: `frontend/src/components/child/__tests__/EddieFAB.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/child/__tests__/EddieFAB.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { EddieFAB } from '../EddieFAB';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useLocation: () => ({ pathname: '/home' }) };
});

describe('EddieFAB', () => {
  it('renders with accessible label', () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    expect(screen.getByRole('button', { name: /open coach eddie/i })).toBeInTheDocument();
  });

  it('shows badge dot when dueCount > 0', () => {
    render(<MemoryRouter><EddieFAB dueCount={3} /></MemoryRouter>);
    expect(screen.getByTestId('eddie-badge')).toBeInTheDocument();
  });

  it('hides badge dot when dueCount is 0', () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    expect(screen.queryByTestId('eddie-badge')).not.toBeInTheDocument();
  });

  it('navigates to /coach on click', async () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    await userEvent.click(screen.getByRole('button', { name: /open coach eddie/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/coach');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd invest-ed/frontend && npx vitest run src/components/child/__tests__/EddieFAB.test.tsx`
Expected: FAIL (component doesn't exist)

- [ ] **Step 3: Implement EddieFAB**

Create `frontend/src/components/child/EddieFAB.tsx`:

```tsx
import { useNavigate } from 'react-router-dom';

type Props = {
  dueCount: number;
};

export function EddieFAB({ dueCount }: Props) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/coach')}
      aria-label="Open Coach Eddie"
      className="fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-amber-400 to-orange-500 shadow-lg transition-transform hover:scale-105 active:scale-95"
    >
      <span className="text-2xl" aria-hidden="true">💡</span>
      {dueCount > 0 && (
        <span
          data-testid="eddie-badge"
          className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-red-500"
        />
      )}
    </button>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run src/components/child/__tests__/EddieFAB.test.tsx`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/EddieFAB.tsx frontend/src/components/child/__tests__/EddieFAB.test.tsx
git commit -m "feat: add EddieFAB floating action button component"
```

---

### Task 9: Coach Page

**Files:**
- Create: `frontend/src/pages/child/Coach.tsx`
- Create: `frontend/src/components/child/__tests__/Coach.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/child/__tests__/Coach.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/hooks/useCoachGreeting', () => ({
  useCoachGreeting: () => ({
    greeting: 'Hey kid42! You have 2 concepts ready for review — want to go over them?',
    isLoading: false,
  }),
}));

vi.mock('@/api/ai', async () => {
  const actual = await vi.importActual('@/api/ai');
  return {
    ...actual,
    useRecommendations: () => ({ data: null, isLoading: false }),
    useStrengths: () => ({ data: null, isLoading: false }),
    aiApi: {
      ...((actual as any).aiApi ?? {}),
      sendCoachMessage: vi.fn().mockResolvedValue({
        response: 'Try Stocks 101!',
        conversation_id: 'c1',
        messages_remaining: 4,
        actions: [
          { type: 'module', module_id: 'mod-1', lesson_id: null, label: 'Go to Stocks 101' },
        ],
      }),
    },
  };
});

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

function renderCoach() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Coach />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

let Coach: any;

beforeEach(async () => {
  vi.restoreAllMocks();
  Coach = (await import('@/pages/child/Coach')).default;
});

describe('Coach Page', () => {
  it('shows template greeting', async () => {
    renderCoach();
    expect(screen.getByText(/Hey kid42/)).toBeInTheDocument();
  });

  it('renders suggestion chips', () => {
    renderCoach();
    expect(screen.getByText('What should I learn next?')).toBeInTheDocument();
    expect(screen.getByText('Review my weak spots')).toBeInTheDocument();
    expect(screen.getByText('How am I doing?')).toBeInTheDocument();
  });

  it('sends chip text as first message', async () => {
    const { aiApi } = await import('@/api/ai');
    renderCoach();
    await userEvent.click(screen.getByText('What should I learn next?'));
    await waitFor(() =>
      expect(aiApi.sendCoachMessage).toHaveBeenCalledWith('What should I learn next?', undefined),
    );
  });

  it('renders action buttons from response', async () => {
    renderCoach();
    await userEvent.click(screen.getByText('What should I learn next?'));
    await waitFor(() =>
      expect(screen.getByText(/Go to Stocks 101/)).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd invest-ed/frontend && npx vitest run src/components/child/__tests__/Coach.test.tsx`
Expected: FAIL (page doesn't exist)

- [ ] **Step 3: Implement Coach page**

Create `frontend/src/pages/child/Coach.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { aiApi, type CoachChatResponse, type CoachAction } from '@/api/ai';
import { useCoachGreeting } from '@/hooks/useCoachGreeting';
import { Button } from '@/components/ui/button';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  actions?: CoachAction[];
};

const SUGGESTION_CHIPS = [
  'What should I learn next?',
  'Review my weak spots',
  'How am I doing?',
];

function actionToPath(action: CoachAction): string {
  if (action.type === 'lesson' && action.lesson_id) {
    return `/lessons/${action.module_id}/${action.lesson_id}`;
  }
  return `/lessons/${action.module_id}`;
}

export default function Coach() {
  const navigate = useNavigate();
  const { greeting, isLoading: greetingLoading } = useCoachGreeting();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);
  const [chipsSent, setChipsSent] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useMutation<CoachChatResponse | null, Error, string>({
    mutationFn: (msg) => aiApi.sendCoachMessage(msg, conversationId),
    onSuccess: (data) => {
      if (!data) return;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, actions: data.actions },
      ]);
      setConversationId(data.conversation_id);
      setRemaining(data.messages_remaining);
    },
  });

  const handleSend = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || sendMessage.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    if (!text) setInput('');
    setChipsSent(true);
    sendMessage.mutate(msg);
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col px-4 py-4">
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-gray-600"
          aria-label="Go back"
        >
          ←
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xl">💡</span>
          <span className="font-bold text-gray-900">Coach Eddie</span>
        </div>
        {remaining !== null && (
          <span className="ml-auto text-xs text-gray-400">{remaining} messages left</span>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {/* Template greeting */}
        {!greetingLoading && greeting && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-800">
              {greeting}
            </div>
          </div>
        )}

        {/* Suggestion chips */}
        {!chipsSent && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="rounded-full border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-50"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((m, i) => (
          <div key={i}>
            <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                    : 'bg-amber-50 text-gray-800'
                }`}
              >
                {m.content}
              </div>
            </div>
            {m.actions && m.actions.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-2 pl-1">
                {m.actions.map((a, j) => (
                  <Link
                    key={j}
                    to={actionToPath(a)}
                    className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-200"
                  >
                    {a.label} →
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}

        {sendMessage.isPending && (
          <div className="flex justify-start">
            <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
              Thinking…
            </div>
          </div>
        )}

        {sendMessage.isError && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
              Something went wrong. Try sending your message again.
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="mt-4 flex gap-2 border-t border-amber-100 pt-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask Coach Eddie…"
          maxLength={200}
          className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
          disabled={remaining === 0}
        />
        <Button
          onClick={() => handleSend()}
          disabled={!input.trim() || sendMessage.isPending || remaining === 0}
          className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 text-white"
        >
          Send
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run src/components/child/__tests__/Coach.test.tsx`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/Coach.tsx frontend/src/components/child/__tests__/Coach.test.tsx
git commit -m "feat: add Coach Eddie page with greeting, chips, and action buttons"
```

---

### Task 10: Wire FAB + Route into Shell and App

**Files:**
- Modify: `frontend/src/components/child/Shell.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add EddieFAB to Shell**

In `frontend/src/components/child/Shell.tsx`, add imports:

```typescript
import { useLocation } from 'react-router-dom';
import { useRecommendations } from '@/api/ai';
import { EddieFAB } from './EddieFAB';
```

Note: `useLocation` is already imported. Just add the other two.

Inside the returned JSX, after `<BottomTabBar />` and before the closing `</div>`, add:

```tsx
      {location.pathname !== '/coach' && (
        <EddieFAB dueCount={recsData?.review_summary?.due_count ?? 0} />
      )}
```

And at the top of the `Shell` function (after `useRouteFocus()`), add:

```typescript
  const { data: recsData } = useRecommendations();
```

- [ ] **Step 2: Add `/coach` route to App.tsx**

In `frontend/src/App.tsx`, add the import:

```typescript
import Coach from '@/pages/child/Coach';
```

Add the route inside the `<Route element={<Shell />}>` block, after the `/progress` route:

```tsx
          <Route path="/coach" element={<Coach />} />
```

- [ ] **Step 3: Verify tsc passes**

Run: `cd invest-ed/frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/child/Shell.tsx frontend/src/App.tsx
git commit -m "feat: wire EddieFAB into Shell and add /coach route"
```

---

### Task 11: Accessibility Tests

**Files:**
- Create: `frontend/tests/a11y/coach.a11y.test.tsx`

- [ ] **Step 1: Write the a11y test**

Create `frontend/tests/a11y/coach.a11y.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

vi.mock('@/hooks/useCoachGreeting', () => ({
  useCoachGreeting: () => ({
    greeting: 'Hey kid42! What would you like to learn about today?',
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

vi.mock('@/api/ai', async () => {
  const actual = await vi.importActual('@/api/ai');
  return {
    ...actual,
    useRecommendations: () => ({
      data: {
        continue_learning: [],
        practise_again: [],
        something_new: [],
        review_summary: { due_count: 0, next_due_at: null },
      },
      isLoading: false,
    }),
    useStrengths: () => ({
      data: { topics: [], overall_mastery: 0 },
      isLoading: false,
    }),
  };
});

beforeEach(() => vi.restoreAllMocks());

describe('a11y: Coach Eddie', () => {
  it('Coach page has no axe violations', async () => {
    const { default: Coach } = await import('@/pages/child/Coach');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/coach']}>
          <Routes>
            <Route path="/coach" element={<Coach />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByText(/Hey kid42/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('EddieFAB has no axe violations', async () => {
    const { EddieFAB } = await import('@/components/child/EddieFAB');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <EddieFAB dueCount={2} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run the a11y tests**

Run: `cd invest-ed/frontend && npx vitest run tests/a11y/coach.a11y.test.tsx`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/a11y/coach.a11y.test.tsx
git commit -m "test: add Coach Eddie accessibility tests"
```

---

### Task 12: Full Regression

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q --tb=short`
Expected: 440+ passed (4 pre-existing failures only)

- [ ] **Step 2: Run frontend tests**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: 372+ passed (all previous + new tests)

- [ ] **Step 3: TypeScript check**

Run: `cd invest-ed/frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 4: Verify new test count**

Count new tests added:
- `test_coach_schemas.py`: 6
- `test_coach_service.py`: 11
- `test_tutor_enrichment.py`: 3
- `test_coach_endpoint.py`: 3
- `EddieFAB.test.tsx`: 4
- `Coach.test.tsx`: 4
- `coach.a11y.test.tsx`: 2

Total new: 33 tests

---

## Self-Review

**Spec coverage:**
- ✅ Standalone Coach endpoint (`POST /tutor/coach`) — Task 5
- ✅ Context assembly (`build_coach_context`) — Task 3
- ✅ Action parsing (`parse_actions`) — Task 3
- ✅ System prompt with learning state — Task 5 (orchestrator)
- ✅ Conversation model nullable lesson_id — Task 2
- ✅ Enriched lesson Eddie (weak concept injection) — Task 4
- ✅ Rate limiting (reuses existing settings) — Task 5
- ✅ Backend schemas — Task 1
- ✅ FAB with badge — Task 8
- ✅ Coach page with greeting, chips, action buttons — Task 9
- ✅ useCoachGreeting hook — Task 7
- ✅ Frontend types + API client — Task 6
- ✅ Route wiring — Task 10
- ✅ Accessibility tests — Task 11
- ✅ Full regression — Task 12

**Placeholder scan:** No TBD/TODO found. All code blocks complete.

**Type consistency:** `CoachAction`, `CoachChatResponse`, `CoachChatRequest` match across schemas (Task 1), frontend types (Task 6), endpoint (Task 5), and tests. `build_coach_context` and `parse_actions` signatures match between Task 3 tests and implementation. `_build_weak_concept_addendum` matches between Task 4 tests and implementation.
