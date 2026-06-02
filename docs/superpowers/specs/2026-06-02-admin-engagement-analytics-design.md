# Admin Engagement Analytics — Design

**Status:** Approved design, pending spec review → implementation plan.
**Date:** 2026-06-02
**Author:** pairing session (Lee + Claude)

## Goal

Give admins per-module engagement insight: which lessons learners complete, where
they drop off ("get stuck"), and how hard each quiz/scenario is — surfaced on the
admin module page.

## Background & constraint

Today the only learning signal we capture is `LessonCompletion(user_id, lesson_id,
completed_at, score)`. There is **no record of a lesson being opened/viewed**, so we
cannot currently distinguish "never reached this lesson" from "opened it and gave up".
This design adds a lightweight **lesson-view event** to close that gap, then computes
all metrics from views + completions.

Progress/state for learners is computed live (`derive_level_states`), so none of this
affects learner-facing behaviour; it is read-only analytics for admins plus one new
write path (recording a view).

## Scope (agreed)

In scope — four metrics per module:
1. **Per-lesson completion count** (distinct learners who completed each lesson).
2. **Funnel drop-off** (where within a module learners stop progressing).
3. **Average quiz/scenario score** per lesson.
4. **Module-level summary** (learners started, % completed, average score).

Out of scope (explicitly deferred):
- Per-answer / wrong-answer attempt tracking (question-level retry analysis).
- Time-series trends of views/engagement over time.
- Per-child drill-down in this surface (existing parent analytics already covers per-child).

## Data model

New table `lesson_views`:
- `id` UUID PK
- `user_id` UUID FK → users.id, `ondelete="CASCADE"`, indexed
- `lesson_id` UUID FK → lessons.id, `ondelete="CASCADE"`, indexed
- `first_viewed_at` timestamptz, default now
- `UniqueConstraint(user_id, lesson_id)` — one row per learner per lesson (distinct viewers)

Rationale: we only need **distinct viewer counts**, not a view-frequency log, so a
de-duplicated row (keep first view) is the minimal sufficient shape. Mirrors the
`LessonCompletion` table’s structure and `uq_lesson_completion_user_lesson` constraint.

Migration: hand-written Alembic revision chained on current head `d4e5f6a7b8c9`.

## Event capture (the one new write path)

`POST /content/lessons/{lesson_id}/view` on the existing content router
(`app/routers/content.py`, `APIRouter(tags=["content"])`).
- Auth: `Depends(get_current_user)` — same as `/lessons/{id}/complete`.
- Behaviour: idempotent upsert — insert a `LessonView` if absent for
  `(user, lesson)`; if present, no-op (keep `first_viewed_at`). Returns `204 No Content`.
- 404 if the lesson does not exist.
- CSRF: content POSTs are already handled by the existing trusted-origin /
  `X-Capacitor-App` mechanism (same as `complete`); no exemption change.

Client: the child Lesson page (`src/pages/child/Lesson.tsx`) fires this once when the
lesson screen mounts (fire-and-forget; a failed view-ping must never block the lesson).
Add `recordLessonView(lessonId)` to `src/api/content.ts`.

## Aggregation service

New `app/services/engagement_service.py` with **pure functions** taking already-fetched
rows (so they are unit-testable without a DB), plus a thin async loader that the router
calls. Computed for one module across all its levels, lessons ordered by
`(level.order_index, lesson.order_index)`:

Per lesson:
- `views` — distinct viewers
- `completions` — distinct completers
- `completion_rate` — completions / views; `None` when views == 0 (never divide by zero)
- `average_score` — mean of non-null `LessonCompletion.score` for that lesson
  (None for card/video lessons, which have no score)
- `drop_off` — completers(previous lesson) − completers(this lesson), clamped at ≥ 0;
  the first lesson’s drop_off is 0. This locates where progression stalls.

Module summary:
- `learners_started` — distinct users with ≥1 view of any lesson in the module
- `learners_completed` — distinct users who completed **every** lesson in the module
  (consistent with how `derive_level_states` defines completion: done == total)
- `completion_rate` — learners_completed / learners_started
- `average_score` — mean of all non-null scores across the module’s lessons

Edge cases the pure functions must handle: a module/level with zero lessons; lessons
with zero views (rate = None, no divide-by-zero); a learner who completed a lesson
without a recorded view (counts as both viewer and completer — completion implies a
view); modules where no one has started (all zeros, rate None).

## Admin API

`GET /admin/modules/{module_id}/engagement` on the admin router (already behind
`Depends(get_current_admin)`). Returns:

```
ModuleEngagementOut {
  module_id: UUID
  learners_started: int
  learners_completed: int
  completion_rate: float | None
  average_score: float | None
  lessons: [ LessonEngagementOut {
      lesson_id: UUID
      type: str
      label: str            # same labelling rule as the lesson list (card title / quiz question / scenario prompt / video caption)
      order: int            # 0-based position within the module
      views: int
      completions: int
      completion_rate: float | None
      average_score: float | None
      drop_off: int
  } ]
}
```
404 if the module does not exist. Pydantic v2 schemas in `app/schemas/admin.py`.

## Admin UI

An **Engagement panel on the admin module view** (where you land when you click a
module — `src/components/admin/ModuleForm.tsx`, edit mode only; new modules have no
data). Add `useModuleEngagement(moduleId)` to `src/api/admin.ts`
(`GET /admin/modules/{id}/engagement`), and a `ModuleEngagement.tsx` component:

- **Summary header:** learners started, completion rate (%), average score.
- **Per-lesson table** in curriculum order: label, type chip, views, completions,
  completion-rate bar, average score (— for card/video), and a drop-off indicator.
  Visually emphasise the lesson with the largest drop-off / lowest completion rate so
  the sticking point is obvious at a glance.
- Loading and empty states ("No engagement data yet" when nobody has started).
- Numbers only — no per-child PII in this view.

## Testing

- Backend: unit tests for the pure aggregation functions (normal case; empty module;
  zero-view lessons; drop-off computation; completion-implies-view; no-learners case).
  Endpoint tests for `POST /lessons/{id}/view` (insert, idempotent re-post, 404) and
  `GET /admin/modules/{id}/engagement` (auth required, shape, 404), using the existing
  `client`/`db_session` fixtures.
- Frontend: `ModuleEngagement` component tests (summary + per-lesson rows + empty
  state) and an accessibility test (jsx-a11y / vitest-axe) consistent with other admin
  components.

## Privacy & data notes

- View events are children’s behavioural data; admins see only **aggregates**, never
  per-child rows, in this surface.
- View data is **forward-only**: counts begin accumulating when this ships. Completions
  and scores retain their history; "views/started" do not backfill.

## Non-goals / future hooks

- If question-level retry analysis is wanted later, add a separate quiz-attempt event;
  this design intentionally does not.
- The `lesson_views` table could later carry an append-only log for time-series, but
  the de-duplicated shape is deliberate for the chosen metrics.
