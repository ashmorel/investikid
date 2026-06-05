# Video-Health Trigger Endpoint + Scheduled Workflow — Design

**Status:** Approved (design); pending spec review.
**Date:** 2026-06-05
**Context:** The video-health check has a working CLI (`python -m app.video_health.run`), but running it as a **separate Railway cron service** proved fragile: it needs the whole backend env mirrored, the start-command overridden, has confusing "no logs until the scheduled tick" behaviour, and a misleading crashed/failed deploy status. This replaces that with a secret-guarded HTTP trigger on the **already-running backend** plus a tiny scheduled GitHub Actions workflow.

## Goal
Run the periodic dead-video check reliably and verifiably, without a second Railway service or duplicated config.

## Architecture
A new `POST /internal/video-health/run` endpoint on the existing backend runs the same check + dead-alert email as the CLI (reusing `app.video_health.run.run`). It's authenticated by a shared secret header (not the user session), and CSRF-exempt (machine caller). A scheduled GitHub Actions workflow `curl`s it daily with the secret from a repo secret; a non-2xx response fails the workflow (so breakage is visible in GitHub). Anyone could instead point a Railway `curl` cron / cron-job.org at the same endpoint.

## Components

1. **Config** (`app/core/config.py`): `cron_secret: str = ""`. Documented in `backend/.env.example`. When empty, the endpoint is disabled (`503 not_configured`) — the feature is opt-in, like R2/OAuth.
2. **Endpoint** — `POST /internal/video-health/run` in a new `app/routers/internal.py` (router with NO `get_current_admin` dependency; auth is the secret):
   - If `not settings.cron_secret` → `503` `{"detail":"not_configured"}`.
   - Read header `X-Cron-Secret`; compare with `secrets.compare_digest`. Missing/wrong → `401` `{"detail":"unauthorized"}`.
   - On success: `summary = await run(session)` (the existing `app/video_health/run.py::run`, which checks all videos, upserts `video_health`, emails `admin_alert_email` recipients only when dead, and commits). Return `{ "ok": int, "dead": int, "unknown": int }` (the summary minus the internal `dead_items`, or the full summary — keep it small).
   - Register the router in `app/main.py`.
3. **CSRF exemption** — add the exact path `/internal/video-health/run` to `app/core/csrf.py` `_DEFAULT_EXEMPT_PATHS` (machine POST with no CSRF cookie/token; the secret is the auth), mirroring the Stripe-webhook / OAuth exemptions.
4. **GitHub Actions workflow** — `.github/workflows/video-health-cron.yml`:
   - `on: schedule: - cron: "0 6 * * *"` + `workflow_dispatch` (manual run button).
   - One job: `curl -fsS -X POST -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}" "${{ secrets.BACKEND_URL }}/internal/video-health/run"`. `-f` makes a non-2xx exit non-zero → the workflow (and its email/UI) flags failures.
   - Requires two **GitHub repo secrets** (user sets): `BACKEND_URL` (the Railway backend base URL) + `CRON_SECRET` (same value as the backend env).

## Security
- Secret compared with `secrets.compare_digest` (constant-time). The endpoint is idempotent and only triggers an internal check + an alert email — low blast radius even if the secret leaked. No PII in the response. Disabled by default (`cron_secret` empty). Not rate-limited (secret-gated + idempotent); can add later if abused.

## Out of scope
- Removing the `python -m app.video_health.run` CLI — keep it (still useful for manual/one-off runs and as the shared `run()` the endpoint reuses).
- The fragile separate Railway cron service (superseded; the user can delete it).

## Testing
- **Backend:** `503` when `cron_secret` unset; `401` when header missing or wrong; `200` + runs the check when the secret matches (monkeypatch `internal.run`/the checker so no real network — assert it's called and the summary is returned); the endpoint is reachable via POST without a CSRF token (CSRF-exempt — not a 403-for-CSRF). Async tests use `pytestmark loop_scope="session"` + `client`/`db_session`; no real network. 
- **Workflow:** lint-only (YAML well-formed; the curl step shape). Not executed in CI tests (it hits prod on schedule).
- `ruff` + `pytest`; `tsc -b`/lint/test/build unaffected (no FE change); CI 6 jobs green.

## User setup (one-time)
Set `CRON_SECRET` on the **Railway backend** env (any long random string) and add two **GitHub repo secrets**: `CRON_SECRET` (same value) + `BACKEND_URL` (the Railway backend URL). Then GitHub Actions runs it daily; the workflow's "Run workflow" button triggers an immediate test, and the run's log shows the JSON summary. Delete the separate Railway cron service.

## Plan shape
T1 `cron_secret` config + CSRF exemption + the `/internal/video-health/run` endpoint (reusing `run()`) + tests → T2 the scheduled GitHub Actions workflow + docs (PROGRESS/AGENTS + setup note) → regression + push.

## Decisions captured
Secret-guarded HTTP trigger on the existing backend (reuses the tested `run()`); CSRF-exempt; `503` when unset; GitHub Actions scheduler (repo-native, fail-visible) with `BACKEND_URL`+`CRON_SECRET` repo secrets; same endpoint works for a Railway `curl` cron. Replaces the separate Railway cron service.
