# CI Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions CI workflow that runs lint, type-check, unit tests, and build for both frontend and backend on every push/PR to main.

**Architecture:** One workflow file with two parallel jobs (frontend, backend). Frontend gets ESLint 9 flat config with bug-catching rules only. Backend gets Ruff linter. Fix any existing violations so CI is green from day one.

**Tech Stack:** GitHub Actions, ESLint 9 (flat config), Ruff, Node 20, Python 3.12, PostgreSQL 16 (service container)

**Repo layout note:** The git root is `/Users/leeashmore/Local Repo` (the monorepo root). The invest-ed project lives at `invest-ed/` within it. All paths in the workflow use `invest-ed/frontend` and `invest-ed/backend` as working directories.

---

### Task 1: Backend Ruff Configuration

**Files:**
- Create: `invest-ed/backend/ruff.toml`
- Modify: `invest-ed/backend/requirements.txt`

- [ ] **Step 1: Add ruff to requirements.txt**

Add `ruff` under the `# dev/test` section in `invest-ed/backend/requirements.txt`:

```
# dev/test
pytest==8.3.2
pytest-asyncio==0.24.0
pytest-cov==5.0.0
ruff>=0.4
```

- [ ] **Step 2: Install ruff**

Run:
```bash
cd invest-ed/backend && pip install ruff
```

- [ ] **Step 3: Create ruff.toml**

Create `invest-ed/backend/ruff.toml`:

```toml
target-version = "py312"
line-length = 120

[lint]
select = ["E", "F", "I", "UP"]
```

Rules:
- `E` — pycodestyle errors (whitespace, syntax style)
- `F` — pyflakes (unused imports, undefined names)
- `I` — isort (import ordering)
- `UP` — pyupgrade (modernize syntax for target Python version)

- [ ] **Step 4: Run ruff and check output**

Run:
```bash
cd invest-ed/backend && ruff check .
```

Expected: Either clean output (exit 0) or a list of violations to fix in Task 2.

- [ ] **Step 5: Commit**

```bash
git add invest-ed/backend/ruff.toml invest-ed/backend/requirements.txt
git commit -m "chore: add Ruff linter config for backend"
```

---

### Task 2: Fix Backend Ruff Violations

**Files:**
- Modify: Any `.py` files in `invest-ed/backend/` that have violations

- [ ] **Step 1: Run ruff and capture all violations**

Run:
```bash
cd invest-ed/backend && ruff check . 2>&1
```

Review every violation. Common expected issues:
- `I001` — import sorting (imports not in isort order)
- `F401` — unused imports
- `E501` — line too long (over 120 chars)
- `UP` — old syntax that can be modernized

- [ ] **Step 2: Auto-fix safe violations**

Run:
```bash
cd invest-ed/backend && ruff check --fix .
```

This auto-fixes import ordering (`I`), unused imports (`F401`), and pyupgrade (`UP`) changes. Review the diff to confirm changes are correct.

- [ ] **Step 3: Manually fix remaining violations**

For any violations `ruff check --fix` couldn't auto-fix (e.g., long lines, complex issues), fix them manually. If a violation is a false positive, add a `# noqa: XXXX` comment with the specific rule code.

- [ ] **Step 4: Verify ruff passes clean**

Run:
```bash
cd invest-ed/backend && ruff check .
```

Expected: Exit 0, no output.

- [ ] **Step 5: Verify tests still pass**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_llm_client.py tests/test_ai_content_service.py tests/test_auth.py -v
```

Expected: All pass. (Run a representative sample — the full suite has pre-existing cross-file isolation issues unrelated to lint fixes.)

- [ ] **Step 6: Commit**

```bash
git add -A invest-ed/backend/
git commit -m "fix: resolve Ruff lint violations in backend"
```

---

### Task 3: Frontend ESLint Configuration

**Files:**
- Create: `invest-ed/frontend/eslint.config.js`
- Modify: `invest-ed/frontend/package.json` (add `lint` script and dev dependencies)

- [ ] **Step 1: Install ESLint dev dependencies**

Run:
```bash
cd invest-ed/frontend && npm install -D eslint @eslint/js typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh
```

This installs:
- `eslint` — the linter (v9+)
- `@eslint/js` — base recommended rules
- `typescript-eslint` — TS-aware rules
- `eslint-plugin-react-hooks` — Rules of Hooks enforcement
- `eslint-plugin-react-refresh` — catches HMR-breaking components

- [ ] **Step 2: Add lint script to package.json**

In `invest-ed/frontend/package.json`, add to the `"scripts"` section:

```json
"lint": "eslint ."
```

The scripts block should look like:
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:e2e": "playwright test",
  "lint": "eslint ."
}
```

- [ ] **Step 3: Create eslint.config.js**

Create `invest-ed/frontend/eslint.config.js`:

```js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
);
```

Key decisions:
- No style/formatting rules (no Prettier, no semicolons). Bug-catching only.
- `@typescript-eslint/no-unused-vars` is `off` because `tsconfig.json` already enforces `noUnusedLocals` and `noUnusedParameters`.
- `react-refresh/only-export-components` is `warn` (not error) — it's a DX hint, not a bug.

- [ ] **Step 4: Run ESLint and check output**

Run:
```bash
cd invest-ed/frontend && npm run lint
```

Expected: Either clean output (exit 0) or a list of violations to fix in Task 4.

- [ ] **Step 5: Commit**

```bash
git add invest-ed/frontend/eslint.config.js invest-ed/frontend/package.json invest-ed/frontend/package-lock.json
git commit -m "chore: add ESLint 9 flat config for frontend (bug-catching rules only)"
```

---

### Task 4: Fix Frontend ESLint Violations

**Files:**
- Modify: Any `.ts`/`.tsx` files in `invest-ed/frontend/src/` and `invest-ed/frontend/tests/` that have violations

- [ ] **Step 1: Run ESLint and capture all violations**

Run:
```bash
cd invest-ed/frontend && npm run lint 2>&1
```

Review every violation. Common expected issues:
- `react-hooks/exhaustive-deps` — missing dependencies in useEffect/useMemo/useCallback
- `react-hooks/rules-of-hooks` — hooks called conditionally or in loops
- `@typescript-eslint/no-explicit-any` — use of `any` type
- `react-refresh/only-export-components` — non-component exports from component files

- [ ] **Step 2: Fix violations in source files**

Fix each violation in the source code. Guidelines:
- For `react-hooks/exhaustive-deps`: add the missing dependency to the array. If adding it would cause an infinite loop, restructure the code (extract to useCallback, or use a ref). Only `// eslint-disable-next-line` as a last resort with a comment explaining why.
- For `@typescript-eslint/no-explicit-any`: replace `any` with the correct type, or `unknown` if the type genuinely can't be narrowed.
- For `react-refresh/only-export-components` warnings: these are non-blocking (warn level), but fix if easy (move non-component exports to a separate file).

- [ ] **Step 3: Verify ESLint passes clean**

Run:
```bash
cd invest-ed/frontend && npm run lint
```

Expected: Exit 0, no errors. Warnings from `react-refresh` are acceptable.

- [ ] **Step 4: Verify tests still pass**

Run:
```bash
cd invest-ed/frontend && npm test
```

Expected: 208+ tests pass. (Some pre-existing failures in UI tests from earlier renames are acceptable — focus on no new failures from lint fixes.)

- [ ] **Step 5: Verify TypeScript still compiles**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit
```

Expected: Exit 0, no errors.

- [ ] **Step 6: Commit**

```bash
git add -A invest-ed/frontend/src/ invest-ed/frontend/tests/
git commit -m "fix: resolve ESLint violations in frontend"
```

---

### Task 5: GitHub Actions CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml` (at the git root: `/Users/leeashmore/Local Repo/.github/workflows/ci.yml`)

- [ ] **Step 1: Create the workflow directory**

Run:
```bash
mkdir -p /Users/leeashmore/Local\ Repo/.github/workflows
```

- [ ] **Step 2: Create ci.yml**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  frontend:
    name: Frontend (lint · typecheck · test · build)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: invest-ed/frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: invest-ed/frontend/package-lock.json

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type-check
        run: npx tsc --noEmit

      - name: Unit tests
        run: npm test

      - name: Build
        run: npm run build

  backend:
    name: Backend (lint · test)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: invest-ed/backend

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: investedb_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U test -d investedb_test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    env:
      DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/investedb_test
      TEST_DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/investedb_test
      JWT_SECRET: ci-test-secret
      REDIS_URL: redis://localhost:6379/0

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: invest-ed/backend/requirements.txt

      - run: pip install -r requirements.txt

      - name: Lint
        run: ruff check .

      - name: Tests
        run: python -m pytest -v
```

Key details:
- Both jobs run in parallel (no `needs:` dependency).
- PostgreSQL 16 service container with health check — ensures DB is ready before tests.
- `REDIS_URL` is set but no Redis container — it's required by `Settings` but not used in tests.
- `npm ci` is used (not `npm install`) for reproducible installs from lockfile.
- Node and pip caches are enabled for faster repeat runs.
- `tsc --noEmit` is used instead of `tsc -b` to avoid the `tsconfig.node.json` composite warning.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for frontend and backend"
```

---

### Task 6: End-to-End Verification

**Files:**
- No new files — verification only

- [ ] **Step 1: Verify all local checks pass**

Run each check locally, in order:

```bash
# Backend lint
cd invest-ed/backend && ruff check .

# Backend tests (representative sample)
cd invest-ed/backend && python -m pytest tests/test_llm_client.py tests/test_ai_content_service.py tests/test_auth.py tests/test_users.py -v

# Frontend lint
cd invest-ed/frontend && npm run lint

# Frontend type-check
cd invest-ed/frontend && npx tsc --noEmit

# Frontend tests
cd invest-ed/frontend && npm test

# Frontend build
cd invest-ed/frontend && npm run build
```

Expected: All pass (or only pre-existing failures in the full backend suite).

- [ ] **Step 2: Push branch and verify GitHub Actions**

```bash
git push -u origin feature/ci-pipeline
```

Go to the repository's Actions tab on GitHub. Verify:
- The CI workflow triggers
- Both `frontend` and `backend` jobs start
- Both jobs complete green (or identify any CI-specific failures to fix)

- [ ] **Step 3: Fix any CI-specific failures**

If the GitHub Actions run surfaces issues that didn't appear locally (e.g., different Node/Python version behavior, missing env vars, test isolation issues in the full pytest suite), fix them and push again.

Common CI-specific issues:
- Tests that depend on local `.env` values not present in CI
- Import errors from packages not in `requirements.txt`
- Tests that assume a specific timezone or locale

- [ ] **Step 4: Create PR**

```bash
gh pr create --title "ci: add CI pipeline with ESLint, Ruff, and GitHub Actions" --body "$(cat <<'EOF'
## Summary
- Add GitHub Actions CI workflow with parallel frontend and backend jobs
- Add ESLint 9 flat config for frontend (bug-catching rules only, no style opinions)
- Add Ruff linter for backend (pycodestyle, pyflakes, isort, pyupgrade)
- Fix all existing lint violations so CI is green from day one

## CI Jobs
**Frontend:** lint → type-check → unit tests → build
**Backend:** lint → tests (with PostgreSQL 16 service container)

## Test plan
- [ ] GitHub Actions workflow runs green on this PR
- [ ] `npm run lint` passes locally
- [ ] `ruff check .` passes locally
- [ ] All existing tests still pass

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
