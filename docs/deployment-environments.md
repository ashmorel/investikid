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

## Provisioning status (2026-06-06)

**Railway (project `Invest-Ed`) — testing + staging DONE, production untouched.**
- **testing** → backend `https://lee-local-code-repo-testing.up.railway.app`; source `investikid@testing`, root `/backend`; own Postgres (`DATABASE_URL` = `${{ Postgres.DATABASE_URL }}` reference); migrated + seeded; `ENVIRONMENT=testing`, `EMAIL_BACKEND=logging`. Auto-deploys on push to `testing`.
- **staging** → backend `https://lee-local-code-repo-staging.up.railway.app`; source `investikid@staging`, root `/backend`; own Postgres (reference); full migration chain + seeded; `ENVIRONMENT=staging`, `EMAIL_BACKEND=logging`. Auto-deploys on push to `staging`.
- **production** → still on the old repo (`Lee-Local-Code-Repo`, `/invest-ed/backend`), own DB, **not migrated by the cutover**. Repoint later (gated, backup-first).
- ⚠️ testing + staging carry **forked production secrets** (live OpenAI/Together/Resend keys, `JWT_SECRET`, `CRON_SECRET`, DB password, `ADMIN_TOKEN`, `SECRET_KEY`). **Rotate / set test-only keys** — Coach Penny in non-prod currently bills your prod LLM accounts.
- `CORS_ORIGINS` + `APP_BASE_URL` in testing/staging still hold prod values — update to the Vercel branch URLs below.

**Vercel (project `investikid.ai`, team `lee-ashmore-s-projects`) — repoint PENDING / unverified.**
- As of this check, **all deployments (incl. live `app.investikid.ai`) are still from the old repo** `Lee-Local-Code-Repo@main` (`de1eae1`). No `investikid` deploy has occurred yet.
- To finish: Settings → Git → connect **`ashmorel/investikid`**; Build & Deployment → **Root Directory = `frontend`**; set env vars (below); protect the staging Preview.
- Verify the repoint by pushing to `testing` → a Preview should build from `investikid`.
- Predicted Vercel branch URLs (use for `VITE_WEB_ORIGIN` + the Railway `CORS_ORIGINS`/`APP_BASE_URL` above):
  - testing: `https://investikidai-git-testing-lee-ashmore-s-projects.vercel.app`
  - staging: `https://investikidai-git-staging-lee-ashmore-s-projects.vercel.app`
  - production: `https://app.investikid.ai`

**Frontend env vars per env** (`VITE_API_BASE_URL` → the matching Railway backend):
- testing → `https://lee-local-code-repo-testing.up.railway.app`
- staging → `https://lee-local-code-repo-staging.up.railway.app`
- production → the existing prod backend URL (unchanged)

## Related docs
- `docs/deployment-checkpoint.md` — how to run the manual checkpoint workflow.
- `docs/superpowers/specs/2026-06-06-invested-repo-environment-migration-design.md` — the original
  migration design.
