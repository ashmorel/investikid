# W3 — Curriculum Credibility — Design Spec

**Date:** 2026-06-10
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Roadmap:** Phase 1, workstream W3 (`docs/2026-06-10-best-in-class-roadmap.md`). W4 (parent outcome reports) builds on this — `LevelMastery` is the data W4's weekly digest reads.

## Goal
Give parents a reason to trust (and pay for) the curriculum: every module cites recognised financial-education standards and sources, every level states plain-language learning objectives, and "mastered" becomes an **auditable, dated record** instead of an implicit computation.

## Decisions (locked with user)
1. **Region-aware external standards** — UK modules cite the Money & Pensions Service *Financial Education Planning Framework*; US-relevant modules cite *Jump$tart National Standards* (FDIC Money Smart as secondary). Which framework(s) a module cites follows its existing `country_codes` ([] = both).
2. **Objectives per Level, standards/sources per Module** — levels carry the "by the end you can…" statements; the module carries the alignment + references.
3. **Mastery = first time the existing `pass_threshold` is met** — no new quiz; we record the signal `derive_level_states` already computes.

## Current state (verified)
- `Module` (`backend/app/models/content.py`): topic, title, `country_codes`, is_premium, order_index, icon, prerequisite_ids, min/max_age, completion_cash_reward. **No** standards/sources fields.
- `Level`: title, order_index, is_premium, **`pass_threshold` (0.7)**, content_source, icon. **No** objectives field.
- `LessonCompletion`: per-lesson `score`. `level_service.derive_level_states` computes pass state on the fly; `TopicMastery` (skill_profile) tracks per-topic mastery_score. **Nothing records the moment a level is first passed.**
- Admin Module form + seed (`backend/app/seed/content.py`, `_MODULES`) exist; the seed path is the canonical way content promotes across envs.

## Design

### A. Data model (one Alembic migration, chained)
- `modules.standards_alignment` — JSON, nullable, list of `{framework: str, code: str, label: str}`.
- `modules.sources` — JSON, nullable, list of `{title: str, url: str}`.
- `levels.learning_objectives` — JSON, nullable, list of strings (2–4 per level, child-readable).
- **New table `level_mastery`** — `id` UUID PK, `user_id` FK→users (CASCADE), `level_id` FK→levels (CASCADE), `mastered_at` timestamptz, `score` float (the avg quiz score at the moment of mastery), **unique (user_id, level_id)**.

### B. Mastery recording (backend service)
On quiz/scenario lesson completion (the existing completion path), after the score is saved: recompute the level's average quiz/scenario score for that user; if `avg >= level.pass_threshold` **and** all the level's quiz/scenario lessons have completions **and** no `level_mastery` row exists → insert one (idempotent via the unique constraint; race-safe with on-conflict-do-nothing). Never updated or deleted afterwards (auditable). No change to `derive_level_states` or unlock logic — this only *records*.

### C. API surfacing
- Child level/module payloads (`LevelOut`/module detail): add `learning_objectives`, `mastered_at` (null until mastered).
- Module payloads: add `standards_alignment`, `sources`.
- Parent `ChildAnalyticsOut` → `LevelProgressOut`: add `mastered_at`; `ModuleProgressOut`: add `standards_alignment` (the badge data W4 will reuse).
- Admin module/level update endpoints accept the new fields (validated shapes: list lengths, URL format for sources).

### D. Frontend surfacing
- **Child Level page:** an "In this level you'll learn…" intro block (objectives) + a "Mastered ✓ {date}" stamp once recorded. Tier-appropriate copy; WCAG AA.
- **Parent ChildAnalytics:** standards badge per module ("Aligned to UK MaPS · US Jump$tart" from `standards_alignment` frameworks) + mastery dates on level rows.
- **Admin:** ModuleForm gains standards/sources editors (simple list editors); a per-level objectives editor.

### E. Content pack (the bulk — same flow as the Level 2/3 rollout)
AI-drafted, **user spot-reviews one assembled doc** before seeding:
- For each of the **12 modules**: 1–3 `standards_alignment` entries per relevant framework + 1–3 `sources`.
- For each of the **36 levels**: 2–4 plain-language objectives.
- **Authoring rule:** framework strand names/codes are taken from the *published* MaPS framework / Jump$tart standards (fetched during authoring, not invented). The mapping is a content judgment surfaced for user review.
- Lands in `seed/content.py` (module dicts gain `standards_alignment`/`sources`; level dicts gain `learning_objectives`); seeder upserts these fields idempotently (update-in-place on existing rows, like icon/is_premium today).

## Sub-project split (each independently shippable)
1. **W3a — Schema + mastery recording + API** (migration, service hook, schemas, tests).
2. **W3b — Content pack** (draft → assembled review doc → user approval → seed + idempotent upsert).
3. **W3c — Surfacing** (child objectives/mastered stamp, parent badge/dates, admin editors, a11y tests).

## Testing
- **W3a:** migration up/down; mastery written exactly once at threshold (incl. race/idempotency, partial-completion not mastered, threshold-exact mastered); API fields present; existing progression tests unchanged.
- **W3b:** seed idempotency (re-seed updates fields, no dupes); shape validation of all entries; spot-review doc approved by user before seeding.
- **W3c:** vitest + vitest-axe for the three surfaces; parent badge renders frameworks from data (no hardcoding).

## Out of scope
Unlock/progression changes; a dedicated mastery quiz; simulator; premium gating changes; W4's digest (separate spec — reads `level_mastery`).

## Open risks
- **Framework fidelity:** MaPS/Jump$tart strand wording must be quoted accurately; mitigated by fetching the published docs during W3b authoring + user review.
- **Existing users:** children who already passed levels before this ships have no `level_mastery` rows. Mitigation: a one-off backfill in the same migration window — compute from existing `LessonCompletion` data and insert with `mastered_at = now()` flagged `score` from history (documented as backfilled). (Decide at W3a plan time; default = do the backfill so W4 reports aren't empty.)
