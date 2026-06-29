# A1.2 — Decouple concept matching from module.topic (global slug match)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Why:** A1 keyed the `Concept` taxonomy to the 9 legacy `ModuleTopic` values, but the live **regenerated** GB/US/HK curriculum uses **free-form slugified pipeline topics** (`proposal_service._slugify_topic`; `content.py:39` says module topic is NOT constrained to ModuleTopic). So every "fetch concepts for this lesson's `module.topic`" returns empty → the LLM classifier **skipped all 1260 prod lessons** and the string backfill matched 0, and **new generated content also fails to tag** (the generator scopes candidate slugs by `module.topic` too). `Concept.slug` is **globally unique** (DB constraint), so matching does not need the topic axis at all.

**Fix:** Match concepts **globally by unique slug**, independent of `module.topic`. Present the LLM the full 47-concept taxonomy (grouped by concept-topic only for prompt readability); resolve any pick by global unique slug. Apply to the classifier, the generator's `concept_slug` path, and the draft-approval resolve. `Concept.topic` stays as organizational metadata (Progress page grouping), never as a matching key. Fix the admin "unmapped" count, which currently joins `module.topic == concept.topic` and so misreports.

**Tech Stack:** FastAPI · SQLAlchemy async · React · the existing LLM infra · pytest · vitest.

## Global Constraints

- **Slug is the source of truth.** Every write to a lesson's `concept_id` resolves through a slug lookup against the whole `concepts` table (slug is UNIQUE). The model can still never invent a concept — an unknown slug resolves to None.
- **No data migration.** Behaviour change only.
- **Back-compat:** un-tagged lessons still behave identically elsewhere; `_concept_of` (Task 3) unchanged. The `concept_classified_at` one-attempt marker stays.
- **Re-attempt the already-skipped lessons:** because A1.1 stamped `concept_classified_at` on all 1260 when they skipped, the fix MUST also provide a way to clear that marker so the corrected classifier can retry them (see Task 1, step 5). Otherwise the monotonic-drain marker permanently locks out the lessons the broken version skipped.
- Backend `ruff` clean; frontend `tsc`/`lint`(0 err)/`build`/vitest(+axe) green. Commit to branch `concept-global-match-a1.2`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`.

## File Structure
- `backend/app/services/concept_mapper.py` — add a global slug resolver (modify).
- `backend/app/services/concept_classify_service.py` — full-taxonomy candidates + global resolve; drop the topic skip (modify).
- `backend/app/services/admin_content_generation_service.py` — generation candidate slugs = full taxonomy (modify).
- `backend/app/services/lesson_approval_service.py` — resolve emitted `concept_slug` globally (modify).
- `backend/app/routers/admin_content.py` — `unmapped` count = published lessons with `concept_id IS NULL` (global), not topic-joined (modify).
- `backend/app/routers/internal.py` — add a guarded "reset classification markers" action so the corrected classifier can retry (modify).
- `frontend/src/components/admin/ConceptsAdmin.tsx` (+ test) — show a single global unmapped-lessons figure (modify).
- Tests across the above.

---

### Task 1: Backend — global slug matching for classify + generate + approve (+ marker reset)

**Files:** `concept_mapper.py`, `concept_classify_service.py`, `admin_content_generation_service.py`, `lesson_approval_service.py`, `internal.py`; tests.

- [ ] **Step 1 (tests first):**
  - `concept_mapper`: a global resolver returns the concept_id for any seeded slug regardless of topic; returns None for an unknown slug. (Slug is globally unique, so no topic needed.)
  - `concept_classify_service`: with the LLM mocked, a lesson whose module.topic is a **free-form non-taxonomy string** (e.g. `"growing-your-money"`) is STILL classified (candidates = full taxonomy) and, on a valid pick, `concept_id` is set. The old "no taxonomy for topic" skip no longer fires for a real (non-empty) taxonomy.
  - `lesson_approval_service`: an approved draft whose `concept_slug` is valid resolves globally and sets `concept_id` even when the module topic is free-form.
  - generator: `_generate_one`/the native pipeline passes the FULL taxonomy slugs (not topic-scoped) into the prompt.
  - Run → fails.
- [ ] **Step 2:** In `concept_mapper.py`, add `async def resolve_slug_global(session, slug) -> UUID | None` (exact match on the unique `slug`, plus the existing normalized fuzzy on slug/name across ALL concepts). Keep the existing topic-scoped function or have it delegate; update callers to the global one.
- [ ] **Step 3:** In `concept_classify_service.py`: replace `_fetch_concepts_for_topic(topic)` with a `_fetch_all_concepts(session)` (cached once per run) returning all concepts (include topic in each dict so the prompt can group them). Build the candidate list from the full taxonomy; drop the per-topic skip (the only remaining skips are no-text and the genuine empty-taxonomy case). Resolve the pick with `resolve_slug_global`. The published-only + `concept_classified_at IS NULL` + limit + idempotency + best-effort all stay.
- [ ] **Step 4:** In `admin_content_generation_service.py`: the generation prompt's candidate slugs = the full taxonomy (a `_fetch_all_concept_slugs(session)` or reuse). In `lesson_approval_service.py`: resolve the draft's `concept_slug` via `resolve_slug_global`.
- [ ] **Step 5:** In `internal.py`, add a guarded action to **reset the classification markers** so the corrected classifier can retry the lessons the broken version skipped — e.g. `POST /internal/concepts/classify/reset` (cron-secret, CSRF-exempt — add to `_DEFAULT_EXEMPT_PATHS`) that sets `concept_classified_at = NULL` for lessons where `concept_id IS NULL` (only the still-untagged ones; never un-mark a tagged lesson). Returns the reset count. Test the auth + CSRF-exempt (401/503 not 403) + that it only nulls untagged rows.
- [ ] **Step 6:** Backend `ruff` clean; the new + existing classify/generation/approval suites green.

### Task 2: Admin unmapped count = global + frontend

**Files:** `admin_content.py`, `frontend ConceptsAdmin.tsx` (+ tests).

- [ ] **Step 1 (tests first):** backend — `GET /admin/concepts` returns a single global `unmapped_lessons` = count of published lessons with `concept_id IS NULL` (NOT joined on topic). frontend — the page shows that one figure (not a per-topic badge that's now meaningless). Adjust/replace the existing per-topic `unmapped_count` tests. Run → fails.
- [ ] **Step 2:** Backend: replace per-topic `unmapped_count` with a top-level `unmapped_lessons` integer (published, concept_id IS NULL). Frontend: render it once (e.g. a header line "N lessons not yet tagged"); keep per-concept `lesson_count`. vitest + axe.
- [ ] **Step 3:** Gates green (backend ruff/tests; frontend tsc/lint/build/vitest).

---

## Verification (controller, post-merge)
- Deploy; `POST /internal/concepts/classify/reset` (clears the stale markers), then run the `concept-classify` workflow. Confirm `lessons_tagged > 0` (the real proof). Spot-check `/admin/concepts` shows the unmapped figure dropping.

## Out of scope
- Re-keying `Concept.topic` or reconciling the module-topic vocabulary (not needed once matching is global).
- `_concept_of`, the model, the streak/SR engine.
