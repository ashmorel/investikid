# InvestiKid Repo Split and Environment Promotion Design

## Goal

Move `invest-ed/` into its own GitHub repository and configure a clear promotion path:

1. **Testing** by default for day-to-day development.
2. **Staging** for controlled validation against production-like or production data with limited user access.
3. **Production** only after explicit approval.

## Current State

- InvestiKid lives inside the broader `Lee-Local-Code-Repo` monorepo at `invest-ed/`.
- GitHub Actions currently live at the monorepo root in `.github/workflows/`.
- Vercel deploys the frontend from `invest-ed/frontend/`.
- Railway deploys the backend from `invest-ed/backend/`.
- Recent local work added:
  - a `testing` branch
  - a manual `Deployment checkpoint` workflow
  - Vercel config disabling automatic `main` deploys and enabling `testing`
- `invest-ed/frontend/.env.production` is tracked in git and must be removed from tracking before any public repo move.

## Target Repository

Create a dedicated repository, recommended name:

```text
ashmorel/investikid
```

The new repository root should be the current `invest-ed/` folder contents:

```text
backend/
frontend/
docs/
AGENTS.md
```

Root-level GitHub Actions should move into the new repo:

```text
.github/workflows/ci.yml
.github/workflows/deployment-checkpoint.yml
.github/workflows/video-health-cron.yml
```

Paths inside workflows must be rewritten because `invest-ed/` will become the repo root:

- `invest-ed/frontend` -> `frontend`
- `invest-ed/backend` -> `backend`
- `invest-ed/docs` -> `docs`

## Environment Model

### Testing

Purpose:
- Default deployment target for normal code updates.
- Uses test database and non-production service credentials.
- Can build/test web, iOS, and Android without touching production.

Branch:

```text
testing
```

Vercel:
- Preview environment.
- Auto-deploy from `testing`.
- `VITE_API_BASE_URL` points to Railway testing backend.

Railway:
- Permanent `testing` environment.
- Backend service deploys from `testing`.
- Separate testing Postgres database.
- Test-only secrets.

iOS/Android:
- Manual GitHub Actions checkpoint builds.
- iOS works now.
- Android remains future-ready until `@capacitor/android` and `frontend/android/` exist.

### Staging

Purpose:
- Controlled validation after testing passes.
- Uses production data access for controlled validation, but is restricted to a limited user group.
- Intended for release candidates and final sign-off.
- Schema-changing database migrations must be rehearsed against a production clone or migration rehearsal database, not directly against the live production database.

Branch:

```text
staging
```

Vercel:
- If Vercel custom environments are available, create `staging`.
- Otherwise use Preview deployment from the `staging` branch and protect it with Vercel Deployment Protection / Password Protection / SSO.

Railway:
- Permanent `staging` environment.
- Backend service deploys from `staging`.
- Use tightly controlled production database credentials for read/application validation only.
- Disable automatic deploy-time migrations in staging if it points at the live production database.
- Add a separate migration rehearsal database cloned from production for Alembic migrations and destructive/write-heavy tests.
- Restrict access at application level and platform/network level.

Access:
- Add an app-level allowlist or admin-only gate before exposing staging with production data.
- Do not rely only on an obscure URL.
- Use a restricted staging database role wherever possible. If write access is required for specific staging workflows, limit it to controlled user accounts and never run schema migrations against the live production database from staging.

### Production

Purpose:
- Real users.
- Manual release only.

Branch:

```text
main
```

Vercel:
- Production environment tracks `main`.
- Automatic Git deploys from `main` disabled or production deploys require manual promotion.

Railway:
- Production environment.
- Disable production auto-deploy from `main` or require manual deploy/approval.

GitHub Actions:
- `Deployment checkpoint` requires:
  - `target_environment=production`
  - run from `main`
  - explicit notes
  - selected validation/builds

## Public Repo Security Requirements

Before making any repo public:

- Remove tracked env files, especially `frontend/.env.production`.
- Add `.env.*` ignore rules while allowing `.env.example`.
- Rotate any values that ever appeared in tracked env files.
- Rotate `CRON_SECRET`, already flagged as previously pasted during debugging.
- Run a real secret scanner such as `gitleaks`.
- Enable GitHub secret scanning once the repo is public or if GitHub Advanced Security is available.

## History Strategy

There are two viable approaches:

### Option A: Clean New History

Create a fresh `investikid` repository from the current `invest-ed/` tree with a new initial commit.

Pros:
- Simplest public-readiness path.
- Avoids carrying old monorepo history and tracked env-file history into a public repo.
- Best default if the repo may become public.

Cons:
- Loses detailed commit history for `invest-ed/`.

### Option B: Preserve Filtered History

Use `git filter-repo --path invest-ed/ --path .github/workflows/... --path-rename invest-ed/:` and then clean sensitive files from history.

Pros:
- Preserves InvestiKid commit history.

Cons:
- More complex.
- Must rewrite history carefully because `frontend/.env.production` exists in history.
- Requires all collaborators to re-clone or reset.

Recommendation:

User decision: use **Option B: Preserve Filtered History**.

Implementation requirement:

- Filter history down to `invest-ed/`.
- Remove `frontend/.env.production` from every commit in the new repository history.
- Add current root workflows as a new commit after filtering, with paths rewritten for the new repository root.

## Open Decisions

1. Android timing:
   - keep workflow option guarded for now
   - or add Capacitor Android as a separate implementation project
