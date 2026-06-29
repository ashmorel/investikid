# A2 Unit 1.1 — Diagnostic Item Answer Verifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Why:** Diagnostic item generation trusts the LLM's *self-declared* answer; moderation
checks safety and validation checks structure — **nothing verifies the answer is correct**.
A wrong answer in a *measurement* instrument mis-scores children and corrupts the baseline
evidence (a real example slipped through human review: a break-even question whose declared
answer was 20 when the correct answer is 10). This adds an **independent verifier**: a second,
stronger model solves each item **blind** (never seeing the declared answer) and we flag
mismatches + ambiguous items for human re-review — going forward AND retroactively over the
~162 already-approved items.

**Architecture:** A `verify_item` service asks a strong-tier model (premium / the lineup's
verifier role) to solve `(question, choices)` with NO declared answer, returning its chosen
index + an ambiguity signal + a short note. We compare to `answer_index` → a `verifier_status`
(`agree` / `mismatch` / `ambiguous` / `error`). Generation runs it per draft; an admin sweep
runs it over existing items. The admin UI surfaces the flag + a "needs review" filter. The
verifier is **advisory** — it FLAGS, it does NOT auto-unapprove (an LLM verifier can be wrong;
the human adjudicates, consistent with AD4).

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React · the LLM client/json infra · pytest · vitest.

## Global Constraints

- **Verifier is blind + independent:** it must NOT be shown the declared `answer_index`/`explanation`.
  Use a strong tier (default `premium`), configurable.
- **Advisory, not authoritative:** mismatches/ambiguous → FLAG (set `verifier_status` + store the
  verifier's answer + note). NEVER auto-change `answer_index`, never auto-unapprove. The operator decides.
- **Best-effort:** a verifier error on one item → `verifier_status="error"`, continue the batch; never crash generation or the sweep.
- All admin endpoints `get_current_admin`-gated; the sweep (LLM, bulk) is rate-limited. WCAG 2.2 AA on UI (vitest-axe), i18n keys, no `as any`.
- Backend `ruff` clean; frontend `tsc`/`lint`(0)/`build`/vitest green. Commit to branch `diagnostic-verifier`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`.
- **DB migration:** additive nullable columns on `diagnostic_items`. Check `alembic heads` (expected `c9d8e7f6a5b4`), chain from it, VERIFY a unique revision id (grep first). Ship task asks the operator about a prod snapshot.

## File Structure
- `backend/app/models/diagnostic.py` — add verifier columns (modify) + migration (new).
- `backend/app/services/diagnostic_item_service.py` — `verify_item` + wire into `generate_items` + a `sweep_verify` (modify).
- `backend/app/routers/admin_diagnostic.py` + `schemas/diagnostic.py` — verify endpoint + expose verifier fields + filter (modify).
- `frontend/src/api/adminDiagnostic.ts` + `components/admin/DiagnosticItemsAdmin.tsx` (+ test) — verifier badge + "needs review" filter + "Verify all" action (modify).
- Tests alongside.

---

### Task 1: Migration + verifier columns

Add nullable columns to `DiagnosticItem`: `verifier_status` (str(12)|None — `agree`/`mismatch`/`ambiguous`/`error`; null = unverified), `verifier_answer_index` (int|None), `verifier_note` (Text|None), `verified_at` (tz datetime|None).

- [ ] **Step 1 (test first):** extend `test_diagnostic_item_model.py` — a new item has all four verifier fields default `None`; they persist when set. Run → fail.
- [ ] **Step 2:** add the columns (mirror existing style).
- [ ] **Step 3:** `alembic heads` → confirm `c9d8e7f6a5b4`; grep-verify a fresh unique revision id; hand-write additive `add_column` ×4 (all nullable); clean `downgrade`; `alembic upgrade head`; single head.
- [ ] **Step 4:** model tests green; `ruff` clean.

### Task 2: `verify_item` service + wire into generation

**Interface:** `async def verify_item(session, item_or_fields, *, tier="premium") -> VerifyResult{verifier_answer_index, status, note}` —
1. Build a prompt with ONLY `question` + `choices` (NO declared answer/explanation), wrapped in `with_generation_framing`, asking the model to (a) pick the single best choice index, (b) say whether more than one choice is defensibly correct (ambiguous), (c) give a one-line reason. Strong tier (`premium` default). Parse via `llm_json` (object-safe).
2. Compare to the item's `answer_index`: `agree` if match AND not ambiguous; `ambiguous` if the model flags multiple defensible answers; `mismatch` if its pick ≠ declared. On any LLM/parse error → `error`.
3. Set `verifier_status`, `verifier_answer_index`, `verifier_note`, `verified_at` on the item.
**Wire into `generate_items`:** after persisting each draft, run `verify_item` so new drafts carry a verifier status. Best-effort (an error → `verifier_status="error"`, draft still persists).

- [ ] **Step 1 (test first):** `test_diagnostic_verify.py` (mock the LLM): verifier agrees → `status="agree"`; verifier picks a different index → `mismatch` (+ `verifier_answer_index` stored); verifier flags ambiguity → `ambiguous`; LLM error → `error`, no crash; the verifier prompt does NOT include the declared answer (assert the answer isn't in the prompt passed to the mocked client). And: `generate_items` sets a verifier status on each draft. Run → fail.
- [ ] **Step 2:** implement; reuse `get_llm_client`/`with_generation_framing`/`llm_json` (object-wrapped-array safe).
- [ ] **Step 3:** backend tests green; `ruff` clean.

### Task 3: Sweep endpoint + expose verifier fields/filter

- `POST /admin/diagnostic-items/verify` (admin-gated, rate-limited) body `{market_code?, topic?, status?, limit, only_unverified?}` → runs `verify_item` over matching items (default: all, or `status="approved"` for the retroactive sweep), sets fields, returns counts `{verified, agree, mismatch, ambiguous, error}` + the list of flagged item ids.
- `GET /admin/diagnostic-items` response: include `verifier_status`/`verifier_answer_index`/`verifier_note`/`verified_at` per item; add an optional `verifier=` filter (e.g. `needs_review` = mismatch OR ambiguous).

- [ ] **Step 1 (test first):** `test_admin_diagnostic_verify.py` — unauth → 401/403; the sweep verifies matching items + returns counts + flagged ids (mock the LLM, seed a known-wrong item → it's flagged `mismatch`); the list exposes verifier fields and the `verifier=needs_review` filter returns only mismatch/ambiguous. Run → fail.
- [ ] **Step 2:** implement; the sweep is batched + best-effort. Default the sweep tier to `premium`.
- [ ] **Step 3:** backend tests green; `ruff` clean.

### Task 4: Admin UI — verifier badge + needs-review filter

- [ ] **Step 1 (test first):** `DiagnosticItemsAdmin.test.tsx` — a `mismatch`/`ambiguous` item shows a prominent **verifier warning** (showing the verifier's answer + note vs the declared answer); a **"Needs review"** filter shows only flagged items; a **"Verify all"** button calls the sweep; agree/unverified render without alarm; vitest-axe clean. Run → fail.
- [ ] **Step 2:** implement (extend the existing page): per-item verifier badge/warning, the filter, the "Verify all" action (+ show the returned counts). i18n keys; no `as any`; ≥44px.
- [ ] **Step 3:** `tsc`/`lint`/vitest(+axe)/`build` green.

### Task 5: Verify + ship + run the retroactive sweep
- [ ] Backend `ruff` + full `pytest`; frontend gates; single alembic head. SDD finishing flow → opus whole-branch review → green CI → Railway (backend) + manual Vercel (web). Admin page is web-only.
- [ ] **Ask the operator about a prod snapshot before the migration.**
- [ ] **Run the retroactive sweep on prod** over the **approved** items (premium tier), report the counts + the flagged items (id, topic, declared vs verifier answer, note) to the operator so they can re-review/fix the mismatched/ambiguous ones on `/admin/diagnostic-items` BEFORE recruiting the beta cohort.

## Out of scope
- Auto-correcting answers or auto-unapproving (advisory only — human decides).
- Non-MCQ item types (all diagnostic items are MCQ).
- The diagnostic engine / onboarding / checkpoints (built; unchanged here).
