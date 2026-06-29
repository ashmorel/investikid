# A2 Unit 1 — Calibrated Diagnostic Item Bank — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD: failing test → minimal code → commit. Checkbox steps.

**Goal:** The calibrated **diagnostic item bank** — a `DiagnosticItem` model, an LLM
generation pass (per market/topic/difficulty, grounded in the concept taxonomy,
moderated), and an `/admin/diagnostic-items` **expert-review** surface so only
operator-approved items are ever served. This is the unblocker for the whole A2
diagnostic engine (Unit 2 consumes only `approved` items). Spec:
`docs/superpowers/specs/2026-06-29-mastery-measurement-a2-a3-design.md` (AD1–AD4 locked).

**Architecture:** A standalone `diagnostic_items` table (NOT a flag on `Lesson` — these
are a measurement instrument, never award XP, own approval lifecycle). An admin-triggered
generator produces `status=draft` candidates per (market, topic, difficulty_tier) using
the existing LLM infra + moderation, grounded in the topic's `Concept` rows. An admin page
previews/edits/approves/rejects/retires; only `approved` items reach Unit 2. Calibration
columns (`times_shown`/`times_correct`) ship here but accrue in Unit 2.

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React 18 · the LLM client/json/
moderation infra · pytest · vitest.

## Global Constraints

- **Approved-only is sacred:** Unit 2 (later) will serve ONLY `status=approved` items. The
  generator lands `draft`; nothing auto-approves. `approved_by`/`approved_at` recorded on
  approval.
- **Never part of the lesson track:** diagnostic items never award XP/streak/coins, never
  appear in modules/levels, never go through `lesson_approval_service`.
- **Grounded + safe generation:** reuse `get_llm_client` (tier configurable, default the
  standard/authoring tier per the generator's norm), `with_generation_framing` (NOT the
  interactive guardrail), `llm_json` extraction, and `moderate_output` (kids' app). Items
  are grounded in the topic's `Concept` rows (slug/name/blurb) and written in market English
  (American for US/CA — reuse the existing `_market_english` rule from the content pipeline).
- **Market scope:** every item carries `market_code`; generation + listing are market-scoped.
- All admin endpoints `get_current_admin`-gated. WCAG 2.2 AA on the new page (vitest-axe),
  ≥44px targets, i18n keys (no literal strings), no `as any`.
- Backend `ruff` clean; frontend `tsc`/`lint`(0)/`build`/vitest green. Commit to branch
  `diagnostic-item-bank`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`.
- **DB migration:** one additive table. Check `alembic heads` (expected `c8d9e0f1a2b3`),
  chain from it, pick a VERIFIED-unused revision id (grep the versions dir first — a
  duplicate id already caused a CycleDetected once on this project). The ship task asks the
  operator about a prod snapshot.

## File Structure
- `backend/app/models/diagnostic.py` — `DiagnosticItem` (new).
- `backend/alembic/versions/<rev>_diagnostic_items.py` — migration (new).
- `backend/app/schemas/diagnostic.py` — `DiagnosticItemOut`/`In`/`Patch`, generation req (new).
- `backend/app/services/diagnostic_item_service.py` — generation + CRUD/lifecycle (new).
- `backend/app/routers/admin_diagnostic.py` — admin endpoints (new), mounted under `/admin`.
- `frontend/src/api/adminDiagnostic.ts` + `frontend/src/components/admin/DiagnosticItemsAdmin.tsx` (+ route + nav) (new).
- Tests alongside.

---

### Task 1: `DiagnosticItem` model + migration

**Files:** `backend/app/models/diagnostic.py`, migration; register in `app/models/__init__.py`.

**Fields:** `id` (UUID pk), `market_code` (str, indexed), `topic` (str 30), `concept_id`
(UUID|None FK→concepts.id, nullable, `ondelete=SET NULL`), `difficulty_tier` (int 1–3),
`question` (text), `choices` (JSON list[str]), `answer_index` (int), `explanation` (text),
`status` (str: `draft`/`approved`/`retired`, default `draft`, indexed), `source` (str:
`generated`/`authored`), `times_shown` (int default 0), `times_correct` (int default 0),
`approved_by` (UUID|None), `approved_at` (datetime|None), `created_at`.

- [ ] **Step 1 (test first):** `test_diagnostic_item_model.py` — create an item; defaults
  (`status="draft"`, `times_shown=0`); nullable `concept_id`/`approved_*`; status accepts
  the three values. Run → fail.
- [ ] **Step 2:** Model (mirror `models/concept.py` style) + register in `__init__.py`.
- [ ] **Step 3:** `alembic heads` → confirm `c8d9e0f1a2b3`; grep-verify a fresh revision
  id is unused; hand-write the additive `create_table` migration + indexes on
  `(market_code, topic, status)`; clean `downgrade`. `alembic upgrade head`; single head.
- [ ] **Step 4:** model tests green; `ruff` clean.

### Task 2: Generation service

**Files:** `backend/app/services/diagnostic_item_service.py`, `schemas/diagnostic.py`.

**Interface:** `async def generate_items(session, *, market_code, topic, difficulty_tier,
count, tier="standard") -> list[DiagnosticItem]` — fetches the topic's `Concept` rows,
builds a `with_generation_framing` prompt for `count` MCQs at that difficulty in market
English grounded in those concepts, calls the LLM, extracts via `llm_json`
(object-wrapped-array safe — use `extract_json_list` per the known gotcha), validates each
(4 choices, valid answer_index, non-empty), runs `moderate_output` on each, persists
moderation-safe ones as `status="draft", source="generated"` (tagging `concept_id` when the
model ties an item to a concept; else NULL). Returns persisted drafts. Best-effort per item;
never raise into the caller for one bad item.

- [ ] **Step 1 (test first):** `test_diagnostic_generate.py` (mock the LLM + moderation):
  a valid generated MCQ persists as a `draft`; a moderation-failing item is dropped; a
  malformed item (bad answer_index / <4 choices) is dropped; items carry the requested
  market/topic/difficulty. Run → fail.
- [ ] **Step 2:** Implement. Reuse `get_llm_client`, `with_generation_framing`,
  `extract_json_list` (`services/llm_json.py`), `moderate_output`, and the `_market_english`
  rule. Ground the prompt in the topic's concepts.
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 3: Admin review API + lifecycle

**Files:** `backend/app/routers/admin_diagnostic.py` (mounted under `/admin` in the
aggregator), `schemas/diagnostic.py`.

**Endpoints (all `get_current_admin`):**
- `POST /admin/diagnostic-items/generate` — body `{market_code, topic, difficulty_tier, count}` → runs `generate_items`, returns the drafts. LLM-rate-limited.
- `GET /admin/diagnostic-items?market_code=&topic=&status=` — list (filterable), incl. a coverage summary (approved count per topic×difficulty vs the ≥2 target).
- `PATCH /admin/diagnostic-items/{id}` — edit question/choices/answer_index/explanation/difficulty/concept (only while `draft`).
- `POST /admin/diagnostic-items/{id}/approve` — `draft → approved`, set `approved_by`/`approved_at`.
- `POST /admin/diagnostic-items/{id}/reject` — `draft → retired` (kept for audit, never served).
- `POST /admin/diagnostic-items/{id}/retire` — `approved → retired` (e.g. a non-discriminating item).

- [ ] **Step 1 (test first):** `test_admin_diagnostic.py` — unauth → 401/403; generate
  returns drafts; approve sets status+approver; an `approved` item can't be edited (409/422);
  reject/retire transition correctly; the coverage summary reflects approved counts. Use
  `admin_client`/`db_session`; mock the generator's LLM. Run → fail.
- [ ] **Step 2:** Implement; mount the sub-router under `/admin` (carries the existing
  `get_current_admin` dep). LLM endpoint rate-limited like the other generation routes.
- [ ] **Step 3:** backend `ruff` + suite green.

### Task 4: Admin page

**Files:** `frontend/src/api/adminDiagnostic.ts`, `frontend/src/components/admin/DiagnosticItemsAdmin.tsx` (+ lazy route in `App.tsx` + nav entry in `AdminSidebar.tsx`), i18n `admin.json`.

- [ ] **Step 1 (test first):** `DiagnosticItemsAdmin.test.tsx` — renders items grouped by
  topic×difficulty with status; a "Generate N" control calls the API; approve/reject/edit
  call their mutations; shows the coverage-vs-target summary; vitest-axe clean. Mock the API.
  Run → fail.
- [ ] **Step 2:** Build the page (mirror `CollectablesAdmin`/`ConceptsAdmin` + `FormSection`
  style): market+topic filters, a generate control, per-item preview (question/choices/answer
  highlighted/explanation), inline edit (draft only), approve/reject/retire actions (≥44px),
  the coverage summary against the ≥2-per-cell target. i18n keys; no `as any`.
- [ ] **Step 3:** `tsc`/`lint`/targeted vitest(+axe)/`build` green.

### Task 5: Verify + ship
- [ ] Backend `ruff` + full `pytest`; frontend `typecheck`/`lint`/`test`/`build`. Single
  alembic head. Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. **Ask the operator about a
  prod snapshot before the migration.** Commit/merge per the SDD finishing flow; green CI →
  Railway + manual Vercel. Admin page is web-only (no native rebuild).
- [ ] **Operator (post-ship, not code):** run generation for the 3 EN markets × 9 topics ×
  3 difficulties, then approve ≥2 per cell on `/admin/diagnostic-items` — the expert-review
  gate that unblocks Unit 2.

## Out of scope (later units)
- `MasteryCheckpoint` + the diagnostic engine + scoring (Unit 2).
- Onboarding placement / A3 (Unit 3). Re-check trigger (Unit 4). Per-concept scoring (Unit 5).
- Calibration *accrual* (`times_shown`/`times_correct` columns exist here; Unit 2 increments them).
