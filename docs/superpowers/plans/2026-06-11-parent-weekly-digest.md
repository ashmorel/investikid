# W4 — Parent Weekly Digest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** A weekly outcome email per parent (skills mastered via W3 objectives, week-in-numbers, weak area, next lesson, authored conversation prompt, outcome-led premium line for non-subscribers), default-on with an opt-out toggle, sent by the existing cron machinery.

**Spec:** `docs/superpowers/specs/2026-06-11-parent-weekly-digest-design.md` (incl. the approved 12 conversation prompts in section E — copy verbatim).

**Verify:** backend `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` + `pytest`; frontend `npx tsc -b && npm run lint && npm run test`. Branch `testing`; explicit `git add`; commit suffix `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Async tests: `loop_scope="session"` + fixtures.

**Verified facts:**
- Children link to parents via `User.parent_email` (`app/models/user.py:28`).
- `ParentPreferences` keyed by `parent_email`, has `trial_reminder_opt_out`; endpoints `GET/PATCH /parent/preferences` (`app/routers/parent.py:71/82`, schemas in `app/schemas/parent_preferences.py`).
- Clone pattern: `app/services/trial_reminder_service.py::run(session) -> dict` (opt-out check at line ~51, idempotency via `subject_id`) + `app/routers/internal.py::/trial-reminders/run` (CRON_SECRET guard) + cron step in `.github/workflows/video-health-cron.yml`.
- Email registry: `app/services/email.py` — `_render`, `_render_html`, `_EMAIL_SUBJECTS`.
- Data: `LevelMastery` (user_id, level_id, mastered_at, score); `Level.learning_objectives`; `LessonCompletion.completed_at`; streak on `UserProgress`; `gap_detection_service.get_strengths_and_gaps(...)`; `recommendation_service.get_recommendations(...)` (check their exact signatures/return shapes before use); subscription state per parent (see how `PremiumValueCard`/parent router decides subscribed — reuse).
- Alembic head after W3a: `537993f57477` — run `alembic heads` to confirm before writing the new migration.

---

### Task 1: Migration + model fields + seed prompts
**Files:** Modify `app/models/parent_preferences.py`, `app/models/content.py` (Module), `app/seed/content.py` (12 `conversation_prompt` values from spec section E, verbatim; seeder upsert like W3b fields); Create `alembic/versions/<rev>_weekly_digest.py`; Tests extend `tests/test_seed_content.py` + a small model test.
- [ ] Add `ParentPreferences.weekly_digest_opt_out: Mapped[bool]` (server_default false) + `last_digest_sent_at: Mapped[datetime | None]`; `Module.conversation_prompt: Mapped[str | None]` (String(300)).
- [ ] Chained migration (down_revision = current head): 3 columns, downgrade drops them. No backfill.
- [ ] Seed: add `"conversation_prompt": "..."` to each of the 12 module dicts (spec table, verbatim); seeder upserts it (create + update paths, absent key untouched) — same mechanics as W3b.
- [ ] Tests: prompts all present/non-empty/≤300 in `_MODULES`; seeder applies + idempotent; prefs defaults false/None.
- [ ] ruff + targeted pytest → commit `feat(w4): digest prefs + module conversation prompts (schema + seed)`.

### Task 2: Digest service
**Files:** Create `app/services/digest_service.py`; Test `tests/test_digest_service.py`.
- [ ] `build_weekly_digest(session, parent_email, *, now=None) -> dict | None`: children = users with `parent_email == parent_email`; window start = `max(prefs.last_digest_sent_at, now-7d)` (or `now-7d` if never sent). Per child: masteries in window (join Level+Module for titles + objectives), lessons-completed count in window, streak, weakest topic via `get_strengths_and_gaps` (omit on no signal/error — never fail the digest on an enrichment), next lesson via the recommendation service (same resilience), conversation prompt from most-recently-mastered module in window else the recommended module (else omit). Return None if NO child has completions or masteries in window.
- [ ] `run_weekly_digests(session, *, now=None) -> dict`: distinct parent_emails with children; skip if opted out; skip if `last_digest_sent_at` > now-7d; build (None → skipped count); send template `weekly_digest` with the digest context; set `last_digest_sent_at = now` only on send. Summary `{sent, skipped_quiet, skipped_recent, skipped_opt_out}`.
- [ ] Tests per spec Testing list (window, first-send, 7-day gate, opt-out, quiet skip + last_sent NOT updated, multi-child, prompt fallback, premium flag only for non-subscribed — determine subscribed via existing subscription lookup, mirror parent router).
- [ ] ruff + pytest → commit `feat(w4): weekly digest builder + runner`.

### Task 3: Email template + endpoint + cron step
**Files:** Modify `app/services/email.py`, `app/routers/internal.py`, `.github/workflows/video-health-cron.yml`; Tests `tests/test_email_templates.py`-style + `tests/test_internal_*.py`-style (find real names).
- [ ] Template `weekly_digest` (subject "What {names} learned this week 🌟"; text + HTML per spec section D; premium paragraph only when context says non-subscribed; footer dashboard link + preferences pointer; no tracking).
- [ ] `POST /internal/weekly-digest/run` — exact clone of trial-reminders guard; calls `run_weekly_digests`; returns summary.
- [ ] Cron: add a `Trigger weekly digests` step to the workflow **in this branch only** (it reaches `main` via promotion — do NOT separately edit main; note in commit body, mirroring 4C).
- [ ] Tests: render full + minimal contexts (no weak topic, single child, subscribed parent → no premium para); endpoint 401 without secret, 200 + summary with.
- [ ] ruff + pytest → commit `feat(w4): weekly_digest email + internal run endpoint + cron step`.

### Task 4: Preferences toggle (BE + FE) + full regression + push
**Files:** Modify `app/schemas/parent_preferences.py`, `frontend/src/api/<parent prefs client>`, `frontend/src/components/parent/NotificationPreferencesCard.tsx` + its test.
- [ ] BE: `weekly_digest_opt_out` on `ParentPreferencesOut`/`Update` (PATCH applies it — follow trial field).
- [ ] FE: "Weekly progress email" toggle mirroring the trial-reminder toggle (copy, layout, optimistic update, axe).
- [ ] Tests: BE PATCH round-trip; FE toggle renders/updates/axe.
- [ ] Full regression both stacks; push `origin testing`; report CI (re-run once if the known PyPI pip-audit flake hits).

## Self-review
Spec A=T1, B=T2, C=T3, D=T3, E=T1, F=T4; quiet-skip + opt model + authored prompts decisions honoured; cron gotcha handled in T3; no LLM anywhere.
