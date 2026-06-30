# Diagnostic items — "Unpublish to edit" (approved → draft) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Why:** The verifier flags *approved* items, but editing is draft-only and there's no
`approved → draft` path — so a confirmed-wrong approved item can only be retired-and-replaced,
not fixed in place. Add an **unpublish** action so an operator can: unpublish a flagged
approved item → fix its `answer_index` → re-approve. Also: **clear the stale verifier flag when
a draft's content is edited**, so a corrected item drops out of the "Needs review" filter.

**Architecture:** New `unpublish_item` (`approved → draft`, clears `approved_by`/`approved_at`)
+ `POST /admin/diagnostic-items/{id}/unpublish` (409 if not approved). `patch_item` resets the
four `verifier_*` fields to NULL when it changes content (the prior verification is invalidated
by the edit). Admin UI gets an "Unpublish to edit" button on approved items. **No DB migration.**

## Global Constraints
- Admin-gated (`get_current_admin`); the lifecycle stays a clean state machine: `draft↔approved`
  (approve / unpublish), `draft→retired` (reject), `approved→retired` (retire).
- `unpublish` requires `approved` (409 otherwise); editing stays draft-only (unchanged).
- **Advisory verifier integrity unchanged:** unpublish/patch never touch `answer_index` except via
  the operator's explicit edit. Clearing `verifier_*` on a content edit is correct (stale flag).
- WCAG 2.2 AA (vitest-axe), ≥44px, i18n keys, no `as any`. Backend `ruff` clean; frontend gates green.
- Commit to branch `diagnostic-unpublish-edit`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`. **No DB migration.**

## File Structure
- `backend/app/services/diagnostic_item_service.py` — `unpublish_item` + `patch_item` verifier-clear (modify).
- `backend/app/routers/admin_diagnostic.py` — `POST .../unpublish` (modify).
- `frontend/src/api/adminDiagnostic.ts` + `components/admin/DiagnosticItemsAdmin.tsx` (+ test) — unpublish button (modify).
- Tests alongside.

---

### Task 1: Backend — `unpublish` + clear verifier on edit

- [ ] **Step 1 (test first):** `test_admin_diagnostic` (or the verify test file) —
  - `POST /admin/diagnostic-items/{id}/unpublish` on an **approved** item → status `draft`,
    `approved_by`/`approved_at` cleared to None; returns 200.
  - unpublish on a **draft** or **retired** item → 409.
  - unauth → 401/403; unknown id → 404.
  - `PATCH /admin/diagnostic-items/{id}` (draft) that changes `answer_index` (or question/choices/
    explanation) → the item's `verifier_status`/`verifier_answer_index`/`verifier_note`/`verified_at`
    are reset to None (stale flag cleared). A patch that changes nothing content-related (or the
    no-op case) leaves them — keep it simple: clear on any successful content patch.
  - End-to-end: an **approved, mismatch-flagged** item → unpublish → patch a correct `answer_index`
    → approve → it is `approved` with `verifier_status` None (no longer in `verifier=needs_review`).
  Run → fail.
- [ ] **Step 2:** `unpublish_item(session, item)` → `status="draft"`, `approved_by=None`,
  `approved_at=None`. Router `POST .../unpublish` (admin-gated): 404 unknown, 409 if `status != "approved"`,
  else unpublish + commit. In `patch_item`, when a content field actually changes, set the four
  `verifier_*` fields to None. Update the router docstring's state-machine diagram to include
  `approved → draft (unpublish)`.
- [ ] **Step 3:** backend tests green; `ruff` clean.

### Task 2: Admin UI — "Unpublish to edit" button

- [ ] **Step 1 (test first):** `DiagnosticItemsAdmin.test.tsx` —
  - an **approved** item shows an "Unpublish to edit" button (≥44px); clicking calls the unpublish
    mutation + invalidates the list.
  - a **draft**/**retired** item does NOT show it.
  - (the existing Edit form already appears for drafts — after unpublish the item becomes draft so
    Edit/Approve are available; no new edit UI needed.)
  - vitest-axe clean.
  Run → fail.
- [ ] **Step 2:** `adminDiagnostic.ts` — `useUnpublishItem()` mutation (POST `.../unpublish`,
  invalidates the list). `DiagnosticItemsAdmin.tsx` — render the "Unpublish to edit" action on
  approved items (near the existing Retire action; show it especially when the item is flagged so
  the operator can fix-then-reapprove). i18n keys; no `as any`; ≥44px.
- [ ] **Step 3:** `tsc`/`lint`/vitest(+axe)/`build` green.

### Task 3: Verify + ship
- [ ] Backend `ruff` + the diagnostic suites (run isolated); frontend gates. SDD finishing flow →
  (sonnet per-task reviews already done) → green CI → Railway (backend) + manual Vercel (web).
  Admin page is web-only (no native). **No migration → no snapshot ask.**
- [ ] Update `MASTER-BACKLOG` note + the operator runbook (the flagged-item adjudication now has a
  fix-in-place path: Unpublish → fix answer → Approve).

## Out of scope
- Auto-correcting answers (the operator still edits explicitly).
- Re-running the verifier automatically on re-approve (the flag clears on edit; a later sweep
  re-verifies if wanted).
