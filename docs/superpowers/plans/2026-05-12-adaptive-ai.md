# Adaptive AI — Personalised Learning Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI layer that tracks skill profiles, recommends quests, generates practice content, and provides an optional AI tutor — making each child's learning experience personal.

**Architecture:** A `SkillProfile` data model feeds a deterministic recommendation engine (no LLM cost). A provider-agnostic `LLMClient` abstraction powers two LLM features: practice quiz generation (grounded in lesson content) and a conversational tutor ("Coach Eddie"). Premium users get a stronger model and higher limits.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, OpenAI SDK, Anthropic SDK, sse-starlette, Pydantic, React 18, TanStack Query, TypeScript

---

### File Structure

**New backend files:**

```
backend/app/
  models/
    skill_profile.py            — TopicMastery + WeakConcept models
  schemas/
    ai.py                       — Pydantic schemas for recommendations, practice, tutor, mastery
  services/
    llm_client.py               — LLMClient protocol + OpenAI/Anthropic implementations
    skill_profile_service.py    — update_mastery(), record_weak_concept(), get_profile()
    recommendation_service.py   — score_modules(), get_recommendations()
    ai_content_service.py       — generate_practice_quiz()
    tutor_service.py            — chat(), build system prompt, safety filter
  routers/
    ai.py                       — /recommendations, /lessons/{id}/practice, /tutor/chat, /profile/mastery
backend/alembic/versions/
    xxxx_add_skill_profile_tables.py
backend/tests/
    test_skill_profile_service.py
    test_recommendation_service.py
    test_llm_client.py
    test_ai_content_service.py
    test_tutor_service.py
    test_ai_router.py
```

**Modified backend files:**

```
backend/app/core/config.py     — Add LLM + tutor config fields
backend/app/models/__init__.py — Register new models
backend/app/main.py            — Include ai router, add /tutor/chat to CSRF exemptions
backend/app/routers/content.py — Update complete_lesson to update skill profile + return practice_available
backend/app/schemas/content.py — Add practice_available to LessonCompletionResult
backend/tests/conftest.py      — Add cleanup for new tables
```

**New frontend files:**

```
frontend/src/
  api/ai.ts                                         — API client for AI endpoints
  components/child/lesson/CoachEddiePanel.tsx        — Slide-up tutor chat panel
  components/child/lesson/PracticeQuiz.tsx            — Practice quiz wrapper
  components/child/MasteryBadge.tsx                   — Topic mastery progress ring
```

**Modified frontend files:**

```
frontend/src/api/content.ts            — Add practice_available to LessonCompletionResult type
frontend/src/pages/child/Home.tsx      — Use /recommendations for next quest
frontend/src/pages/child/Lesson.tsx    — Show practice button + Coach Eddie button
frontend/src/components/child/lesson/QuizLesson.tsx     — Add Coach Eddie button
frontend/src/components/child/lesson/ScenarioLesson.tsx — Add Coach Eddie button
```

---

### Task 1: Skill Profile Data Model + Migration

**Files:**
- Create: `backend/app/models/skill_profile.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/conftest.py`
- Create: Alembic migration

- [ ] **Step 1: Create the skill profile models**

Create `backend/app/models/skill_profile.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_topic_mastery_user_topic"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic: Mapped[str] = mapped_column(String(30), primary_key=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quizzes_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quizzes_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WeakConcept(Base):
    __tablename__ = "weak_concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(30), nullable=False)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    times_wrong: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    times_reinforced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 2: Register models in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.skill_profile import TopicMastery, WeakConcept  # noqa: F401
```

- [ ] **Step 3: Update test conftest cleanup**

In `backend/tests/conftest.py`, inside the `db_session` fixture's cleanup block, add these deletes **before** the `delete(UserProgress)` line:

```python
from app.models.skill_profile import TopicMastery, WeakConcept
await clean_session.execute(delete(WeakConcept))
await clean_session.execute(delete(TopicMastery))
```

- [ ] **Step 4: Generate and run migration**

```bash
cd backend
alembic revision --autogenerate -m "add skill profile tables"
alembic upgrade head
```

- [ ] **Step 5: Verify migration applied**

```bash
cd backend
python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        result = await conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_name IN ('topic_mastery', 'weak_concepts')\"))
        tables = [r[0] for r in result]
        print(f'Tables found: {tables}')
        assert len(tables) == 2, f'Expected 2 tables, got {len(tables)}'
    await engine.dispose()

asyncio.run(check())
"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/skill_profile.py backend/app/models/__init__.py backend/tests/conftest.py backend/alembic/versions/
git commit -m "feat: add skill profile data model (topic_mastery + weak_concepts)"
```

---

### Task 2: Skill Profile Service

**Files:**
- Create: `backend/app/services/skill_profile_service.py`
- Create: `backend/tests/test_skill_profile_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_skill_profile_service.py`:

```python
import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.skill_profile import TopicMastery, WeakConcept
from app.models.user import User, UserProgress
from app.services.skill_profile_service import (
    get_mastery_profile,
    record_weak_concept,
    reinforce_concept,
    update_mastery_on_completion,
)


@pytest_asyncio.fixture
async def user_with_module(db_session):
    user = User(
        email="skill@example.com",
        username="skillkid",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting", title="Budgeting Basics",
        country_codes=[], is_premium=False, order_index=0, icon="💰",
    )
    db_session.add(module)
    await db_session.flush()

    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "What is the 50/30/20 rule?",
            "choices": ["A", "B", "C"],
            "answer_index": 1,
            "explanation": "It splits income into needs, wants, savings.",
        },
    )
    card = Lesson(
        module_id=module.id, type="card", xp_reward=10, order_index=1,
        content_json={"title": "What is a budget?", "body": "A plan for your money."},
    )
    db_session.add_all([quiz, card])
    await db_session.flush()
    return user, module, quiz, card


@pytest.mark.asyncio
async def test_update_mastery_correct(db_session, user_with_module):
    user, module, quiz, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=True)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 1
    assert mastery.quizzes_correct == 1
    assert mastery.mastery_score == 1.0


@pytest.mark.asyncio
async def test_update_mastery_wrong(db_session, user_with_module):
    user, module, quiz, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=False)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 1
    assert mastery.quizzes_correct == 0
    assert mastery.mastery_score == 0.0


@pytest.mark.asyncio
async def test_update_mastery_card_only_updates_activity(db_session, user_with_module):
    user, module, _, card = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=False, correct=None)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 0
    assert mastery.last_activity_at is not None


@pytest.mark.asyncio
async def test_record_weak_concept(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc is not None
    assert wc.times_wrong == 1
    assert wc.resolved is False


@pytest.mark.asyncio
async def test_record_weak_concept_increments(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc.times_wrong == 2


@pytest.mark.asyncio
async def test_reinforce_concept_resolves(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await reinforce_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await reinforce_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc.times_reinforced == 2
    assert wc.resolved is True


@pytest.mark.asyncio
async def test_get_mastery_profile(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=True)
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    profile = await get_mastery_profile(db_session, user.id)
    assert len(profile["topics"]) == 1
    assert profile["topics"][0]["topic"] == "budgeting"
    assert profile["topics"][0]["mastery_score"] == 1.0
    assert len(profile["weak_concepts"]) == 1
    assert profile["weak_concepts"][0]["concept"] == "50/30/20 rule"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_skill_profile_service.py -v
```

Expected: `ModuleNotFoundError` — `skill_profile_service` does not exist yet.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/skill_profile_service.py`:

```python
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import TopicMastery, WeakConcept


async def update_mastery_on_completion(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    *,
    is_quiz: bool,
    correct: bool | None,
) -> None:
    """Update or create a TopicMastery row after a lesson completion.

    For quiz/scenario lessons, ``is_quiz=True`` and ``correct`` is True/False.
    For card/video lessons, ``is_quiz=False`` and ``correct`` is None — only
    the last_activity_at timestamp is updated.
    """
    mastery = await session.get(TopicMastery, (user_id, topic))
    now = datetime.now(timezone.utc)

    if mastery is None:
        mastery = TopicMastery(
            user_id=user_id,
            topic=topic,
            mastery_score=0.0,
            quizzes_attempted=0,
            quizzes_correct=0,
            last_activity_at=now,
        )
        session.add(mastery)

    mastery.last_activity_at = now

    if is_quiz and correct is not None:
        mastery.quizzes_attempted += 1
        if correct:
            mastery.quizzes_correct += 1
        mastery.mastery_score = (
            mastery.quizzes_correct / mastery.quizzes_attempted
            if mastery.quizzes_attempted > 0
            else 0.0
        )


async def record_weak_concept(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
) -> None:
    """Record or increment a weak concept when a user gets a question wrong."""
    existing = await session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.topic == topic,
            WeakConcept.concept == concept,
        )
    )
    if existing:
        existing.times_wrong += 1
        existing.resolved = False  # re-open if they struggle again
    else:
        session.add(
            WeakConcept(
                user_id=user_id,
                topic=topic,
                concept=concept,
                times_wrong=1,
            )
        )


async def reinforce_concept(
    session: AsyncSession,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
) -> None:
    """Increment reinforcement count when user gets a previously-weak concept right."""
    existing = await session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.topic == topic,
            WeakConcept.concept == concept,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    if existing:
        existing.times_reinforced += 1
        if existing.times_reinforced >= 2:
            existing.resolved = True


async def get_mastery_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Return the user's full mastery profile for the /profile/mastery endpoint."""
    topics_result = await session.scalars(
        select(TopicMastery).where(TopicMastery.user_id == user_id)
    )
    topics = [
        {
            "topic": tm.topic,
            "mastery_score": tm.mastery_score,
            "quizzes_attempted": tm.quizzes_attempted,
            "quizzes_correct": tm.quizzes_correct,
            "last_activity_at": tm.last_activity_at.isoformat(),
        }
        for tm in topics_result.all()
    ]

    weak_result = await session.scalars(
        select(WeakConcept).where(
            WeakConcept.user_id == user_id,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    weak = [
        {
            "topic": wc.topic,
            "concept": wc.concept,
            "times_wrong": wc.times_wrong,
            "times_reinforced": wc.times_reinforced,
        }
        for wc in weak_result.all()
    ]

    return {"topics": topics, "weak_concepts": weak}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_skill_profile_service.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/skill_profile_service.py backend/tests/test_skill_profile_service.py
git commit -m "feat: add skill profile service with mastery tracking and weak concepts"
```

---

### Task 3: Recommendation Engine

**Files:**
- Create: `backend/app/services/recommendation_service.py`
- Create: `backend/tests/test_recommendation_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_recommendation_service.py`:

```python
import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
import pytest_asyncio

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery, WeakConcept
from app.models.user import User
from app.services.recommendation_service import get_recommendations


def _make_module(topic: str, title: str, order: int, **kw):
    return Module(topic=topic, title=title, country_codes=[], is_premium=False, order_index=order, icon="📚", **kw)


@pytest_asyncio.fixture
async def seeded(db_session):
    user = User(
        email="rec@example.com", username="reckid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)

    stocks = _make_module("stocks", "What is a Stock?", 0)
    budgeting = _make_module("budgeting", "Budgeting Basics", 1)
    risk = _make_module("risk", "Risk & Diversification", 2)
    crypto = _make_module("crypto", "What is Crypto?", 3)
    db_session.add_all([stocks, budgeting, risk, crypto])
    await db_session.flush()

    # Stocks has 1 lesson, budgeting has 1 lesson
    stocks_lesson = Lesson(module_id=stocks.id, type="quiz", xp_reward=25, order_index=0,
                           content_json={"question": "q", "choices": ["a", "b"], "answer_index": 0, "explanation": "e"})
    budgeting_lesson = Lesson(module_id=budgeting.id, type="card", xp_reward=10, order_index=0,
                              content_json={"title": "t", "body": "b"})
    db_session.add_all([stocks_lesson, budgeting_lesson])
    await db_session.flush()

    return {
        "user": user,
        "stocks": stocks, "budgeting": budgeting, "risk": risk, "crypto": crypto,
        "stocks_lesson": stocks_lesson, "budgeting_lesson": budgeting_lesson,
    }


@pytest.mark.asyncio
async def test_new_user_gets_no_prerequisite_modules_first(db_session, seeded):
    """A brand-new user should see stocks and budgeting (no prerequisites) before risk and crypto."""
    recs = await get_recommendations(db_session, seeded["user"])
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    # stocks and budgeting should come before risk and crypto
    stocks_idx = module_ids.index(seeded["stocks"].id)
    budgeting_idx = module_ids.index(seeded["budgeting"].id)
    risk_idx = module_ids.index(seeded["risk"].id)
    crypto_idx = module_ids.index(seeded["crypto"].id)
    assert stocks_idx < risk_idx
    assert stocks_idx < crypto_idx
    assert budgeting_idx < crypto_idx


@pytest.mark.asyncio
async def test_weak_concepts_boost_topic(db_session, seeded):
    """A user with weak concepts in budgeting should see budgeting ranked higher."""
    user = seeded["user"]
    # Give user some stocks mastery so risk becomes "ready"
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=0.8,
        quizzes_attempted=5, quizzes_correct=4,
        last_activity_at=datetime.now(timezone.utc) - timedelta(days=3),
    ))
    # Add weak concept in budgeting
    db_session.add(WeakConcept(
        user_id=user.id, topic="budgeting", concept="50/30/20 rule",
        times_wrong=2, times_reinforced=0, resolved=False,
    ))
    await db_session.flush()

    recs = await get_recommendations(db_session, user)
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    budgeting_idx = module_ids.index(seeded["budgeting"].id)
    # budgeting should be first or second (weakness boost)
    assert budgeting_idx <= 1


@pytest.mark.asyncio
async def test_next_quest_returns_first_incomplete_lesson(db_session, seeded):
    """next_quest should point to the first incomplete lesson in the top-ranked module."""
    recs = await get_recommendations(db_session, seeded["user"])
    assert recs["next_quest"] is not None
    assert recs["next_quest"]["lesson_id"] is not None


@pytest.mark.asyncio
async def test_completed_modules_ranked_last(db_session, seeded):
    """Fully completed modules should appear at the end of the list."""
    user = seeded["user"]
    # Complete the stocks lesson
    db_session.add(LessonCompletion(
        user_id=user.id, lesson_id=seeded["stocks_lesson"].id, score=1.0,
    ))
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=1.0,
        quizzes_attempted=1, quizzes_correct=1,
        last_activity_at=datetime.now(timezone.utc),
    ))
    await db_session.flush()

    recs = await get_recommendations(db_session, user)
    module_ids = [r["module_id"] for r in recs["suggested_modules"]]
    stocks_idx = module_ids.index(seeded["stocks"].id)
    # Stocks should be last (or near last) since it's complete
    assert stocks_idx >= len(module_ids) - 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_recommendation_service.py -v
```

Expected: `ModuleNotFoundError` — `recommendation_service` does not exist yet.

- [ ] **Step 3: Implement the recommendation engine**

Create `backend/app/services/recommendation_service.py`:

```python
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import TopicMastery, WeakConcept
from app.models.user import User
from app.services.content_service import is_module_accessible

TOPIC_PREREQUISITES: dict[str, list[str]] = {
    "stocks": [],
    "savings": [],
    "budgeting": [],
    "risk": ["stocks"],
    "real_estate": ["stocks"],
    "crypto": ["stocks", "risk"],
    "taxes": ["budgeting"],
    "debt": ["budgeting"],
    "entrepreneurship": ["budgeting"],
}

_WEIGHT_READINESS = 0.4
_WEIGHT_WEAKNESS = 0.3
_WEIGHT_FRESHNESS = 0.2
_WEIGHT_COMPLETION = 0.1

_MASTERY_THRESHOLD = 0.5  # prerequisite considered "met" at this score
_FRESHNESS_CAP_DAYS = 30


async def get_recommendations(
    session: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Return personalised module rankings and a next-quest suggestion."""
    # Load all accessible modules
    all_modules = (
        await session.scalars(select(Module).order_by(Module.order_index))
    ).all()
    modules = [
        m for m in all_modules
        if is_module_accessible(user.country_code, user.is_premium, m.country_codes, m.is_premium)
    ]

    if not modules:
        return {"next_quest": None, "suggested_modules": []}

    # Load user's mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    ).all()
    mastery_by_topic: dict[str, TopicMastery] = {tm.topic: tm for tm in mastery_rows}

    # Load unresolved weak concepts grouped by topic
    weak_rows = (
        await session.scalars(
            select(WeakConcept).where(
                WeakConcept.user_id == user.id,
                WeakConcept.resolved == False,  # noqa: E712
            )
        )
    ).all()
    weak_by_topic: dict[str, list[WeakConcept]] = {}
    for wc in weak_rows:
        weak_by_topic.setdefault(wc.topic, []).append(wc)

    # Load completion counts per module
    module_ids = [m.id for m in modules]
    lesson_counts_result = await session.execute(
        select(Lesson.module_id, func.count(Lesson.id))
        .where(Lesson.module_id.in_(module_ids))
        .group_by(Lesson.module_id)
    )
    total_lessons: dict[uuid.UUID, int] = dict(lesson_counts_result.all())

    completed_counts_result = await session.execute(
        select(Lesson.module_id, func.count(LessonCompletion.id))
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(Lesson.module_id.in_(module_ids), LessonCompletion.user_id == user.id)
        .group_by(Lesson.module_id)
    )
    completed_lessons: dict[uuid.UUID, int] = dict(completed_counts_result.all())

    now = datetime.now(timezone.utc)
    scored: list[dict[str, Any]] = []

    for m in modules:
        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)

        # --- Readiness score ---
        prereqs = TOPIC_PREREQUISITES.get(m.topic, [])
        if not prereqs:
            readiness = 1.0
        else:
            met = sum(
                1 for p in prereqs
                if mastery_by_topic.get(p) and mastery_by_topic[p].mastery_score >= _MASTERY_THRESHOLD
            )
            readiness = met / len(prereqs)

        # --- Weakness score ---
        weak_count = len(weak_by_topic.get(m.topic, []))
        weakness = min(weak_count / 3.0, 1.0)  # cap at 3 weak concepts

        # --- Freshness score ---
        mastery = mastery_by_topic.get(m.topic)
        if mastery:
            days_since = (now - mastery.last_activity_at).days
            freshness = min(days_since / _FRESHNESS_CAP_DAYS, 1.0)
        else:
            freshness = 1.0  # never touched = very fresh

        # --- Completion score ---
        if total == 0:
            completion = 0.5
        elif completed == 0:
            completion = 0.5  # untouched
        elif completed < total:
            completion = 0.8  # in progress (momentum)
        else:
            completion = 0.1  # fully done

        score = (
            _WEIGHT_READINESS * readiness
            + _WEIGHT_WEAKNESS * weakness
            + _WEIGHT_FRESHNESS * freshness
            + _WEIGHT_COMPLETION * completion
        )

        # Build reason string
        reason = _build_reason(m, readiness, weakness, completed, total)

        scored.append({
            "module_id": m.id,
            "score": round(score, 4),
            "reason": reason,
            "topic": m.topic,
            "_completed_count": completed,
            "_total_count": total,
        })

    # Sort by score descending, then order_index for ties
    scored.sort(key=lambda s: (-s["score"], modules[[m.id for m in modules].index(s["module_id"])].order_index))

    # Find next quest: first incomplete lesson in the top-ranked module
    next_quest = None
    for entry in scored:
        if entry["_completed_count"] >= entry["_total_count"] and entry["_total_count"] > 0:
            continue  # skip fully complete modules
        lessons = (
            await session.scalars(
                select(Lesson)
                .where(Lesson.module_id == entry["module_id"])
                .order_by(Lesson.order_index)
            )
        ).all()
        completed_ids_result = await session.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user.id,
                LessonCompletion.lesson_id.in_([l.id for l in lessons]),
            )
        )
        completed_ids = set(completed_ids_result.all())
        for lesson in lessons:
            if lesson.id not in completed_ids:
                next_quest = {
                    "module_id": entry["module_id"],
                    "lesson_id": lesson.id,
                    "reason": entry["reason"],
                }
                break
        if next_quest:
            break

    suggested = [
        {"module_id": s["module_id"], "score": s["score"], "reason": s["reason"]}
        for s in scored
    ]

    return {"next_quest": next_quest, "suggested_modules": suggested}


def _build_reason(
    module: Module,
    readiness: float,
    weakness: float,
    completed: int,
    total: int,
) -> str:
    if completed > 0 and completed < total:
        return f"Continue where you left off in {module.title}"
    if weakness > 0:
        return f"Practice your weak spots in {module.topic.replace('_', ' ')}"
    if readiness >= 1.0:
        return f"You're ready for {module.title}"
    if readiness > 0:
        return f"Almost ready for {module.title} — keep building foundations"
    return f"New topic: {module.title}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_recommendation_service.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_service.py
git commit -m "feat: add deterministic recommendation engine with topic prerequisites"
```

---

### Task 4: LLM Client Abstraction

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/llm_client.py`
- Create: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Add config fields**

Add these fields to the `Settings` class in `backend/app/core/config.py`, after the existing `app_base_url` field:

```python
    # LLM / AI
    llm_provider: str = "openai"  # "openai" | "anthropic"
    llm_api_key: str = ""
    llm_model_free: str = "gpt-4o-mini"
    llm_model_premium: str = "gpt-4o"
    # Coach Eddie tutor
    tutor_max_messages_free: int = 6
    tutor_max_messages_premium: int = 12
    tutor_rate_limit_per_hour: int = 10
    tutor_max_input_chars: int = 200
    tutor_max_response_tokens: int = 150
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_llm_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_client import (
    LLMError,
    OpenAIClient,
    AnthropicClient,
    get_llm_client,
)


@pytest.mark.asyncio
async def test_openai_client_complete():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"answer": 42}'

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result == '{"answer": 42}'
        mock_instance.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_anthropic_client_complete():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Hello there!"

    with patch("app.services.llm_client.AsyncAnthropic") as MockAnthropic:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        MockAnthropic.return_value = mock_instance

        client = AnthropicClient(api_key="test-key", model="claude-3-haiku-20240307")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result == "Hello there!"
        mock_instance.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_openai_client_raises_llm_error_on_failure():
    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        with pytest.raises(LLMError, match="API down"):
            await client.complete(
                system_prompt="You are helpful.",
                messages=[{"role": "user", "content": "Hi"}],
            )


def test_get_llm_client_returns_correct_provider():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_model_free = "gpt-4o-mini"
        mock_settings.llm_model_premium = "gpt-4o"

        free_client = get_llm_client(premium=False)
        assert isinstance(free_client, OpenAIClient)

        premium_client = get_llm_client(premium=True)
        assert isinstance(premium_client, OpenAIClient)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_llm_client.py -v
```

Expected: `ModuleNotFoundError` — `llm_client` does not exist yet.

- [ ] **Step 4: Install dependencies**

```bash
cd backend && pip install "openai>=1.0" "anthropic>=0.30" "sse-starlette>=1.6"
```

Add to `backend/requirements.txt`:
```
openai>=1.0
anthropic>=0.30
sse-starlette>=1.6
```

- [ ] **Step 5: Implement the LLM client**

Create `backend/app/services/llm_client.py`:

```python
from __future__ import annotations

from typing import AsyncIterator, Literal, Protocol

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.core.config import settings


class LLMError(Exception):
    """Raised when an LLM call fails after retries."""


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str: ...

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]: ...


class OpenAIClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        kwargs: dict = {
            "model": self._model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        attempts = 0
        last_error: Exception | None = None
        while attempts < 2:
            try:
                response = await self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                attempts += 1
        raise LLMError(str(last_error)) from last_error

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=all_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            raise LLMError(str(exc)) from exc


class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        attempts = 0
        last_error: Exception | None = None
        while attempts < 2:
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.content[0].text
            except Exception as exc:
                last_error = exc
                attempts += 1
        raise LLMError(str(last_error)) from last_error

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(
                model=self._model,
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            raise LLMError(str(exc)) from exc


def get_llm_client(premium: bool = False) -> LLMClient:
    """Return an LLM client configured for the given tier."""
    model = settings.llm_model_premium if premium else settings.llm_model_free
    if settings.llm_provider == "anthropic":
        return AnthropicClient(api_key=settings.llm_api_key, model=model)
    return OpenAIClient(api_key=settings.llm_api_key, model=model)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_llm_client.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/services/llm_client.py backend/tests/test_llm_client.py backend/requirements.txt
git commit -m "feat: add provider-agnostic LLM client with OpenAI and Anthropic support"
```

---

### Task 5: AI Content Generator

**Files:**
- Create: `backend/app/models/generated_content.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/services/ai_content_service.py`
- Create: `backend/tests/test_ai_content_service.py`

- [ ] **Step 1: Create the generated_content model**

Create `backend/app/models/generated_content.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GeneratedContent(Base):
    __tablename__ = "generated_content"
    __table_args__ = (
        UniqueConstraint("lesson_id", "concept", "model_used", name="uq_generated_content_lesson_concept_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Register model + update conftest**

Add to `backend/app/models/__init__.py`:
```python
from app.models.generated_content import GeneratedContent  # noqa: F401
```

In `backend/tests/conftest.py`, add cleanup **before** the `delete(LessonCompletion)` line:
```python
from app.models.generated_content import GeneratedContent
await clean_session.execute(delete(GeneratedContent))
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend
alembic revision --autogenerate -m "add generated content table"
alembic upgrade head
```

- [ ] **Step 4: Write failing tests**

Create `backend/tests/test_ai_content_service.py`:

```python
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.generated_content import GeneratedContent
from app.models.user import User
from app.services.ai_content_service import generate_practice_quiz


VALID_QUIZ_JSON = (
    '{"question": "If your weekly allowance is £20, how much is 20% to save?",'
    ' "choices": ["£2", "£4", "£10"], "answer_index": 1,'
    ' "explanation": "20% of £20 is £4."}'
)


@pytest_asyncio.fixture
async def lesson_fixture(db_session):
    user = User(
        email="practice@example.com", username="practicekid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting", title="Budgeting Basics",
        country_codes=[], is_premium=False, order_index=0, icon="💰",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "Using the 50/30/20 rule, how much of £100 should you save?",
            "choices": ["£50", "£20", "£30"],
            "answer_index": 1,
            "explanation": "The 50/30/20 rule says save 20%.",
        },
    )
    db_session.add(quiz)
    await db_session.flush()
    return user, module, quiz


@pytest.mark.asyncio
async def test_generate_practice_quiz_calls_llm(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=VALID_QUIZ_JSON)

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    assert result["question"] is not None
    assert len(result["choices"]) >= 3
    assert isinstance(result["answer_index"], int)
    mock_client.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_practice_quiz_uses_cache(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    # Pre-populate cache
    cached = GeneratedContent(
        lesson_id=quiz.id,
        concept="50/30/20 rule",
        content_json={
            "question": "Cached question",
            "choices": ["A", "B", "C"],
            "answer_index": 0,
            "explanation": "Cached.",
        },
        model_used="gpt-4o-mini",
    )
    db_session.add(cached)
    await db_session.flush()

    mock_client = AsyncMock()
    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    assert result["question"] == "Cached question"
    mock_client.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_practice_quiz_fallback_on_invalid_json(db_session, lesson_fixture):
    user, module, quiz = lesson_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not valid json at all")

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        result = await generate_practice_quiz(
            db_session, quiz, topic="budgeting", concept="50/30/20 rule", premium=False,
        )
    # Should fall back to original question (shuffled or not)
    assert result["question"] is not None
    assert len(result["choices"]) >= 2
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_ai_content_service.py -v
```

Expected: `ModuleNotFoundError` — `ai_content_service` does not exist yet.

- [ ] **Step 6: Implement the AI content service**

Create `backend/app/services/ai_content_service.py`:

```python
from __future__ import annotations

import json
import random
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson
from app.models.generated_content import GeneratedContent
from app.services.llm_client import LLMError, get_llm_client

from app.core.config import settings


class PracticeQuizSchema(BaseModel):
    """Validates LLM-generated practice quiz JSON."""
    question: str
    choices: list[str]
    answer_index: int
    explanation: str

    @field_validator("choices")
    @classmethod
    def choices_length(cls, v: list[str]) -> list[str]:
        if len(v) < 2 or len(v) > 5:
            raise ValueError("choices must have 2-5 items")
        return v

    @field_validator("answer_index")
    @classmethod
    def answer_in_range(cls, v: int, info) -> int:
        # Validated after choices is set; we re-check in the caller
        if v < 0:
            raise ValueError("answer_index must be >= 0")
        return v


_SYSTEM_PROMPT = (
    "You are a quiz generator for a children's financial education app. "
    "Generate a single multiple-choice question that tests the same concept as the "
    "provided lesson, but from a different angle. "
    "Rules:\n"
    "1. Only use facts from the provided lesson content. Do not introduce new financial claims.\n"
    "2. Never mention specific real companies, stock prices, or crypto values.\n"
    "3. Never give real financial advice.\n"
    "4. Use simple, kid-friendly language.\n"
    "5. Return ONLY valid JSON with this exact schema: "
    '{"question": "...", "choices": ["...", "...", "..."], "answer_index": 0, "explanation": "..."}\n'
    "6. choices must have exactly 3 items. answer_index is 0-based."
)


async def generate_practice_quiz(
    session: AsyncSession,
    lesson: Lesson,
    *,
    topic: str,
    concept: str,
    premium: bool,
    wrong_answer_index: int | None = None,
) -> dict[str, Any]:
    """Generate or serve a cached practice quiz for a lesson concept."""
    model_name = settings.llm_model_premium if premium else settings.llm_model_free

    # Check cache
    cached = await session.scalar(
        select(GeneratedContent).where(
            GeneratedContent.lesson_id == lesson.id,
            GeneratedContent.concept == concept,
            GeneratedContent.model_used == model_name,
        )
    )
    if cached:
        return cached.content_json

    # Build grounded prompt
    content = lesson.content_json or {}
    user_message = f"Lesson topic: {topic}\nLesson content: {json.dumps(content)}"
    if wrong_answer_index is not None and "choices" in content:
        choices = content.get("choices", [])
        if 0 <= wrong_answer_index < len(choices):
            user_message += f"\nThe student chose: {choices[wrong_answer_index]} (wrong)"

    client = get_llm_client(premium=premium)

    for attempt in range(2):
        try:
            raw = await client.complete(
                system_prompt=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
                max_tokens=400,
                response_format="json",
            )
            parsed = json.loads(raw)
            validated = PracticeQuizSchema(**parsed)
            if validated.answer_index >= len(validated.choices):
                raise ValueError("answer_index out of range")
            result = validated.model_dump()

            # Cache it
            session.add(GeneratedContent(
                lesson_id=lesson.id,
                concept=concept,
                content_json=result,
                model_used=model_name,
            ))
            await session.flush()
            return result

        except (json.JSONDecodeError, ValueError, LLMError):
            if attempt == 0:
                continue  # retry once
            # Fall back to original question with shuffled choices
            return _fallback(content)

    return _fallback(content)


def _fallback(original_content: dict[str, Any]) -> dict[str, Any]:
    """Return the original question with shuffled choices as a fallback."""
    choices = list(original_content.get("choices", ["A", "B", "C"]))
    answer_idx = original_content.get("answer_index", 0)
    correct = choices[answer_idx] if answer_idx < len(choices) else choices[0]
    random.shuffle(choices)
    return {
        "question": original_content.get("question", original_content.get("prompt", "Practice question")),
        "choices": choices,
        "answer_index": choices.index(correct),
        "explanation": original_content.get("explanation", "Review the lesson for the answer."),
    }
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_ai_content_service.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/generated_content.py backend/app/models/__init__.py backend/tests/conftest.py backend/app/services/ai_content_service.py backend/tests/test_ai_content_service.py backend/alembic/versions/
git commit -m "feat: add AI practice quiz generator with caching and fallback"
```

---

### Task 6: Coach Eddie Tutor Service

**Files:**
- Create: `backend/app/models/tutor.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/services/tutor_service.py`
- Create: `backend/tests/test_tutor_service.py`

- [ ] **Step 1: Create tutor conversation model**

Create `backend/app/models/tutor.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TutorConversation(Base):
    __tablename__ = "tutor_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    messages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Register model + update conftest**

Add to `backend/app/models/__init__.py`:
```python
from app.models.tutor import TutorConversation  # noqa: F401
```

In `backend/tests/conftest.py`, add cleanup **before** the `delete(GeneratedContent)` line:
```python
from app.models.tutor import TutorConversation
await clean_session.execute(delete(TutorConversation))
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend
alembic revision --autogenerate -m "add tutor conversations table"
alembic upgrade head
```

- [ ] **Step 4: Write failing tests**

Create `backend/tests/test_tutor_service.py`:

```python
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services.tutor_service import (
    TutorLimitReached,
    TutorInputTooLong,
    chat,
    safety_filter,
)


@pytest_asyncio.fixture
async def tutor_fixture(db_session):
    user = User(
        email="tutor@example.com", username="tutorkid", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="stocks", title="What is a Stock?",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "What is a stock?",
            "choices": ["A loan", "A slice of a company", "A bond"],
            "answer_index": 1,
            "explanation": "A stock is a tiny piece of a company.",
        },
    )
    db_session.add(quiz)
    db_session.add(TopicMastery(
        user_id=user.id, topic="stocks", mastery_score=0.4,
        quizzes_attempted=5, quizzes_correct=2,
    ))
    await db_session.flush()
    return user, module, quiz


@pytest.mark.asyncio
async def test_chat_returns_response(db_session, tutor_fixture):
    user, module, quiz = tutor_fixture
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="A stock means you own a small part of a business!")

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        result = await chat(
            session=db_session,
            user=user,
            lesson=quiz,
            topic="stocks",
            message="I don't understand what a stock is",
            conversation_id=None,
            premium=False,
        )
    assert result["response"] is not None
    assert result["conversation_id"] is not None
    assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_chat_rejects_long_input(db_session, tutor_fixture):
    user, module, quiz = tutor_fixture
    with pytest.raises(TutorInputTooLong):
        await chat(
            session=db_session,
            user=user,
            lesson=quiz,
            topic="stocks",
            message="x" * 300,
            conversation_id=None,
            premium=False,
        )


def test_safety_filter_catches_financial_advice():
    dangerous = "You should buy Apple stock right now, it's going up!"
    filtered = safety_filter(dangerous)
    assert "parent or teacher" in filtered.lower()


def test_safety_filter_passes_clean_response():
    clean = "A stock is a small piece of a company. If the company does well, your stock can be worth more!"
    assert safety_filter(clean) == clean
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_tutor_service.py -v
```

Expected: `ModuleNotFoundError` — `tutor_service` does not exist yet.

- [ ] **Step 6: Implement the tutor service**

Create `backend/app/services/tutor_service.py`:

```python
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Lesson
from app.models.skill_profile import TopicMastery
from app.models.tutor import TutorConversation
from app.models.user import User
from app.services.llm_client import get_llm_client


class TutorLimitReached(Exception):
    """User has hit the message limit for this conversation."""


class TutorInputTooLong(Exception):
    """User message exceeds the maximum character limit."""


_SYSTEM_PROMPT_TEMPLATE = (
    "You are Coach Eddie, a friendly and encouraging money tutor for kids learning "
    "about finance. You are helping with a specific lesson — its content is provided below.\n\n"
    "Rules:\n"
    "1. Only explain concepts from the provided lesson content.\n"
    "2. Never give real financial advice or suggest the child spend, save, or invest real money.\n"
    "3. Never mention specific real companies, stock prices, or crypto values.\n"
    "4. Keep responses under 100 words.\n"
    "5. Use simple, encouraging language.\n"
    "6. If the child asks something outside the lesson topic, say: "
    "'Great question! That's outside what we're covering in this quest — ask a parent or teacher!'\n"
    "7. {skill_level_instruction}\n\n"
    "Lesson content:\n{lesson_content}"
)

_SKILL_INSTRUCTIONS = {
    "low": "The student is a beginner. Use very simple words, short sentences, and lots of encouragement. Give examples they can relate to (pocket money, toys, snacks).",
    "medium": "The student has some understanding. Give clear explanations with relatable examples. Encourage them to think about why.",
    "high": "The student is doing well. Challenge them with deeper questions. Ask 'what if' scenarios to deepen understanding.",
}

# Patterns that suggest financial advice
_ADVICE_PATTERNS = re.compile(
    r"\byou should (buy|sell|invest|spend|save|trade)\b"
    r"|\b(buy|sell|invest in) [A-Z][a-z]",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "That's a great question! Ask a parent or teacher for advice "
    "about real money decisions. 😊"
)


def safety_filter(response: str) -> str:
    """Replace responses containing financial advice patterns with a safe fallback."""
    if _ADVICE_PATTERNS.search(response):
        return _SAFE_FALLBACK
    return response


def _skill_level(mastery_score: float) -> str:
    if mastery_score < 0.3:
        return "low"
    if mastery_score <= 0.7:
        return "medium"
    return "high"


async def chat(
    *,
    session: AsyncSession,
    user: User,
    lesson: Lesson,
    topic: str,
    message: str,
    conversation_id: uuid.UUID | None,
    premium: bool,
) -> dict[str, Any]:
    """Process a Coach Eddie message and return the response."""
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise TutorInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = (
        settings.tutor_max_messages_premium if premium
        else settings.tutor_max_messages_free
    )

    # Load or create conversation
    conversation: TutorConversation | None = None
    if conversation_id:
        conversation = await session.get(TutorConversation, conversation_id)

    model_name = settings.llm_model_premium if premium else settings.llm_model_free

    if conversation is None:
        conversation = TutorConversation(
            user_id=user.id,
            lesson_id=lesson.id,
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

    # Get mastery for tone adaptation
    mastery = await session.get(TopicMastery, (user.id, topic))
    mastery_score = mastery.mastery_score if mastery else 0.0
    level = _skill_level(mastery_score)

    # Build system prompt
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        lesson_content=json.dumps(lesson.content_json or {}),
    )

    # Build message history
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    # Call LLM
    client = get_llm_client(premium=premium)
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    # Safety filter
    filtered_response = safety_filter(raw_response)

    # Persist conversation
    conversation.messages = [
        *conversation.messages,
        {"role": "user", "content": message},
        {"role": "assistant", "content": filtered_response},
    ]
    conversation.message_count += 2
    await session.flush()

    return {
        "response": filtered_response,
        "conversation_id": conversation.id,
        "messages_remaining": max(0, max_messages - conversation.message_count),
    }
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_tutor_service.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/tutor.py backend/app/models/__init__.py backend/tests/conftest.py backend/app/services/tutor_service.py backend/tests/test_tutor_service.py backend/alembic/versions/
git commit -m "feat: add Coach Eddie tutor service with safety filter and conversation limits"
```

---

### Task 7: AI Schemas + Router

**Files:**
- Create: `backend/app/schemas/ai.py`
- Create: `backend/app/routers/ai.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/csrf.py`
- Modify: `backend/app/routers/content.py`
- Modify: `backend/app/schemas/content.py`
- Create: `backend/tests/test_ai_router.py`

- [ ] **Step 1: Create AI schemas**

Create `backend/app/schemas/ai.py`:

```python
import uuid
from pydantic import BaseModel


class RecommendationOut(BaseModel):
    module_id: uuid.UUID
    score: float
    reason: str


class NextQuestOut(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID
    reason: str


class RecommendationsResponse(BaseModel):
    next_quest: NextQuestOut | None
    suggested_modules: list[RecommendationOut]


class PracticeRequest(BaseModel):
    wrong_answer_index: int | None = None


class PracticeResponse(BaseModel):
    question: str
    choices: list[str]
    answer_index: int
    explanation: str


class TutorChatRequest(BaseModel):
    lesson_id: uuid.UUID
    message: str
    conversation_id: uuid.UUID | None = None


class TutorChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    messages_remaining: int


class TopicMasteryOut(BaseModel):
    topic: str
    mastery_score: float
    quizzes_attempted: int
    quizzes_correct: int
    last_activity_at: str


class WeakConceptOut(BaseModel):
    topic: str
    concept: str
    times_wrong: int
    times_reinforced: int


class MasteryProfileResponse(BaseModel):
    topics: list[TopicMasteryOut]
    weak_concepts: list[WeakConceptOut]
```

- [ ] **Step 2: Create AI router**

Create `backend/app/routers/ai.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.content import Lesson, Module
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.ai import (
    MasteryProfileResponse,
    PracticeRequest,
    PracticeResponse,
    RecommendationsResponse,
    TutorChatRequest,
    TutorChatResponse,
)
from app.services.ai_content_service import generate_practice_quiz
from app.services.recommendation_service import get_recommendations
from app.services.skill_profile_service import get_mastery_profile
from app.services.tutor_service import TutorInputTooLong, TutorLimitReached, chat

router = APIRouter(tags=["ai"])


@router.get("/recommendations", response_model=RecommendationsResponse)
async def recommendations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await get_recommendations(session, current_user)
    return result


@router.post("/lessons/{lesson_id}/practice", response_model=PracticeResponse)
async def practice_quiz(
    lesson_id: uuid.UUID,
    payload: PracticeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    module = await session.get(Module, lesson.module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")

    # Derive concept from lesson title
    content = lesson.content_json or {}
    concept = content.get("question") or content.get("title") or content.get("prompt") or "general"

    result = await generate_practice_quiz(
        session,
        lesson,
        topic=module.topic,
        concept=concept,
        premium=current_user.is_premium,
        wrong_answer_index=payload.wrong_answer_index,
    )
    return result


@router.post("/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(
    payload: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, payload.lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    module = await session.get(Module, lesson.module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")

    try:
        result = await chat(
            session=session,
            user=current_user,
            lesson=lesson,
            topic=module.topic,
            message=payload.message,
            conversation_id=payload.conversation_id,
            premium=current_user.is_premium,
        )
    except TutorInputTooLong as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except TutorLimitReached as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    return result


@router.get("/profile/mastery", response_model=MasteryProfileResponse)
async def mastery_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await get_mastery_profile(session, current_user.id)
    return profile
```

- [ ] **Step 3: Register router in main.py**

In `backend/app/main.py`, add the import alongside the other router imports:

```python
from app.routers import ai as ai_router
```

Add after the last `include_router` call:

```python
    application.include_router(ai_router.router)
```

- [ ] **Step 4: Add CSRF exemptions**

In `backend/app/core/csrf.py`, add `/tutor/chat` and `/lessons/` prefix to the exempt lists:

Update `_DEFAULT_EXEMPT_PATHS` to include `/tutor/chat`:

```python
_DEFAULT_EXEMPT_PATHS = frozenset({
    "/auth/login", "/auth/register", "/health",
    "/consent/decide",
    "/parent/auth/request",
    "/tutor/chat",
})
```

Add `/lessons/` to `_DEFAULT_EXEMPT_PREFIXES` (practice endpoint uses dynamic path):

```python
_DEFAULT_EXEMPT_PREFIXES = ("/consent/request/", "/lessons/")
```

- [ ] **Step 5: Update complete_lesson to feed skill profile**

In `backend/app/routers/content.py`, add import at the top:

```python
from app.services.skill_profile_service import (
    record_weak_concept,
    reinforce_concept,
    update_mastery_on_completion,
)
from app.services.content_service import derive_lesson_title
```

In the `complete_lesson` function, after the `if not already:` block (after `await evaluate_and_award_badges(...)` on line 169), add:

```python
    # Update skill profile
    module = await session.get(Module, lesson.module_id)
    topic = module.topic if module else "unknown"
    is_quiz = lesson.type in ("quiz", "scenario")
    correct = payload.score is not None and payload.score >= 0.5 if is_quiz else None

    if not already:
        await update_mastery_on_completion(
            session, current_user.id, topic, is_quiz=is_quiz, correct=correct,
        )

        if is_quiz and correct is False:
            concept = derive_lesson_title(lesson.type, lesson.content_json or {})
            await record_weak_concept(session, current_user.id, topic, concept)
        elif is_quiz and correct is True:
            concept = derive_lesson_title(lesson.type, lesson.content_json or {})
            await reinforce_concept(session, current_user.id, topic, concept)
```

- [ ] **Step 6: Add `practice_available` to completion result**

In `backend/app/schemas/content.py`, add field to `LessonCompletionResult`:

```python
class LessonCompletionResult(BaseModel):
    xp_awarded: int
    already_completed: bool
    total_xp: int
    level: int
    streak_count: int
    practice_available: bool = False
```

In `backend/app/routers/content.py`, update the return in `complete_lesson` to include `practice_available`:

Replace the existing return statement with:

```python
    practice_available = (
        not already
        and lesson.type in ("quiz", "scenario")
        and payload.score is not None
        and payload.score < 0.5
    )

    return LessonCompletionResult(
        xp_awarded=xp_awarded, already_completed=already,
        total_xp=progress.xp, level=progress.level, streak_count=progress.streak_count,
        practice_available=practice_available,
    )
```

- [ ] **Step 7: Write router integration tests**

Create `backend/tests/test_ai_router.py`:

```python
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.content import Lesson, Module
from app.models.skill_profile import TopicMastery
from app.models.user import User, UserProgress
from app.core.security import hash_password


@pytest_asyncio.fixture
async def auth_client(db_session, client):
    user = User(
        email="ai@example.com", username="aikid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    progress = UserProgress(user_id=user.id)
    db_session.add(progress)
    module = Module(
        topic="stocks", title="What is a Stock?",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "What is a stock?",
            "choices": ["A loan", "A slice of a company", "A bond"],
            "answer_index": 1,
            "explanation": "A stock is a tiny piece of a company.",
        },
    )
    db_session.add(quiz)
    await db_session.flush()

    # Log in
    response = await client.post("/auth/login", json={
        "email": "ai@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    return client, user, module, quiz


@pytest.mark.asyncio
async def test_get_recommendations(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "next_quest" in data
    assert "suggested_modules" in data


@pytest.mark.asyncio
async def test_get_mastery_profile(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/profile/mastery")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "weak_concepts" in data


@pytest.mark.asyncio
async def test_practice_quiz_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=(
        '{"question": "New Q", "choices": ["A", "B", "C"], "answer_index": 0, "explanation": "E"}'
    ))

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            f"/lessons/{quiz.id}/practice",
            json={"wrong_answer_index": 0},
        )
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "choices" in data


@pytest.mark.asyncio
async def test_tutor_chat_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="A stock is a small piece of a company!")

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/chat", json={
            "lesson_id": str(quiz.id),
            "message": "What is a stock?",
        })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "messages_remaining" in data
```

- [ ] **Step 8: Run all tests**

```bash
cd backend && python -m pytest tests/test_ai_router.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 9: Run the full test suite**

```bash
cd backend && python -m pytest -v
```

Expected: All existing tests still pass, plus all new tests pass.

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/ai.py backend/app/routers/ai.py backend/app/main.py backend/app/core/csrf.py backend/app/routers/content.py backend/app/schemas/content.py backend/tests/test_ai_router.py
git commit -m "feat: add AI router with recommendations, practice, tutor, and mastery endpoints"
```

---

### Task 8: Frontend — API Client + Types

**Files:**
- Create: `frontend/src/api/ai.ts`
- Modify: `frontend/src/api/content.ts`

- [ ] **Step 1: Create AI API client**

Create `frontend/src/api/ai.ts`:

```typescript
import { apiFetch } from './client';

export type TopicMasteryOut = {
  topic: string;
  mastery_score: number;
  quizzes_attempted: number;
  quizzes_correct: number;
  last_activity_at: string;
};

export type WeakConceptOut = {
  topic: string;
  concept: string;
  times_wrong: number;
  times_reinforced: number;
};

export type MasteryProfile = {
  topics: TopicMasteryOut[];
  weak_concepts: WeakConceptOut[];
};

export type NextQuest = {
  module_id: string;
  lesson_id: string;
  reason: string;
};

export type SuggestedModule = {
  module_id: string;
  score: number;
  reason: string;
};

export type Recommendations = {
  next_quest: NextQuest | null;
  suggested_modules: SuggestedModule[];
};

export type PracticeQuiz = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
};

export type TutorResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};

export const aiApi = {
  getRecommendations: () =>
    apiFetch<Recommendations>('/recommendations'),

  getMasteryProfile: () =>
    apiFetch<MasteryProfile>('/profile/mastery'),

  getPracticeQuiz: (lessonId: string, wrongAnswerIndex?: number) =>
    apiFetch<PracticeQuiz>(`/lessons/${lessonId}/practice`, {
      method: 'POST',
      body: JSON.stringify({ wrong_answer_index: wrongAnswerIndex ?? null }),
    }),

  sendTutorMessage: (lessonId: string, message: string, conversationId?: string) =>
    apiFetch<TutorResponse>('/tutor/chat', {
      method: 'POST',
      body: JSON.stringify({
        lesson_id: lessonId,
        message,
        conversation_id: conversationId ?? null,
      }),
    }),
};
```

- [ ] **Step 2: Add `practice_available` to content types**

In `frontend/src/api/content.ts`, add `practice_available` to the `LessonCompletionResult` type:

```typescript
practice_available: boolean;
```

- [ ] **Step 3: Build check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/ai.ts frontend/src/api/content.ts
git commit -m "feat: add frontend AI API client and types"
```

---

### Task 9: Frontend — Home Page Recommendations

**Files:**
- Modify: `frontend/src/pages/child/Home.tsx`

- [ ] **Step 1: Update Home page to use recommendations API**

In `frontend/src/pages/child/Home.tsx`, add a query for recommendations alongside the existing queries. Import the AI API and use the recommendation data for the "Your Next Quest" card instead of the current static module lookup. Use the `reason` string from the recommendation as a subtitle below the quest card.

Key changes:
- Add `import { aiApi, type Recommendations } from '@/api/ai';`
- Add a `useQuery` for recommendations: `queryKey: ['recommendations'], queryFn: () => aiApi.getRecommendations()`
- Replace the existing "next quest" logic with the recommendation's `next_quest` data
- Display `next_quest.reason` as a subtitle on the quest card
- Keep the existing layout and styling — only change the data source

- [ ] **Step 2: Build check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Manual verification**

Run `npm run dev`, log in, verify the Home page loads with a recommended quest and reason text.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/child/Home.tsx
git commit -m "feat: use recommendation engine for Home page next quest"
```

---

### Task 10: Frontend — Practice Quiz + Coach Eddie

**Files:**
- Create: `frontend/src/components/child/lesson/PracticeQuiz.tsx`
- Create: `frontend/src/components/child/lesson/CoachEddiePanel.tsx`
- Modify: `frontend/src/pages/child/Lesson.tsx`
- Modify: `frontend/src/components/child/lesson/QuizLesson.tsx`
- Modify: `frontend/src/components/child/lesson/ScenarioLesson.tsx`

- [ ] **Step 1: Create PracticeQuiz component**

Create `frontend/src/components/child/lesson/PracticeQuiz.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { aiApi, type PracticeQuiz as PracticeQuizType } from '@/api/ai';
import { QuizLesson } from './QuizLesson';

type Props = {
  lessonId: string;
  wrongAnswerIndex?: number;
  onClose: () => void;
};

export function PracticeQuiz({ lessonId, wrongAnswerIndex, onClose }: Props) {
  const practiceQ = useQuery<PracticeQuizType | null>({
    queryKey: ['practice', lessonId],
    queryFn: () => aiApi.getPracticeQuiz(lessonId, wrongAnswerIndex),
    retry: false,
  });

  if (practiceQ.isLoading) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        Generating practice question...
      </div>
    );
  }

  if (practiceQ.isError || !practiceQ.data) {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-sm text-muted-foreground">Could not generate a practice question.</p>
        <button onClick={onClose} className="text-sm text-amber-600 underline">Go back</button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="rounded-lg bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">
          Practice — no XP
        </span>
        <button onClick={onClose} className="text-sm text-amber-600 underline">
          Skip
        </button>
      </div>
      <QuizLesson
        contentJson={practiceQ.data}
        onComplete={() => onClose()}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create CoachEddiePanel component**

Create `frontend/src/components/child/lesson/CoachEddiePanel.tsx`:

```tsx
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { aiApi, type TutorResponse } from '@/api/ai';
import { Button } from '@/components/ui/button';

type Message = { role: 'user' | 'assistant'; content: string };

type Props = {
  lessonId: string;
  onClose: () => void;
};

export function CoachEddiePanel({ lessonId, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);

  const sendMessage = useMutation<TutorResponse | null, Error, string>({
    mutationFn: (msg) => aiApi.sendTutorMessage(lessonId, msg, conversationId),
    onSuccess: (data) => {
      if (!data) return;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response },
      ]);
      setConversationId(data.conversation_id);
      setRemaining(data.messages_remaining);
    },
  });

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || sendMessage.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setInput('');
    sendMessage.mutate(msg);
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-2xl animate-in slide-in-from-bottom">
      <div className="rounded-t-2xl border-2 border-amber-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-amber-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">💡</span>
            <span className="font-bold text-gray-900">Coach Eddie</span>
          </div>
          <div className="flex items-center gap-3">
            {remaining !== null && (
              <span className="text-xs text-gray-400">{remaining} messages left</span>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
          </div>
        </div>

        {/* Messages */}
        <div className="max-h-64 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-gray-400 text-center">
              Ask me anything about this quest! 🎯
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                m.role === 'user'
                  ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                  : 'bg-amber-50 text-gray-800'
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {sendMessage.isPending && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
                Thinking...
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-amber-100 p-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask Coach Eddie..."
            maxLength={200}
            className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
            disabled={remaining === 0}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || sendMessage.isPending || remaining === 0}
            className="bg-gradient-to-r from-amber-400 to-orange-500 text-white rounded-xl px-4"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update Lesson page to show practice button and Coach Eddie**

In `frontend/src/pages/child/Lesson.tsx`:

- Add imports for `PracticeQuiz`, `CoachEddiePanel`, and `useState`
- Add state: `const [showPractice, setShowPractice] = useState(false);` and `const [showEddie, setShowEddie] = useState(false);`
- In the `complete.isSuccess` block, if `complete.data.practice_available` is true, show a "Practice this" button that sets `showPractice(true)`
- If `showPractice` is true, render `<PracticeQuiz lessonId={lessonId!} onClose={() => setShowPractice(false)} />` instead of the CompletionPanel
- Pass `onShowEddie={() => setShowEddie(true)}` to QuizLesson and ScenarioLesson
- Render `{showEddie && <CoachEddiePanel lessonId={lessonId!} onClose={() => setShowEddie(false)} />}` at the bottom

- [ ] **Step 4: Add Coach Eddie button to QuizLesson and ScenarioLesson**

In `frontend/src/components/child/lesson/QuizLesson.tsx`, add an optional `onShowEddie?: () => void` prop. Below the answer choices (before the submit button), add:

```tsx
{onShowEddie && (
  <button
    type="button"
    onClick={onShowEddie}
    className="text-sm text-amber-600 hover:text-amber-700 underline"
  >
    💡 Ask Coach Eddie
  </button>
)}
```

Do the same in `ScenarioLesson.tsx`.

- [ ] **Step 5: Build check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 6: Manual verification**

Run `npm run dev`, log in, complete a quiz incorrectly, verify:
1. "Practice this" button appears on completion panel
2. Practice quiz loads and renders
3. "Ask Coach Eddie" button appears on quiz/scenario lessons
4. Coach Eddie chat panel opens and responds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/child/lesson/PracticeQuiz.tsx frontend/src/components/child/lesson/CoachEddiePanel.tsx frontend/src/pages/child/Lesson.tsx frontend/src/components/child/lesson/QuizLesson.tsx frontend/src/components/child/lesson/ScenarioLesson.tsx
git commit -m "feat: add practice quiz, Coach Eddie tutor, and AI-powered lesson experience"
```

---

### Task 11: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass, including all new AI tests.

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: No TypeScript or build errors.

- [ ] **Step 3: Manual E2E flow**

1. Start backend: `cd backend && uvicorn app.main:app --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Log in as a child user
4. Verify Home page shows AI-recommended next quest with reason text
5. Complete a quiz correctly → check mastery profile updates (`GET /profile/mastery`)
6. Complete a quiz incorrectly → verify "Practice this" button on completion
7. Click "Practice this" → verify generated practice quiz loads
8. On a quiz lesson, click "Ask Coach Eddie" → verify chat panel opens and responds
9. Verify free user message limit is enforced

- [ ] **Step 4: Commit any fixes found during verification**

```bash
git add -A
git commit -m "fix: address issues found during e2e verification"
```

(Only if fixes are needed — skip if everything works.)
