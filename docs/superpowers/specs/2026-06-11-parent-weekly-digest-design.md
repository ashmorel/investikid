# W4 — Parent Weekly Outcome Reports — Design Spec

**Date:** 2026-06-11 · **Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Roadmap:** Phase 1, workstream W4 (`docs/2026-06-10-best-in-class-roadmap.md`). Builds directly on W3's `level_mastery` records and `learning_objectives`.

## Goal
Make learning outcomes visible to parents without them having to open the app: a weekly email per parent that says what their child *can now do*, what to practise, what's next, and what to talk about — and carries the outcome-led premium message for non-subscribed parents.

## Decisions (locked with user)
1. **Conversation prompts are authored per module** (seed content, no LLM) — deterministic, no moderation surface in a scheduled email.
2. **Quiet weeks are skipped silently** — no activity → no email.
3. **Default on + easy opt-out** — service communication about the parent's own child; toggle in the existing notification preferences.

## Current state (verified)
- `ParentPreferences` (`backend/app/models/parent_preferences.py`): keyed by `parent_email`, has `trial_reminder_opt_out` — the exact pattern to extend.
- Email service (`backend/app/services/email.py`): template registry with `_render` / `_render_html` / `_EMAIL_SUBJECTS`; Resend or logging backend.
- Cron pattern: daily GitHub workflow (`video-health-cron.yml`, 06:00 UTC) hits `/internal/...` endpoints with `CRON_SECRET`; `trial_reminder_service` + `/internal/trial-reminders/run` is the model to clone.
- Data available: `level_mastery` (dated, with scores), `Level.learning_objectives`, `LessonCompletion`, streaks (`UserProgress`), gap-detection service, recommendation service (level-aware next lesson), subscription state per parent.

## Design

### A. Data (one chained Alembic migration)
- `parent_preferences.weekly_digest_opt_out: bool` (server_default false).
- `parent_preferences.last_digest_sent_at: timestamptz | None`.
- `modules.conversation_prompt: String(300) | None` — seed-authored (section E), upserted by the seeder like W3b fields.

### B. Digest service (`backend/app/services/digest_service.py`)
`build_weekly_digest(session, parent) -> DigestData | None` per parent:
- Window = `max(last_digest_sent_at, now-7d)` … now (first digest uses 7 days).
- Per linked child: masteries in window (level → module title, level title, objectives), lessons completed count in window, current streak, weakest topic (gap-detection; omit if no signal), next recommended lesson, and one conversation prompt chosen from the most recent mastered module in window (fallback: the module of the next recommended lesson).
- Return `None` when **no child** has any activity (no completions and no masteries in window) → skip silently.
- `run_weekly_digests(session)`: iterate parents with linked children; skip when opted out or `last_digest_sent_at` < 7 days ago; build; send template `weekly_digest`; set `last_digest_sent_at = now` **only when an email was actually sent**. Returns a summary dict (sent/skipped counts) like the trial-reminder runner.

### C. Endpoint + cron
- `POST /internal/weekly-digest/run` guarded by `CRON_SECRET` (clone of trial-reminders endpoint).
- New step in `.github/workflows/video-health-cron.yml` **on `testing` only** — ⚠️ do NOT add to `main`'s workflow until W4 is promoted to prod (the scheduled cron runs from `main` against prod; an early step would 404 daily — same gotcha 4C documented).

### D. Email template `weekly_digest` (text + HTML, kid-app brand tone)
Subject: "What {child names} learned this week 🌟". Sections per child: outcomes ("{name} mastered {module} · {level} — they can now {objective}"), week-in-numbers (lessons, streak), "Worth practising" (weak topic, optional), "Up next" (recommended lesson), "Talk about it" (the module's conversation prompt). Footer: dashboard link + one-line opt-out pointer (preferences page). **Non-subscribed parents only:** one outcome-led premium paragraph + CTA ("Premium unlocks the next level of {module} — {first locked objective}"-style, data-driven, no pressure copy). No tracking pixels.

### E. Conversation prompts (seed content — user spot-reviews)
| Module | `conversation_prompt` |
|---|---|
| What is a Stock? | Ask them what you actually own when you buy a share — and who you're buying it from. |
| Compound Interest Basics | Ask how long money takes to double at 6% — they know a quick trick (the Rule of 72). |
| What is a REIT? | Ask how someone could invest in property without buying a house. |
| Budgeting Basics | Ask them to help plan one family purchase this week using their budgeting rule. |
| Needs vs Wants | Next time an advert comes on, ask them what tricks it's using to make you want it. |
| Risk & Diversification | Ask why putting all your money on one thing is risky — and what 'don't put all your eggs in one basket' means for investing. |
| What is Crypto? | Ask them what they'd say if a video promised to double your crypto in a week. |
| How Taxes Work | On your next shop, ask them where the VAT on the receipt goes. |
| Debt & Credit Explained | Ask them when borrowing money can be a good idea — and when it's a trap. |
| Starting a Side Hustle | Ask what they'd sell to earn their first £10 — and how they'd test the idea cheaply. |
| Revenue, Costs & Profit | Ask them how a lemonade stand selling £20 of drinks could still lose money. |
| Your First Paycheque | Show them (or sketch) a payslip and ask them to find the difference between gross and net pay. |

### F. Preferences UI
One new toggle in the existing parent `NotificationPreferencesCard` ("Weekly progress email"), wired to a `weekly_digest_opt_out` field through the existing preferences endpoints — mirror the trial-reminder toggle precisely.

## Testing
- Service: window logic; first-send (no last_sent); 7-day gate; opt-out skip; quiet-week skip (returns None, last_sent NOT updated); multi-child aggregation; prompt fallback; premium paragraph only for non-subscribed.
- Endpoint: 401 without secret; runs and reports counts.
- Email: text+HTML render with full and minimal contexts (no weak topic, single child).
- Migration up/down; seeder upserts `conversation_prompt`; all 12 prompts non-empty ≤300 chars (seed test).
- FE: toggle renders, round-trips, axe-clean.

## Out of scope
LLM content; PDF export; in-app digest view (dashboard already live); per-child frequency; localisation; changes to gap/recommendation services themselves.

## Open risks
- **Email volume/cost:** Resend free tier is ample at beta scale; the 7-day gate + skip-empty bound sends to ≤1/parent/week.
- **Non-prod sends:** testing/staging share live Resend keys (known env issue) — the cron step lands on `testing` first, so digests would send from the testing env to its (test) parents. Acceptable today because envs hold test accounts; flagged for the env-secrets cleanup.
