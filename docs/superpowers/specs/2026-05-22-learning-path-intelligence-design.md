# Learning Path Intelligence (Phase 1: Recommendations) — Design Spec

**Sub-project:** 11 of Invest-Ed hardening programme
**Date:** 2026-05-22
**Status:** Approved

## Goal

Add a recommendation engine that suggests the best next module for each child based on prerequisites, age, topic preference, and quiz performance. Surface it as an "Up Next" card on the child's Home screen.

## Scope

- Backend recommendation service with weighted scoring algorithm
- Topic mastery tracking (denormalised, updated on lesson completion)
- Admin-defined module prerequisites and age ranges
- "Up Next" card on child Home page
- Admin panel updates for prerequisite and age range fields

**Out of scope (phases 2 & 3):** Knowledge gap detection UI, spaced repetition scheduling, lesson-level skill tags, Coach Eddie integration with recommendations, parent-facing recommendation insights, multiple recommendations.

## Architecture

### Data Model Changes

**Module model — add three columns:**
- `prerequisite_ids: ARRAY(UUID)` — optional list of module IDs that must be completed before this module is recommended. Default empty array.
- `min_age: Integer | None` — minimum recommended age. NULL means no lower bound.
- `max_age: Integer | None` — maximum recommended age. NULL means no upper bound.

**New table: `topic_mastery`**
```sql
CREATE TABLE topic_mastery (
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic      VARCHAR(30) NOT NULL,
    avg_score  FLOAT       NOT NULL DEFAULT 0,
    lessons_completed INT  NOT NULL DEFAULT 0,
    total_lessons     INT  NOT NULL DEFAULT 0,
    last_activity TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, topic)
);
```

Denormalised for fast reads. Updated by the lesson completion endpoint via an upsert after each completion.

**No changes to:** Lesson, LessonCompletion, UserProgress.

### Recommendation Algorithm

The service ranks all incomplete, eligible modules and returns the top pick.

**Hard filters (module excluded if any fail):**
1. Already completed — all lessons in the module are done
2. Prerequisites not met — any prerequisite module has uncompleted lessons
3. Age out of range — child's age (from `dob`) falls outside `min_age`/`max_age`
4. Premium gating — module is premium and child is not premium
5. Country filtering — module has `country_codes` set and child's `country_code` is not included

**Soft scoring (higher = recommended first):**
| Factor | Weight | Logic |
|--------|--------|-------|
| Topic match | 30% | Module topic matches user's `topic_path` preference |
| Readiness | 25% | All prerequisites completed with avg score ≥ 0.7 |
| Near completion | 20% | Module is partially started (≥1 lesson done but not all) — score scales with % complete |
| Natural order | 15% | Lower `order_index` within same topic scores higher |
| Topic variety | 10% | Bonus if child hasn't touched this topic recently |

**Reason string:** Human-readable based on the top scoring factor:
- Topic match: "You're great at {topic} — try this next!"
- Near completion: "You're halfway through — keep going!"
- Topic variety: "Something new to explore!"
- Readiness: "You're ready for the next level!"
- Default/order: "Recommended for you"

**Fallback:** Returns `null` when no modules pass the filters.

### Backend API

**New endpoint (child-facing):**
| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| GET | `/content/recommended` | Child JWT | `{ module: ModuleOut, reason: str } | null` |

Added to the existing `content.py` router.

**Modified endpoints:**
- `POST /content/lessons/{id}/complete` — add `update_topic_mastery()` call after successful completion
- `PUT /admin/modules/{id}` — accept `prerequisite_ids`, `min_age`, `max_age`
- `GET /admin/modules` — response includes new fields

### Service Layer

**`backend/app/services/recommendation.py`**
- `RecommendationService.get_recommendation(user, session) -> RecommendationResult | None`
- Pure logic: query modules + completions + mastery, apply filters, score, rank, return top result
- Fully unit-testable without HTTP layer

**`backend/app/services/topic_mastery.py`**
- `update_topic_mastery(user_id, topic, session) -> None`
- Called from completion endpoint. Upserts the `topic_mastery` row for the given user+topic.
- Queries all lesson completions for that user in modules with the given topic, calculates avg_score, lessons_completed, total_lessons.

### Schemas

**New recommendation schema:**
```python
class RecommendationOut(BaseModel):
    module: ModuleOut
    reason: str

    model_config = ConfigDict(from_attributes=True)
```

**Module admin schema updates:**
```python
class ModuleCreate(BaseModel):
    # ... existing fields ...
    prerequisite_ids: list[uuid.UUID] = []
    min_age: int | None = None
    max_age: int | None = None

class ModuleUpdate(BaseModel):
    # ... existing fields ...
    prerequisite_ids: list[uuid.UUID] | None = None
    min_age: int | None = None
    max_age: int | None = None

class ModuleOut(BaseModel):
    # ... existing fields ...
    prerequisite_ids: list[uuid.UUID]
    min_age: int | None
    max_age: int | None
```

**Prerequisite validation:** On module create/update, validate that `prerequisite_ids` do not include the module's own ID and that all referenced IDs exist. No circular dependency detection beyond self-reference (admin is trusted to set sensible prerequisites).

### Frontend

**New component: `UpNextCard.tsx`** (`frontend/src/components/child/`)
- Renders at the top of the child Home page, above the module list
- Shows: module icon, title, reason string, topic badge (pill), "Start"/"Continue" button
- Hidden when endpoint returns null — no empty state
- Loading: skeleton shimmer consistent with existing patterns
- Same dark theme and card styling as `ModuleCard`
- Button navigates to `/modules/{id}`

**New hook:** `useRecommendation()` in `frontend/src/api/content.ts` (or new file)
- `GET /content/recommended` with child auth
- TanStack Query, staleTime appropriate for session (e.g. 5 minutes)

**Admin panel ModuleForm updates:**
- Prerequisites field: multi-select dropdown of other modules (excluding self), showing icon + title
- Age range: two number inputs (Min Age / Max Age), empty = no restriction
- Inline help: "Leave empty for all ages"

### Testing Strategy

**Backend (pytest):**
- RecommendationService unit tests:
  - Returns top-scored module when multiple eligible
  - Excludes completed modules
  - Excludes modules with unmet prerequisites
  - Excludes age-inappropriate modules
  - Excludes premium modules for free users
  - Excludes country-filtered modules
  - Prefers topic_path match over unrelated topics
  - Prefers partially-started modules
  - Returns null when all modules completed
  - Returns null when no modules exist
- Topic mastery service: upsert creates row, updates on re-completion, avg_score calculation
- Recommendation endpoint: authenticated returns recommendation, unauthenticated returns 401
- Admin module update: accepts prerequisite_ids/age range, validates no self-reference, validates referenced IDs exist

**Frontend (vitest):**
- UpNextCard: renders module info and reason, navigates on click, hidden when no recommendation, loading skeleton
- ModuleForm updates: prerequisite multi-select renders, age range inputs render and validate

**Accessibility (axe):**
- UpNextCard passes axe audit
- New admin fields keyboard-accessible

### File Structure

**Backend:**
```
backend/
├── alembic/versions/
│   └── xxxx_add_recommendations.py
├── app/
│   ├── models/
│   │   └── content.py            # Add fields to Module, new TopicMastery
│   ├── services/
│   │   ├── recommendation.py     # RecommendationService
│   │   └── topic_mastery.py      # update_topic_mastery
│   ├── schemas/
│   │   ├── admin.py              # Add prerequisite/age fields
│   │   └── recommendation.py     # RecommendationOut
│   └── routers/
│       ├── content.py            # Add /recommended endpoint + mastery call
│       └── admin.py              # Prerequisite validation on module update
└── tests/
    ├── test_recommendation.py
    └── test_topic_mastery.py
```

**Frontend:**
```
frontend/src/
├── api/
│   └── content.ts                # useRecommendation hook (or new file)
├── components/child/
│   └── UpNextCard.tsx
├── components/admin/
│   └── ModuleForm.tsx            # Add prerequisite + age fields
├── components/child/__tests__/
│   └── UpNextCard.test.tsx
├── components/admin/__tests__/
│   └── ModuleForm.test.tsx       # Updated tests
└── tests/a11y/
    └── recommendations.a11y.test.tsx
```
