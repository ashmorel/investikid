# Learning Path Intelligence Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Phase 1's single "Next Quest" recommendation into a categorised, spaced-repetition-aware system with a Strengths & Gaps page.

**Architecture:** Extend existing `recommendation_service.py` with SM-2 scheduling data from a new `spaced_repetition_service.py`. A `_categorise_scored_modules()` pure function groups results into "Continue Learning", "Practise Again", "Something New" categories. A separate `gap_detection_service.py` provides read-only per-topic summaries. Frontend replaces the single QuestCard with three colour-coded sections and adds a new Strengths & Gaps page.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, React 18, TypeScript, Tailwind CSS, TanStack Query, vitest, vitest-axe, framer-motion

---

## File Structure

**Backend — new files:**
- `backend/alembic/versions/e4f5a6b7c8d9_add_spaced_repetition_items.py` — Migration for SR table
- `backend/app/services/spaced_repetition_service.py` — SM-2 lite math + scheduling
- `backend/app/services/gap_detection_service.py` — Per-topic strengths/gaps reader
- `backend/tests/test_spaced_repetition_service.py` — SM-2 unit tests
- `backend/tests/test_gap_detection_service.py` — Gap detection unit tests
- `backend/tests/test_recommendation_categorised.py` — Categorisation unit tests
- `backend/tests/test_strengths_endpoint.py` — Schema validation tests

**Backend — modified files:**
- `backend/app/models/skill_profile.py` — Add `SpacedRepetitionItem` model
- `backend/app/schemas/ai.py` — Add categorised recommendation + strengths schemas
- `backend/app/services/recommendation_service.py` — Add `_categorise_scored_modules()`, change return shape
- `backend/app/routers/ai.py` — Add `GET /profile/strengths`, update response_model for recommendations

**Frontend — new files:**
- `frontend/src/components/child/RecommendationCard.tsx` — Category-aware module card
- `frontend/src/components/child/ReviewBanner.tsx` — Overdue review nudge banner
- `frontend/src/pages/child/StrengthsGaps.tsx` — Dedicated mastery page
- `frontend/src/components/child/__tests__/RecommendationCard.test.tsx`
- `frontend/src/components/child/__tests__/ReviewBanner.test.tsx`
- `frontend/tests/a11y/strengths-gaps.a11y.test.tsx`

**Frontend — modified files:**
- `frontend/src/api/ai.ts` — New types + `getStrengths()` + `useStrengths()`
- `frontend/src/pages/child/Home.tsx` — Replace QuestCard with categorised sections
- `frontend/src/components/child/BottomTabBar.tsx` — Add "Progress" tab
- `frontend/src/App.tsx` — Add `/progress` route

---

### Task 1: SpacedRepetitionItem Model + Migration

**Files:**
- Modify: `backend/app/models/skill_profile.py`
- Create: `backend/alembic/versions/e4f5a6b7c8d9_add_spaced_repetition_items.py`

- [ ] **Step 1: Add SpacedRepetitionItem model to skill_profile.py**

Add below the `WeakConcept` class in `backend/app/models/skill_profile.py`:

```python
class SpacedRepetitionItem(Base):
    __tablename__ = "spaced_repetition_items"
    __table_args__ = (
        UniqueConstraint("user_id", "weak_concept_id", name="uq_sr_user_concept"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weak_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weak_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
```

The existing imports in the file already cover `UUID`, `ForeignKey`, `Float`, `Integer`, `DateTime`, `Boolean`, `String`, `UniqueConstraint`, `Mapped`, `mapped_column`, `uuid`, `datetime`, `UTC`. No new imports needed.

- [ ] **Step 2: Create Alembic migration**

Create `backend/alembic/versions/e4f5a6b7c8d9_add_spaced_repetition_items.py`:

```python
"""add spaced repetition items table

Revision ID: e4f5a6b7c8d9
Revises: 9b7815c040
Create Date: 2026-05-22 23:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "9b7815c040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spaced_repetition_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("weak_concept_id", sa.Uuid(), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("repetition_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["weak_concept_id"], ["weak_concepts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "weak_concept_id", name="uq_sr_user_concept"),
    )
    op.create_index("ix_sr_user_next_review", "spaced_repetition_items", ["user_id", "next_review_at"])


def downgrade() -> None:
    op.drop_index("ix_sr_user_next_review", table_name="spaced_repetition_items")
    op.drop_table("spaced_repetition_items")
```

- [ ] **Step 3: Verify migration chain**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/python -m alembic heads`
Expected: Single head `e4f5a6b7c8d9`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/skill_profile.py backend/alembic/versions/e4f5a6b7c8d9_add_spaced_repetition_items.py
git commit -m "feat: add SpacedRepetitionItem model and migration"
```

---

### Task 2: Spaced Repetition Service + Tests

**Files:**
- Create: `backend/app/services/spaced_repetition_service.py`
- Create: `backend/tests/test_spaced_repetition_service.py`

- [ ] **Step 1: Write failing tests for calculate_next_review**

Create `backend/tests/test_spaced_repetition_service.py`:

```python
"""Tests for SM-2 lite spaced repetition service."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spaced_repetition_service import calculate_next_review


class TestCalculateNextReview:
    def test_correct_first_rep_sets_interval_1(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=0, quality=4,
        )
        assert interval == 1
        assert rep == 1
        assert ease > 2.0

    def test_correct_second_rep_sets_interval_3(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=1, quality=4,
        )
        assert interval == 3
        assert rep == 2

    def test_correct_third_rep_multiplies_by_ease(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=3, repetition_count=2, quality=4,
        )
        assert interval == round(3 * 2.5)
        assert rep == 3

    def test_correct_adjusts_ease_factor(self):
        ease, _, _ = calculate_next_review(
            ease_factor=2.5, interval_days=1, repetition_count=0, quality=4,
        )
        # With quality=4: ef += 0.1 - (5-4)*(0.08 + (5-4)*0.02) = 0.1 - 0.1 = 0
        assert ease == pytest.approx(2.5, abs=0.01)

    def test_wrong_resets_to_interval_1(self):
        ease, interval, rep = calculate_next_review(
            ease_factor=2.5, interval_days=10, repetition_count=5, quality=1,
        )
        assert interval == 1
        assert rep == 0

    def test_wrong_decreases_ease(self):
        ease, _, _ = calculate_next_review(
            ease_factor=2.5, interval_days=10, repetition_count=5, quality=1,
        )
        assert ease == pytest.approx(2.3, abs=0.01)

    def test_ease_factor_floors_at_1_3(self):
        ease, _, _ = calculate_next_review(
            ease_factor=1.3, interval_days=1, repetition_count=0, quality=1,
        )
        assert ease == 1.3

    def test_ease_factor_does_not_go_below_floor(self):
        ease, _, _ = calculate_next_review(
            ease_factor=1.4, interval_days=1, repetition_count=0, quality=1,
        )
        assert ease >= 1.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_spaced_repetition_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.spaced_repetition_service'`

- [ ] **Step 3: Implement calculate_next_review**

Create `backend/app/services/spaced_repetition_service.py`:

```python
"""SM-2 lite spaced repetition scheduling for children's weak concepts."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import SpacedRepetitionItem, WeakConcept

_EASE_FLOOR = 1.3
_DEFAULT_EASE = 2.5


def calculate_next_review(
    *,
    ease_factor: float,
    interval_days: int,
    repetition_count: int,
    quality: int,
) -> tuple[float, int, int]:
    """Pure SM-2 lite math. Returns (new_ease, new_interval, new_rep_count).

    quality: 4 = correct, 1 = wrong (binary, derived from quiz result).
    """
    if quality >= 3:
        # Correct answer
        if repetition_count == 0:
            new_interval = 1
        elif repetition_count == 1:
            new_interval = 3
        else:
            new_interval = round(interval_days * ease_factor)
        new_rep = repetition_count + 1
        new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    else:
        # Wrong answer — reset
        new_interval = 1
        new_rep = 0
        new_ease = ease_factor - 0.2

    new_ease = max(new_ease, _EASE_FLOOR)
    return new_ease, new_interval, new_rep


async def get_due_items(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[SpacedRepetitionItem]:
    """Return SR items that are due for review (next_review_at <= now) and not resolved."""
    now = datetime.now(UTC)
    result = await session.scalars(
        select(SpacedRepetitionItem)
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= now,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return list(result.all())


async def get_due_count(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Count of SR items due for review."""
    now = datetime.now(UTC)
    count = await session.scalar(
        select(func.count(SpacedRepetitionItem.id))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= now,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return int(count or 0)


async def get_next_due_at(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> datetime | None:
    """Earliest next_review_at for unresolved items (may be in the future)."""
    result = await session.scalar(
        select(func.min(SpacedRepetitionItem.next_review_at))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            WeakConcept.resolved == False,  # noqa: E712
        )
    )
    return result


async def record_review(
    session: AsyncSession,
    user_id: uuid.UUID,
    weak_concept_id: uuid.UUID,
    *,
    correct: bool,
) -> None:
    """Upsert SR item with new schedule after a quiz interaction."""
    now = datetime.now(UTC)
    quality = 4 if correct else 1

    # Try to find existing item
    item = await session.scalar(
        select(SpacedRepetitionItem).where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.weak_concept_id == weak_concept_id,
        )
    )

    if item is None:
        # First encounter — create with defaults
        new_ease, new_interval, new_rep = calculate_next_review(
            ease_factor=_DEFAULT_EASE,
            interval_days=1,
            repetition_count=0,
            quality=quality,
        )
        item = SpacedRepetitionItem(
            user_id=user_id,
            weak_concept_id=weak_concept_id,
            ease_factor=new_ease,
            interval_days=new_interval,
            repetition_count=new_rep,
            next_review_at=now + timedelta(days=new_interval),
            last_reviewed_at=now,
            created_at=now,
        )
        session.add(item)
    else:
        # Update existing
        new_ease, new_interval, new_rep = calculate_next_review(
            ease_factor=item.ease_factor,
            interval_days=item.interval_days,
            repetition_count=item.repetition_count,
            quality=quality,
        )
        item.ease_factor = new_ease
        item.interval_days = new_interval
        item.repetition_count = new_rep
        item.next_review_at = now + timedelta(days=new_interval)
        item.last_reviewed_at = now

    await session.flush()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_spaced_repetition_service.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/spaced_repetition_service.py backend/tests/test_spaced_repetition_service.py
git commit -m "feat: add spaced repetition service with SM-2 lite algorithm"
```

---

### Task 3: Backend Schemas — Categorised Recommendations + Strengths

**Files:**
- Modify: `backend/app/schemas/ai.py`
- Create: `backend/tests/test_strengths_endpoint.py`

- [ ] **Step 1: Write failing schema tests**

Create `backend/tests/test_strengths_endpoint.py`:

```python
"""Tests for categorised recommendation and strengths schemas."""
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.ai import (
    CategorisedRecommendations,
    RecommendationCategoryItem,
    ReviewSummary,
    StrengthsAndGaps,
    TopicStrength,
)


class TestRecommendationCategoryItem:
    def test_valid_item(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.75,
            reason="Keep going!",
        )
        assert item.review_prompt is None
        assert item.weak_concepts == []

    def test_with_review_prompt_and_concepts(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.6,
            reason="Time to review!",
            review_prompt="3 concepts due",
            weak_concepts=["compound interest", "APR"],
        )
        assert item.review_prompt == "3 concepts due"
        assert len(item.weak_concepts) == 2

    def test_lesson_id_nullable(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=None,
            score=0.5,
            reason="Something new",
        )
        assert item.lesson_id is None


class TestReviewSummary:
    def test_valid_summary(self):
        s = ReviewSummary(due_count=3, next_due_at=datetime.now(UTC))
        assert s.due_count == 3

    def test_next_due_at_nullable(self):
        s = ReviewSummary(due_count=0, next_due_at=None)
        assert s.next_due_at is None


class TestCategorisedRecommendations:
    def test_empty_categories(self):
        r = CategorisedRecommendations(
            continue_learning=[],
            practise_again=[],
            something_new=[],
            review_summary=ReviewSummary(due_count=0, next_due_at=None),
        )
        assert len(r.continue_learning) == 0

    def test_full_response(self):
        item = RecommendationCategoryItem(
            module_id=uuid.uuid4(),
            lesson_id=uuid.uuid4(),
            score=0.8,
            reason="Great!",
        )
        r = CategorisedRecommendations(
            continue_learning=[item],
            practise_again=[],
            something_new=[item],
            review_summary=ReviewSummary(due_count=1, next_due_at=datetime.now(UTC)),
        )
        assert len(r.continue_learning) == 1
        assert len(r.something_new) == 1


class TestTopicStrength:
    def test_valid_strength(self):
        t = TopicStrength(
            topic="savings",
            mastery_score=0.85,
            status="strong",
            weak_count=0,
            due_for_review=0,
            total_concepts=5,
        )
        assert t.status == "strong"

    def test_needs_practice(self):
        t = TopicStrength(
            topic="interest_rates",
            mastery_score=0.58,
            status="needs_practice",
            weak_count=2,
            due_for_review=1,
            total_concepts=4,
        )
        assert t.weak_count == 2


class TestStrengthsAndGaps:
    def test_valid_response(self):
        r = StrengthsAndGaps(
            topics=[
                TopicStrength(
                    topic="savings", mastery_score=0.85, status="strong",
                    weak_count=0, due_for_review=0, total_concepts=5,
                ),
            ],
            overall_mastery=0.85,
        )
        assert r.overall_mastery == 0.85

    def test_empty_topics(self):
        r = StrengthsAndGaps(topics=[], overall_mastery=0.0)
        assert len(r.topics) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_strengths_endpoint.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add schemas to ai.py**

Add the following to the end of `backend/app/schemas/ai.py` (after `MasteryProfileResponse`):

```python
from datetime import datetime


class RecommendationCategoryItem(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID | None = None
    score: float
    reason: str
    review_prompt: str | None = None
    weak_concepts: list[str] = []


class ReviewSummary(BaseModel):
    due_count: int
    next_due_at: datetime | None = None


class CategorisedRecommendations(BaseModel):
    continue_learning: list[RecommendationCategoryItem]
    practise_again: list[RecommendationCategoryItem]
    something_new: list[RecommendationCategoryItem]
    review_summary: ReviewSummary


class TopicStrength(BaseModel):
    topic: str
    mastery_score: float
    status: str
    weak_count: int
    due_for_review: int
    total_concepts: int


class StrengthsAndGaps(BaseModel):
    topics: list[TopicStrength]
    overall_mastery: float
```

Note: `datetime` import needs to be added at the top of the file alongside the existing `uuid` import:
```python
import uuid
from datetime import datetime
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_strengths_endpoint.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/ai.py backend/tests/test_strengths_endpoint.py
git commit -m "feat: add categorised recommendations and strengths schemas"
```

---

### Task 4: Gap Detection Service + Tests

**Files:**
- Create: `backend/app/services/gap_detection_service.py`
- Create: `backend/tests/test_gap_detection_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_gap_detection_service.py`:

```python
"""Tests for gap detection service — per-topic strengths and gaps."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.services.gap_detection_service import (
    _classify_topic,
    _compute_overall_mastery,
    _sort_topics,
)


class TestClassifyTopic:
    def test_strong_when_mastery_above_threshold(self):
        assert _classify_topic(0.85) == "strong"

    def test_strong_at_exact_threshold(self):
        assert _classify_topic(0.8) == "strong"

    def test_needs_practice_below_threshold(self):
        assert _classify_topic(0.79) == "needs_practice"

    def test_needs_practice_at_zero(self):
        assert _classify_topic(0.0) == "needs_practice"

    def test_new_when_none(self):
        assert _classify_topic(None) == "new"


class TestComputeOverallMastery:
    def test_average_of_scores(self):
        result = _compute_overall_mastery([0.8, 0.6, 0.9])
        assert result == pytest.approx(0.7667, abs=0.001)

    def test_empty_returns_zero(self):
        assert _compute_overall_mastery([]) == 0.0

    def test_single_score(self):
        assert _compute_overall_mastery([0.75]) == 0.75


class TestSortTopics:
    def test_needs_practice_first(self):
        topics = [
            {"status": "strong", "topic": "a"},
            {"status": "needs_practice", "topic": "b"},
            {"status": "new", "topic": "c"},
        ]
        sorted_topics = _sort_topics(topics)
        assert sorted_topics[0]["status"] == "needs_practice"
        assert sorted_topics[1]["status"] == "strong"
        assert sorted_topics[2]["status"] == "new"

    def test_same_status_preserves_order(self):
        topics = [
            {"status": "needs_practice", "topic": "z"},
            {"status": "needs_practice", "topic": "a"},
        ]
        sorted_topics = _sort_topics(topics)
        assert sorted_topics[0]["topic"] == "z"
        assert sorted_topics[1]["topic"] == "a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_gap_detection_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement gap detection service**

Create `backend/app/services/gap_detection_service.py`:

```python
"""Per-topic strengths and gaps analysis — read-only service."""
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import SpacedRepetitionItem, TopicMastery, WeakConcept
from app.schemas.ai import StrengthsAndGaps, TopicStrength

_STRONG_THRESHOLD = 0.8
_STATUS_ORDER = {"needs_practice": 0, "strong": 1, "new": 2}


def _classify_topic(mastery_score: float | None) -> str:
    """Classify a topic based on mastery score."""
    if mastery_score is None:
        return "new"
    if mastery_score >= _STRONG_THRESHOLD:
        return "strong"
    return "needs_practice"


def _compute_overall_mastery(scores: list[float]) -> float:
    """Average of all mastery scores, or 0.0 if empty."""
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def _sort_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort: needs_practice first, strong second, new last."""
    return sorted(topics, key=lambda t: _STATUS_ORDER.get(t["status"], 99))


async def get_strengths_and_gaps(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> StrengthsAndGaps:
    """Per-topic summary combining TopicMastery + WeakConcept + SR schedule."""
    # Load mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user_id)
        )
    ).all()
    mastery_by_topic = {tm.topic: tm for tm in mastery_rows}

    # Load weak concept counts per topic (unresolved only)
    weak_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(WeakConcept.id))
        .where(WeakConcept.user_id == user_id, WeakConcept.resolved == False)  # noqa: E712
        .group_by(WeakConcept.topic)
    )
    weak_counts: dict[str, int] = dict(weak_counts_result.all())

    # Load total concept counts per topic (all, including resolved)
    total_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(WeakConcept.id))
        .where(WeakConcept.user_id == user_id)
        .group_by(WeakConcept.topic)
    )
    total_concepts: dict[str, int] = dict(total_counts_result.all())

    # Load due-for-review counts per topic
    due_counts_result = await session.execute(
        select(WeakConcept.topic, func.count(SpacedRepetitionItem.id))
        .join(WeakConcept, WeakConcept.id == SpacedRepetitionItem.weak_concept_id)
        .where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.next_review_at <= func.now(),
            WeakConcept.resolved == False,  # noqa: E712
        )
        .group_by(WeakConcept.topic)
    )
    due_counts: dict[str, int] = dict(due_counts_result.all())

    # Collect all known topics
    all_topics = set(mastery_by_topic.keys()) | set(weak_counts.keys()) | set(total_concepts.keys())

    topic_list: list[dict[str, Any]] = []
    mastery_scores: list[float] = []

    for topic in all_topics:
        mastery = mastery_by_topic.get(topic)
        score = mastery.mastery_score if mastery else None
        status = _classify_topic(score)

        if score is not None:
            mastery_scores.append(score)

        topic_list.append({
            "topic": topic,
            "mastery_score": score if score is not None else 0.0,
            "status": status,
            "weak_count": weak_counts.get(topic, 0),
            "due_for_review": due_counts.get(topic, 0),
            "total_concepts": total_concepts.get(topic, 0),
        })

    sorted_topics = _sort_topics(topic_list)

    return StrengthsAndGaps(
        topics=[TopicStrength(**t) for t in sorted_topics],
        overall_mastery=_compute_overall_mastery(mastery_scores),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_gap_detection_service.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/gap_detection_service.py backend/tests/test_gap_detection_service.py
git commit -m "feat: add gap detection service with topic classification"
```

---

### Task 5: Categorised Recommendations + Tests

**Files:**
- Modify: `backend/app/services/recommendation_service.py`
- Create: `backend/tests/test_recommendation_categorised.py`

- [ ] **Step 1: Write failing tests for _categorise_scored_modules**

Create `backend/tests/test_recommendation_categorised.py`:

```python
"""Tests for categorised recommendation logic."""
import uuid

import pytest

from app.services.recommendation_service import _categorise_scored_modules


def _make_scored(*, topic="stocks", completed=0, total=5, score=0.5, order_index=0,
                 has_due_sr=False, weak_concepts=None):
    return {
        "module_id": uuid.uuid4(),
        "score": score,
        "reason": "Test reason",
        "topic": topic,
        "_completed_count": completed,
        "_total_count": total,
        "_order_index": order_index,
        "_lesson_id": uuid.uuid4(),
        "_has_due_sr": has_due_sr,
        "_weak_concepts": weak_concepts or [],
    }


class TestCategoriseModules:
    def test_partial_completion_goes_to_continue_learning(self):
        scored = [_make_scored(completed=2, total=5)]
        result = _categorise_scored_modules(scored)
        assert len(result["continue_learning"]) == 1
        assert len(result["practise_again"]) == 0
        assert len(result["something_new"]) == 0

    def test_due_sr_items_go_to_practise_again(self):
        scored = [_make_scored(completed=5, total=5, has_due_sr=True,
                               weak_concepts=["compound interest"])]
        result = _categorise_scored_modules(scored)
        assert len(result["practise_again"]) == 1
        assert result["practise_again"][0]["weak_concepts"] == ["compound interest"]

    def test_untouched_goes_to_something_new(self):
        scored = [_make_scored(completed=0, total=5)]
        result = _categorise_scored_modules(scored)
        assert len(result["something_new"]) == 1

    def test_max_2_per_category(self):
        scored = [
            _make_scored(completed=0, total=5, score=0.9),
            _make_scored(completed=0, total=5, score=0.8),
            _make_scored(completed=0, total=5, score=0.7),
        ]
        result = _categorise_scored_modules(scored)
        assert len(result["something_new"]) == 2

    def test_empty_input_returns_empty_categories(self):
        result = _categorise_scored_modules([])
        assert result["continue_learning"] == []
        assert result["practise_again"] == []
        assert result["something_new"] == []

    def test_review_prompt_when_due(self):
        scored = [_make_scored(completed=5, total=5, has_due_sr=True,
                               weak_concepts=["APR", "compound interest"])]
        result = _categorise_scored_modules(scored)
        item = result["practise_again"][0]
        assert item["review_prompt"] is not None
        assert "2" in item["review_prompt"]

    def test_no_review_prompt_when_not_due(self):
        scored = [_make_scored(completed=2, total=5)]
        result = _categorise_scored_modules(scored)
        item = result["continue_learning"][0]
        assert item.get("review_prompt") is None

    def test_partial_with_due_sr_goes_to_continue_learning(self):
        """Partial completion takes priority over practice — user is mid-module."""
        scored = [_make_scored(completed=2, total=5, has_due_sr=True,
                               weak_concepts=["APR"])]
        result = _categorise_scored_modules(scored)
        assert len(result["continue_learning"]) == 1

    def test_sorted_by_score_within_category(self):
        scored = [
            _make_scored(completed=0, total=5, score=0.3),
            _make_scored(completed=0, total=5, score=0.9),
        ]
        result = _categorise_scored_modules(scored)
        assert result["something_new"][0]["score"] >= result["something_new"][1]["score"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_recommendation_categorised.py -v`
Expected: FAIL with `ImportError: cannot import name '_categorise_scored_modules'`

- [ ] **Step 3: Add _categorise_scored_modules to recommendation_service.py**

Add this pure function after the `_build_reason` function and before `get_recommendations` in `backend/app/services/recommendation_service.py`:

```python
_MAX_PER_CATEGORY = 2


def _categorise_scored_modules(
    scored: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Split scored modules into three categories. Pure function, no DB access.

    Priority: partial completion → continue_learning (even if has due SR).
    Completed with due SR → practise_again.
    Untouched (0 completed) → something_new.
    """
    continue_learning: list[dict[str, Any]] = []
    practise_again: list[dict[str, Any]] = []
    something_new: list[dict[str, Any]] = []

    for entry in scored:
        completed = entry["_completed_count"]
        total = entry["_total_count"]
        has_due = entry.get("_has_due_sr", False)
        weak = entry.get("_weak_concepts", [])

        item: dict[str, Any] = {
            "module_id": entry["module_id"],
            "lesson_id": entry.get("_lesson_id"),
            "score": entry["score"],
            "reason": entry["reason"],
            "review_prompt": None,
            "weak_concepts": [],
        }

        if 0 < completed < total:
            # Partial completion takes priority
            continue_learning.append(item)
        elif has_due and weak:
            # Completed module with due SR items
            item["weak_concepts"] = weak
            item["review_prompt"] = f"{len(weak)} concept{'s' if len(weak) != 1 else ''} to review"
            practise_again.append(item)
        else:
            # Untouched
            something_new.append(item)

    # Sort each category by score descending and cap at max
    continue_learning.sort(key=lambda x: -x["score"])
    practise_again.sort(key=lambda x: -x["score"])
    something_new.sort(key=lambda x: -x["score"])

    return {
        "continue_learning": continue_learning[:_MAX_PER_CATEGORY],
        "practise_again": practise_again[:_MAX_PER_CATEGORY],
        "something_new": something_new[:_MAX_PER_CATEGORY],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_recommendation_categorised.py -v`
Expected: 9 passed

- [ ] **Step 5: Update get_recommendations to return categorised shape**

Replace the `get_recommendations` function in `backend/app/services/recommendation_service.py` with:

```python
async def get_recommendations(
    session: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Return personalised categorised module recommendations."""
    from app.services.spaced_repetition_service import (
        get_due_count,
        get_due_items,
        get_next_due_at,
    )

    empty_result = {
        "continue_learning": [],
        "practise_again": [],
        "something_new": [],
        "review_summary": {"due_count": 0, "next_due_at": None},
    }

    if not user.profiling_enabled:
        seed = await _topic_path_seed(session, user)
        if seed:
            return {
                "continue_learning": [],
                "practise_again": [],
                "something_new": [{
                    "module_id": seed["module_id"],
                    "lesson_id": seed["lesson_id"],
                    "score": 0.0,
                    "reason": seed["reason"],
                    "review_prompt": None,
                    "weak_concepts": [],
                }],
                "review_summary": {"due_count": 0, "next_due_at": None},
            }
        return empty_result

    # Load all modules ordered by order_index
    all_modules = (
        await session.scalars(select(Module).order_by(Module.order_index))
    ).all()

    if not all_modules:
        return empty_result

    module_ids = [m.id for m in all_modules]

    # Load completion counts per module
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

    # Build sets for hard filtering
    fully_completed_module_ids: set[uuid.UUID] = {
        mid for mid in module_ids
        if total_lessons.get(mid, 0) > 0 and completed_lessons.get(mid, 0) >= total_lessons.get(mid, 0)
    }
    completed_module_ids_for_prereqs: set[uuid.UUID] = fully_completed_module_ids.copy()

    # Calculate user age
    user_age = _calculate_age(user.dob) if user.dob else 0

    # Load mastery data
    mastery_rows = (
        await session.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    ).all()
    mastery_by_topic: dict[str, TopicMastery] = {tm.topic: tm for tm in mastery_rows}

    # Load due SR items to identify topics with due reviews
    due_items = await get_due_items(session, user.id)
    # Map: topic -> list of weak concept names that are due
    from app.models.skill_profile import WeakConcept as WC
    due_concept_ids = {item.weak_concept_id for item in due_items}
    due_concepts_by_topic: dict[str, list[str]] = {}
    if due_concept_ids:
        concepts = (
            await session.scalars(
                select(WC).where(WC.id.in_(due_concept_ids))
            )
        ).all()
        for c in concepts:
            due_concepts_by_topic.setdefault(c.topic, []).append(c.concept)

    # Filter, score, and find first incomplete lesson per module
    scored: list[dict[str, Any]] = []

    for m in all_modules:
        total = total_lessons.get(m.id, 0)
        completed = completed_lessons.get(m.id, 0)

        # For practise_again: include fully completed modules with due SR items
        has_due_sr = m.topic in due_concepts_by_topic
        is_fully_completed = m.id in fully_completed_module_ids

        # Apply hard filters (skip completed unless they have due SR items)
        if is_fully_completed and not has_due_sr:
            continue
        if not is_fully_completed and not _apply_hard_filters(
            m, user, fully_completed_module_ids, completed_module_ids_for_prereqs, user_age
        ):
            continue

        # Score the module
        score_result = _score_module(m, user, completed, total, mastery_by_topic)

        # Build reason string
        reason = _build_reason(
            m,
            completed=completed,
            total=total,
            is_topic_match=score_result["is_topic_match"],
            is_variety=score_result["variety"],
            readiness_score=score_result["readiness"],
        )

        # Find first incomplete lesson
        lesson_id = None
        if not is_fully_completed:
            lessons = (
                await session.scalars(
                    select(Lesson)
                    .where(Lesson.module_id == m.id)
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
                    lesson_id = lesson.id
                    break

        scored.append({
            "module_id": m.id,
            "score": score_result["score"],
            "reason": reason,
            "topic": m.topic,
            "_completed_count": completed,
            "_total_count": total,
            "_order_index": m.order_index,
            "_lesson_id": lesson_id,
            "_has_due_sr": has_due_sr,
            "_weak_concepts": due_concepts_by_topic.get(m.topic, []),
        })

    if not scored:
        return empty_result

    # Sort by score descending, then order_index for ties
    scored.sort(key=lambda s: (-s["score"], s["_order_index"]))

    # Categorise
    categories = _categorise_scored_modules(scored)

    # Build review summary
    due_count = await get_due_count(session, user.id)
    next_due = await get_next_due_at(session, user.id)

    return {
        "continue_learning": categories["continue_learning"],
        "practise_again": categories["practise_again"],
        "something_new": categories["something_new"],
        "review_summary": {
            "due_count": due_count,
            "next_due_at": next_due.isoformat() if next_due else None,
        },
    }
```

- [ ] **Step 6: Run all recommendation tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_recommendation_enhanced.py tests/test_recommendation_categorised.py -v`
Expected: All pass (existing tests for pure functions still pass, new categorisation tests pass)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_categorised.py
git commit -m "feat: categorised recommendations with SR-aware practise_again"
```

---

### Task 6: Wire Backend Endpoints

**Files:**
- Modify: `backend/app/routers/ai.py`
- Modify: `backend/app/schemas/ai.py` (update import in router)

- [ ] **Step 1: Update recommendations endpoint response model**

In `backend/app/routers/ai.py`, update the import block to include the new schema:

```python
from app.schemas.ai import (
    CategorisedRecommendations,
    MasteryProfileResponse,
    PracticeRequest,
    PracticeResponse,
    StrengthsAndGaps,
    TutorChatRequest,
    TutorChatResponse,
)
```

Remove `RecommendationsResponse` from the import (no longer used).

- [ ] **Step 2: Update recommendations endpoint**

Change the `@router.get("/recommendations")` decorator from:
```python
@router.get("/recommendations", response_model=RecommendationsResponse)
```
to:
```python
@router.get("/recommendations", response_model=CategorisedRecommendations)
```

The handler body stays the same — `get_recommendations` now returns the new shape.

- [ ] **Step 3: Add strengths endpoint**

Add after the `mastery_profile` endpoint in `backend/app/routers/ai.py`:

```python
from app.services.gap_detection_service import get_strengths_and_gaps


@router.get("/profile/strengths", response_model=StrengthsAndGaps)
async def strengths(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await get_strengths_and_gaps(session, current_user.id)
    return result
```

- [ ] **Step 4: Hook practice quiz into SR scheduling**

The practice quiz endpoint (`POST /lessons/{id}/practice`) in `backend/app/routers/ai.py` needs to call `record_review()` after generating the quiz. The `wrong_answer_index` parameter tells us whether the user got the previous question wrong.

Add the import at the top of `ai.py`:
```python
from app.services.spaced_repetition_service import record_review
```

Then modify the `practice_quiz` handler. After the `result = await generate_practice_quiz(...)` line, add SR tracking logic:

```python
    # Track spaced repetition for the concept
    # If wrong_answer_index is provided, the user answered wrong previously
    if payload.wrong_answer_index is not None:
        # Find or create a weak concept for this topic+concept
        from app.models.skill_profile import WeakConcept
        from sqlalchemy import select as sa_select
        weak = await session.scalar(
            sa_select(WeakConcept).where(
                WeakConcept.user_id == current_user.id,
                WeakConcept.topic == module.topic,
                WeakConcept.concept == concept,
            )
        )
        if weak:
            await record_review(
                session, current_user.id, weak.id, correct=False,
            )
            await session.commit()
```

This hooks SR scheduling into the existing practice quiz flow: when a child gets a question wrong and requests a new practice quiz (passing `wrong_answer_index`), the weak concept is scheduled for future review.

- [ ] **Step 5: Run existing backend tests to verify no regressions**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_recommendation_enhanced.py tests/test_recommendation_categorised.py tests/test_strengths_endpoint.py tests/test_spaced_repetition_service.py tests/test_gap_detection_service.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ai.py
git commit -m "feat: wire categorised recommendations, strengths endpoint, and SR quiz hook"
```

---

### Task 7: Frontend Types + API Client Updates

**Files:**
- Modify: `frontend/src/api/ai.ts`

- [ ] **Step 1: Update frontend types and API client**

Replace the contents of `frontend/src/api/ai.ts` with:

```typescript
import { useQuery } from '@tanstack/react-query';
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

// --- Categorised Recommendations (Phase 2) ---

export type RecommendationCategoryItem = {
  module_id: string;
  lesson_id: string | null;
  score: number;
  reason: string;
  review_prompt: string | null;
  weak_concepts: string[];
};

export type ReviewSummary = {
  due_count: number;
  next_due_at: string | null;
};

export type CategorisedRecommendations = {
  continue_learning: RecommendationCategoryItem[];
  practise_again: RecommendationCategoryItem[];
  something_new: RecommendationCategoryItem[];
  review_summary: ReviewSummary;
};

// --- Strengths & Gaps ---

export type TopicStrength = {
  topic: string;
  mastery_score: number;
  status: 'strong' | 'needs_practice' | 'new';
  weak_count: number;
  due_for_review: number;
  total_concepts: number;
};

export type StrengthsAndGaps = {
  topics: TopicStrength[];
  overall_mastery: number;
};

// --- Practice Quiz ---

export type PracticeQuiz = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
  variant_rung?: string | null;
};

// --- Tutor ---

export type TutorResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};

// --- API functions ---

export const aiApi = {
  getRecommendations: () =>
    apiFetch<CategorisedRecommendations>('/recommendations'),

  getMasteryProfile: () =>
    apiFetch<MasteryProfile>('/profile/mastery'),

  getStrengths: () =>
    apiFetch<StrengthsAndGaps>('/profile/strengths'),

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

// --- Hooks ---

export function useRecommendations() {
  return useQuery({
    queryKey: ['recommendations'],
    queryFn: () => aiApi.getRecommendations(),
    retry: false,
    staleTime: 60_000,
  });
}

export function useStrengths() {
  return useQuery({
    queryKey: ['strengths'],
    queryFn: () => aiApi.getStrengths(),
    retry: false,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`
Expected: There will be errors in `Home.tsx` because it still references the old `Recommendations` type. That's expected — we fix Home.tsx in Task 9.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/ai.ts
git commit -m "feat: update frontend AI types for categorised recommendations"
```

---

### Task 8: RecommendationCard + ReviewBanner Components

**Files:**
- Create: `frontend/src/components/child/RecommendationCard.tsx`
- Create: `frontend/src/components/child/ReviewBanner.tsx`
- Create: `frontend/src/components/child/__tests__/RecommendationCard.test.tsx`
- Create: `frontend/src/components/child/__tests__/ReviewBanner.test.tsx`

- [ ] **Step 1: Write failing RecommendationCard tests**

Create `frontend/src/components/child/__tests__/RecommendationCard.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { RecommendationCard } from '../RecommendationCard';

const BASE_ITEM = {
  module_id: 'mod-1',
  lesson_id: 'les-1',
  score: 0.75,
  reason: 'Keep going!',
  review_prompt: null,
  weak_concepts: [],
};

function renderCard(props: Partial<Parameters<typeof RecommendationCard>[0]> = {}) {
  return render(
    <MemoryRouter>
      <RecommendationCard
        item={BASE_ITEM}
        category="continue_learning"
        moduleTitle="Saving & Budgeting"
        completedCount={3}
        totalCount={6}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe('RecommendationCard', () => {
  it('renders module title and reason', () => {
    renderCard();
    expect(screen.getByText('Saving & Budgeting')).toBeInTheDocument();
    expect(screen.getByText('Keep going!')).toBeInTheDocument();
  });

  it('shows progress bar for continue_learning', () => {
    renderCard({ category: 'continue_learning' });
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('3 of 6')).toBeInTheDocument();
  });

  it('shows weak concept chips for practise_again', () => {
    renderCard({
      category: 'practise_again',
      item: {
        ...BASE_ITEM,
        weak_concepts: ['compound interest', 'APR vs APY'],
        review_prompt: '2 concepts to review',
      },
    });
    expect(screen.getByText('compound interest')).toBeInTheDocument();
    expect(screen.getByText('APR vs APY')).toBeInTheDocument();
  });

  it('renders a link for navigation', () => {
    renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/lessons/mod-1/les-1');
  });

  it('does not show progress bar for something_new', () => {
    renderCard({ category: 'something_new', completedCount: 0, totalCount: 5 });
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Write failing ReviewBanner tests**

Create `frontend/src/components/child/__tests__/ReviewBanner.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ReviewBanner } from '../ReviewBanner';

describe('ReviewBanner', () => {
  it('renders when due_count > 0', () => {
    render(<ReviewBanner dueCount={3} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/3 concepts/i)).toBeInTheDocument();
  });

  it('is hidden when due_count is 0', () => {
    const { container } = render(<ReviewBanner dueCount={0} />);
    expect(container.firstChild).toBeNull();
  });

  it('uses singular for 1 concept', () => {
    render(<ReviewBanner dueCount={1} />);
    expect(screen.getByText(/1 concept to/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/child/__tests__/RecommendationCard.test.tsx src/components/child/__tests__/ReviewBanner.test.tsx`
Expected: FAIL — modules not found

- [ ] **Step 4: Implement ReviewBanner**

Create `frontend/src/components/child/ReviewBanner.tsx`:

```typescript
type ReviewBannerProps = {
  dueCount: number;
};

export function ReviewBanner({ dueCount }: ReviewBannerProps) {
  if (dueCount <= 0) return null;

  const conceptText = dueCount === 1 ? '1 concept to practise' : `${dueCount} concepts to practise`;

  return (
    <div
      role="alert"
      className="rounded-2xl bg-gradient-to-r from-purple-600 to-purple-400 p-4 flex items-center gap-3"
    >
      <span className="text-2xl" aria-hidden="true">🔔</span>
      <div>
        <p className="text-white font-semibold text-sm">Time to review!</p>
        <p className="text-purple-100 text-xs">
          You have {conceptText} — keep your streak going!
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement RecommendationCard**

Create `frontend/src/components/child/RecommendationCard.tsx`:

```typescript
import { Link } from 'react-router-dom';
import type { RecommendationCategoryItem } from '@/api/ai';

type Category = 'continue_learning' | 'practise_again' | 'something_new';

const CATEGORY_COLORS: Record<Category, { border: string; text: string; chip: string; chipText: string }> = {
  continue_learning: {
    border: 'border-l-green-400',
    text: 'text-green-400',
    chip: 'bg-green-900/30',
    chipText: 'text-green-400',
  },
  practise_again: {
    border: 'border-l-amber-400',
    text: 'text-amber-400',
    chip: 'bg-amber-900/30',
    chipText: 'text-amber-400',
  },
  something_new: {
    border: 'border-l-sky-400',
    text: 'text-sky-400',
    chip: 'bg-sky-900/30',
    chipText: 'text-sky-400',
  },
};

type RecommendationCardProps = {
  item: RecommendationCategoryItem;
  category: Category;
  moduleTitle: string;
  completedCount: number;
  totalCount: number;
};

export function RecommendationCard({
  item,
  category,
  moduleTitle,
  completedCount,
  totalCount,
}: RecommendationCardProps) {
  const colors = CATEGORY_COLORS[category];
  const href = item.lesson_id
    ? `/lessons/${item.module_id}/${item.lesson_id}`
    : `/lessons/${item.module_id}`;

  return (
    <Link
      to={href}
      className={`block rounded-xl border-l-4 ${colors.border} bg-slate-800 p-4 transition-colors hover:bg-slate-700`}
    >
      <p className="font-semibold text-white text-sm">{moduleTitle}</p>

      {category === 'continue_learning' && totalCount > 0 && (
        <>
          <p className="text-slate-400 text-xs mt-1">{completedCount} of {totalCount}</p>
          <div
            role="progressbar"
            aria-valuenow={completedCount}
            aria-valuemin={0}
            aria-valuemax={totalCount}
            aria-label={`${completedCount} of ${totalCount} lessons completed`}
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-600"
          >
            <div
              className="h-full rounded-full bg-green-400"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        </>
      )}

      {category === 'practise_again' && item.weak_concepts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {item.weak_concepts.map((concept) => (
            <span
              key={concept}
              className={`${colors.chip} ${colors.chipText} rounded-full px-2 py-0.5 text-xs`}
            >
              {concept}
            </span>
          ))}
        </div>
      )}

      <p className={`${colors.text} text-xs mt-2`}>{item.reason}</p>
    </Link>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/components/child/__tests__/RecommendationCard.test.tsx src/components/child/__tests__/ReviewBanner.test.tsx`
Expected: 8 passed

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/child/RecommendationCard.tsx frontend/src/components/child/ReviewBanner.tsx frontend/src/components/child/__tests__/RecommendationCard.test.tsx frontend/src/components/child/__tests__/ReviewBanner.test.tsx
git commit -m "feat: add RecommendationCard and ReviewBanner components"
```

---

### Task 9: Update Home Page — Categorised Sections

**Files:**
- Modify: `frontend/src/pages/child/Home.tsx`

- [ ] **Step 1: Replace Home.tsx with categorised sections**

Replace the entire contents of `frontend/src/pages/child/Home.tsx`:

```typescript
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type ModuleOut } from '@/api/content';
import { useRecommendations, type RecommendationCategoryItem } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { ReviewBanner } from '@/components/child/ReviewBanner';
import { RecommendationCard } from '@/components/child/RecommendationCard';
import { Button } from '@/components/ui/button';

type Category = 'continue_learning' | 'practise_again' | 'something_new';

const CATEGORY_META: Record<Category, { label: string; icon: string; color: string }> = {
  continue_learning: { label: 'Continue Learning', icon: '▶', color: 'text-green-400' },
  practise_again: { label: 'Practise Again', icon: '🔄', color: 'text-amber-400' },
  something_new: { label: 'Something New', icon: '✨', color: 'text-sky-400' },
};

function CategorySection({
  category,
  items,
  modules,
}: {
  category: Category;
  items: RecommendationCategoryItem[];
  modules: ModuleOut[];
}) {
  if (items.length === 0) return null;
  const meta = CATEGORY_META[category];

  return (
    <section className="mt-5" aria-label={meta.label}>
      <h2 className={`${meta.color} text-xs font-bold uppercase tracking-wider mb-2`}>
        {meta.icon} {meta.label}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const mod = modules.find((m) => m.id === item.module_id);
          return (
            <RecommendationCard
              key={item.module_id}
              item={item}
              category={category}
              moduleTitle={mod?.title ?? 'Module'}
              completedCount={0}
              totalCount={0}
            />
          );
        })}
      </div>
    </section>
  );
}

export default function Home() {
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();
  const { data: recs, isLoading: recsLoading } = useRecommendations();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const modules = modulesQ.data ?? [];
  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;
  const xpInLevel = xp % 100;
  const xpForNext = 100;

  const hasAnything =
    (recs?.continue_learning?.length ?? 0) > 0 ||
    (recs?.practise_again?.length ?? 0) > 0 ||
    (recs?.something_new?.length ?? 0) > 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-extrabold text-gray-900">
        Hey {me?.username ?? '…'}! 👋
      </h1>
      <p className="mt-1 text-sm text-gray-500">Ready to level up your money skills?</p>

      <div className="mt-4">
        <StatsBar
          xp={xp}
          level={level}
          streakCount={progress?.streak_count ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
        />
      </div>

      {/* XP Progress to next level */}
      <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Level {level}</span>
          <span>{xpInLevel} / {xpForNext} XP</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-amber-100">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
            initial={{ width: 0 }}
            animate={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
            transition={{ duration: 0.8, delay: 0.2 }}
          />
        </div>
      </div>

      {/* Review nudge banner */}
      {recs && recs.review_summary.due_count > 0 && (
        <div className="mt-5">
          <ReviewBanner dueCount={recs.review_summary.due_count} />
        </div>
      )}

      {/* Categorised recommendations */}
      {recsLoading ? (
        <p className="mt-5 text-sm text-gray-500">Loading recommendations…</p>
      ) : hasAnything ? (
        <>
          <CategorySection category="continue_learning" items={recs?.continue_learning ?? []} modules={modules} />
          <CategorySection category="practise_again" items={recs?.practise_again ?? []} modules={modules} />
          <CategorySection category="something_new" items={recs?.something_new ?? []} modules={modules} />
        </>
      ) : (
        <section className="mt-5 rounded-2xl border-2 border-amber-200 bg-white p-4">
          <p className="text-sm text-center text-gray-500">
            Complete a lesson to get personalised recommendations!
          </p>
        </section>
      )}

      <div className="mt-5">
        <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`
Expected: Clean (no errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/child/Home.tsx
git commit -m "feat: replace single quest card with categorised recommendation sections"
```

---

### Task 10: Strengths & Gaps Page + Route + Nav

**Files:**
- Create: `frontend/src/pages/child/StrengthsGaps.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/child/BottomTabBar.tsx`

- [ ] **Step 1: Create StrengthsGaps page**

Create `frontend/src/pages/child/StrengthsGaps.tsx`:

```typescript
import { useStrengths, type TopicStrength } from '@/api/ai';

const STATUS_STYLES: Record<string, { border: string; text: string; label: string; emoji: string }> = {
  strong: { border: 'border-l-green-400', text: 'text-green-400', label: 'Strong — keep it up!', emoji: '⭐' },
  needs_practice: { border: 'border-l-amber-400', text: 'text-amber-400', label: 'Needs practice', emoji: '🔄' },
  new: { border: 'border-l-slate-500', text: 'text-slate-400', label: 'Not started yet', emoji: '🆕' },
};

function MasteryRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (value * circumference);

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`Overall mastery: ${pct}%`}>
      <div className="relative h-[120px] w-[120px]">
        <svg viewBox="0 0 120 120" className="-rotate-90">
          <circle cx="60" cy="60" r="52" fill="none" stroke="#334155" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="52" fill="none" stroke="#a78bfa" strokeWidth="10"
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-white">
          {pct}%
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold text-purple-400">Overall Mastery</p>
      <p className="text-xs text-slate-400">Across all topics you've studied</p>
    </div>
  );
}

function TopicCard({ topic }: { topic: TopicStrength }) {
  const style = STATUS_STYLES[topic.status] ?? STATUS_STYLES.new;
  const pct = Math.round(topic.mastery_score * 100);

  return (
    <div className={`rounded-xl border-l-4 ${style.border} bg-slate-800 p-4`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-white text-sm">{topic.topic.replace(/_/g, ' ')}</p>
          <p className={`${style.text} text-xs mt-0.5`}>{style.emoji} {style.label}</p>
        </div>
        {topic.status !== 'new' ? (
          <span className={`${style.text} text-xl font-bold`}>{pct}%</span>
        ) : (
          <span className="text-xl font-bold text-slate-500">—</span>
        )}
      </div>

      {topic.status !== 'new' && (
        <div
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${topic.topic.replace(/_/g, ' ')} mastery: ${pct}%`}
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-600"
        >
          <div
            className={`h-full rounded-full ${topic.status === 'strong' ? 'bg-green-400' : 'bg-amber-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <div className="flex gap-4 mt-2 text-xs text-slate-400">
        {topic.status !== 'new' && (
          <>
            <span>{topic.weak_count} weak concept{topic.weak_count !== 1 ? 's' : ''}</span>
            {topic.due_for_review > 0 && (
              <span className="text-amber-400">{topic.due_for_review} due for review</span>
            )}
          </>
        )}
        {topic.status === 'new' && <span>Start this topic to track your progress</span>}
      </div>
    </div>
  );
}

export default function StrengthsGaps() {
  const { data, isLoading } = useStrengths();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-gray-500">Loading your progress…</p>
      </div>
    );
  }

  const topics = data?.topics ?? [];
  const overall = data?.overall_mastery ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-extrabold text-gray-900">My Progress</h1>
      <p className="mt-1 text-sm text-gray-500">See how you're doing across all topics</p>

      <div className="mt-6">
        <MasteryRing value={overall} />
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {topics.length > 0 ? (
          topics.map((t) => <TopicCard key={t.topic} topic={t} />)
        ) : (
          <p className="text-sm text-center text-gray-500">
            Complete some lessons to see your progress here!
          </p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

Add the import at the top of `frontend/src/App.tsx`:
```typescript
import StrengthsGaps from '@/pages/child/StrengthsGaps';
```

Add the route inside the `<Route element={<Shell />}>` block, after the `/stats` route:
```tsx
<Route path="/progress" element={<StrengthsGaps />} />
```

- [ ] **Step 3: Add "Progress" tab to BottomTabBar**

In `frontend/src/components/child/BottomTabBar.tsx`, add the import:
```typescript
import { Home, BookOpen, TrendingUp, BarChart3, Target } from 'lucide-react';
```

Update the `TABS` array to include the new tab (insert before Stats):
```typescript
const TABS = [
  { to: '/home', label: 'Home', Icon: Home },
  { to: '/lessons', label: 'Quests', Icon: BookOpen },
  { to: '/progress', label: 'Progress', Icon: Target },
  { to: '/simulator', label: 'Simulator', Icon: TrendingUp },
  { to: '/stats', label: 'Stats', Icon: BarChart3 },
] as const;
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/StrengthsGaps.tsx frontend/src/App.tsx frontend/src/components/child/BottomTabBar.tsx
git commit -m "feat: add Strengths & Gaps page with route and nav tab"
```

---

### Task 11: Frontend Tests — StrengthsGaps + Accessibility

**Files:**
- Create: `frontend/tests/a11y/strengths-gaps.a11y.test.tsx`

- [ ] **Step 1: Write StrengthsGaps a11y test**

Create `frontend/tests/a11y/strengths-gaps.a11y.test.tsx`:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url === path || url.endsWith(path)) {
        return new Response(JSON.stringify(body), { status: 200 });
      }
    }
    return new Response(JSON.stringify(null), { status: 200 });
  });
}

function renderAt(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/progress']}>
        <Routes>
          <Route path="/progress" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('a11y: Strengths & Gaps page', () => {
  it('passes axe audit with topics', async () => {
    mockJsonRoute({
      '/profile/strengths': {
        topics: [
          { topic: 'savings', mastery_score: 0.92, status: 'strong', weak_count: 0, due_for_review: 0, total_concepts: 5 },
          { topic: 'interest_rates', mastery_score: 0.58, status: 'needs_practice', weak_count: 2, due_for_review: 1, total_concepts: 4 },
          { topic: 'investing', mastery_score: 0, status: 'new', weak_count: 0, due_for_review: 0, total_concepts: 0 },
        ],
        overall_mastery: 0.75,
      },
    });
    const { default: StrengthsGaps } = await import('@/pages/child/StrengthsGaps');
    const { container } = renderAt(<StrengthsGaps />);
    await waitFor(() => expect(screen.getByText('My Progress')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('passes axe audit with empty state', async () => {
    mockJsonRoute({
      '/profile/strengths': { topics: [], overall_mastery: 0 },
    });
    const { default: StrengthsGaps } = await import('@/pages/child/StrengthsGaps');
    const { container } = renderAt(<StrengthsGaps />);
    await waitFor(() => expect(screen.getByText('My Progress')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run the a11y tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run tests/a11y/strengths-gaps.a11y.test.tsx`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/a11y/strengths-gaps.a11y.test.tsx
git commit -m "test: add Strengths & Gaps page accessibility tests"
```

---

### Task 12: Full Regression

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_spaced_repetition_service.py tests/test_gap_detection_service.py tests/test_recommendation_categorised.py tests/test_strengths_endpoint.py tests/test_recommendation_enhanced.py tests/test_recommendation_schemas.py -v`
Expected: All pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`
Expected: All pass (362+ tests — baseline was 362, new tests added)

- [ ] **Step 3: TypeScript check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 4: ESLint check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx eslint src --ext .ts,.tsx --quiet`
Expected: Clean

- [ ] **Step 5: Build check**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Report results**

Report total test counts (backend + frontend), any failures, and overall status.
