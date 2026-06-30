# A2 Unit 4 — Session-Milestone Re-check (the post-test) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Goal:** Close the "+X%" loop. A child who has been active for a milestone number of
days (5 / 15 / 30 **active days**, per OD2) is offered a short, declinable **progress
check** — a `kind="progress"` diagnostic — whose checkpoint, compared to the baseline,
yields *"mastery +X% after Y sessions."* The engine (`start`/`submit`/`evidence`) and the
flow UI (`OnboardingDiagnostic`) already exist; this adds the **active-days counter**, the
**"re-check due" signal**, and a **non-blocking Home prompt** that reuses the diagnostic flow.

**Architecture:** `record_daily_activity` increments a new `UserProgress.active_days`
whenever a child's activity advances to a new day. `GET /diagnostic/recheck-status` reports
whether a re-check is due = `active_days >= MILESTONES[<#progress checkpoints so far>]`
(each completed progress check consumes one milestone; after 3, no more). `submit` stamps
`session_count = active_days` on a `progress` checkpoint (server-side). The child app shows
a gentle Home card when due; tapping runs the existing diagnostic flow with `kind="progress"`.

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React · pytest · vitest.

## Global Constraints

- **Non-blocking + declinable:** the re-check is an offer (a Home card), NEVER a forced
  redirect. Dismissing it must not block the app; it can reappear a later session, but once
  the child completes a progress check the milestone is consumed and it stops.
- **Server-authoritative `session_count`:** `session_count` on a progress checkpoint is the
  server's `active_days` — never a client value. (No reward side-effects, inherited from U2.)
- **Reuse, don't fork:** reuse `start_diagnostic(kind="progress")` + `submit_diagnostic` +
  the `OnboardingDiagnostic` flow (parameterised by kind). Don't build a parallel flow.
- WCAG 2.2 AA (vitest-axe), ≥44px / ≥16px iOS, i18n keys, no `as any`, tier-aware copy.
- Backend `ruff` clean; frontend `tsc`/`lint`(0)/`build`/vitest green. Commit to branch
  `diagnostic-recheck`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`. Native-visible (child
  UI) → ship runs `cap sync` (or defers per operator).
- **DB migration:** one additive nullable/defaulted column. Check `alembic heads` (expected
  `e7f8a9b0c1d2`), chain from it, VERIFY a unique revision id (grep first). Ship asks the operator about a prod snapshot.

## File Structure
- `backend/app/models/user.py` — `UserProgress.active_days` (modify) + migration (new).
- `backend/app/services/content_service.py` — increment `active_days` in `record_daily_activity` (modify).
- `backend/app/services/diagnostic_service.py` — recheck-status logic + `session_count` wiring (modify).
- `backend/app/routers/diagnostic.py` — `GET /diagnostic/recheck-status` (modify).
- `frontend/src/pages/child/OnboardingDiagnostic.tsx` — accept a `kind` prop (modify).
- `frontend/src/components/child/...` — a "progress check due" Home card + the recheck hook (new/modify).
- Tests alongside.

---

### Task 1: `active_days` counter

- [ ] **Step 1 (test first):** in the streak/activity tests, assert: first-ever activity sets `active_days=1`; a SECOND activity the SAME day does NOT increment; activity on a NEW day increments by 1. Run → fail.
- [ ] **Step 2:** add `UserProgress.active_days` (int, default 0, server_default "0"). In `record_daily_activity`, increment `active_days` exactly when the activity advances to a new day (i.e. NOT on the same-day early-return path — mirror where `last_activity_date` advances). Migration: additive `add_column` (verify unique rev id, chain `e7f8a9b0c1d2`, clean downgrade, single head, `alembic upgrade head`).
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 2: Re-check status endpoint + `session_count` wiring

`MILESTONES = (5, 15, 30)` active days.
- [ ] **Step 1 (test first):** `test_diagnostic_recheck.py` — `GET /diagnostic/recheck-status` returns `{due, milestone, active_days, completed_checks}` where `completed_checks` = the user's count of `kind="progress"` checkpoints and `due = active_days >= MILESTONES[completed_checks]` (and `completed_checks < len(MILESTONES)`); a child below the next milestone → `due:false`; at/over → `due:true` with that `milestone`; after 3 progress checkpoints → `due:false` (exhausted). Plus: submitting a `progress` session stamps `session_count = active_days` (server-side, not a client value); unauth → 401. Run → fail.
- [ ] **Step 2:** implement the recheck-status service + endpoint (read-only, per-user). In `submit_diagnostic`, when the session's `kind == "progress"`, set the checkpoint's `session_count` from the user's `active_days` (load it; don't accept a client value). Baseline path unchanged (session_count stays 0).
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 3: Frontend — progress-check Home card + flow reuse

- [ ] **Step 1 (test first):**
  - `OnboardingDiagnostic` accepts a `kind: 'baseline' | 'progress'` prop (default `'baseline'`) and passes it to `start`; the results copy adapts (progress → "Here's how much you've grown" tier-aware). Existing baseline tests stay green.
  - a **"progress check due" Home card** renders ONLY when `recheck-status.due` is true; tapping launches the progress diagnostic (kind=progress); it's **dismissible** (dismiss hides it for the session, doesn't block); after completion the recheck query invalidates so the card disappears (the checkpoint consumed the milestone). vitest-axe clean.
  Run → fail.
- [ ] **Step 2:** implement: the `kind` prop + a `useRecheckStatus()` hook + the Home card (gentle, declinable, tier-aware, ≥44px, i18n keys). Wire the progress route/launch (reuse the onboarding flow component; the card navigates to it with kind=progress, or renders it inline). On complete → navigate Home + invalidate `['diagnostic','recheck']` and `['diagnostic','evidence']`.
- [ ] **Step 3:** `tsc`/`lint`/vitest(+axe)/`build` green.

### Task 4: Verify + ship
- [ ] Backend `ruff` + full `pytest`; frontend gates; single alembic head. Reason through the flow end-to-end: baseline captured (A3) → child active 5 days → Home card → progress check → evidence now shows baseline→progress deltas ("+X% after Y").
- [ ] Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. **Ask the operator about a prod snapshot before the migration.** SDD finishing flow → opus whole-branch review → green CI → Railway (backend) + manual Vercel (web). Native-visible → `cap sync` (operator batches the native build).

## Out of scope (later)
- **Unit 5** — per-concept rolling mastery scoring (Progress drill-down).
- **Unit 6 / A4** — parent-report growth block (consumes `/diagnostic/evidence`) + public evidence page.
- Baseline-on-first-touch (the AD2 fast-follow).
- Any "+X%" *public* claim (gated on beta validation per OD4).
