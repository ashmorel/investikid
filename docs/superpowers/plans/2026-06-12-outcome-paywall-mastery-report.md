# Outcome-Led Paywall & Mastery Report (M6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Per `docs/superpowers/specs/2026-06-12-outcome-paywall-mastery-report-design.md` — mastery-report endpoint, parent dashboard hero, outcome-led PremiumValueCard, digest premium-line variants. No migration.

### Task 1: mastery_report_service + endpoint
- [ ] `app/services/mastery_report_service.py`: `build_mastery_report(session, parent_email, *, days=30, now=None)` per spec shape; reuse `digest_service._weak_topic` / `_next_recommendation`; objectives deduped + capped 8; standards distinct.
- [ ] `GET /parent/mastery-report` in parent router + schemas (`MasteryReportOut` etc.).
- [ ] Tests `tests/test_mastery_report.py` (seeded masteries in/out of window, dedupe/cap, empty, auth).
- [ ] Commit `feat(m6): parent mastery-report endpoint`.

### Task 2: digest premium-line variants + analytics prop
- [ ] `ALLOWED_PROP_KEYS` += `variant`; `email.py`: three premium-line variants chosen by `hash(parent_email) % 3` (stable; expose `premium_variant(parent_email)` helper for tests); digest send records `digest_sent` with `props.variant`.
- [ ] Tests: variant determinism + all reachable; digest_sent carries variant; email html contains the right line per variant.
- [ ] Commit `feat(m6): digest premium-line copy variants (analytics-tagged)`.

### Task 3: MasteryReportCard (parent dashboard hero)
- [ ] `src/api/parent.ts`: `getMasteryReport()` types/fetcher.
- [ ] `src/components/parent/MasteryReportCard.tsx` per spec (headline, chips cap 8, standards badges, weak-area line, empty state, skeleton/error); mounted at top of ParentDashboard.
- [ ] Tests + axe; ParentDashboard composition test updated.
- [ ] Commit `feat(m6): mastery report hero on parent dashboard`.

### Task 4: PremiumValueCard outcome reframe
- [ ] Evidence-led headline from mastery report (fallback copy without data); benefits trimmed to 3; behaviour (hidden when subscribed, pending-request highlight, CTA) unchanged.
- [ ] Update existing PremiumValueCard tests + axe.
- [ ] Commit `feat(m6): outcome-led premium value card`.

### Task 5: Verify + push + docs
- [ ] Backend ruff + pytest; frontend tsc + lint + vitest + build; cap sync ios.
- [ ] Push `testing`, CI green; roadmap M6 status + memory.
