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
3. Set per-environment env vars (`VITE_API_BASE_URL`, `VITE_WEB_ORIGIN`, `VITE_*` social IDs)
   pointing each env at its matching Railway backend.

### Railway
1. Create environments `testing`, `staging`, `production`.
2. Map each to its branch; **enable auto-deploy on `testing`/`staging`, keep `production`
   manual / approval-gated** (matches manual promotion).
3. **Testing DB = a snapshot of the current prod DB** (prod holds only test data today). Give
   testing its own database + test-only secrets.
4. Per-env vars: `ENVIRONMENT`, `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `APP_BASE_URL`,
   `CRON_SECRET`, etc.
5. **Staging migration safety:** if staging ever points at the live production database, do **not**
   run schema migrations against it. Either disable deploy-time `alembic upgrade head` for the
   staging service or point staging at a production-clone/rehearsal DB. (`railway.json`'s start
   command migrates on every deploy — override it per-environment for staging.)

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

## Related docs
- `docs/deployment-checkpoint.md` — how to run the manual checkpoint workflow.
- `docs/superpowers/specs/2026-06-06-invested-repo-environment-migration-design.md` — the original
  migration design.
