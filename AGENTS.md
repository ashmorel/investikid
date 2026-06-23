# InvestiKid

A children's finance-education app (web + iOS), heading to a TestFlight beta. This is the active project in this repository.

## ▶ Current work — resume here
**[`docs/MASTER-BACKLOG.md`](docs/MASTER-BACKLOG.md) is the single go-forward tracker** (strategic detail in [`docs/2026-06-12-market-leader-roadmap.md`](docs/2026-06-12-market-leader-roadmap.md); the rebrand-era archive is `docs/superpowers/PROGRESS.md`). Check the backlog first — that's where outstanding work and what's-live both live.

**Shipped & live in prod** (all on `main`, deployed): the **"Yasmin's Choice" rebrand** (SP-0/A/B/C/D1/D2/E/F + country-region switcher), the **market-leader build track M3–M9** (Home redesign, product analytics, pricing/packaging, outcome paywall + Mastery Report, daily goal + server push, Penny cosmetics, group challenges + seasonal events), **SP-Bio Face ID login** (+ Android parity), **LLM topical guardrails**, **Revise** (spaced repetition), the **localization + multi-market programme** — engineering complete end-to-end: Gemini model lineup, i18n foundation, localized AI, the `Market` entity + per-market progress, multi-market kids' UI, cross-market rewards, the content-translation pipeline (E1), the multi-market premium gate, and the per-market content-wave pipeline (E2) incl. **E2.1 intelligent market content** (UK-residue adaptation guard + model-proposed market-specific modules with one-click create + market-native generation). **Operator content production is now underway — GB, US and HK have real published content LIVE (2026-06-22)**: GB re-designed (9 modules/405 lessons; old UK curriculum auto-archived), US (9/405), HK (10/449, English + HKD-grounded), each market-native and generated at the new **tiered lesson depth (10/15/20 per tier)** on gpt-5-mini. Shipped alongside: **module archive + 30-day purge** (`modules.archived_at`, soft-delete/restore, republish auto-archives, daily purge cron), an admin **Modules market-filter tab + per-row badge**, a **server-side content pipeline** (`market_content_pipeline.py` + cron-gated `/internal/market-content` + `generate-market-content.yml` — generate a market end-to-end via `gh workflow run`, no admin UI), and an **LLM credit/billing fallback** (authoring Opus→gpt-5-mini when Opus is out of credits). **6 markets remain** (AU/CA/IE/ES/FR/DE/SG) — same one-command tooling. And **Penny's Arcade Phase 1** (2026-06-23): games hub + Quiz Rush, migration `f1a2b3c4d5e6`. Details in [`docs/MASTER-BACKLOG.md`](docs/MASTER-BACKLOG.md) (2026-06-22 + 2026-06-23 entries).

**Child app routes (as of 2026-06-23):** `/home`, `/learn`, `/market` (market picker), `/markets` (legacy), `/revise`, `/revise/session`, `/simulator`, `/shop`, `/arcade` (Penny's Arcade hub), `/arcade/quiz-rush` (Quiz Rush — Phase 1), `/arcade/moneyword` (MoneyWord daily word puzzle — **new Phase 2**), `/progress`, `/stats`, `/settings`.
**Admin routes (as of 2026-06-23):** `/admin`, `/admin/modules`, `/admin/badges`, `/admin/challenges`, `/admin/feedback`, `/admin/video-health`, `/admin/video-curation`, `/admin/market-content`, `/admin/arcade-words` (MoneyWord word-bank review — **new Phase 2**), `/admin/analytics`, `/admin/settings`.

**What's left** is on the backlog: **launch-critical human/operator items** (TestFlight upload + beta cohort, M5 pricing go-live, App Store listing) and **operator content production** for the 9 empty markets on the now-shipped localization engine. No localization engineering is outstanding.

> **Repo model:** this is the dedicated `ashmorel/investikid` repo. Branches flow **`testing` → `staging` → `main`** with three separate Postgres DBs; production promotion is **manual** (Railway backend on green `main` CI; Vercel prod web is a manual `vercel deploy --prod` + alias to `app.investikid.ai`). Ask before any **production** DB migration whether to snapshot first.
> **⚠️ BETA shortcut — CURRENT (set 2026-06-21):** while in beta, commit **straight to `main`** and skip the `testing`/`staging` hops to ship faster. CI still gates `main`; the `testing`/`staging` branches + DBs are untouched, not retired. **Reinstate the full `testing` → `staging` → `main` flow at the official release.** See `docs/deployment-environments.md`.

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
- iOS/Android: `npx cap sync ios` / `npx cap sync android` after a build, then rebuild in Xcode / Android Studio. The native bundle bakes the API base from `frontend/.env.local` (`VITE_API_BASE_URL=https://api.investikid.ai` — the canonical domain, not the railway host); store-ready builds are iOS **14** / Android `versionCode` **2** (bump per upload). Full steps: `docs/deployment-environments.md`.

## Golden rules
- **Never read or modify any `.env` file.** Secrets live there; `.env.example` lists the variables.
- Commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Railway deploys the backend only on green CI** (5 jobs: frontend, backend, security, a11y, responsive). **Vercel prod web does NOT auto-deploy** — ship it manually: `vercel --prod` then `vercel alias set frontend-<hash>-investikid.vercel.app app.investikid.ai` (the custom domain is pinned and won't auto-follow). A git push alone ships nothing to web. See lines above + `docs/deployment-environments.md`.
- TDD; minimal focused changes. DB changes = hand-written chained Alembic migration (check `alembic heads` first).
- Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient` on the app engine.
- LLM output is always moderated (`moderate_output`); premium-gate with `is_premium`; rate-limit LLM endpoints. It's a kids' app — keep it safe and WCAG 2.2 AA accessible.
- iOS: keep form controls ≥16px on touch (no `maximum-scale`); keep the WKWebView re-layout + safe-area handling.
- **After every push to `main`, update the progress docs as part of the same task** — move the shipped item into "Live in prod" in `docs/MASTER-BACKLOG.md` and refresh `docs/superpowers/PROGRESS.md` / the roadmap entry. A change isn't done until the trackers reflect it.

## Feature workflow
For any non-trivial feature/change: **design spec → implementation plan → TDD**. Write a short spec to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (goal, scope, data/API, UX, edge cases, test plan), then a task-by-task plan in `docs/superpowers/plans/`, then implement test-first (failing test → minimal code → commit per task). Verify (ruff + pytest; tsc + lint + test + build, plus `vitest-axe` for new UI), push, confirm green CI. Surface trade-offs instead of assuming; minimum code; touch only what the task needs.

## Domain invariants & criteria (honor in future changes)
These are settled decisions — match them unless the user explicitly changes them.

- **Web auth is same-site.** Prod web (`app.investikid.ai`) calls the API at **`https://api.investikid.ai`** (a Railway custom domain on the prod backend), never `investikid.up.railway.app`. They share `investikid.ai`, so the `SameSite=None` auth cookie is first-party; the railway host is cross-site and Safari/Chrome block the cookie → login shows "Could not start your session". The Vercel **Production** `VITE_API_BASE_URL` must stay `https://api.investikid.ai`; verify from the live bundle (`grep -c api.investikid.ai` =1, railway =0). Spec: `docs/superpowers/specs/2026-06-15-web-auth-same-site-api-design.md`.
- **Content authoring (market content generation).** Write in the market's English variant — **American English for US/CA** (`mom/neighbor/color/check/soccer`, never `mum/neighbour/colour/cheque/maths/paper round`), British elsewhere (`_market_english`). Ground every example in the verified `MarketBrief` (local products/regulators/currency) — never UK-specific products in non-GB markets. Keep lessons **diverse**: rotate character names/genders/backgrounds + scenarios, blend card/quiz/scenario formats, and use the sibling-`avoid` list so a level's questions aren't near-duplicates. **Spread concepts** across distinct facets per level — don't stack 3+ concepts on one product/account (a market's dominant product, e.g. ISA/MPF/FSCS, may anchor its *own dedicated* level, but mixed with other angles). Tiered depth = **10 / 15 / 20** lessons for complexity tier 1/2/3.
- **Simulator apply-missions.** Mission *completion* (`evaluate_apply_missions`) reads **global** portfolio state, so it MUST be scoped to the child's `active_market_code` — otherwise one action completes every market's same-type mission and multiplies XP+cash. Keep missions **sparse/curated** (never bulk-create the same mission_type across many lessons/markets). Investing modules auto-attach **one** mission to their culminating lesson (`investing_missions.sync_investing_missions`): growth/compound→`first_buy`, risk/diversification→`diversify`(n=3); 20 XP + admin-editable per-market cash (`simulator.investing_mission_cash`). `publish_market` re-syncs after a republish; backfill via `sync-investing-missions.yml`.
- **Beta delivery + prod safety** (also above): straight-to-`main` in beta; **ask before any prod DB migration** whether to snapshot; manual Vercel prod deploy = `vercel deploy --prod --archive=tgz --yes` then `vercel alias set <slug> app.investikid.ai` (the `--prod` deploy does NOT auto-switch the alias); new `/internal/*` cron POSTs need a CSRF allowlist entry.

## Gotchas
- The local test Postgres can hang after a killed pytest run — if a DB test hangs ~90s+, it's environmental; rely on CI.
- A Figma design-system token file (colours/type/radii, generated from `tailwind.config.js` + `index.css`) exists for reference — foundation only, not full screens.

> Cursor-specific, path-scoped rules live in `.cursor/rules/`.
