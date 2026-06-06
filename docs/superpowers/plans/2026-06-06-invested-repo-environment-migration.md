# InvestiKid Repo Split and Environment Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move InvestiKid into its own repository and configure testing -> staging -> production promotion so routine code deploys to testing first and production is explicit.

**Architecture:** Create a dedicated InvestiKid repo whose root is the current `invest-ed/` folder. Move and rewrite GitHub Actions paths for the new root. Use branch-based environments: `testing`, `staging`, and `main`, with Vercel/Railway configured to match.

**Tech Stack:** GitHub, GitHub Actions, Vercel, Railway, FastAPI, React/Vite, Capacitor iOS, future Capacitor Android.

---

## Files and Systems

- New repo root:
  - `backend/`
  - `frontend/`
  - `docs/`
  - `AGENTS.md`
  - `.github/workflows/*.yml`
- Source repo:
  - `/Users/leeashmore/Local Repo/invest-ed/`
  - `/Users/leeashmore/Local Repo/.github/workflows/`
- Platform configuration:
  - GitHub repository settings and secrets
  - Vercel project Git/environment settings
  - Railway environments and service branch settings

## Task 1: Confirm Migration Choices

- [ ] **Step 1: Confirm repository name**

```text
ashmorel/investikid
```

- [ ] **Step 2: Confirm visibility**

```text
private initially, public only after cleanup and secret rotation
```

- [ ] **Step 3: Confirm history strategy**

```text
Preserve filtered history
```

Remove `frontend/.env.production` from the filtered history before pushing.

- [ ] **Step 4: Confirm staging data strategy**

```text
live production DB access for controlled staging validation, plus a separate migration rehearsal database for schema changes
```

Never run staging deploy-time migrations against the live production database.

## Task 2: Prepare InvestiKid Repo Tree Locally

- [ ] **Step 1: Create a clean staging directory**

Run:

```bash
mkdir -p "/Users/leeashmore/Local Repo/_repo-split"
rm -rf "/Users/leeashmore/Local Repo/_repo-split/investikid"
mkdir "/Users/leeashmore/Local Repo/_repo-split/investikid"
```

- [ ] **Step 2: Copy InvestiKid files**

Run:

```bash
rsync -a \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'node_modules' \
  --exclude 'dist' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  "/Users/leeashmore/Local Repo/invest-ed/" \
  "/Users/leeashmore/Local Repo/_repo-split/investikid/"
```

- [ ] **Step 3: Copy root workflows**

Run:

```bash
mkdir -p "/Users/leeashmore/Local Repo/_repo-split/investikid/.github/workflows"
cp "/Users/leeashmore/Local Repo/.github/workflows/ci.yml" \
   "/Users/leeashmore/Local Repo/_repo-split/investikid/.github/workflows/ci.yml"
cp "/Users/leeashmore/Local Repo/.github/workflows/deployment-checkpoint.yml" \
   "/Users/leeashmore/Local Repo/_repo-split/investikid/.github/workflows/deployment-checkpoint.yml"
cp "/Users/leeashmore/Local Repo/.github/workflows/video-health-cron.yml" \
   "/Users/leeashmore/Local Repo/_repo-split/investikid/.github/workflows/video-health-cron.yml"
```

- [ ] **Step 4: Rewrite workflow paths for new repo root**

Run:

```bash
cd "/Users/leeashmore/Local Repo/_repo-split/investikid"
perl -pi -e 's#invest-ed/frontend#frontend#g; s#invest-ed/backend#backend#g; s#invest-ed/docs#docs#g' .github/workflows/*.yml
```

- [ ] **Step 5: Add root `.gitignore`**

Create `/Users/leeashmore/Local Repo/_repo-split/investikid/.gitignore`:

```gitignore
.env
.env.*
!.env.example

.venv/
node_modules/
dist/
dist-ssr/
build/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
*.tsbuildinfo
playwright-report/
test-results/
.DS_Store

frontend/ios/App/App/public/
frontend/ios/App/Pods/
frontend/ios/App/App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
```

## Task 3: Verify No Secrets Enter New Repo

- [ ] **Step 1: Confirm env files are absent except examples**

Run:

```bash
cd "/Users/leeashmore/Local Repo/_repo-split/investikid"
find . -name '.env*' -print
```

Expected:

```text
./backend/.env.example
```

- [ ] **Step 2: Run provider-pattern grep**

Run:

```bash
cd "/Users/leeashmore/Local Repo/_repo-split/investikid"
rg -n --hidden --glob '!node_modules/**' --glob '!dist/**' --glob '!build/**' \
  '(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)'
```

Expected:

```text
no output
```

- [ ] **Step 3: Install and run gitleaks if available**

Run:

```bash
cd "/Users/leeashmore/Local Repo/_repo-split/investikid"
gitleaks detect --no-git --source . --redact
```

Expected:

```text
no leaks found
```

If `gitleaks` is not installed, install it with Homebrew:

```bash
brew install gitleaks
```

## Task 4: Initialize and Push Dedicated Repo

- [ ] **Step 1: Initialize git**

Run:

```bash
cd "/Users/leeashmore/Local Repo/_repo-split/investikid"
git init
git branch -M main
git add .
git commit -m "chore: initialize InvestiKid repository"
```

- [ ] **Step 2: Create GitHub repo**

Run:

```bash
gh repo create ashmorel/investikid --private --source . --remote origin --push
```

Expected:

```text
repository created and main pushed
```

- [ ] **Step 3: Create environment branches**

Run:

```bash
git checkout -b testing
git push -u origin testing
git checkout main
git checkout -b staging
git push -u origin staging
git checkout main
```

## Task 5: Configure GitHub Environments and Secrets

- [ ] **Step 1: Create GitHub environments**

In GitHub:

```text
Settings -> Environments -> New environment
```

Create:

```text
testing
staging
production
```

- [ ] **Step 2: Protect production**

For `production`:

```text
Required reviewers: enabled
Deployment branches: selected branches only -> main
```

- [ ] **Step 3: Restrict staging**

For `staging`:

```text
Deployment branches: selected branches only -> staging
```

- [ ] **Step 4: Add environment secrets**

Add secrets as needed:

```text
CRON_SECRET
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

Do not add real secret values to files.

## Task 6: Configure Railway

- [ ] **Step 1: Create permanent environments**

In Railway project:

```text
testing
staging
production
```

- [ ] **Step 2: Configure testing**

Settings:

```text
Branch: testing
Database: testing database
Auto-deploy: enabled
```

Required env vars:

```text
ENVIRONMENT=testing
DATABASE_URL=<testing database url>
TEST_DATABASE_URL=<testing database url or separate test db>
JWT_SECRET=<testing random secret>
CORS_ORIGINS=<Vercel testing/preview origin>
APP_BASE_URL=<Vercel testing/preview origin>
EMAIL_BACKEND=logging
CRON_SECRET=<testing cron secret>
```

- [ ] **Step 3: Configure staging**

Settings:

```text
Branch: staging
Database: production-like data source
Auto-deploy: enabled or manually approved
```

Required controls:

```text
ENVIRONMENT=staging
CORS_ORIGINS=<Vercel staging origin>
APP_BASE_URL=<Vercel staging origin>
restricted user access enabled at app/platform level
```

- [ ] **Step 4: Configure production**

Settings:

```text
Branch: main
Auto-deploy: disabled or approval-gated
```

Production deploys should happen only after the production checkpoint passes.

## Task 7: Configure Vercel

- [ ] **Step 1: Connect new GitHub repo**

In Vercel:

```text
Import Project -> ashmorel/investikid
Root directory: frontend
```

- [ ] **Step 2: Configure testing**

Use Preview environment variables for `testing` branch:

```text
VITE_API_BASE_URL=<Railway testing backend URL>
VITE_WEB_ORIGIN=<Vercel testing URL>
VITE_GOOGLE_WEB_CLIENT_ID=<testing Google web client id if testing social login>
VITE_GOOGLE_IOS_CLIENT_ID=<testing Google iOS client id if testing social login>
VITE_APPLE_SERVICES_ID=<testing Apple services id if testing social login>
```

- [ ] **Step 3: Configure staging**

If custom environments are available:

```text
Environment: staging
Branch: staging
```

If not:

```text
Use Preview deployment from staging branch
Enable Deployment Protection / password / SSO
Use staging env vars where Vercel allows branch-scoped env vars
```

- [ ] **Step 4: Configure production**

Production:

```text
Branch tracking: main
Automatic main deploy: disabled by frontend/vercel.json or Vercel project settings
Promotion/deploy: manual
```

## Task 8: Validate Promotion Flow

- [ ] **Step 1: Push a harmless change to `testing`**

Run:

```bash
git checkout testing
git commit --allow-empty -m "chore: validate testing environment"
git push
```

Expected:

```text
Railway testing deploys
Vercel Preview/testing deploys
GitHub CI runs with testing environment
```

- [ ] **Step 2: Validate staging**

Run:

```bash
git checkout staging
git merge testing --ff-only
git push
```

Expected:

```text
staging deploy/checkpoint uses staging branch and restricted access
```

- [ ] **Step 3: Validate production checkpoint**

Run the GitHub Actions workflow:

```text
Actions -> Deployment checkpoint -> Run workflow
target_environment=production
run_web=true
run_backend=true
run_security=true
run_a11y=true
run_responsive=true
run_ios=false unless needed
run_android=false until Android exists
notes=<release intent>
```

Expected:

```text
workflow runs only from main and requires notes
```

- [ ] **Step 4: Manual production release**

After checkpoint passes:

```text
promote/deploy Vercel production manually
deploy Railway production manually or approval-gated
```

## Task 9: Clean Up Old Monorepo

- [ ] **Step 1: Freeze old `invest-ed/` work**

Add a note to old monorepo `AGENTS.md`:

```text
InvestiKid moved to ashmorel/investikid. Do not edit invest-ed/ here except for archival cleanup.
```

- [ ] **Step 2: Archive or remove old workflows**

Remove InvestiKid workflows from the old monorepo after the new repo is validated.

- [ ] **Step 3: Keep old repo private**

Do not make the old monorepo public unless it receives its own full secret/history cleanup.

## Self-Review

- Spec coverage:
  - Dedicated repo: covered in Tasks 2-4.
  - Testing default: covered in Tasks 6-8.
  - Staging with production data and restricted access: covered in Tasks 6-8.
  - Production manual: covered in Tasks 5-8.
  - Web/iOS/Android build selection: covered through the deployment checkpoint workflow and Android guard.
  - Public readiness: covered in Task 3 and Task 9.
- Placeholder scan:
  - No `TBD` or unbounded TODO steps.
  - User-owned secret values are represented as placeholders intentionally; no secrets should be written to files.
- Type/path consistency:
  - New repo root uses `frontend/`, `backend/`, and `docs/`.
  - Old monorepo paths use `/Users/leeashmore/Local Repo/invest-ed/`.
