# Monitoring & Incident Runbook

**Purpose:** What to watch in production, how to tell healthy from broken, and how to respond. Scoped to the live stack: backend on **Railway** (`api.investikid.ai`), web on **Vercel** (`app.investikid.ai`), Postgres on Railway, scheduled jobs via **GitHub Actions**.

## Health at a glance
| Signal | Healthy | Where |
|---|---|---|
| Backend | `GET https://api.investikid.ai/health` → 200 | Railway service logs (`railway logs`) |
| Web | `https://app.investikid.ai` → 200, app loads | Vercel dashboard / deployment logs |
| DB | queries return; `alembic heads` = single head, prod migrated | Railway Postgres |
| Auth | `POST /auth/login` (bad creds) → 401 JSON; `/users/me` preflight 200 | — |

## Scheduled jobs (daily, GitHub Actions `video-health-cron.yml`, **06:00 UTC**)
All are `POST /internal/*`, gated by the `X-Cron-Secret` header (`CRON_SECRET`). A run is healthy when each returns **200**.
| Endpoint | Does | If it fails |
|---|---|---|
| `internal/video-health/run` | flags dead lesson videos | broken videos surface in Admin → Video health; emails `ADMIN_ALERT_EMAIL` |
| `internal/trial-reminders/run` | trial-ending nudges | reminders skipped that day |
| `internal/push-streak-risk/run` | streak-risk push | nudges skipped |
| `internal/analytics-retention/run` | prunes old analytics | data grows; not user-facing |
| `internal/weekly-digest/run` | parent weekly digest | digest skipped (sends weekly) |
| `internal/subscriptions/reconcile` | **re-pulls Stripe/Apple/Google state** so a missed billing webhook self-heals | premium entitlements may drift until next run — **prioritise** |
| `internal/purge-archived-modules` | hard-deletes >30-day-archived modules | cleanup deferred; harmless short-term |

**Cron failure triage:** `401`=GitHub vs backend `CRON_SECRET` mismatch; `503`=`CRON_SECRET` unset on backend; `404`=backend not serving / wrong `BACKEND_URL` Actions var; `5xx`=app error (check `railway logs`). Re-run: GitHub → Actions → "Video health cron" → Run workflow.

## Common incidents
**Web login broken ("Could not start your session").** Almost always the cross-site cookie regression: check Vercel Production `VITE_API_BASE_URL` = `https://api.investikid.ai` (NOT the railway URL) and that the live bundle greps `api.investikid.ai`=1. Fix: correct the env var, redeploy web, re-alias. See `docs/deployment-environments.md`.

**Backend down / 5xx after deploy.** Check Railway deploy logs for a failed `alembic upgrade head` (migration error) or a bad env var. Roll back: redeploy the previous green commit in Railway. Railway only deploys on green `main` CI.

**Premium not unlocking after purchase.** A webhook was likely missed. Confirm the daily `subscriptions/reconcile` ran; to force it, re-run the cron workflow. Stripe (web), Apple (`apple_billing_service`), Google (`google_billing_service`) each have their own webhook path (`webhook_service`).

**Bad/again unsafe AI output.** All LLM output is moderated (`moderate_output`) + topical guardrails. If something slips, capture the message, check `railway logs`, and tighten the guardrail corpus. LLM endpoints are rate-limited and premium-gated.

**Dead lesson video.** Surfaces via the video-health cron in Admin → Video health; swap the video URL in the admin lesson editor.

## Rollback quick reference
- **Backend:** Railway → redeploy previous green deployment.
- **Web:** `vercel alias set <previous-deployment> app.investikid.ai` (instant).
- **DB migration:** migrations are forward-only; if a migration is bad, fix-forward with a new migration (ask about a prod snapshot first).

## Gaps / TODO (set up before/at public launch)
- Automated alerting on: backend 5xx rate, cron non-200, reconcile failures (currently manual — check the daily Actions run).
- Cost alerts: Railway, Vercel, Cloudflare R2 (video bandwidth), LLM provider spend.
- An on-call owner + escalation path.
