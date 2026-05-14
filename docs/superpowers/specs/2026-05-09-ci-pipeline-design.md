# Plan 6A: CI Pipeline

## Goal

Add a GitHub Actions CI workflow that runs lint, type-check, unit tests, and build for both frontend and backend on every push to `main` and every pull request. Catches regressions before merge.

## Scope

- One workflow file: `.github/workflows/ci.yml`
- Two parallel jobs: `frontend` and `backend`
- New ESLint flat config for the frontend (bug-catching rules only, no style opinions)
- Ruff linter for the backend
- Fix any existing lint violations surfaced by the new linters

## Architecture

### Workflow: `.github/workflows/ci.yml`

Triggered on `push` to `main` and `pull_request` to `main`. Two parallel jobs.

### Job 1: `frontend`

Runs on `ubuntu-latest`, working directory `invest-ed/frontend`.

Steps:
1. Checkout repo
2. Setup Node 20 + `npm ci` (with `node_modules` cache keyed on `package-lock.json`)
3. **Lint** — `npm run lint` (ESLint, see below)
4. **Type-check** — `npx tsc -b`
5. **Unit tests** — `npm test` (Vitest, 217 tests)
6. **Build** — `npm run build` (Vite production build)

### Job 2: `backend`

Runs on `ubuntu-latest`, working directory `invest-ed/backend`.

PostgreSQL 16 service container for tests:
- `POSTGRES_DB=investedb_test`, `POSTGRES_USER=test`, `POSTGRES_PASSWORD=test`
- Port 5432 mapped, health check on `pg_isready`

Environment variables for the app's `Settings` (pydantic-settings reads from env):
- `DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/investedb_test`
- `TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/investedb_test`
- `JWT_SECRET=ci-test-secret`
- `REDIS_URL=redis://localhost:6379/0` (not used in tests but required by Settings)

Steps:
1. Checkout repo
2. Setup Python 3.12 + `pip install -r requirements.txt` (with pip cache)
3. **Lint** — `ruff check .`
4. **Tests** — `python -m pytest -v`

Redis is declared as a required env var but not actually used by the test suite (rate limiter resets in conftest). No Redis service container needed — the settings just needs a value present.

## Frontend ESLint Configuration

New file: `frontend/eslint.config.js` (ESLint 9 flat config format).

**Plugins and purpose:**
- `@eslint/js` — base recommended rules
- `typescript-eslint` — TS-aware rules (type-checked where useful)
- `eslint-plugin-react-hooks` — Rules of Hooks + exhaustive deps (error level)
- `eslint-plugin-react-refresh` — catches components that break HMR (warn level)

**Key decisions:**
- No style/formatting rules — no Prettier, no semicolon opinions. Bugs only.
- `@typescript-eslint/no-unused-vars` set to `off` — already enforced by `tsconfig.json`'s `noUnusedLocals` and `noUnusedParameters`.
- Ignores: `dist/`, `node_modules/`

**New dev dependencies:**
- `eslint` (^9)
- `@eslint/js`
- `typescript-eslint`
- `eslint-plugin-react-hooks`
- `eslint-plugin-react-refresh`

**New script in `package.json`:**
- `"lint": "eslint ."`

## Backend Ruff Configuration

Add `ruff` to `requirements.txt` (under the `# dev/test` section).

New file: `backend/ruff.toml` with minimal config:
- `select`: `["E", "F", "I", "UP"]` (pycodestyle errors, pyflakes, isort, pyupgrade)
- `target-version`: `"py312"`
- `line-length`: 120

No autofix in CI — just check. Developers can run `ruff check --fix` locally.

## Lint Violation Fixes

When ESLint and Ruff are first run, they will likely surface existing violations. These must be fixed as part of this work so CI passes from day one. Common expected issues:
- Missing React hook dependencies (ESLint `react-hooks/exhaustive-deps`)
- Import ordering (Ruff `I` rules)
- Minor pycodestyle issues (Ruff `E` rules)

Fix violations in the source files rather than disabling rules. Only add targeted `// eslint-disable-next-line` or `# noqa` comments if the violation is a false positive.

## Testing Strategy

- Verify ESLint passes on all frontend code: `cd frontend && npm run lint`
- Verify `tsc -b` passes: `cd frontend && npx tsc -b`
- Verify Vitest passes: `cd frontend && npm test`
- Verify Vite build succeeds: `cd frontend && npm run build`
- Verify Ruff passes on all backend code: `cd backend && ruff check .`
- Verify pytest passes: `cd backend && python -m pytest -v`
- Push branch, verify GitHub Actions workflow runs green
