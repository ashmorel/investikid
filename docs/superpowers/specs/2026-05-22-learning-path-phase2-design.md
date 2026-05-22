# Learning Path Intelligence (Phase 2: Gaps, Spaced Repetition, Categories) — Design Spec

**Sub-project:** 12 of Invest-Ed hardening programme
**Date:** 2026-05-22
**Status:** Approved

## Goal

Extend Phase 1's single "Next Quest" recommendation into a categorised, spaced-repetition-aware system. Children see three themed sections on their Home page ("Continue Learning", "Practise Again", "Something New"), receive review nudges when concepts are due, and can explore a dedicated Strengths & Gaps page showing per-topic mastery.

## Scope

- Spaced repetition scheduling (SM-2 lite) triggered by practice quiz completion
- Categorised recommendations on the child Home page (3 sections, max 2 cards each)
- Review nudge banner when SR items are overdue
- Strengths & Gaps page with per-topic mastery, weak concept chips, and SR due dates
- Gap detection service reading existing TopicMastery + WeakConcept + SR data
- Backend tests for SM-2 math, categorisation, gap detection, endpoint schemas
- Frontend tests for new components + axe audits

**Out of scope (Phase 3 / sub-project 13):** Coach Eddie integration with recommendations, parent-facing recommendation insights, lesson-level skill tags.

## Architecture

### Approach: Unified Scoring

Extend the existing `recommendation_service.py` with SM-2 scheduling data. One service scores all modules, then a new `_categorise_scored_modules()` pure function groups results into categories based on score components. A separate `spaced_repetition_service.py` isolates the SM-2 math. A `gap_detection_service.py` provides read-only per-topic summaries for the Strengths & Gaps page.

### Data Model

**New table: `spaced_repetition_items`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | NOT NULL |
| weak_concept_id | UUID FK → weak_concepts | NOT NULL, UNIQUE with user_id |
| ease_factor | Float | Default 2.5, min 1.3 |
| interval_days | Integer | Default 1 |
| repetition_count | Integer | Default 0 |
| next_review_at | DateTime(tz) | When this item is next due |
| last_reviewed_at | DateTime(tz) | Nullable — null means never reviewed |
| created_at | DateTime(tz) | NOT NULL |

Composite unique constraint on `(user_id, weak_concept_id)`. Index on `(user_id, next_review_at)` for efficient "due items" queries.

**Existing tables — no changes:**
- `weak_concepts` — already tracks topic, concept, times_wrong, times_reinforced, resolved
- `topic_mastery` — already has mastery_score, quizzes_attempted, quizzes_correct, last_activity_at

### SM-2 Lite Algorithm

Simplified for children: no manual quality ratings. Binary outcome from quiz results.

**On practice quiz completion, for each weak concept touched:**
- Correct answer → quality = 4 (good recall)
- Wrong answer → quality = 1 (poor recall)

**Update rules:**
- If quality ≥ 3 (correct):
  - repetition 0 → interval = 1 day
  - repetition 1 → interval = 3 days
  - repetition 2+ → interval = previous_interval × ease_factor
  - ease_factor adjusted: `ef += 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)`
  - repetition_count += 1
- If quality < 3 (wrong):
  - Reset: repetition_count = 0, interval = 1 day
  - ease_factor -= 0.2, floored at 1.3

**next_review_at = now + interval_days**

### Backend Services

**New: `backend/app/services/spaced_repetition_service.py`**
- `calculate_next_review(ease_factor, interval_days, repetition_count, quality) -> tuple[float, int, int]` — pure function, returns (new_ease, new_interval, new_rep_count). No DB access.
- `get_due_items(session, user_id) -> list[SpacedRepetitionItem]` — queries items where next_review_at ≤ now and the linked weak_concept is not resolved.
- `get_due_count(session, user_id) -> int` — count only, for review_summary.
- `record_review(session, user_id, weak_concept_id, correct: bool) -> None` — upserts SR item with new schedule. Creates item on first encounter (ease_factor=2.5, interval=1, rep=0).

**New: `backend/app/services/gap_detection_service.py`**
- `get_strengths_and_gaps(session, user_id) -> StrengthsAndGaps` — per-topic summary combining TopicMastery + WeakConcept + SR schedule.
- Returns per topic: topic name, mastery_score, status ("strong" if ≥0.8, "needs_practice" if <0.8, "new" if no mastery data), weak_count (unresolved), due_for_review_count, total_concepts.
- Also returns overall_mastery (average of all topic mastery_scores).
- Pure read service — no writes.

**Modified: `backend/app/services/recommendation_service.py`**
- `get_recommendations()` return shape changes from `{next_quest, suggested_modules}` to categorised format (see API section).
- New `_categorise_scored_modules()` pure function splits scored modules into three buckets:
  - `continue_learning` — modules with 0 < completed_count < total_count (partial completion)
  - `practise_again` — modules linked to topics that have due SR items or unresolved weak concepts
  - `something_new` — modules with completed_count == 0 and no weak concepts in their topic
- Each category capped at 2 items, sorted by score descending within category.
- `practise_again` items include a `review_prompt` string when SR items are overdue.
- Calls `get_due_items()` from spaced_repetition_service to identify due concepts per topic.
- `review_summary` field computed from `get_due_count()`.

**Modified integration (no new endpoint):**
- Practice quiz completion flow (`POST /lessons/{id}/practice` in `ai.py` router) — after quiz grading updates WeakConcept, also calls `record_review()` for each weak concept touched in the quiz. This triggers SR scheduling automatically with no extra child interaction.

### API Endpoints

**Modified: `GET /recommendations`**

New response shape:
```python
class RecommendationCategoryItem(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID | None
    score: float
    reason: str
    review_prompt: str | None = None  # only in practise_again
    weak_concepts: list[str] = []     # concept names, only in practise_again

class ReviewSummary(BaseModel):
    due_count: int
    next_due_at: datetime | None

class CategorisedRecommendations(BaseModel):
    continue_learning: list[RecommendationCategoryItem]
    practise_again: list[RecommendationCategoryItem]
    something_new: list[RecommendationCategoryItem]
    review_summary: ReviewSummary
```

Each category max 2 items. Empty categories return empty lists (frontend hides them).

**New: `GET /profile/strengths`**

```python
class TopicStrength(BaseModel):
    topic: str
    mastery_score: float
    status: str  # "strong", "needs_practice", "new"
    weak_count: int
    due_for_review: int
    total_concepts: int

class StrengthsAndGaps(BaseModel):
    topics: list[TopicStrength]
    overall_mastery: float
```

Added to the existing `ai.py` router alongside `/profile/mastery`.

### Frontend

**Modified: `frontend/src/pages/child/Home.tsx`**
- Replace single QuestCard with three `RecommendationCategory` sections
- Review nudge banner at top (purple gradient) when `review_summary.due_count > 0`
- Each category: coloured header label, 1-2 `RecommendationCard` components
- Empty categories hidden entirely
- Fallback: "Complete a lesson to get personalised recommendations" when all categories empty

**New component: `frontend/src/components/child/RecommendationCard.tsx`**
- Colour-coded left border (green/amber/blue based on category prop)
- Module title, lesson progress or concept chips depending on category
- Progress bar for continue_learning cards
- Weak concept chips (amber pills) for practise_again cards
- Reason string at bottom
- Click navigates to `/modules/{module_id}` or practice quiz for practise_again

**New component: `frontend/src/components/child/ReviewBanner.tsx`**
- Purple gradient banner with bell icon
- Shows due_count and encouraging message
- Only renders when due_count > 0
- Click navigates to first due practice quiz

**New page: `frontend/src/pages/child/StrengthsGaps.tsx`**
- Overall mastery ring chart (SVG donut) at top
- Per-topic cards sorted by actionability: needs_practice first, strong second, new last
- Three colour states: green (≥0.8 mastery, "Strong"), amber (<0.8, "Needs practice"), grey (no data, "Not started")
- Weak concept chips expand inline under amber topic cards with SR due dates
- Positive framing throughout: "Needs practice" not "Failing", "Concepts to work on" not "Weaknesses"

**New nav link:** "My Progress" in child sidebar, routes to `/progress`

**Modified: `frontend/src/api/ai.ts`**
- Update `getRecommendations()` return type to `CategorisedRecommendations`
- New `getStrengths()` function → `GET /profile/strengths`
- New `useStrengths()` TanStack Query hook

### Testing Strategy

**Backend (pytest):**

*Spaced repetition service (unit, no DB):*
- `calculate_next_review` with correct answer: interval increases, ease_factor adjusts
- `calculate_next_review` with wrong answer: resets to interval=1, rep=0, ease_factor decreases
- `calculate_next_review`: ease_factor floors at 1.3
- `calculate_next_review`: first rep → 1 day, second rep → 3 days, third+ → interval × ease
- `record_review`: creates SR item on first encounter with defaults
- `record_review`: updates existing item with new schedule
- `get_due_items`: returns items where next_review_at ≤ now, excludes resolved concepts

*Gap detection service (unit):*
- Topics with no mastery data → status "new"
- Topics with mastery ≥ 0.8 → status "strong"
- Topics with mastery < 0.8 → status "needs_practice"
- due_for_review counts from SR items
- overall_mastery is average of all topic scores
- Sorted: needs_practice first, strong second, new last

*Recommendation categorisation (unit, no DB):*
- `_categorise_scored_modules`: partial completion → continue_learning
- `_categorise_scored_modules`: due SR items → practise_again
- `_categorise_scored_modules`: untouched → something_new
- Empty categories excluded from output (empty lists)
- Max 2 items per category enforced
- review_prompt present when items overdue, absent otherwise

*Endpoint schemas (unit):*
- `GET /recommendations` returns CategorisedRecommendations shape
- `GET /profile/strengths` returns StrengthsAndGaps shape
- Each category item validates required fields

*Integration (needs DB):*
- Full `get_recommendations()` returns categorised shape with real data
- Practice quiz completion triggers SR record_review
- review_summary.due_count reflects actual due items

**Frontend (vitest):**

*RecommendationCard:*
- Renders module title and reason
- Shows progress bar for continue_learning category
- Shows weak concept chips for practise_again category
- Navigates on click

*ReviewBanner:*
- Renders when due_count > 0
- Hidden when due_count == 0
- Shows correct due count

*Home page categories:*
- Renders three sections when all have items
- Hides empty categories
- Shows review banner when items are due
- Fallback message when all categories empty

*StrengthsGaps page:*
- Renders overall mastery ring with correct percentage
- Renders topic cards with correct colour states
- Sorts topics by actionability
- Shows weak concept chips under amber topics
- Handles empty state (no mastery data)

**Accessibility (vitest-axe):**
- Home page categories pass axe audit
- Strengths & Gaps page passes axe audit
- Review banner is announced by screen readers (role="alert" or aria-live)

### File Structure

**Backend:**
```
backend/
├── alembic/versions/
│   └── xxxx_add_spaced_repetition_items.py
├── app/
│   ├── models/
│   │   └── skill_profile.py          # Add SpacedRepetitionItem model
│   ├── services/
│   │   ├── spaced_repetition_service.py  # NEW — SM-2 math + scheduling
│   │   ├── gap_detection_service.py      # NEW — per-topic strengths/gaps
│   │   └── recommendation_service.py     # MODIFIED — categorised output
│   ├── schemas/
│   │   └── ai.py                         # Add categorised recommendation schemas
│   └── routers/
│       └── ai.py                         # MODIFIED — new /profile/strengths, updated /recommendations shape, SR hook on practice quiz
└── tests/
    ├── test_spaced_repetition_service.py
    ├── test_gap_detection_service.py
    ├── test_recommendation_categorised.py
    └── test_strengths_endpoint.py
```

**Frontend:**
```
frontend/src/
├── api/
│   └── ai.ts                                # MODIFIED — new types + useStrengths hook
├── components/child/
│   ├── RecommendationCard.tsx                # NEW
│   ├── ReviewBanner.tsx                      # NEW
│   └── __tests__/
│       ├── RecommendationCard.test.tsx       # NEW
│       └── ReviewBanner.test.tsx             # NEW
├── pages/child/
│   ├── Home.tsx                              # MODIFIED — categorised sections
│   └── StrengthsGaps.tsx                     # NEW
├── pages/child/__tests__/
│   ├── Home.test.tsx                         # MODIFIED
│   └── StrengthsGaps.test.tsx                # NEW
└── tests/a11y/
    ├── home-categories.a11y.test.tsx         # NEW
    └── strengths-gaps.a11y.test.tsx          # NEW
```

### Error Handling

- No SR data yet → "Practise again" section hidden, no review banner
- No mastery data → Strengths page shows all topics as "Not started"
- API error → TanStack Query retry with existing error boundary pattern
- Empty recommendations → "Complete a lesson to get personalised recommendations" fallback message

### Migration & Backwards Compatibility

- New Alembic migration adds `spaced_repetition_items` table — no existing table changes
- `GET /recommendations` response shape changes — breaking change for the frontend, but both ship together in the same deployment
- Old `next_quest` / `suggested_modules` shape replaced by categorised shape
- Home.tsx updated to consume new shape — single deployment, no migration period needed
- Coach Eddie (sub-project 13) will consume the new categorised shape — forward compatible
