# Level-Aware Recommendations + Parent Per-Level Analytics (Leveled Progression 15.3) — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Builds on:** 15.1 (the `Level` entity + `level_service.derive_level_states` + `next_lesson_service`), and the existing recommendation/analytics services. **Deterministic — no LLM.** No DB migration.

## Goal

Make the two surfaces that are still module-grained understand levels:
1. **Recommendations** never point a child at a lesson inside a **locked** level, and carry level context so the UI can show "Level 2 · {lesson}".
2. **Parent analytics** gain a per-module → per-level progress breakdown (the same level states the child already sees on the Module page).

## Already done (do NOT rebuild)
`Level` model, `derive_level_states` (returns per-level `state`/`locked_reason`/`passed`/`lessons_total`/`lessons_completed`), `GET /modules/{id}/levels`, and `next_lesson_service.resolve_next_lesson` (already level-aware) are all built. The child already sees per-level state via the Module-page `LevelCard`s — so **no child-facing analytics view** is in scope.

## Decisions (from brainstorming)
- Recommendations: **level-aware lesson pointer + level context only** (no level-based re-scoring; module scoring/categories unchanged).
- Analytics: **parent only** (child already sees level state on Module pages).

---

## Section 1 — Level-aware recommendations

### 1a. Service (`app/services/recommendation_service.py`)
Today (~lines 288–350) the per-module "first incomplete lesson" pointer iterates a module's lessons in order and picks the first one with no `LessonCompletion`, **ignoring level locks**. Change it to be level-aware using the existing `derive_level_states`:
- For the module being turned into a recommendation item, build `LevelStateInput[]` from its levels + a `lessons_by_level` map (mirroring how `next_lesson_service` builds them, lines 39–56), plus the user's `completed_ids`, `scores`, and `is_premium`.
- Call `derive_level_states(...)`. Walk the module's levels in `order_index`; pick the **first level whose state is `in_progress`** (i.e. unlocked + not complete). Within it, pick the first lesson (by `order_index`) with no completion. That `(level_id, lesson_id)` is the pointer.
- If no level is `in_progress` (all complete, or the next is locked), the item has **`lesson_id = None`** and **`level_id = None`** (the card still surfaces the module, just without a deep link — consistent with today's "no incomplete lesson" behaviour).
- Resolve `level_title` from the chosen level for the schema.
- **Lessons not attached to a level** (`Lesson.level_id is None`): keep today's behaviour (first incomplete lesson, `level_id = None`) so legacy/unlevelled modules still work.
- Keep `_apply_hard_filters` (age/premium/region/prerequisite) exactly as-is — gating is unchanged.

To avoid duplicating the level-walking logic, extract a small pure helper (in `level_service.py`) `first_actionable_lesson(level_inputs, lessons_by_level_ordered, completed_ids, scores, user_is_premium) -> tuple[level_id, lesson_id] | None` and use it in `recommendation_service`. (Optional: also use it in `next_lesson_service` if it slots in cleanly — but do **not** risk breaking `next_lesson_service`; leave it untouched if the refactor isn't clean.)

### 1b. Schema (`app/schemas/ai.py`)
`RecommendationCategoryItem` gains:
```python
    level_id: uuid.UUID | None = None
    level_title: str | None = None
```
Populated by the service for `continue_learning` (and the profiling-off seed where a level applies). Backwards-compatible (optional fields).

### 1c. Frontend (`src/components/RecommendationCard.tsx` / wherever items render)
When `level_title` is present, render it as a small prefix/eyebrow — e.g. "Level 2 · {lesson/CTA}". When absent, render exactly as today. Accessible (it's text, part of the card's accessible name/label), semantic tokens.

### 1d. Tests (backend)
- A module with a **locked premium** later level + an unlocked first level → recommendation points at a lesson in the first level, never the locked one; `level_id`/`level_title` set.
- A module whose first level is complete-and-passed and second is `in_progress` → pointer is in the second level.
- A module whose only remaining lessons are in a **progression-locked** level → `lesson_id`/`level_id` are `None` (module still recommended).
- An unlevelled module (lessons with `level_id None`) → today's behaviour preserved (first incomplete lesson, `level_id None`).
- `_apply_hard_filters` gating unchanged (existing recommendation tests still pass).

Frontend test: `RecommendationCard` shows the level prefix when `level_title` is set, omits it otherwise; axe-clean.

---

## Section 2 — Parent per-level analytics

### 2a. Service (`app/services/analytics_service.py::build_child_analytics`)
Add a `modules_progress` list computed from the child's **accessible** modules (region/premium-filtered consistently with how content is served — reuse `content_region_for`/`is_module_accessible`). For each module: load its levels + lessons, the child's completions + scores + premium, call `derive_level_states`, and build:
- `ModuleProgressOut{ module_id, title, icon, lessons_completed, lessons_total, levels: list[LevelProgressOut] }`
- `LevelProgressOut{ level_id, title, state, locked_reason, passed, lessons_completed, lessons_total }` (straight from the `LevelState` plus the level's title).
Order modules by `order_index`; levels by `order_index`. The existing global fields (`level`, `xp`, `streak_count`, `lessons_completed/total`, `recent_lessons`, `badges`) are unchanged.

### 2b. Schema (`app/schemas/parent.py`)
Add `LevelProgressOut` + `ModuleProgressOut` and `modules_progress: list[ModuleProgressOut]` on `ChildAnalyticsOut`. (`build_child_analytics` is called from `GET /parent/children` per child — the new field rides along; no new endpoint.)

### 2c. Frontend (`src/components/ChildAnalytics.tsx`)
Add a **"Progress by module"** section below the existing stats: a list of modules, each an accessible **disclosure** (reuse the a11y `Disclosure` primitive) showing the module's completion (x/y lessons + a progress bar — reuse the existing `ProgressBar`) and, expanded, per-level rows: level title, a **state badge** (In progress / Completed / 🔒 Locked, with passed ✓ when passed), and x/y lessons. Semantic tokens, ≥16px/keyboard, no raw palette.

### 2d. Tests
- Backend: `build_child_analytics` returns `modules_progress` with correct per-level `state`/`passed`/counts for a child with a passed level 1 + locked level 2; respects region/premium accessibility; modules/levels ordered.
- Frontend: `ChildAnalytics` renders the module list, expands a module to show level rows + state badges, and is axe-clean. Update the existing analytics mock/fixtures to include `modules_progress`.

---

## Verification
Backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. Parent/child web surfaces, no native change → no `cap sync`.

## Out of scope
Level-based re-scoring of recommendations; a separate child progress view; any model/DB migration; changes to `derive_level_states` semantics or `next_lesson_service` behaviour (reused, not changed). 15.2's AI-draft flow is untouched.
