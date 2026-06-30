# A2 Unit 5 — Per-Concept Mastery Scoring (Progress drill-down) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Goal:** A **thin** per-concept mastery score (AD3) — now that ~93% of lessons are tagged
to the concept taxonomy, accrue per-`(user, concept, market)` accuracy from quiz attempts
and surface it as a **drill-down under each topic** on the Progress page (and a sharper
signal for Revise later). This is the granular layer *under* the topic-level evidence;
distinct from the diagnostic checkpoints.

**Architecture:** A `ConceptMastery` table mirrors the existing `TopicMastery`
(cumulative `attempts`/`correct`/`mastery_score`), keyed by `(user_id, concept_id,
market_code)`. A `record_concept_attempt(...)` upsert is called at the **same lesson-
completion seam** that already calls `update_mastery_on_completion` (`content.py:408`) —
but ONLY when the completed lesson has a `concept_id`. `get_strengths_and_gaps` is extended
so each `TopicStrength` carries its attempted concepts (name/status/score); the Progress
page renders them as an expandable per-topic drill-down.

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React 18 · pytest · vitest.

## Global Constraints

- **Thin + consistent with `TopicMastery`:** cumulative `attempts`/`correct`/`mastery_score`
  (same classification thresholds as topics: `_STRONG_THRESHOLD`). Windowed/decayed scoring
  is a later refinement — NOT in this unit (note it, don't build it).
- **Only tagged lessons count:** `record_concept_attempt` is called only when the lesson's
  `concept_id` is set; an untagged lesson updates `TopicMastery` exactly as today and writes
  no concept row. No behaviour change for untagged content.
- **No new reward/answer-leak surface:** this only reads quiz correctness already computed at
  the completion seam; it touches no XP/streak/coins and no diagnostic path.
- All endpoints stay `get_current_user`-gated. WCAG 2.2 AA on the Progress drill-down
  (vitest-axe), ≥44px, i18n keys, no `as any`.
- Backend `ruff` clean; frontend `tsc`/`lint`(0)/`build`/vitest green. Commit to branch
  `concept-mastery`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`. Native-visible (Progress
  page) → ship runs `cap sync` (or defers per operator).
- **DB migration:** one additive table. Check `alembic heads` (expected `f9a0b1c2d3e4`),
  chain from it, VERIFY a unique revision id (grep first). Ship asks the operator about a snapshot.

## File Structure
- `backend/app/models/skill_profile.py` — `ConceptMastery` (new, alongside `TopicMastery`) + migration (new).
- `backend/app/services/skill_profile_service.py` — `record_concept_attempt` (modify).
- `backend/app/routers/content.py` — call it at the completion seam when concept_id set (modify).
- `backend/app/services/gap_detection_service.py` + `backend/app/schemas/ai.py` — per-concept breakdown on `TopicStrength` (modify).
- `frontend/src/pages/child/StrengthsGaps.tsx` (+ api/test) — per-topic concept drill-down (modify).
- Tests alongside.

---

### Task 1: `ConceptMastery` model + `record_concept_attempt`

Model `ConceptMastery` (mirror `TopicMastery`): `user_id` (FK), `concept_id` (FK→concepts.id), `market_code` (str8), `attempts` (int default 0), `correct` (int default 0), `mastery_score` (float default 0), `last_attempt_at` (tz dt|None). Composite PK `(user_id, concept_id, market_code)` (or surrogate id + unique constraint — match how `TopicMastery` keys itself).

- [ ] **Step 1 (test first):** `test_concept_mastery.py` — `record_concept_attempt(session, user_id, concept_id, market, correct=True)` upserts a row with attempts=1/correct=1/score=1.0; a second correct → 2/2/1.0; a wrong → 3/2/0.667; `last_attempt_at` set. Run → fail.
- [ ] **Step 2:** model + migration (additive `create_table`; verify unique rev id, chain `f9a0b1c2d3e4`, clean downgrade, single head, `alembic upgrade head`) + `record_concept_attempt` (upsert mirroring `update_mastery_on_completion`'s recompute).
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 2: Wire into the lesson-completion seam

- [ ] **Step 1 (test first):** in the content/completion tests — completing a **quiz lesson that has a `concept_id`** records a `ConceptMastery` attempt for that concept (correct/incorrect reflected); completing a lesson with **no `concept_id`** records NO concept row (and TopicMastery still updates as before). Run → fail.
- [ ] **Step 2:** at `backend/app/routers/content.py` (~line 408, where `update_mastery_on_completion` is called for quiz lessons), also call `record_concept_attempt(session, user.id, lesson.concept_id, market, correct)` **when `lesson.concept_id` is not None** — using the same `correct` signal + the child's market. Don't change the untagged path.
- [ ] **Step 3:** tests green (incl. no-regression on untagged completion); `ruff` clean.

### Task 3: Expose per-concept breakdown in strengths

- [ ] **Step 1 (test first):** extend the strengths tests — `get_strengths_and_gaps` returns, for each `TopicStrength`, a `concepts: [ConceptStrength{concept_id, slug, name, mastery_score, status, attempts}]` list of the user's **attempted** concepts under that topic (status via the same `_classify` thresholds), sorted needs-practice-first; topics with no attempted concepts → empty list. Run → fail.
- [ ] **Step 2:** add `ConceptStrength` to `schemas/ai.py`; in `gap_detection_service`, load the user's `ConceptMastery` rows joined to `Concept` (name/slug/topic), group under each topic, attach to `TopicStrength.concepts`. Keep the existing topic fields unchanged (additive).
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 4: Progress page drill-down

- [ ] **Step 1 (test first):** `StrengthsGaps` test (mock the api) — a topic with concepts shows an **expandable** "concepts" section listing each concept name + a status pill (strong/needs-practice/new); a topic with no concepts shows no drill-down; vitest-axe clean; ≥44px on the expander. Run → fail.
- [ ] **Step 2:** extend `StrengthsGaps.tsx` (+ the strengths api type) to render the per-topic concept list (collapsible, reusing the existing status-pill/card styling); i18n keys; no `as any`.
- [ ] **Step 3:** `tsc`/`lint`/vitest(+axe)/`build` green.

### Task 5: Verify + ship
- [ ] Backend `ruff` + full `pytest`; frontend gates; single alembic head. Reason end-to-end: a child completes tagged quizzes → ConceptMastery accrues → Progress shows per-concept strengths under each topic.
- [ ] Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. **Ask the operator about a prod snapshot before the migration.** SDD finishing flow → opus whole-branch review → green CI → Railway (backend) + manual Vercel (web). Native-visible → `cap sync` (operator batches the build).

## Out of scope (later)
- Windowed/decayed concept scoring (this is cumulative, thin).
- Wiring concept attempts into the Revise/SR answer path (the lesson-completion seam is the primary signal for v1; add Revise later if the signal is too sparse).
- Smarter Revise targeting off concept scores.
- **Unit 6 / A4** — parent-report growth block + public evidence page.
