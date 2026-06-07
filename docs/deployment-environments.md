# InvestiKid — Deployment Environments

Single source of truth for how InvestiKid promotes code from development to real users.
Supersedes the branch/env notes in `deployment-checkpoint.md` (which now only documents the
manual checkpoint workflow).

## The three environments

| Env | Branch | Purpose | Database | Audience | iOS/Android |
|-----|--------|---------|----------|----------|-------------|
| **Testing** | `testing` | Build & validate every new feature | **Separate test DB — a snapshot of prod** | You | Built **on demand only** |
| **Staging** | `staging` | Promote what passed testing; beta channel | **Own DB — its own snapshot of prod** | **Selected beta-testers only** | Built on demand |
| **Production** | `main` | The live app | Production | Everyone (after beta) | TestFlight / App Store |

**Three separate databases.** testing, staging, and production each have their **own** database
(testing + staging are snapshots of prod). This is what lets new migrations run on staging for
beta-testers **without touching production**. Never point staging at the live production database.

**Promotion flow:** build on `testing` → promote to `staging` for beta-testers → promote to
`main` for everyone. Promote by fast-forwarding the branch (`git checkout staging && git merge
--ff-only testing && git push`, then the same `staging → main`).

## How deploys actually happen

- **GitHub Actions (`ci.yml`)** only *validates* — frontend, backend, security, a11y, responsive.
  It runs on push to `main`, `staging`, `testing` and on PRs into `main`/`staging`. It is
  **ubuntu-only**: it never builds iOS or Android, so it doesn't burn macOS minutes.
- **Vercel** deploys the frontend via its own Git integration, per branch (see `frontend/vercel.json`).
- **Railway** deploys the backend via its own Git integration, per branch/environment.
- **iOS/Android** are built **only** by the manual **Deployment checkpoint** workflow
  (`Actions → Deployment checkpoint → Run workflow`), with explicit `run_ios` / `run_android`
  toggles (default off). Nothing native builds automatically.

## Database migrations & data across environments

The Railway start command runs on **every** backend deploy of **every** environment:
`alembic upgrade head && python -m app.seed.run && uvicorn …`. Because each environment has its
own `DATABASE_URL`, a new migration is applied to **that env's database** on deploy. So schema
changes ride the code promotion automatically: `testing` DB → `staging` DB → `production` DB.

- **Schema (Alembic migrations)** — in code, promote via git, applied per-env on deploy. ✅
- **Baseline content** (`backend/app/seed/`) — in code, promotes via git, seeded idempotently. ✅
- **Admin-authored content/data** — lives **only in that environment's database** and does **NOT**
  promote via git. Premium content authored in staging's admin will not appear in prod. For
  content that must exist everywhere, author it as **seed code** (promotes cleanly) rather than
  via the admin panel.

## Production promotion checklist (REQUIRED before every prod migration)

Production is **manual promotion**. Before promoting code to `main` / triggering the production
deploy (which runs `alembic upgrade head` against the live prod DB):

1. **🛑 Take a production database backup / snapshot FIRST.** The assistant MUST ask the user
   whether to take a backup before every production migration, and wait for an answer. Use
   Railway's DB snapshot (or `pg_dump`) before the prod deploy runs the migration.
2. Confirm the migration has already been applied + validated on testing **and** staging.
3. Promote (`git checkout main && git merge --ff-only staging && git push`).
4. Trigger the manual Railway production deploy (and Vercel "Promote to Production").

**Production cutover one-offs (do once, when moving prod onto `ashmorel/investikid`):**
- **Repoint prod backend domain** (optional): currently `lee-local-code-repo-production.up.railway.app`. If renamed to `investikid-production`, also update the cron workflow `BACKEND_URL` (`.github/workflows/video-health-cron.yml`) and any client referencing it.
- **Rotate prod secrets** (were exposed in old git history): `JWT_SECRET`, `SECRET_KEY`, `ADMIN_TOKEN`, `CRON_SECRET`, `RESEND_API_KEY` — give prod its own values, distinct from testing/staging.
- **`CRON_SECRET` is coupled** — change it in **two places at once**: Railway **production** env var **and** the GitHub **repo Actions secret** `CRON_SECRET` (same value). Test via Actions → "Video health cron" → Run workflow (expect HTTP 200).
  - ✅ **GitHub Actions secret `CRON_SECRET` now exists** in `ashmorel/investikid` (set 2026-06-07). At cutover, set the **production** Railway `CRON_SECRET` to **match this same value** (or rotate both together).
  - The cron workflow now reads `BACKEND_URL` from a **repo Actions variable** (`${{ vars.BACKEND_URL || '<prod default>' }}`). It is currently set to `https://investikid-testing.up.railway.app` for validation. **At cutover, repoint or delete** `vars.BACKEND_URL` so the scheduled (default-branch) run targets the production backend — `gh variable set BACKEND_URL --body <prod-url>` or `gh variable delete BACKEND_URL` to fall back to the hardcoded default. ⚠️ The workflow change lives on `testing`; `main`'s copy is still the old hardcoded version — fold the `vars.BACKEND_URL` edit into `main` at cutover too.
- **Pipeline validated against `testing` (2026-06-07):** `CRON_SECRET` set on the **testing** Railway backend + GitHub Actions secret (matched); manual `workflow_dispatch --ref testing` returned **HTTP 200** `{"ok":2,"dead":0,"unknown":0}`. The workflow was then **re-disabled** so the daily schedule (which runs from `main` → still the unmigrated prod host) doesn't resume failing before cutover.
- **Re-enable the cron** — the `Video health cron` workflow is currently **disabled** (`disabled_manually`). After the production `CRON_SECRET` + `BACKEND_URL` are set for prod (above), run `gh workflow enable "Video health cron"`.
- **Vercel production env vars** (`VITE_API_BASE_URL`, `VITE_WEB_ORIGIN`) read back empty via CLI — verify/set them before/at cutover.

## Repo configuration that supports this (already in place)

- `frontend/vercel.json` → `git.deploymentEnabled`: `main: false` (production = **manual
  promotion**), `staging: true`, `testing: true`.
- `.github/workflows/ci.yml` → triggers on `main`/`staging`/`testing`; GitHub-environment name
  resolves `main`→`production`, `staging`→`staging`, else `testing`.
- `.github/workflows/deployment-checkpoint.yml` → `target_environment` choices `testing` /
  `staging` / `production`; production checkpoints are guarded (must run from `main` + require
  notes). Opt-in `run_ios` / `run_android`.
- `backend/railway.json` → start command runs `alembic upgrade head` then seed then uvicorn.
  ⚠️ See the staging migration note below.

## What YOU configure on the platforms (one-time)

These need dashboard access and are not in the repo.

### Vercel
1. Import `ashmorel/investikid`; **Root Directory = `frontend`**.
2. Branch → environment:
   - `testing` → Preview (auto-deploys; `vercel.json` enables it).
   - `staging` → Preview, **protected** (Deployment Protection / password / SSO so only your
     beta-testers can reach it).
   - `main` → Production, **auto-deploy disabled** (`vercel.json` `main: false`); you click
     **Promote to Production** after beta sign-off.
3. Per-environment env vars (scope each to Production / Preview-or-branch). Point each env's
   `VITE_API_BASE_URL` at the matching Railway backend, and ensure that Railway env's
   `CORS_ORIGINS`/`APP_BASE_URL` point back at this Vercel URL.
   - `VITE_API_BASE_URL` — that env's Railway backend URL
   - `VITE_WEB_ORIGIN` — that env's Vercel URL
   - `VITE_GOOGLE_WEB_CLIENT_ID`, `VITE_GOOGLE_IOS_CLIENT_ID`, `VITE_APPLE_SERVICES_ID`
     — only if testing social login in that env

### Railway
1. Create environments `testing`, `staging`, `production`.
2. Map each to its branch; **enable auto-deploy on `testing`/`staging`, keep `production`
   manual / approval-gated** (matches manual promotion).
3. **Three separate databases.** `testing` DB = a snapshot of prod; `staging` DB = its own
   snapshot of prod; `production` = the real DB. (Prod holds only test data today, so snapshot
   it twice: Railway database → restore-to-new, or `pg_dump` prod → `pg_restore` into each.)
   The backend auto-runs `alembic upgrade head` on every deploy (`railway.json`), so migrations
   land per-env as code promotes. Because staging has its **own** DB, that auto-migrate is safe —
   beta-testers exercise new schema without touching prod. Keep **production** auto-deploy
   off/approval-gated so a prod migration only runs on your explicit deploy.

4. **Env vars per environment** (Railway → service → Variables):

   *Required (core):*
   - `DATABASE_URL` — that env's Postgres URL
   - `TEST_DATABASE_URL` — same DB or a throwaway (only the test runner uses it; can equal `DATABASE_URL`)
   - `JWT_SECRET` — unique random secret **per env**
   - `ENVIRONMENT` — `testing` | `staging` | `production`
   - `CORS_ORIGINS` — that env's Vercel URL(s), comma-separated
   - `APP_BASE_URL` — that env's Vercel URL (email links incl. the premium-request email → `/parent`)
   - `CRON_SECRET` — **rotate it** (was exposed before); unique per env
   - `ADMIN_BOOTSTRAP_EMAIL` — admin account seeded on deploy

   *Email (premium-request + consent/verify emails):*
   - `EMAIL_BACKEND` — `logging` (testing/staging) or `resend` (production)
   - `EMAIL_FROM`, `RESEND_API_KEY` (if backend=resend), `ADMIN_ALERT_EMAIL`, `FEEDBACK_NOTIFY_EMAIL`

   *Feature-gated (set where the feature should be live):*
   - **AI (Coach Penny / greeting):** `LLM_TOGETHER_API_KEY` (+ `LLM_GROQ_*` / `LLM_PREMIUM_*` if used)
   - **Billing (4A):** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `STRIPE_PORTAL_CONFIG_ID`
   - **Social login:** `GOOGLE_WEB_CLIENT_ID`, `GOOGLE_IOS_CLIENT_ID`, `APPLE_SERVICES_ID`, `APPLE_BUNDLE_ID`
   - `REDIS_URL` (rate limiting, if you run Redis)

### GitHub
1. `Settings → Environments`: create `testing`, `staging`, `production`.
2. Protect `production`: required reviewers + deployment branch restricted to `main`.
3. Restrict `staging` deployment branch to `staging`.
4. Add any environment secrets CI needs.

### iOS (TestFlight)
- `cd frontend && npm run build && npx cap sync ios` (already run for the current `main`),
  then open `ios/App` in Xcode, archive, and upload to TestFlight. Signing/certs are yours.
- For a CI-built artifact instead, run the **Deployment checkpoint** workflow with `run_ios=true`.

## Security pre-public checklist (before making the repo public)
- Rotate any secrets that were ever tracked (the old monorepo tracked `frontend/.env.production`)
  and rotate `CRON_SECRET`.
- Confirm no `.env*` is tracked here (only `backend/.env.example` should be) and run `gitleaks`.
- Enable GitHub secret scanning.

## Provisioning status (2026-06-07)

**Railway (project `Invest-Ed`, service renamed `InvestiKid`) — testing + staging DONE, production untouched.**
- **testing** → backend `https://investikid-testing.up.railway.app`; source `investikid@testing`, root `/backend`; own Postgres (`DATABASE_URL` = `${{ Postgres.DATABASE_URL }}` reference); migrated + seeded; `ENVIRONMENT=testing`, `EMAIL_BACKEND=logging`. Auto-deploys on push to `testing`.
- **staging** → backend `https://investikid-staging.up.railway.app`; source `investikid@staging`, root `/backend`; own Postgres (reference); full migration chain + seeded; `ENVIRONMENT=staging`, `EMAIL_BACKEND=logging`; `CORS_ORIGINS` set to the staging Vercel origin. Auto-deploys on push to `staging`.
- **production** → still on the old repo (`Lee-Local-Code-Repo`, `/invest-ed/backend`), domain still `lee-local-code-repo-production.up.railway.app`, own DB, **not migrated by the cutover**. Repoint later (gated, backup-first).
- ⚠️ testing + staging carry **forked production secrets** (live OpenAI/Together/Resend keys, `JWT_SECRET`, `CRON_SECRET`, DB password, `ADMIN_TOKEN`, `SECRET_KEY`), and they're **identical across both envs**. **Rotate / set unique test-only keys** — Coach Penny in non-prod currently bills your prod LLM accounts.
- `APP_BASE_URL` in testing/staging still = `app.investikid.ai` (prod). Only affects email links, and email is `logging` in these envs, so low impact — repoint to the branch URLs if you want fully correct links.

**Vercel (project `investikid.ai`, team `investikid`) — repoint CONFIRMED + env wired; production cutover pending.**
- **Git connection points at `ashmorel/investikid`** ✅ (Preview builds for `testing`/`staging` come from repo id `1260927337`). Root Directory = `frontend` ✅ (Vite builds succeed).
- **Branch-scoped env vars set via Vercel CLI** ✅ (`vercel env ls`):
  - `VITE_API_BASE_URL` — Preview/`testing` → `https://investikid-testing.up.railway.app`; Preview/`staging` → `https://investikid-staging.up.railway.app`
  - `VITE_WEB_ORIGIN` — Preview/`testing` + Preview/`staging` → the branch URLs below
  - the old all-branches Preview `VITE_API_BASE_URL` was removed. testing + staging redeployed to bake in the new values.
- **Preview deployments are auth-protected** (Vercel Authentication, default on Hobby) → reachable only by the Vercel team account, not anonymous/beta users. No password protection on Hobby — for beta access to staging, plan an **app-level allowlist** rather than Vercel protection.
- **production** → still serving the **old-repo** build (`Lee-Local-Code-Repo@main` `de1eae1`); `vercel.json` `main:false` = no auto-build. **Cutover is a deliberate step** (frontend-only, no DB migration). Prod `VITE_*` values read back empty via CLI (likely Sensitive-flagged) — verify/set them at cutover.
- **⚠️ Vercel team slug is `investikid`** (was `lee-ashmore-s-projects`). Use the **`-investikid`** branch aliases below — the old `-lee-ashmore-s-projects` aliases still resolve but serve a **stale pre-migration build** (baked the old prod backend). `CORS_ORIGINS` (Railway) + `VITE_WEB_ORIGIN` (Vercel) are set to the `-investikid` origins.
- Vercel branch URLs (current/canonical):
  - testing: `https://investikidai-git-testing-investikid.vercel.app`
  - staging: `https://investikidai-git-staging-investikid.vercel.app`
  - production: `https://app.investikid.ai`

## Related docs
- `docs/deployment-checkpoint.md` — how to run the manual checkpoint workflow.
- `docs/superpowers/specs/2026-06-06-invested-repo-environment-migration-design.md` — the original
  migration design.
