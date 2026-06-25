# Contributing

InvestiKid is a proprietary project (see [LICENSE](LICENSE)). This guide
documents how work is done in this repo for maintainers, collaborators, and AI
coding agents. External pull requests are not generally accepted, but bug
reports and security disclosures are welcome — see [SECURITY.md](SECURITY.md).

## Golden rules

- **Never read or modify any `.env` file.** Secrets live there; `.env.example`
  lists the variables.
- **It's a kids' app.** Keep it safe (all LLM output is moderated; premium
  features are server-gated; LLM endpoints are rate-limited) and accessible
  (**WCAG 2.2 AA**).
- **DB changes are hand-written, chained Alembic migrations.** Check
  `alembic heads` first — there must be a single head.

## Feature workflow

For non-trivial work: **design spec → implementation plan → TDD → verify →
ship on green CI**. Specs and plans live in `docs/superpowers/`. Non-trivial
UI/visual changes are designed in Figma first.

1. **Spec** the change (problem, approach, scope).
2. **Plan** the implementation as bite-sized tasks.
3. **TDD** — failing test → minimal code → commit.
4. **Verify** — backend: `ruff check .` + `pytest`; frontend: `tsc` +
   `npm run lint` + `npm test` + `npm run build` (plus `vitest-axe` for new UI).
5. **Ship** — push and wait for green CI.

## Branch model

Branches flow **`testing` → `staging` → `main`** with three separate Postgres
databases; production promotion is manual.

> **Beta shortcut (current):** while in beta we commit **straight to `main`**
> to ship faster. CI still gates `main`. Reinstate the full
> `testing → staging → main` flow at the official release. See
> [`docs/deployment-environments.md`](docs/deployment-environments.md).

Before any **production** database migration, decide whether to take a
backup/snapshot first.

## Commands

**Backend** (from `backend/`, Python 3.12):

```bash
pytest                 # tests
ruff check .           # lint
alembic upgrade head   # migrate
uvicorn app.main:app --reload
```

**Frontend** (from `frontend/`, Node 20):

```bash
npm run dev · npm run build · npm test · npm run lint · npx tsc -b
```

**Native** (after a web build): `npx cap sync ios` / `npx cap sync android`,
then build in Xcode / Android Studio.

## Commit messages

Write clear, imperative messages. End AI-assisted commits with the
co-author trailer, e.g.:

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Where the detailed conventions live

- [`AGENTS.md`](AGENTS.md) — the project guide for AI coding agents
- [`.cursor/rules/`](.cursor/rules) — path-scoped editor rules
  (`backend.mdc`, `frontend.mdc`, `workflow.mdc`)
- [`docs/MASTER-BACKLOG.md`](docs/MASTER-BACKLOG.md) — the live tracker
