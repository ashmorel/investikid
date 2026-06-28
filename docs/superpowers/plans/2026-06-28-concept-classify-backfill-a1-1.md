# A1.1 — LLM Concept-Classification Backfill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD: failing test → minimal code → commit. Steps use checkbox syntax.

**Why:** The Task-5 string-matching backfill matched **0 of 1260** existing lessons in prod — because a lesson's free-text "concept" is a full question/title sentence, while the taxonomy is short concept slugs/names. String matching can't bridge that. This plan tags existing untagged lessons by **LLM classification** into their topic's taxonomy (exactly what the generator does for NEW lessons, applied retroactively), validated through `resolve_concept_slug` so the model can never invent a concept.

**Architecture:** A new `concept_classify_service` queries published lessons with `concept_id IS NULL`, and for each asks the LLM to pick the single best `concept_slug` from that lesson's **topic candidate list** (or abstain), validates the pick via `resolve_concept_slug`, and sets `Lesson.concept_id` (or leaves NULL + logs). Bounded per run (`limit`) and idempotent (the `IS NULL` filter makes it resumable — run repeatedly until `lessons_seen == 0`). Exposed as a cron-gated internal endpoint + a `workflow_dispatch` workflow.

**Tech Stack:** FastAPI · SQLAlchemy async · the existing LLM client/json/moderation infra · pytest.

## Global Constraints

- **The model can NEVER create a concept.** It only picks a slug from the candidate list; the pick is validated via `resolve_concept_slug(session, slug, topic)` → only a real concept_id is ever written. An invalid/hallucinated slug or an abstain → `concept_id` stays NULL + a structured log line.
- **Idempotent + bounded + resumable.** Query filters `Lesson.concept_id IS NULL` AND `Module.published IS TRUE` (matches the admin `unmapped_count` scope). Each run processes at most `limit` lessons. Re-running never re-classifies an already-tagged lesson and never overwrites a set `concept_id`.
- **Best-effort:** per-lesson `try/except` so one LLM/parse failure can't abort the batch; a failed lesson stays NULL and is retried on a later run.
- **Reuse, don't duplicate:** reuse `_fetch_concept_slugs` (or a richer concept-candidate fetch incl. name/blurb) from `admin_content_generation_service`, the LLM client + `llm_json` extraction, `with_generation_framing` (lesson content is untrusted input → injection-resistant framing), and `resolve_concept_slug`. Do NOT re-implement slug matching.
- **Cost-aware:** use the cheap/lite model tier (per the model lineup), one call per lesson, bounded by `limit`. Log progress + a final count summary.
- **CSRF gotcha:** the new internal endpoint MUST be added to `_DEFAULT_EXEMPT_PATHS` in `core/csrf.py` (verify unauth → 401/503, NOT 403).
- Backend `ruff check .` clean. Commit to a feature branch `concept-classify-a1.1`; body ends exactly `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Backend cmds use the venv `/Users/leeashmore/Local Repo/.venv`. Do NOT read/modify any `.env`. No DB migration (additive behaviour only — writes existing nullable `concept_id`).

## File Structure

- `backend/app/services/concept_classify_service.py` — `classify_untagged_lessons(session, *, limit)` (new).
- `backend/app/routers/internal.py` — `POST /internal/concepts/classify?limit=` (modify).
- `backend/app/core/csrf.py` — add the path to `_DEFAULT_EXEMPT_PATHS` (modify).
- `.github/workflows/concept-classify.yml` — `workflow_dispatch` runner, looping until drained or a bounded number of batches (new; mirror `concept-backfill.yml` style).
- `backend/tests/test_concept_classify.py` — tests (new).

---

### Task 1: Classification service + endpoint + CSRF allowlist + tests

**Files:** Create `concept_classify_service.py`, `test_concept_classify.py`; modify `internal.py`, `core/csrf.py`.

**Interfaces:**
- `async def classify_untagged_lessons(session, *, limit: int = 200) -> dict[str, int]` → `{"lessons_seen", "lessons_tagged", "lessons_unmatched", "lessons_errored"}`.
- `POST /internal/concepts/classify?limit=N` (cron-secret auth like the other internal endpoints; default limit sensible, capped).

- [ ] **Step 1 (tests first):** in `test_concept_classify.py`, with the LLM mocked (look at how existing generation tests mock the LLM client — do NOT hit a real LLM):
  - a published untagged lesson whose mocked LLM returns a **valid** candidate slug → `concept_id` is set to that concept; counted in `lessons_tagged`.
  - mocked LLM returns a slug **not in the taxonomy** (hallucination) → `concept_id` stays NULL (resolve rejects); counted in `lessons_unmatched`.
  - mocked LLM **abstains** (returns null/empty) → NULL; `lessons_unmatched`.
  - an **already-tagged** lesson is excluded from the query (idempotent) and its concept_id is untouched on re-run.
  - an **unpublished** module's lesson is NOT processed (scope = published only).
  - `limit` bounds the number processed.
  - endpoint: unauth/no-secret POST → 401/503 (NOT 403 → proves CSRF exemption); correct secret → 200 with the counts.
  Run → fails.
- [ ] **Step 2:** Implement `classify_untagged_lessons`:
  - Query `Lesson` join `Module` where `Lesson.concept_id.is_(None)` AND `Module.published.is_(True)`, `limit`-bounded, ordered deterministically (e.g. by id) so repeated runs make forward progress.
  - Per lesson: get candidate concepts for `module.topic` (reuse `_fetch_concept_slugs`; if richer context helps the model, also pass each concept's `name`/`blurb` — fetch from the `Concept` table for that topic). Build a classification prompt wrapped in `with_generation_framing` that gives the lesson's text (reuse the same source the legacy path uses: `content_json` question/title/prompt, plus any teach-card body) + the candidate list, instructing the model to return the single best `concept_slug` from the list, or null if none clearly fits. Call the lite-tier LLM; extract the slug with `llm_json`. Validate via `resolve_concept_slug(session, slug, module.topic)`; set `Lesson.concept_id` only on a real match. Unmatched/abstain → leave NULL + `logger.info("concept_classify_unmatched lesson=%s topic=%s pick=%s", ...)`. Wrap each lesson in try/except → on error, increment `lessons_errored`, continue.
  - Commit once at the end (endpoint commits); return the counts.
- [ ] **Step 3:** Add `POST /internal/concepts/classify` to `internal.py` (cron-secret guard, identical to `/internal/concepts/backfill`; read `limit` query param with a sane default + cap). Add `"/internal/concepts/classify"` to `_DEFAULT_EXEMPT_PATHS` in `core/csrf.py`.
- [ ] **Step 4:** Tests green; `ruff check .` clean.

### Task 2: workflow_dispatch runner + verify

**Files:** Create `.github/workflows/concept-classify.yml`.

- [ ] **Step 1:** Mirror `.github/workflows/concept-backfill.yml`, but **loop**: POST `/internal/concepts/classify?limit=200` repeatedly (bounded, e.g. up to 12 iterations or until a run reports `lessons_seen == 0`) so one dispatch drains the backlog without a single oversized request. Use `${{ secrets.CRON_SECRET }}` + `${{ vars.BACKEND_URL }}` exactly as the backfill workflow; parse the JSON `lessons_seen` to decide when to stop (jq or a grep). Keep `permissions: contents: read` + a `timeout-minutes`.
- [ ] **Step 2:** `ruff` clean; confirm the workflow YAML is valid (`gh workflow list` shows it after push). Operator/controller triggers it post-merge and confirms `lessons_tagged > 0` against prod (the real accuracy check).

---

## Out of scope

- WeakConcept LLM classification (only 15 rows; once lessons are tagged, NEW weak concepts inherit `concept_id` from the lesson per Task 3). Leave the historical 15 as-is.
- Re-generating or editing lesson content. This only sets the nullable `concept_id`.
- Any change to the generator, `_concept_of`, the model, the admin page, or the string backfill (kept as-is).
