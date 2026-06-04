# InvestiKid

A children's finance-education app (web + iOS), heading to a TestFlight beta. This is the active project in this repository.

## ▶ Current work — resume here
The **"Yasmin's Choice" rebrand** programme is in progress. **`docs/superpowers/PROGRESS.md` is the single source of truth** for status and the next step. Currently: SP-0/A/B/C/D1/D2 shipped (CI green, 6 jobs incl. an iOS Capacitor simulator build); **SP-E (parent/admin polish) is next** — brainstorm → spec → plan → execute. Workflow + full status in `docs/superpowers/PROGRESS.md`.

## Structure
- `backend/` — FastAPI + SQLAlchemy 2.0 (async) + Alembic + Postgres. Deployed on **Railway**.
- `frontend/` — React 18 + Vite + TypeScript + TanStack Query + Tailwind v4 (CSS-first @theme) + shadcn/ui, with a **Capacitor iOS** app in `frontend/ios/`. Web deployed on **Vercel**.
- `docs/superpowers/specs/` & `docs/superpowers/plans/` — dated design specs and implementation plans. Read the relevant one before changing a feature.

## Commands
Backend (run from `backend/`; venv at the repo root `/Users/leeashmore/Local Repo/.venv`):
- Tests: `/Users/leeashmore/Local Repo/.venv/bin/pytest`
- Lint: `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`
- Migrate: `/Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head`
- Run: `/Users/leeashmore/Local Repo/.venv/bin/uvicorn app.main:app --reload`

Frontend (run from `frontend/`):
- `npm run dev` · `npx tsc -b` · `npm run lint` · `npm test` · `npm run build`
- iOS: `npx cap sync ios` after a build, then rebuild in Xcode.

## Golden rules
- **Never read or modify any `.env` file.** Secrets live there; `.env.example` lists the variables.
- Commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Railway deploys the backend only on green CI** (5 jobs: frontend, backend, security, a11y, responsive). Vercel auto-deploys the frontend from `main`.
- TDD; minimal focused changes. DB changes = hand-written chained Alembic migration (check `alembic heads` first).
- Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient` on the app engine.
- LLM output is always moderated (`moderate_output`); premium-gate with `is_premium`; rate-limit LLM endpoints. It's a kids' app — keep it safe and WCAG 2.2 AA accessible.
- iOS: keep form controls ≥16px on touch (no `maximum-scale`); keep the WKWebView re-layout + safe-area handling.

## Feature workflow
For any non-trivial feature/change: **design spec → implementation plan → TDD**. Write a short spec to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (goal, scope, data/API, UX, edge cases, test plan), then a task-by-task plan in `docs/superpowers/plans/`, then implement test-first (failing test → minimal code → commit per task). Verify (ruff + pytest; tsc + lint + test + build, plus `vitest-axe` for new UI), push, confirm green CI. Surface trade-offs instead of assuming; minimum code; touch only what the task needs.

## Gotchas
- The local test Postgres can hang after a killed pytest run — if a DB test hangs ~90s+, it's environmental; rely on CI.
- A Figma design-system token file (colours/type/radii, generated from `tailwind.config.js` + `index.css`) exists for reference — foundation only, not full screens.

> Cursor-specific, path-scoped rules live in `.cursor/rules/`.
