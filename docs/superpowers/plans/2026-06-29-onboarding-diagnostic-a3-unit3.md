# A3 / A2 Unit 3 — Onboarding Diagnostic (baseline pre-test) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Goal:** Capture each child's **baseline** on their first run — a short, skippable
diagnostic between signup and Home that doubles as the pre-test. **Launch-critical:** the
baseline must be captured before beta cohorts start (no second first-session). Mostly
frontend — the engine (`/diagnostic/start|submit|evidence`) shipped in Unit 2; this adds
the child-facing flow + a small backend skip path. Spec:
`docs/superpowers/specs/2026-06-29-mastery-measurement-a2-a3-design.md` (AD2: baseline-on-
first-touch is a SEPARATE fast-follow, NOT in this unit).

**Architecture:** On the child app, if the user has **no baseline checkpoint**
(`GET /diagnostic/evidence` → `has_baseline === false`), they're routed once to
`/onboarding/diagnostic`. That page calls `start`, renders the items (reusing the quiz
components), collects answers, and `submit`s → a `baseline` `MasteryCheckpoint` → a friendly
results screen → Home. A **Skip** writes a `skipped` baseline (comparable cohort). **Empty
bank** (no approved items yet — the current state) → auto-skip straight to Home with a
`skipped` checkpoint, never a broken empty quiz. **A diagnostic error must never lock the
child out** — any failure falls through to Home.

**Tech Stack:** React 18 · TanStack Query · FastAPI (small) · Capacitor · pytest · vitest.

## Global Constraints

- **Never blocks the app:** any error/timeout in start/submit, or an empty bank, resolves to
  Home. The diagnostic is additive; it must not gate access to the product.
- **Shows once:** gated on `has_baseline` (baseline OR skipped both count as done). After
  completion/skip, invalidate the evidence query so it never re-shows. (Existing test
  accounts will get it on next login — desired for the beta cohort.)
- **Child-only:** the flow lives in the child app/shell, not parent/admin.
- **No reward side-effects** (inherited from Unit 2 — the diagnostic never touches XP/streak/coins).
- WCAG 2.2 AA (vitest-axe), ≥44px targets, **iOS form controls ≥16px**, i18n keys only
  (no literal strings), no `as any`. Tier-aware friendly copy (Explorer vs Investor) like
  the rest of the child UI.
- Backend `ruff` clean; frontend `tsc`/`lint`(0)/`build`/vitest(+axe) green. Commit to branch
  `onboarding-diagnostic`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`.
- **Native-visible** (child UI) → ship task runs `npm run build && npx cap sync ios` (+android).
- No DB migration (reuses Unit 2 tables).

## File Structure
- `backend/app/schemas/diagnostic_session.py` — add `skipped: bool` to the submit request (modify).
- `backend/app/services/diagnostic_service.py` + `routers/diagnostic.py` — honor `skipped` (modify).
- `frontend/src/api/diagnostic.ts` — `start`/`submit`/`evidence` hooks (new).
- `frontend/src/pages/child/OnboardingDiagnostic.tsx` — the flow (new) + route in `App.tsx`.
- `frontend/src/components/child/...` — reuse existing quiz/OptionCard components.
- The child Shell/guard (e.g. `frontend/src/components/child/Shell.tsx`) — the `has_baseline` redirect (modify).
- Tests alongside.

---

### Task 1: Backend — `skipped` submit path

**Files:** `schemas/diagnostic_session.py`, `services/diagnostic_service.py`, `routers/diagnostic.py`.

- [ ] **Step 1 (test first):** extend `test_diagnostic_submit.py` — `submit` with `skipped=true` on a non-empty session writes a checkpoint `kind="skipped"`, `overall_score=None`, **no topic rows**, completes the session, and does NOT score / bump `times_correct` / warm-start `TopicMastery`. (A normal submit is unchanged.) Run → fail.
- [ ] **Step 2:** Add optional `skipped: bool = False` to the submit request schema. In `submit_diagnostic`, when `skipped` is true (or the session is empty), short-circuit to writing a `skipped` checkpoint (no scoring, no calibration, no warm-start), mark the session completed. Keep the ownership/replay (409/403/404) guards.
- [ ] **Step 3:** backend tests green; `ruff` clean.

### Task 2: Frontend — the onboarding diagnostic flow

**Files:** `frontend/src/api/diagnostic.ts`, `frontend/src/pages/child/OnboardingDiagnostic.tsx` (+ route), reuse quiz components.

**Behaviour:**
- On mount, call `start` (kind baseline). While loading, a friendly spinner.
- **Empty items** → immediately `submit({skipped:true})` (or rely on the empty-session→skipped path) and call `onComplete` → Home, showing at most a brief "Welcome!" (no empty quiz).
- **Items present** → render them (one-at-a-time or a short scroll), reusing the existing `OptionCard`/quiz components; collect `{item_id: chosen_index}`. A persistent **"Skip for now"** affordance.
- **Finish** → `submit({session_id, answers})` → a results screen ("Here's what you already know 💡" + per-topic chips from the response, tier-aware copy) → `onComplete` → Home.
- **Skip** → `submit({session_id, skipped:true})` → straight to Home.
- **Any error** (start or submit) → log + fall through to `onComplete` (Home). Never trap the child.

- [ ] **Step 1 (test first):** `OnboardingDiagnostic.test.tsx` (mock the API) — renders items from start; selecting answers + finishing calls submit with the chosen map; the results screen shows per-topic chips; **empty-bank path** auto-completes to Home without a quiz; **skip** calls submit with `skipped:true`; a start/submit error still completes (no lockout); **vitest-axe** clean; controls ≥44px / ≥16px font. Run → fail.
- [ ] **Step 2:** Build the page + the `diagnostic.ts` hooks. Reuse the quiz components (don't reinvent option rendering). i18n keys; tier-aware copy.
- [ ] **Step 3:** `tsc`/`lint`/the new vitest/`build` green.

### Task 3: Gating — show it once, before Home

**Files:** the child Shell/route guard, `App.tsx` (route), `frontend/src/api/diagnostic.ts` (evidence hook).

- [ ] **Step 1 (test first):** a test for the guard logic — a child with `has_baseline===false` is redirected to `/onboarding/diagnostic`; with `has_baseline===true` is NOT; after completion the evidence query invalidates so the redirect stops; the guard is child-only (doesn't affect parent/admin); a guard error/loading state does NOT block the app (fails open to Home). Run → fail.
- [ ] **Step 2:** Implement: an evidence check in the child shell (or a wrapper) that redirects to `/onboarding/diagnostic` once when `has_baseline` is false; register the route; `onComplete` navigates to Home and invalidates `['diagnostic','evidence']`. Fail-open on error/loading (never block).
- [ ] **Step 3:** frontend gates green; confirm no redirect loop (the onboarding route itself must not be guarded).

### Task 4: Verify + ship
- [ ] Backend `ruff` + full `pytest`; frontend `typecheck`/`lint`/`test`/`build`. Manually reason through the **empty-bank** path end-to-end (current prod state → child signs up → no items → skipped baseline → Home, no breakage).
- [ ] Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. SDD finishing flow → green CI → Railway (backend) + manual Vercel (web). **Native-visible → `npm run build && npx cap sync ios`** (+ android) for the next beta build (operator archives/uploads).
- [ ] **Operator note:** the onboarding is live but resolves to `skipped` until diagnostic items are approved (Unit 1 `/admin/diagnostic-items`). Approve items so real baselines start being captured **before** recruiting the beta cohort.

## Out of scope (later)
- **Baseline-on-first-touch** (per-topic mini-check when a child first opens an un-baselined topic) — the AD2 fast-follow, its own plan.
- **Unit 4** — session-milestone re-check trigger (the progress checkpoints + the active-days source).
- **Unit 5/6** — per-concept scoring; parent-report growth block.
