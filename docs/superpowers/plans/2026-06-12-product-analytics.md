# Product Analytics (M4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. (This run: executed inline by the controller with per-task TDD + commits.)

**Goal:** First-party COPPA-safe analytics per `docs/superpowers/specs/2026-06-12-product-analytics-design.md` — event table, server/client capture, retention integration, admin dashboard.

**Architecture:** New `AnalyticsEvent` model + `product_analytics_service.record()` seam; hooks in complete_lesson / set_premium / webhook trialing / digest send; batched authenticated ingest endpoint for 4 client events; SQL-aggregate admin summary endpoint + AdminAnalytics page; retention via FK SET NULL + purge hook + cron-driven raw-event deletion.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic; React 18 + TS + TanStack Query. Backend tests: `/Users/leeashmore/Local Repo/.venv/bin/pytest` from `backend/` with `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures. Branch `testing`. Commits end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: Model + migration + service seam
- [ ] `app/models/analytics.py` — `AnalyticsEvent` per spec table (allowlist constants `CLIENT_EVENTS`, `SERVER_EVENTS`, `ALLOWED_PROP_KEYS` live in the service).
- [ ] Register in `app/models/__init__.py`.
- [ ] Migration `chained off 9c3d5e2f0a7b` (hand-written, indexes on event_name/occurred_at/user_id).
- [ ] `app/services/product_analytics_service.py` — `async def record(session, name, *, user=None, role, props=None)`: snapshots age_tier (from user dob via existing age-tier helper) + is_premium, filters props to allowlist, adds row; wraps everything in try/except + log (never raises). Tests: row written with snapshots; bad prop keys dropped; exception swallowed (e.g. session mock that raises).
- [ ] Commit `feat(m4): AnalyticsEvent model + record() seam`.

### Task 2: Server-side hooks
- [ ] `complete_lesson` (content.py): record `lesson_completed` with module/level/lesson ids + `repeat=already`.
- [ ] `entitlements.set_premium`: record `subscription_activated` when transitioning to True (role from user).
- [ ] `webhook_service.handle_subscription_updated`: record `trial_started` on transition into `trialing`.
- [ ] `digest_service.run_weekly_digests`: record `digest_sent` (role='parent', user=child? No — digest is per parent; user_id = the parent has no User row (parents are email-keyed) ⇒ user=None, props={'surface':'weekly_digest'}). Tests for each hook.
- [ ] Commit `feat(m4): server-side analytics hooks`.

### Task 3: Ingest endpoint
- [ ] `app/routers/analytics.py` — `POST /analytics/events` per spec (batch ≤20, client-allowlist only, props filtered, 202 {accepted, dropped}, `@limiter.limit("120/hour")`, `Depends(get_current_user)`). Register router in main.py. Tests: 401 anon; accepts valid batch; drops server-only names + unknown props; caps batch at 20 (422 above); rate-limit decorator present.
- [ ] Commit `feat(m4): analytics ingest endpoint`.

### Task 4: Retention
- [ ] `settings.analytics_retention_days = 400`.
- [ ] `product_analytics_service.purge_old_events(session, now) -> int` (delete < now - retention days).
- [ ] `POST /internal/analytics-retention/run` (CRON_SECRET pattern copied from trial-reminders).
- [ ] `retention.purge_expired_accounts`: null `user_id` on events of purged users.
- [ ] Cron step added to `.github/workflows/video-health-cron.yml` (rides to main with this promotion).
- [ ] Privacy-notice paragraph in `docs/compliance/privacy-notice.md`.
- [ ] Import-surface unit test: `analytics` model imported only by service/admin router/migrations.
- [ ] Commit `feat(m4): analytics retention + privacy notice`.

### Task 5: Admin summary endpoint
- [ ] `GET /admin/analytics/summary?days=` in admin router (or `app/routers/admin_analytics.py` if admin.py is large): returns `{activation, cohorts[], funnel, engagement}` per spec, SQL aggregates only. Tests on seeded fixture: activation % (2 kids, 1 activated → 50), D7 cohort maths, funnel counts, tap-through %.
- [ ] Commit `feat(m4): admin analytics summary endpoint`.

### Task 6: Frontend client lib + wiring
- [ ] `src/lib/analytics.ts` — `track(name, props?)`: module queue, 5s debounce flush + visibilitychange flush, batch ≤20 via shared `apiFetch` (keepalive), silent catch, offline drop, `resetForTests()`. Tests: queue/flush/batch/silent-failure/offline.
- [ ] Wire: Home mount → `home_view` (once/session via module flag); HomeHero CTA onClick → `home_cta_tap`; QuickLinksRow chip onClick → `quicklink_tap{surface}`; `usePremiumPaywall.open` → `paywall_view{surface:kind}`. Tests assert track calls (mock the lib).
- [ ] Commit `feat(m4): client analytics lib + event wiring`.

### Task 7: AdminAnalytics page
- [ ] `src/api/admin.ts` (or sibling) summary fetcher; `src/components/admin/AdminAnalytics.tsx`: KPI cards, cohort table, funnel, engagement, 7/30/90 picker, loading/error per sibling pages; route + `AdminSidebar` item. Tests: renders summary fixture + axe.
- [ ] Commit `feat(m4): admin analytics dashboard`.

### Task 8: Full verification + push + docs
- [ ] Backend: ruff + full pytest. Frontend: tsc + lint + vitest + build (+ cap sync ios — no native change).
- [ ] Push `testing`, CI green.
- [ ] Mark M4 done in `docs/2026-06-12-market-leader-roadmap.md`; update memory.
