# Trial-Ending Reminder (Item 4C — subscription nudges) — Design Spec

**Date:** 2026-06-07
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** premium content & pricing → **4C (subscription nudges)**
**Sequence within item 4:** 4D (simulator) ✅ → 4B (paywall + child→parent request) ✅ → 4A (multi-channel payments: A2/A1/A3) ✅ → **4C (this — subscription nudges)**
**Builds on:** 4B (`PremiumRequest`, `premium_config.py` `PREMIUM_BENEFITS`, the email infra + `SentEmail` ledger) and 4A (7-day trial across Stripe/Apple/Google, `subscriptions` table with `provider`/`status`/`current_period_end`, the source-agnostic entitlement seam).

## Goal

Email each **Stripe-trial** parent **once**, roughly **2 days before** their 7-day free trial converts to paid, encouraging them to stay on Premium. The nudge is parent-facing (the child app stays purchase-free / COPPA-safe), capped (one email per trial), and respects a parent opt-out. Apple and Google trials are **out of scope** — those stores send their own native trial-ending notices, and our `subscriptions` rows can't distinguish an Apple/Google trial from a paid sub (see Decision 1).

## Decisions (from brainstorming)

1. **Stripe-only.** Only Stripe records a distinguishable `status='trialing'` with `current_period_end` = trial end. Apple (`_fetch_status` → active/expired/grace/revoked) and Google (`_map_status` → active/in_grace_period/expired) collapse the trial into `'active'`, so the cron cannot target their trials without false-positives against paying customers. Apple/Google send their own native trial reminders. → The reminder is a "your web trial converts in 2 days" email for **Stripe** parents only.
2. **One nudge moment only.** Just the trial-ending reminder. No event-driven nudges (repeated child requests / many premium locks), no periodic value-recap digest. (YAGNI.)
3. **Channel: email only.** No in-app parent-dashboard banner. The parent may not open the app during the trial; email is the right reach.
4. **Opt-out: yes.** A parent preference, default ON (opted-in), toggled in parent Settings — *"Email me about my subscription"*. GDPR-friendly + matches the brief.
5. **Scheduler: reuse the existing daily cron.** Add a second step to the existing `video-health-cron.yml` GitHub Action (one daily workflow, two curl calls) rather than a new scheduled workflow — cost-efficient and reuses `CRON_SECRET`. Enabled at the same CRON_SECRET cutover already tracked on the reminder list.
6. **No moderation needed.** The email is a fixed template (not LLM output), so `moderate_output` does not apply.

## Section 1 — Data: opt-out store

There is **no Parent table** — parents are represented by `parent_email` strings (auth via magic-link `ParentSession`). So the opt-out gets its own small table keyed by `parent_email`.

**New model `app/models/parent_preferences.py` → table `parent_preferences`:**
- `parent_email: Mapped[str]` — `String(255)`, **primary key**.
- `trial_reminder_opt_out: Mapped[bool]` — `Boolean`, `nullable=False`, `server_default="false"`, `default=False`.
- `created_at: Mapped[datetime]` / `updated_at: Mapped[datetime]` — timezone-aware, mirroring the `Subscription` model's timestamp columns (`onupdate` on `updated_at`).

**Semantics:** a missing row = opted-in (default behaviour). A row with `trial_reminder_opt_out=True` = the parent has opted out.

**Migration:** one hand-written, chained Alembic migration. Run `alembic heads` first and set `down_revision` to the current single head. `create_table` on upgrade, `drop_table` on downgrade.

## Section 2 — Config

In `app/services/premium_config.py` (alongside `PREMIUM_REQUEST_COOLDOWN_HOURS`):

```python
# Send the trial-ending reminder this many days before the trial converts to paid.
TRIAL_ENDING_REMINDER_DAYS: int = 2
```

## Section 3 — Email template

Add a `trial_ending` template to `app/services/email.py`, following the existing `premium_request` pattern (text in `_render`, html in `_render_html`, subject in `_SUBJECT`).

- `_SUBJECT["trial_ending"] = "Your InvestiKid trial ends soon"`
- **Context keys:** `child_label` (str — the child `username`(s) under that `parent_email`, joined for multiple, or `"your child"` when none/unknown — children have a `username`, not a real-name field, consistent with the `premium_request` template's `child_username`), `trial_end` (str — human date, e.g. `"Friday 12 June"`), `benefits` (list[str] — `PREMIUM_BENEFITS`), `manage_hint` (str — a short "open InvestiKid → parent dashboard to manage your plan" instruction; no price/checkout link, consistent with App Store 3.1.1 and the `premium_request` template).
- Text body (`_render`): greet, state that `{child_label}`'s free trial ends on `{trial_end}` and Premium continues after that, list benefits as `- ` bullets, then the manage hint. No price.
- Html body (`_render_html`): mirror the text, matching the styling of the existing `premium_request` html branch.

## Section 4 — Service

**New `app/services/trial_reminder_service.py`:**

- A module-level `uuid.UUID` namespace constant (reuse the project namespace `6f9619ff-8b86-d011-b42d-00c04fc964ff` used by `household_token`, or define a local one) for deterministic dedupe ids.
- `def _reminder_subject_id(subscription_id, period_end) -> uuid.UUID` — `uuid.uuid5(NAMESPACE, f"trial_ending:{subscription_id}:{period_end.date().isoformat()}")`. Stable across re-runs for the same trial.
- `async def run(session) -> dict`:
  1. Compute the window from a single `now = datetime.now(UTC)` and `TRIAL_ENDING_REMINDER_DAYS`: select `Subscription` rows where `provider == "stripe"`, `status == "trialing"`, and `now < current_period_end <= now + timedelta(days=TRIAL_ENDING_REMINDER_DAYS)`.
  2. For each row:
     - Compute `subject_id = _reminder_subject_id(sub.id, sub.current_period_end)`.
     - **Dedupe:** if a `SentEmail` with that `subject_id` already exists → skip (counts as `skipped`).
     - **Opt-out:** look up `ParentPreferences` by `sub.parent_email`; if `trial_reminder_opt_out` is `True` → skip.
     - Build `child_label` from `User` rows where `parent_email == sub.parent_email` (first names; fall back to `"your child"`).
     - Format `trial_end` from `sub.current_period_end`.
     - `await get_email_sender().send(session, to=sub.parent_email, template="trial_ending", context={...}, subject_id=subject_id)`.
     - Count as `sent`.
  3. `await session.commit()`.
  4. Return `{"sent": <int>, "skipped": <int>}`.

**Notes:** The `SentEmail`-by-`subject_id` check is the cap (one email per trial period) and is restart/re-run safe. `get_email_sender()` resolves to `LoggingEmailSender` (test/dev → persists to `sent_emails`) or `ResendEmailSender` (prod) — both write a `SentEmail` row, so dedupe works in every environment.

## Section 5 — Cron trigger

**Endpoint** in `app/routers/internal.py` (mirror `trigger_video_health` exactly):

```python
@router.post("/trial-reminders/run")
async def trigger_trial_reminders(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await trial_reminder_service.run(session)
```

**GitHub Action:** add a second step to the existing job in `.github/workflows/video-health-cron.yml` that POSTs to `$BACKEND_URL/internal/trial-reminders/run` with the `X-Cron-Secret` header, using the same `CRON_SECRET` guard pattern and 200-check as the video-health step. No new scheduled workflow.

> **Flag (not fixed here):** `video-health-cron.yml` still has the stale `BACKEND_URL: https://lee-local-code-repo-production.up.railway.app` (pre-migration name). Repointing prod URLs belongs to the CRON_SECRET cutover, not this feature — surface it, do not silently change prod config. The new step uses the same `$BACKEND_URL` var so both steps move together at cutover.

## Section 6 — Parent Settings opt-out

**Backend** (`app/routers/parent.py`, parent-auth via `get_current_parent`):
- `GET /parent/preferences` → `{ "trial_reminder_opt_out": bool }`. Returns `False` (opted-in) when no row exists.
- `PATCH /parent/preferences` body `{ "trial_reminder_opt_out": bool }` → upsert the `ParentPreferences` row for the authenticated `parent_email`; return the updated value.
- Pydantic v2 schemas in `app/schemas/parent_preferences.py` (`ParentPreferencesOut`, `ParentPreferencesUpdate`).

**Frontend:**
- `src/api/parent.ts` (or the existing parent API client): `getParentPreferences()` + `updateParentPreferences({ trialReminderOptOut })` via `apiFetch`.
- Parent **Settings** page: a toggle labelled *"Email me about my subscription"* (helper text: occasional reminders such as when a free trial is ending). ON when `trial_reminder_opt_out === false`. Uses TanStack Query (query + mutation, invalidate on success). Accessible (label association, keyboard, `aria`), matching existing Settings controls.

## Section 7 — Testing

**Backend (pytest, `loop_scope="session"`, `db_session`/`client` fixtures; patch the email sender as existing email tests do):**
- Service: sends + records `SentEmail` for an in-window Stripe trial; **skips** when a matching `SentEmail` (same `subject_id`) exists (dedupe); **skips** when `trial_reminder_opt_out=True`; **ignores** non-Stripe providers; **ignores** non-`trialing` status; **ignores** trials whose `current_period_end` is outside the window (too far out / already past); `child_label` falls back to `"your child"` when no children; return-summary counts.
- Endpoint: 503 when `cron_secret` unset; 401 on missing/mismatched header; 200 + summary on valid secret (use the real magic-link/secret patterns from existing tests).
- Preferences endpoints: `GET` returns `False` with no row; `PATCH` creates then updates the row; both require parent auth.

**Frontend (vitest + vitest-axe):**
- Settings toggle: renders from `getParentPreferences`, reflects state, calls `updateParentPreferences` on toggle, and has no axe violations.

**Verification:** backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. No iOS-visible surface (parent web/Settings only) → no `cap sync` required beyond the normal build.

## Out of scope

Event-driven nudges (repeated child requests, many premium locks); periodic value-recap digest; in-app dashboard banner; Apple/Google trial detection; any price/checkout in email (App Store 3.1.1); changes to the entitlement core, billing services, or the CRON_SECRET cutover itself (only flagged).

## Verification limits

The cron only runs end-to-end once `CRON_SECRET` is set on the backend and in GitHub Actions (the deferred cutover). Until then, the endpoint returns 503 by design and the service is fully covered by unit tests. Real email delivery (Resend) is exercised in prod only; tests use the logging sender.
