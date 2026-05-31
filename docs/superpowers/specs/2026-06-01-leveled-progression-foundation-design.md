# Leveled Progression — Foundation (Sub-project 1 of 3) — Design Spec

## Goal

Introduce a first-class **Level** structure between Module and Lesson so that, within a topic (e.g. Stocks), a child progresses Level 1 → Level 2 → beyond. A level unlocks when the previous one is completed **and** passed. Levels can be flagged premium. Adds **video lessons** as an authored lesson type within levels. Hand-authored content only — AI-generated levels are a separate later sub-project.

## Scope & decomposition

The user's full vision (leveled progression + AI-generated premium levels + videos) is split into three sub-projects, built in order:

1. **Levels foundation (this spec):** Level model, unlock progression, per-level premium gating, frontend level UI, video lessons as an authored type.
2. **AI-generated levels + admin review (later):** admin-triggered generation → review → publish for premium levels. The `Level.content_source` field is added here so #2 slots in cleanly.
3. **Polish (later):** level-aware recommendations/analytics.

## Context (verified against code, 2026-06-01)

- `Module(topic, title, order_index, prerequisite_ids, min_age, max_age, is_premium, icon)`; `Lesson(module_id, type, content_json, xp_reward, order_index)`; `LessonCompletion(user_id, lesson_id, score, completed_at)` — unique on `(user_id, lesson_id)`, idempotent.
- Lesson types in use: `card`, `quiz`, `scenario`. `video` has a renderer (`VideoLesson`, YouTube embed via `content_json.youtube_id` + `caption`, with `onComplete`) but no seeded content and is not authorable in the admin `LessonForm`.
- `_award_completion` (in `app/routers/content.py`) awards XP, updates `UserProgress` (xp/level/streak), and on a duplicate completion returns `(0, True)` **without updating score**.
- Premium seam: `is_premium(user)` and `module.is_premium`. Locked content uses `ModuleCard`'s locked state.
- Navigation: `/lessons` (modules) → `/lessons/:moduleId` (lessons) → `/lessons/:moduleId/:lessonId` (lesson).
- Admin: Module CRUD + per-module Lesson authoring (`LessonForm` with card/quiz/scenario editors); patterns `OrderArrows`, `ConfirmDialog`.

---

## Section 1 — Architecture & data model

**New `Level` model** (`app/models/content.py`), sits between Module and Lesson:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `module_id` | UUID FK → modules.id, NOT NULL, ondelete CASCADE | |
| `title` | String(200) NOT NULL | e.g. "Level 1: The Basics" |
| `order_index` | Integer NOT NULL | position within the module |
| `is_premium` | Boolean NOT NULL default False | entitlement gate |
| `pass_threshold` | Float NOT NULL default 0.7 | min quiz score (0–1) to advance |
| `content_source` | String(16) NOT NULL default `"authored"` | `"authored"` \| `"ai"` (only authored in this sub-project) |
| `icon` | String(10) NOT NULL server_default "📊" | |
| `created_at` | DateTime(tz) NOT NULL default utcnow | |

**`Lesson` gains `level_id`** (UUID FK → levels.id, ondelete CASCADE). `module_id` is **kept** (denormalized convenience) so existing module-scoped queries (completion lists, recommendations, content endpoints) are untouched — `level_id` becomes the progression unit. Acceptable redundancy for this sub-project; can normalize later.

**Migration (one Alembic file):**
1. Create `levels` table.
2. Add nullable `lessons.level_id` + index.
3. **Backfill:** for each existing `Module`, insert one `Level` (`title="Level 1"`, `order_index=0`, `is_premium=module.is_premium`, `pass_threshold=0.7`, `content_source="authored"`); set every `lesson.level_id` for that module to the new level.
4. (Post-backfill, `level_id` is logically NOT NULL; leave nullable in DB to avoid a two-step migration, enforced in app code.)

Seed (`app/seed/content.py`) updated so new seed runs create a Level 1 per module and attach lessons to it (idempotent, matching existing seed style). Seed is also extended with example **video** lessons (Section 3).

---

## Section 2 — Progression, scoring & premium gating

**Derived state (no new per-child table)** — computed from existing `LessonCompletion` rows, consistent with Phase 2:

- A level is **complete** when every lesson in it has a `LessonCompletion` for the user.
- A level is **passed** when the average `score` across its scored lessons (`quiz`, `scenario`; `card`/`video` excluded — their score is null) ≥ `level.pass_threshold`. A level with no scored lessons is "passed" on completion.
- **Level N+1 unlocks** when Level N (by `order_index`) is both complete and passed.
- Level 1 (lowest `order_index`) is always unlocked (subject to premium).

**Best-score-wins (behaviour change):** `_award_completion` is changed so a repeat completion of a scored lesson **updates `LessonCompletion.score` to the max(old, new)** (and updates `completed_at`), instead of being a pure no-op. XP is still awarded only once (first completion). This lets a child retake quizzes to raise a level's average to the pass threshold. Non-scored repeats remain no-ops.

**Premium gating:** opening a premium level's lessons requires `is_premium(user)`; the backend returns 403 otherwise. The level-list endpoint returns each level's state so the UI can render locks without extra calls.

**Two lock reasons, distinct UI (entitlement precedence):**
- `locked_reason = "premium"` → ✨ upgrade prompt (shown even if also progression-locked).
- `locked_reason = "progression"` → 🔒 "Finish Level N to unlock".
- else `state ∈ {in_progress, completed}`.

**Age filtering** inherits the module's existing `min_age`/`max_age` — no new logic.

---

## Section 3 — Video lessons

`video` becomes a first-class **authored** lesson type within a level (renderer already exists):
- **Admin:** add `video` to the `LessonForm` type picker with an editor for `youtube_id` (accept a YouTube URL or raw ID; store the ID) + `caption`. `content_json = {youtube_id, caption}`.
- **Completion & scoring:** completes on watch via the existing `onComplete`; `score = null`, so it counts toward "all lessons completed" but is excluded from the pass-threshold average.
- **Seed:** add ≥2 example video lessons across modules.
- YouTube links are hand-picked by the admin (no AI sourcing).

---

## Section 4 — Frontend UX

A level layer slots into navigation:

- **Module view** (`/lessons/:moduleId`) → renders a **list of Levels** (ordered). Each level card shows one of four states with a progress hint ("3/5 lessons", pass status):
  - ✓ **Completed**, ▶ **In progress / unlocked** (tappable), 🔒 **Locked (progression)**, ✨ **Premium**.
- **Level view** (`/lessons/:moduleId/:levelId`) → the list of that level's lessons (reuses today's module-lessons screen, scoped to a level).
- **Lesson view** (`/lessons/:moduleId/:levelId/:lessonId`) → unchanged renderer.
- **Home "Next Quest"** points at the child's current unlocked level.
- Reuses `ModuleCard`/locked-card styling, `Shell`, `BottomTabBar`. New `LevelCard` component for the level states.

Routing changes from two segments to three (`moduleId/levelId/lessonId`). Existing deep links to `/lessons/:moduleId/:lessonId` redirect via the lesson's `level_id`.

---

## Section 5 — Admin

- **Modules → (module) → Levels:** new Level CRUD list + form — create, edit, **reorder** (`OrderArrows`), delete (`ConfirmDialog`). Fields: `title`, `order_index`, `is_premium`, `pass_threshold`, `icon`. `content_source` shown read-only as "authored" (sub-project #2 enables "ai").
- **Levels → (level) → Lessons:** existing `LessonForm` (now incl. video), scoped to a `level_id`.
- Admin sidebar: Modules list → module row links to its Levels → level row links to its Lessons. Reuses existing admin API client + auth.

---

## Section 6 — API surface, migration & testing

**Child API (new/changed):**
- `GET /modules/{module_id}/levels` → `[{ id, title, order_index, is_premium, icon, state, locked_reason, lessons_total, lessons_completed, passed }]`. State derived per Section 2. Premium/age filtering applied.
- `GET /levels/{level_id}/lessons` → lessons in the level (403 if level is premium and user is not). Mirrors today's module-lessons shape.
- `POST /lessons/{lesson_id}/complete` → unchanged contract; internally best-score-wins.

**Admin API (new):**
- `GET/POST /admin/modules/{module_id}/levels`, `PUT/DELETE /admin/levels/{level_id}`, `PATCH /admin/modules/{module_id}/levels/reorder`.
- Lesson endpoints accept/scope by `level_id`.

**Schemas:** `app/schemas/content.py` + `app/schemas/admin.py` gain `LevelOut`, `LevelState`, `AdminLevelCreate/Update/Out`. Frontend types in `src/api/content.ts` / `src/api/admin.ts`.

**Migration:** the single Alembic migration in Section 1.

**Testing:**
- Backend: migration backfill (one Level 1 per module, lessons attached); unlock requires complete **and** pass-threshold; premium level → 403 for free user, 200 for premium; best-score-wins updates score but not XP; video lesson completes with null score and is excluded from the average; level-state derivation for each of the four states.
- Frontend: the four level-card states render correctly; module→level→lesson navigation; video authoring in admin; deep-link redirect.
- a11y + responsive (Playwright) suites already gate CI — level cards must pass.

## Out of scope (this sub-project)

- AI-generated level content and the admin review/publish workflow (sub-project #2; `content_source="ai"`).
- Level-aware recommendation tuning / analytics (sub-project #3).
- Normalizing away `Lesson.module_id`.
- Per-quiz (vs. average) pass thresholds.
