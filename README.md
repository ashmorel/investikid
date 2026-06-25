# InvestiKid

[![CI](https://github.com/ashmorel/investikid/actions/workflows/ci.yml/badge.svg)](https://github.com/ashmorel/investikid/actions/workflows/ci.yml)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-red.svg)](LICENSE)
![Platforms: Web · iOS · Android](https://img.shields.io/badge/platforms-web%20%C2%B7%20iOS%20%C2%B7%20Android-blue.svg)

**A finance-education app that teaches kids (and teens) how money works — through bite-sized lessons, a friendly mascot, a stock-market simulator, and a gamified arcade.** Built for safety and accessibility (WCAG 2.2 AA), with parent oversight and per-market localization.

> 🌐 **Live:** the app runs at **[app.investikid.ai](https://app.investikid.ai)** (web), backed by the API at `api.investikid.ai`. Native **iOS** (TestFlight) and **Android** (Google Play) builds ship from the same codebase via Capacitor.

This repository is **source-available but proprietary** — see [LICENSE](LICENSE). It is published for transparency and portfolio purposes; it is **not** open source and the code may not be reused.

---

## What's inside

- **Adaptive lessons** — a tiered curriculum (card / quiz / scenario / video) with spaced-repetition review ("Revise"), generated and moderated per market.
- **Penny's Arcade** — a games hub (Quiz Rush, daily MoneyWord) with coins, an avatar shop, and limited-edition collectables.
- **Stock-market simulator** — a safe, play-money portfolio tied to lesson missions.
- **Parent dashboard** — mastery reports, subscription/billing, consent controls, Face ID, and per-child settings.
- **Multi-market & localized** — 10 markets (GB/US/AU/CA/IE/ES/FR/DE/HK/SG) and 6 UI languages, with per-market progress and rewards.
- **Built safe** — all LLM output is moderated, premium features are server-gated, LLM endpoints are rate-limited, and the UI targets WCAG 2.2 AA.

## Tech stack

| Layer | Stack |
|---|---|
| **Frontend** | React 18 · Vite · TypeScript · TanStack Query · Tailwind CSS v4 · shadcn/ui — deployed on **Vercel** |
| **Native** | **Capacitor** (iOS + Android) wrapping the web app |
| **Backend** | **FastAPI** · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL · Python 3.12 — deployed on **Railway** |
| **CI/CD** | GitHub Actions (5-job gate) → Railway (backend) + Vercel (web) |

## Repository layout

```
backend/    FastAPI + SQLAlchemy (async) + Alembic + Postgres
frontend/   React + Vite app, with Capacitor iOS/Android projects under frontend/ios + frontend/android
docs/       Deployment, operations, roadmap, and the live MASTER-BACKLOG tracker
.github/    CI/CD workflows, Dependabot, issue/PR config
```

## Quick start (local development)

**Backend** (Python 3.12, from `backend/`):

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # apply migrations to your local Postgres
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

Tests & lint: `pytest` · `ruff check .`

**Frontend** (Node 20, from `frontend/`):

```bash
npm ci
npm run dev                     # http://127.0.0.1:5173
```

Build & checks: `npm run build` · `npm test` · `npm run lint`

**Native** (after a web build, from `frontend/`):

```bash
npm run build && npx cap sync ios        # then open in Xcode
npm run build && npx cap sync android    # then open in Android Studio
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full workflow and conventions.

## Documentation

- **[docs/](docs/README.md)** — documentation index
- **[docs/MASTER-BACKLOG.md](docs/MASTER-BACKLOG.md)** — the live tracker (what's shipped / what's next)
- **[docs/deployment-environments.md](docs/deployment-environments.md)** — environments, deploy flow, env vars
- **[AGENTS.md](AGENTS.md)** — guide for AI coding agents working in this repo
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability

## License

Copyright © 2026 Lee Ashmore (InvestiKid). **All rights reserved.** See [LICENSE](LICENSE).
