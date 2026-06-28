# Concept Taxonomy (A1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. TDD: failing test → minimal code → commit.

**Goal:** Add a normalized **`Concept`** layer between the 9 existing topics and lessons, so every lesson/quiz/Revise card/mission can be tagged to a finite, auditable concept. This is the unblocker for A2 (pre/post checks) and A4 (per-concept report drill-down). Today "concepts" are free-text strings derived per lesson (`_concept_of` returns the question text) and stored only on wrong answers — there is no taxonomy. This plan adds one **without breaking** the existing free-text path.

**Architecture:** New `Concept` table (`topic` FK to the 9 topics, `slug`, `name`, `blurb`, `difficulty_tier`, `order`), seeded with ~30–50 curated concepts (3–6 per topic). `Lesson.concept_id` + `WeakConcept.concept_id` nullable FKs (additive). The LLM content generator emits a `concept_slug` that a mapper resolves to a `concept_id` (unmapped → `NULL` + admin flag, lesson still publishes). `_concept_of()` prefers the linked concept name, else the legacy free-text. A thin admin Concepts page lists/edits the taxonomy and reassigns a lesson's concept. Existing free-text `WeakConcept.concept` strings keep working; a best-effort backfill maps the common ones.

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React 18 · TanStack Query 5 · pytest · vitest.

## Global Constraints

- **Additive + back-compat only.** Nothing that reads `WeakConcept.concept` (free-text) may break. `concept_id` is nullable everywhere; a `NULL` concept is always valid (un-mapped content). The Revise/SR/gap-detection behaviour is byte-unchanged when `concept_id` is `NULL`.
- **Taxonomy is authored, finite, auditable.** Concepts are seeded + admin-curated — NEVER created implicitly from LLM output. The mapper only *links to* existing concepts; it never inserts new ones.
- **Reuse the 9 topics.** `Concept.topic` is constrained to the existing topic set (`stocks, savings, real_estate, budgeting, risk, crypto, taxes, debt, entrepreneurship`); do not introduce a parallel topic list.
- **No `as any`** (CI `npm run lint` = `eslint .`, error-level). Backend `ruff check .` clean over the whole dir.
- **DB migration:** adds one table + two nullable columns to prod tables. Railway runs `alembic upgrade head` on deploy. **The ship task asks the operator whether to snapshot prod first** (standing rule). Current head `f8a9b0c1d2e3` — chain from it.
- **Commits:** straight to `main` (beta flow); body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Backend commands use the shared venv `/Users/leeashmore/Local Repo/.venv`.

## File Structure

- `backend/alembic/versions/<rev>_concept_taxonomy.py` — migration (new).
- `backend/app/models/concept.py` — `Concept` model (new).
- `backend/app/models/content.py` — `Lesson.concept_id` FK + relationship (modify).
- `backend/app/models/skill_profile.py` — `WeakConcept.concept_id` FK (modify).
- `backend/app/services/concept_seed.py` — the curated ~30–50 seed + idempotent seeder (new).
- `backend/app/services/concept_mapper.py` — `resolve_concept_slug(slug, topic) -> concept_id | None` (new).
- `backend/app/services/revise_service.py` — `_concept_of()` taxonomy-aware (modify).
- `backend/app/services/ai_content_service.py` — generator emits + maps `concept_slug` (modify).
- `backend/app/routers/admin_content.py` — admin Concepts CRUD + lesson-reassign (modify).
- `backend/app/schemas/concept.py` — `ConceptOut`/`ConceptIn` (new).
- `frontend/src/api/admin.ts` — concept API client fns (modify).
- `frontend/src/pages/admin/ConceptsAdmin.tsx` (+ route + nav entry) — admin page (new).
- Tests alongside each (`backend/tests/test_concept_*.py`, `frontend/tests/unit/ConceptsAdmin.test.tsx`).

---

### Task 1: `Concept` model + migration (table + nullable FKs)

**Files:** Create `backend/app/models/concept.py`, `backend/alembic/versions/<rev>_concept_taxonomy.py`; Modify `backend/app/models/content.py`, `backend/app/models/skill_profile.py`.

**Interfaces:**
- Produces: `Concept{id, topic str(30), slug str(60) unique, name str(120), blurb str(400)|None, difficulty_tier int (1–3), order_index int, created_at}`; `Lesson.concept_id UUID|None FK→concepts.id`; `WeakConcept.concept_id UUID|None FK→concepts.id`.

- [ ] **Step 1 (test first):** `backend/tests/test_concept_model.py` — assert a `Concept` can be created, `slug` is unique, and a `Lesson`/`WeakConcept` accept a nullable `concept_id`. Run → fails (no model).
- [ ] **Step 2:** Create `Concept` (mirror the column style in `skill_profile.py`). Add `concept_id` nullable FK + relationship to `Lesson` (`content.py`) and `WeakConcept` (`skill_profile.py`). Keep the existing `WeakConcept.concept` free-text column untouched.
- [ ] **Step 3:** `cd backend && alembic heads` → confirm `f8a9b0c1d2e3`. Hand-write the migration chained `down_revision = "f8a9b0c1d2e3"`: `create_table("concepts", …)` + unique index on `slug` + `add_column` nullable `concept_id` on `lessons` and `weak_concepts` with FKs. Clean `downgrade()` (drop FKs → columns → table).
- [ ] **Step 4:** `alembic upgrade head` locally; tests green. `ruff check .` clean.

### Task 2: Seed the taxonomy (~30–50 concepts)

**Files:** Create `backend/app/services/concept_seed.py`; wire into the startup seed path (where `seed_markets`/cosmetics seed run).

**Interfaces:** Produces `seed_concepts(session)` — idempotent upsert by `slug`.

- [ ] **Step 1 (test first):** `test_concept_seed.py` — running the seed twice yields the same count, each of the 9 topics has ≥3 concepts, and `difficulty_tier ∈ {1,2,3}`. Fails.
- [ ] **Step 2:** Author the curated list — 3–6 concepts per topic (e.g. `savings`: `why-save`, `emergency-fund`, `interest-basics`, `compound-interest`, `saving-goals`; `risk`: `risk-vs-reward`, `diversification`, `volatility`, `time-horizon`; etc.). Slugs stable + kebab-case; names kid-friendly; `difficulty_tier` set per the existing tier-1/2/3 depth model. Idempotent upsert by `slug` (update name/blurb/tier/order, never duplicate).
- [ ] **Step 3:** Call from the startup seeding sequence (after topics exist, alongside the other seeders). Tests green; `ruff` clean.

### Task 3: `_concept_of()` taxonomy-aware (back-compat)

**Files:** Modify `backend/app/services/revise_service.py`.

**Interfaces:** `_concept_of(lesson)` returns `lesson.concept.name` when `concept_id` set, else the legacy `content.get("question")|title|prompt|"general"`.

- [ ] **Step 1 (test first):** extend `test_revise_service.py` — a lesson WITH a linked concept yields the concept name; a lesson WITHOUT one yields the legacy free-text (unchanged). Fails on the first assert.
- [ ] **Step 2:** Update `_concept_of` to prefer the relationship. Ensure the lesson's `concept` relationship is loaded where `_concept_of` is called (eager/selectin to avoid N+1 in session building). When recording a weak concept, also set `WeakConcept.concept_id` from `lesson.concept_id` when present (free-text `concept` still written for back-compat).
- [ ] **Step 3:** Full revise/SR suite green — behaviour identical for un-mapped lessons. `ruff` clean.

### Task 4: Generator emits + maps `concept_slug`

**Files:** Create `backend/app/services/concept_mapper.py`; Modify `backend/app/services/ai_content_service.py` (+ the market-content pipeline generation path).

**Interfaces:** `resolve_concept_slug(session, slug, topic) -> concept_id | None` — exact slug match within topic, then a normalized fuzzy match; no match → `None`. Generation sets `Lesson.concept_id` from the resolved slug; unmapped → `NULL` + a structured log line (`concept_unmapped topic=… slug=…`) for the admin queue.

- [ ] **Step 1 (test first):** `test_concept_mapper.py` — exact slug → id; close variant ("compound interest" vs `compound-interest`) → id; nonsense → `None`. The generator schema includes `concept_slug` and a generated lesson gets its `concept_id` set (mock the LLM). Fails.
- [ ] **Step 2:** Add `concept_slug` to the lesson-generation prompt/schema (the model picks from the topic's concept slugs — pass them in the prompt so it chooses from the real taxonomy, not invents). Map on persist via `resolve_concept_slug`. NEVER insert a concept from generator output (constraint).
- [ ] **Step 3:** Backend suite + the generation/pipeline tests green; `ruff` clean. (No regen of live content here — mapping applies going forward; Task 5 backfills history.)

### Task 5: Best-effort backfill of existing `WeakConcept` + published lessons

**Files:** a one-off, idempotent, cron/CLI-gated backfill (`POST /internal/concepts/backfill`, CSRF-exempt + cron-secret — follow the existing internal-endpoint + CSRF-allowlist pattern).

- [ ] **Step 1 (test first):** `test_concept_backfill.py` — a `WeakConcept` whose free-text matches a concept name/slug gets `concept_id` set; an unmatched one stays `NULL`; re-running changes nothing. Fails.
- [ ] **Step 2:** Implement the matcher (reuse `concept_mapper`) over `WeakConcept` rows and published `Lesson` rows with `concept_id IS NULL`. Add the route to `_DEFAULT_EXEMPT_PATHS` in `core/csrf.py` (standing gotcha) + a `workflow_dispatch` workflow. Verify an unauth curl returns 401/503, NOT 403.
- [ ] **Step 3:** Tests green; `ruff` clean. (Operator runs it once post-deploy.)

### Task 6: Admin Concepts page (list / edit / reassign)

**Files:** Modify `backend/app/routers/admin_content.py`, `frontend/src/api/admin.ts`; Create `backend/app/schemas/concept.py`, `frontend/src/pages/admin/ConceptsAdmin.tsx` (+ route + admin-nav entry).

**Interfaces:** `GET /admin/concepts` (grouped by topic, with `lesson_count` + `unmapped_count`), `POST /admin/concepts`, `PATCH /admin/concepts/{id}`, `PATCH /admin/lessons/{id}/concept` (reassign). All `get_current_admin`-gated.

- [ ] **Step 1 (test first):** backend `test_concepts_admin.py` — unauth 401/403; admin can create/edit a concept and reassign a lesson's concept; `lesson_count` reflects links. Frontend `ConceptsAdmin.test.tsx` — renders topic groups, shows unmapped count, edit submits (vitest-axe clean). Fail.
- [ ] **Step 2:** Implement the endpoints (reuse the admin sub-router + dep) and the page (match the existing admin form/token style; `FormSection` primitive). Surface the "unmapped lessons" count per topic so the operator can clear the Task-4 queue.
- [ ] **Step 3:** Backend (`ruff` + admin suite) + frontend (`tsc` + `lint` + targeted vitest + `build`) green.

### Task 7: Verification + ship

- [ ] **Step 1:** Backend `ruff check .` + full `pytest` green. Frontend `npm run -s typecheck && npm run -s lint && npm run -s test && npm run -s build` green (incl. vitest-axe on the new page).
- [ ] **Step 2:** `alembic heads` == 1 (single head). Confirm un-mapped path is behaviour-identical (a spot test: a lesson with `concept_id=NULL` flows through Revise/gap-detection exactly as before).
- [ ] **Step 3:** Update `MASTER-BACKLOG.md` (move A1 to a "Live"/in-progress note) + this plan's checkboxes + `PROGRESS.md`. **Ask the operator whether to snapshot prod before the migration.** Commit to `main`; green CI → Railway backend + manual Vercel web (`vercel --prod` then `vercel alias set <hash> app.investikid.ai`). `npx cap sync ios` if any native-visible change (admin page is web-only — no native rebuild needed).

---

## Out of scope (later units, separate plans)

- **A2** diagnostic engine + `MasteryCheckpoint` + the generate-then-expert-review calibrated item bank (with `difficulty_tier` + expert sign-off gate + beta item-distribution monitoring per the OD4 decision).
- **A3** onboarding placement step + baseline-on-first-touch.
- **A4** parent-report growth block + child per-concept drill-down.
- Per-concept rolling mastery *scoring* (this plan adds the link + taxonomy; the score column/derivation lands with A2/A4).
