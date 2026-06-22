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

**Promotion flow (official release):** build on `testing` → promote to `staging` for beta-testers
→ promote to `main` for everyone. Promote by fast-forwarding the branch (`git checkout staging &&
git merge --ff-only testing && git push`, then the same `staging → main`).

> **⚠️ BETA shortcut — CURRENT (set 2026-06-21):** while in beta we commit **straight to `main`**
> and skip the `testing` and `staging` hops to ship faster. CI still gates `main` and Railway/Vercel
> still deploy from it; the `testing`/`staging` branches and DBs are untouched, not retired.
> **Reinstate the full `testing` → `staging` → `main` flow at the official (non-beta) release.**

## How deploys actually happen

- **GitHub Actions (`ci.yml`)** only *validates* — frontend, backend, security, a11y, responsive.
  It runs on push to `main`, `staging`, `testing` and on PRs into `main`/`staging`. It is
  **ubuntu-only**: it never builds iOS or Android, so it doesn't burn macOS minutes.
- **Vercel** deploys preview branches via its Git integration, but **production does NOT auto-deploy**
  (`frontend/vercel.json` `main:false`). Prod is a **manual two-step** from `frontend/`:
  1. `vercel --prod --force --yes` → builds + returns a `frontend-<hash>-investikid.vercel.app` URL (wait for READY).
  2. `vercel alias set frontend-<hash>-investikid.vercel.app app.investikid.ai` — **required**: the custom
     domain is pinned to a specific deployment and does **not** auto-follow the latest prod deploy. Skipping
     step 2 leaves `app.investikid.ai` on the OLD build. Verify: `vercel alias ls | grep app.investikid.ai`
     shows the new hash + `curl -s -o /dev/null -w '%{http_code}' https://app.investikid.ai` → 200.
  A git push alone ships nothing to web — never call a frontend change "live" until both steps run.
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
2. **🛑 Physical-device QA sign-off (hard gate).** A completed, PASS sign-off for the build being
   promoted MUST exist in `docs/release-signoffs/` (copy of `docs/release-qa-checklist.md`, run on a
   **real iPhone and Android**). Do NOT promote without it. Green CI + web build is necessary but
   **not** sufficient — StoreKit/Play billing, WKWebView video, push prompts, app-kill persistence,
   and safe-area layout only behave truthfully on hardware. Any FAIL on auth, video, progress-save,
   or billing blocks the release until fixed and re-tested (or an explicit written waiver is recorded).
3. Confirm the migration has already been applied + validated on testing **and** staging.
4. Promote (`git checkout main && git merge --ff-only staging && git push`).
5. Trigger the manual Railway production deploy (and Vercel "Promote to Production").

**Production cutover — ✅ COMPLETED 2026-06-08.** Production now runs on `ashmorel/investikid`
(`main`): backend `https://investikid.up.railway.app` (Railway `InvestiKid` → production →
InvestiKid, **Root Directory `backend`**), frontend `https://app.investikid.ai` (Vercel
production, deployed manually via `vercel --prod` from `main`). The four pending migrations
(guardian-attested, lesson-drafts, subscriptions, parent-preferences) were applied to the prod DB
after a manual snapshot; login verified end-to-end.
  - **Root cause that had blocked it:** the prod Railway service's **Root Directory was stale**
    (`invest-ed/backend`, from the old monorepo) → every prod backend deploy failed at build
    (`directory … does not exist`) until it was changed to `backend`.
- **Repoint prod backend domain** (optional): backend is `investikid.up.railway.app`. If ever renamed, also update the cron workflow `BACKEND_URL` (repo Actions variable `vars.BACKEND_URL`) and any client referencing it.
- ✅ **Prod secret rotation — RESOLVED 2026-06-11.** `JWT_SECRET` rotated (fresh value per
  environment — prod/staging/testing each have their own, so non-prod tokens can never replay
  against prod); `RESEND_API_KEY` rotated (new key created, verified sending, old key revoked);
  `CRON_SECRET` was already rotated 2026-06-08. `ADMIN_TOKEN` and `SECRET_KEY` env vars deleted —
  the app no longer reads either (admin is account-based; `SECRET_KEY` was never a Settings field).
  Note: rotating `JWT_SECRET` invalidated all sessions (one-time forced re-login).
- ✅ **`CRON_SECRET` — RESOLVED 2026-06-08.** `CRON_SECRET` is set and **matched** on production Railway (`InvestiKid` → production → InvestiKid) **and** the GitHub Actions secret. The `Video health cron` workflow is **enabled** and a manual run against production (`https://investikid.up.railway.app`) returned **HTTP 200** `{"ok":2,"dead":0,"unknown":0}`. The daily 06:00 UTC schedule now runs cleanly.
  - The cron workflow on **both `main` and `testing`** reads `BACKEND_URL` from the **repo Actions variable** (`${{ vars.BACKEND_URL || '<hardcoded fallback>' }}`; main `d8bef57`, testing `8622920`). The scheduled run executes from `main`.
  - **`vars.BACKEND_URL` = `https://investikid.up.railway.app`** (the prod backend). If the prod host ever changes (custom domain / rename): `gh variable set BACKEND_URL --body <prod-url>`.
  - History: pipeline first validated against `testing` (2026-06-07, HTTP 200), then pointed at prod and re-validated (2026-06-08). One transient 401 occurred before prod had redeployed with the new secret — re-running after the prod deploy completed returned 200.
  - If it ever fails again: **401**=GitHub vs Railway secret mismatch; **503**=`CRON_SECRET` unset on backend; **404**=backend not serving / wrong `BACKEND_URL`.
- ⏳ **4C trial-reminders cron step — pending prod promotion.** Feature 4C adds a second daily cron step hitting `/internal/trial-reminders/run`. It is on the **`testing`** branch's `video-health-cron.yml` only (commit `1672c648`). **Do NOT add it to `main` until 4C is deployed to production** — the scheduled cron runs from `main` against prod, and the prod backend won't serve `/internal/trial-reminders/run` until 4C is promoted; adding it early would 404 and fail the daily cron. At 4C prod promotion: add the identical `Trigger trial-ending reminders` step to `main`'s `.github/workflows/video-health-cron.yml`.
- ✅ **Vercel production env vars (corrected 2026-06-22).** `VITE_API_BASE_URL` = **`https://api.investikid.ai`** (the same-site API subdomain — NOT `investikid.up.railway.app`) and `VITE_WEB_ORIGIN` = `https://app.investikid.ai` on the **Production** scope. They're Sensitive-flagged (read back blank via CLI) — verify instead from the live bundle (`curl app.investikid.ai/assets/index-*.js | grep -c api.investikid.ai` → 1, railway → 0).
  - ⚠️ **`VITE_API_BASE_URL` MUST be the same-site `api.investikid.ai`, never the railway URL.** `app.investikid.ai` → `investikid.up.railway.app` is cross-site, so the `SameSite=None` auth cookie becomes third-party → Safari/Chrome block it → `/me` 401 → "Could not start your session" (login appears to succeed then fails). `app.investikid.ai` → `api.investikid.ai` is same-site (shared `investikid.ai`) → first-party cookie → works. See `docs/superpowers/specs/2026-06-15-web-auth-same-site-api-design.md`.
  - **Regression history:** on 2026-06-21 the Production vars were re-created with the railway URL, silently reintroducing the cross-site bug; re-corrected to `api.investikid.ai` + redeployed 2026-06-22. If login breaks again, check this var FIRST.

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
   - **Redis (optional, for market-data caching)** — to gain cross-restart / multi-replica caching of simulator quotes + search results, provision a **Redis** service per environment and set `REDIS_URL` on the backend. Without it the app runs exactly as today (in-memory cache only); the Redis layer (`app/services/price_cache.py`) is a safe no-op when Redis is unreachable.

### GitHub
1. `Settings → Environments`: create `testing`, `staging`, `production`.
2. Protect `production`: required reviewers + deployment branch restricted to `main`.
3. Restrict `staging` deployment branch to `staging`.
4. Add any environment secrets CI needs.

### iOS (TestFlight) + Android (Play)
- **Native API base:** the app bundles the web build, so it must point at prod. This is baked from
  `frontend/.env.local` → `VITE_API_BASE_URL=https://api.investikid.ai` (the canonical custom domain — NOT
  the `*.up.railway.app` host, so we can re-point hosting later without breaking installed apps; native auth
  uses tokens/headers so it's free of the web same-site-cookie constraint). After any `npm run build`, verify
  the synced assets bake it: `grep -roh "api.investikid.ai" frontend/ios/App/App/public/assets/*.js | head -1`
  (and the Android `android/app/src/main/assets/public/assets/*.js` equivalent) print `api.investikid.ai`, no `railway.app`.
- **Current store-ready builds:** iOS `CURRENT_PROJECT_VERSION` = **14** (MARKETING_VERSION 1.0);
  Android `versionCode` = **2** (versionName 1.0). Bump both for every new upload (build # / versionCode must increase).
- **iOS:** `cd frontend && npm run build && npx cap sync ios`, then open `ios/App/App.xcodeproj` in Xcode
  (Capacitor 8 = SwiftPM — open the **.xcodeproj**, not a workspace), archive, upload to TestFlight. Signing/certs are yours.
- **Android:** `npx cap sync android`, then either open `frontend/android` in Android Studio → Generate Signed Bundle (AAB), **or** build it from the terminal (signs automatically, no wizard): `cd frontend/android && ./gradlew :app:bundleRelease`. Output: `app/build/outputs/bundle/release/app-release.aab` → upload to Play internal.
- For CI-built artifacts instead, run the **Deployment checkpoint** workflow with `run_ios=true` / `run_android=true`.

#### Local toolchain (Android, this Mac)
- **Gradle needs JDK 17/21**; the system default is Java 8. Installed **OpenJDK 21** via Homebrew (`brew install openjdk@21`, keg-only, no sudo) and wired it into `~/.zshrc`:
  `export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"` + `export PATH="$JAVA_HOME/bin:$PATH"`. A new terminal then runs `./gradlew` on JDK 21 with no per-command `JAVA_HOME=` prefix. (Android Studio uses its own bundled JBR 21 regardless.)
- **Signing is gradle-configured, so no passwords are typed at build time.** `app/build.gradle` reads `frontend/android/keystore.properties` (`storeFile` = `/Users/leeashmore/investikid-upload.jks`, `keyAlias` = `investikid-upload`, passwords in that file) into `signingConfigs.release`. The app is on **Play App Signing** — `investikid-upload.jks` is the *upload* key (Google holds the app-signing key). **Back up `investikid-upload.jks` + `keystore.properties`** (e.g. password manager); a lost upload key needs a Play Console upload-key reset.

## Security pre-public checklist (before making the repo public)
- Rotate any secrets that were ever tracked (the old monorepo tracked `frontend/.env.production`)
  and rotate `CRON_SECRET`.
- Confirm no `.env*` is tracked here (only `backend/.env.example` should be) and run `gitleaks`.
- Enable GitHub secret scanning.

## Provisioning status (2026-06-07)

**Railway (project `InvestiKid`, service renamed `InvestiKid`) — testing + staging + production DONE (production cut over 2026-06-08).**
- **testing** → backend `https://investikid-testing.up.railway.app`; source `investikid@testing`, root `/backend`; own Postgres (`DATABASE_URL` = `${{ Postgres.DATABASE_URL }}` reference); migrated + seeded; `ENVIRONMENT=testing`, `EMAIL_BACKEND=logging`. Auto-deploys on push to `testing`.
- **staging** → backend `https://investikid-staging.up.railway.app`; source `investikid@staging`, root `/backend`; own Postgres (reference); full migration chain + seeded; `ENVIRONMENT=staging`, `EMAIL_BACKEND=logging`; `CORS_ORIGINS` set to the staging Vercel origin. Auto-deploys on push to `staging`.
- **production** → ✅ **cut over 2026-06-08** to `ashmorel/investikid@main`, **Root Directory `backend`** (was a stale `invest-ed/backend` — the bug that had failed every prod deploy at build), backend `https://investikid.up.railway.app`, own Postgres; full migration chain applied after a manual snapshot; `ENVIRONMENT=production`. The old `lee-local-code-repo-production.up.railway.app` host is now dead (Railway "Application not found").
- ⚠️ testing + staging carry **forked production secrets** (live OpenAI/Together/Resend keys, `JWT_SECRET`, `CRON_SECRET`, DB password, `ADMIN_TOKEN`, `SECRET_KEY`), and they're **identical across both envs**. **Rotate / set unique test-only keys** — Coach Penny in non-prod currently bills your prod LLM accounts.
- `APP_BASE_URL` in testing/staging still = `app.investikid.ai` (prod). Only affects email links, and email is `logging` in these envs, so low impact — repoint to the branch URLs if you want fully correct links.

**Vercel (project `investikid.ai`, team `investikid`) — repoint CONFIRMED + env wired; production cutover ✅ DONE 2026-06-08.**
- **Git connection points at `ashmorel/investikid`** ✅ (Preview builds for `testing`/`staging` come from repo id `1260927337`). Root Directory = `frontend` ✅ (Vite builds succeed).
- **Branch-scoped env vars set via Vercel CLI** ✅ (`vercel env ls`):
  - `VITE_API_BASE_URL` — Preview/`testing` → `https://investikid-testing.up.railway.app`; Preview/`staging` → `https://investikid-staging.up.railway.app`
  - `VITE_WEB_ORIGIN` — Preview/`testing` + Preview/`staging` → the branch URLs below
  - the old all-branches Preview `VITE_API_BASE_URL` was removed. testing + staging redeployed to bake in the new values.
- **Preview deployments are auth-protected** (Vercel Authentication, default on Hobby) → reachable only by the Vercel team account, not anonymous/beta users. No password protection on Hobby — for beta access to staging, plan an **app-level allowlist** rather than Vercel protection.
- **production** → ✅ serving `ashmorel/investikid@main` (deployed manually via `vercel --prod` from `main`, since `vercel.json` `main:false` disables auto-build). Prod `VITE_API_BASE_URL` was **added** at cutover — it had been **missing entirely**, which is why the old prod build pointed at a dead backend and login failed. Values are Sensitive-flagged (blank via CLI) but verified from the live bundle.
- **⚠️ Vercel team slug is `investikid`** (was `lee-ashmore-s-projects`). Use the **`-investikid`** branch aliases below — the old `-lee-ashmore-s-projects` aliases still resolve but serve a **stale pre-migration build** (baked the old prod backend). `CORS_ORIGINS` (Railway) + `VITE_WEB_ORIGIN` (Vercel) are set to the `-investikid` origins.
- Vercel branch URLs (current/canonical):
  - testing: `https://investikidai-git-testing-investikid.vercel.app`
  - staging: `https://investikidai-git-staging-investikid.vercel.app`
  - production: `https://app.investikid.ai`

## Related docs
- `docs/deployment-checkpoint.md` — how to run the manual checkpoint workflow.
- `docs/superpowers/specs/2026-06-06-invested-repo-environment-migration-design.md` — the original
  migration design.
