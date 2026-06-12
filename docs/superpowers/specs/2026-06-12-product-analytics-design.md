# Privacy-Safe Product Analytics (M4) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M4 of `docs/2026-06-12-market-leader-roadmap.md` · **Owner-approved** (design presented + approved in session).

## Goal

Make the roadmap's KPI table measurable — activation, D7/D30 retention, trial funnel,
digest sends, and the M3 Home hero tap-through — with **first-party, COPPA/AADC-safe**
event capture and an admin dashboard. No third-party trackers anywhere; counts and
funnels, never behavioural profiles.

## Data model

New table `analytics_events` (Alembic migration chained off head `9c3d5e2f0a7b`):

| column | type | notes |
|---|---|---|
| id | UUID PK | default uuid4 |
| event_name | String(50), indexed | closed allowlist (below) |
| occurred_at | DateTime(tz), indexed | server clock for server events; client timestamp ignored (server receive time used) |
| user_id | UUID FK users.id, ON DELETE SET NULL, nullable, indexed | pseudonymous join key for cohorts |
| role | String(10) | 'child' \| 'parent' |
| age_tier | String(10), nullable | snapshot at event time |
| is_premium | Boolean, nullable | snapshot at event time |
| props | JSON, nullable | allowlisted keys only: `module_id`, `level_id`, `lesson_id`, `surface`, `repeat`, `plan`, `source` |

Deliberately **no** IP address, no user-agent, no free text (tighter than `AuditLog`).

## Event allowlist (v1)

**Server-recorded** (in `app/services/product_analytics_service.py: record(session, name, *, user=None, role, props=None)` — fire-and-forget semantics, never raises into the caller; flush rides the caller's transaction):
- `lesson_completed` — in `content.py complete_lesson` after `_award_completion` (props: module_id, level_id, lesson_id, repeat=already)
- `subscription_activated` — in `entitlements.set_premium` when value becomes True (props: source if available)
- `trial_started` — in `webhook_service.handle_subscription_updated` when status transitions to `trialing` (Stripe only in v1; Apple/Google trials deferred — note in dashboard footer)
- `digest_sent` — in `digest_service.run_weekly_digests` per successful send (role='parent')

**Client-recorded** via `POST /analytics/events` (child session required):
- `home_view` (once per Home mount, throttled to 1/session in the client lib)
- `home_cta_tap` (hero Continue CTA — the M3 success metric; props: surface='hero')
- `quicklink_tap` (props: surface='portfolio'|'review'|'badges')
- `paywall_view` (in `usePremiumPaywall.open`; props: surface=kind)

## Ingest endpoint

`POST /analytics/events` (router `app/routers/analytics.py`): body
`{ events: [{ event_name, props? }] }`, max 20/batch. Auth = `get_current_user`
(child session; CSRF normal). Validation: event_name must be in the CLIENT allowlist
(server-only names rejected), props filtered to allowlisted keys, values coerced to
short strings/bool. Rate-limited `@limiter.limit("120/hour")` keyed by user. Response
202 `{accepted: n}`. Unknown names/keys are silently dropped (counted in response),
never 4xx — the client must never break the app over analytics.

Client lib `frontend/src/lib/analytics.ts`: `track(name, props?)` — in-memory queue,
flush (batch) on 5s debounce and on `visibilitychange→hidden` via `fetch(..., {keepalive: true})`
through the shared session/CSRF `apiFetch` wrapper; silent catch; no-ops offline
(`navigator.onLine === false` drops events — no persistence, by design); no-ops for
unauthenticated pages.

## Privacy spine

- Events are service-improvement counts; they are **never read by personalization
  paths**, so the `profiling_enabled` AADC gate is structurally untouched. Enforced
  structurally: the model is imported only by `product_analytics_service.py` and the admin
  analytics router — a unit test greps the app package to pin this invariant.
- **Account deletion**: FK `ON DELETE SET NULL` covers hard deletes; `retention.purge_expired_accounts`
  additionally nulls `user_id` on events of purged accounts (soft-deleted users keep rows
  joinable until purge, matching the existing PII window).
- **Raw-event retention**: events older than `analytics_retention_days` (default 400)
  are deleted by `POST /internal/analytics-retention/run` (CRON_SECRET-guarded, same
  pattern as trial-reminders); a new step in `.github/workflows/video-health-cron.yml`
  on `testing` rides to `main` with this feature in the same promotion (4C gotcha
  respected — endpoint and step promote together).
- `docs/compliance/privacy-notice.md` gains a short "Product analytics" paragraph
  (first-party, pseudonymous, what's collected, retention, no third parties).

## Admin dashboard

`GET /admin/analytics/summary?days=30` (admin-gated, sibling of existing admin routes)
returns one JSON payload computed with SQL aggregates:
- `activation`: % of child accounts created in window with a `lesson_completed` within
  24h of `users.created_at` (joins users ↔ events).
- `cohorts`: per signup-week (last 8): signups, % with any child event in days 7–13
  (D7), days 28–34 (D30).
- `funnel`: counts of paywall_view → trial_started → subscription_activated in window.
- `engagement`: home_view count, home_cta_tap count + tap-through % (cta/views),
  quicklink_tap by surface, lesson_completed count, digest_sent count.

Frontend: new **Analytics** item in `AdminSidebar` → `AdminAnalytics.tsx` page:
KPI cards + cohort table + funnel row + engagement row, range picker (7/30/90 days),
loading/error states per existing admin pages, vitest-axe test.

## Out of scope (v1, noted in dashboard footer where relevant)

`/try` demo tracking (preserves W7's zero-API surface) · digest opens (Resend dashboard)
· crash-free sessions (separate tooling decision) · Apple/Google trial events ·
event-level admin browsing (aggregates only).

## Testing plan

Backend: model/migration smoke; analytics_service.record (snapshot fields, never raises);
ingest endpoint (auth 401, allowlist filtering, batch cap, server-name rejection, rate-limit
key); event hooks (complete_lesson records with repeat flag; set_premium True records;
webhook trialing transition records; digest send records); retention endpoint (deletes old,
keeps new, CRON_SECRET guard); purge nulls user_id; admin summary maths on a seeded
fixture (activation %, D7 cohort, funnel, tap-through). Async tests use
`pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session`
fixtures per repo convention.

Frontend: analytics lib (queue/flush/batch cap/silent failure/offline no-op — mock fetch);
track-call wiring (Home mount fires home_view once; hero CTA fires home_cta_tap;
quicklink fires with surface; paywall open fires paywall_view); AdminAnalytics renders
summary + axe. Full gates: ruff + pytest; tsc + lint + vitest + build.
