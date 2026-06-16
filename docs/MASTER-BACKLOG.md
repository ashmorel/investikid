# InvestiKid — Master Backlog

**Updated:** 2026-06-16
**Purpose:** the single go-forward list of what's left. Strategic context + per-M
detail live in [`docs/2026-06-12-market-leader-roadmap.md`](2026-06-12-market-leader-roadmap.md);
this is the actionable tracker. Update it as items ship.

**Owner legend:** 👤 you (human) · ⚙️ operator (console/config, no code) ·
💻 code (dev) · 🤔 decision.

---

## ✅ Live in prod (for context — not outstanding)

Full build track **M3–M9** (home redesign, product analytics, pricing/packaging,
outcome paywall + Mastery Report, daily goal + push foundation, Penny cosmetics,
group challenges + seasonal events) · **SP-Bio Face ID login** · **iOS push parity**
(FCM bridge, verified E2E) · **parent-management dashboard** (access bridge,
back-to-app, full logout) · **web auth** (same-site `api.investikid.ai`) · prod
**Firebase** credential · **CRON_SECRET** rotated · **R2 upload-size** enforcement ·
LLM token instrumentation · device-QA fixes (login cookie race, safe-area,
BottomSheet portal, ChildCard wrap, toasts) · **app icon** finalised.

- **LLM topical guardrails** — ✅ shipped to prod 2026-06-16 (regex input gate + shared preamble across all 9 LLM surfaces + structured guardrail logs + adversarial test suite).
- **Security: `starlette` ≥1.3.1 bump** — ✅ in prod (`starlette==1.3.1` / `fastapi==0.137.1`; clears GHSA-wqp7/x746/jp82/82w8; pip-audit clean).
- **Simulator stock-page crash fix** — ✅ shipped to prod 2026-06-16 (drop NaN price-history rows at the provider + guard `StockChart` against null close).

---

## 🔴 Now — launch-critical path (mostly human)

| Item | Owner | Notes |
|---|---|---|
| **Archive + upload iOS build to TestFlight** | 👤 | Build **1.0 (6)**, prod-pointed, all fixes bundled. Bump to 7 if 6 already uploaded. |
| **Recruit + distribute beta cohort (M2)** | 👤 | 10–20 families across **8–10 / 11–13 / 15–18** bands (the teen band feeds M10). Comp premium generously. |
| **Google Play upload** | 👤 | Signed AAB built + ready; needs account approval + upload. |

## 🟠 Next — operator config to transact & submit (no code)

| Item | Owner | Notes |
|---|---|---|
| **M5 pricing go-live** | ⚙️ | Stripe monthly+annual Prices (GBP/HKD); App Store Connect `premium_annual` + price points + **Apple Small Business Program** (15% vs 30%); Play Console `premium_annual`; set `*_ANNUAL` env vars. *Until done, IAP can't transact (the "something went wrong" on Subscribe).* |
| **M11 App Store Connect listing** | ⚙️ | Paste copy/keywords from the [listing kit](launch/2026-06-15-app-store-listing-kit.md); capture 5 screenshots; enter **privacy nutrition labels**; confirm **age rating** (4+ vs 9+/12+ — 🤔 decision in the kit). |
| **Confirm OpenAI account spend cap + billing** | ⚙️🤔 | 30-sec check so premium (`gpt-4o-mini`) doesn't silently fall back to Llama. No top-up needed for beta; size the real cap post-beta from token data. |

## 🟡 Soon — code I can do when scheduled

| Item | Owner | Notes |
|---|---|---|
| **Revision / spaced-repetition** | 💻🤔 | Lightweight "Revise" surface that resurfaces completed-lesson concepts so learning sticks; reuse existing lesson/quiz content + progress signals (`StrengthsGaps`), award XP/streak, WCAG 2.2 AA. **Decision:** slot into the stickiness track now (pre-beta) or defer post-launch. Last open item from the 2026-06-15 Quality & safety set (guardrails + starlette now shipped). |
| **M10 teen-testing prep** | 💻 | Figma visual-direction mockups (darker/flatter theme, dialled-back mascot, denser simulator) for the teen sessions — *before* any Investor-Mode code change. Then one iteration pass from findings. Needs the beta cohort recruited first. |
| **Vite 7 upgrade (clears esbuild advisory)** | 💻 | Last open Dependabot alert is esbuild GHSA-gv7w-rqvm-qjhr (high, but **dev-server-only** — not a production/runtime risk). The patched esbuild only ships with **Vite 7**; the other 4 alerts (vite/form-data/@babel/core) were cleared 2026-06-16 within Vite 6. Do the Vite 6→7 major bump + regression pass when convenient. Low urgency. |
| **Native → `api.investikid.ai`** | 💻 | Migrate `NATIVE_API_FALLBACK` to the same-site API in a future native build (cleaner; build 6 keeps the railway URL, which still works). Low priority. |
| **Testing/staging web same-site** | 💻⚙️ | Replicate the `api-testing` / `api-staging` subdomains if web QA on those envs is needed. Deferred (prod-only fix shipped). |

## 🔵 Later — launch readiness (M12) & teen validation (M10)

| Item | Owner | Notes |
|---|---|---|
| **M10 · Teen validation** | 👤💻 | 5–8 real 15–18s, structured script → documented findings + one shipped Investor-Mode iteration. Runs once beta cohort exists. |
| **M12 · Launch readiness** | 👤💻⚙️ | Full device-QA sign-off on the launch build (billing, video, auth, progress-save, offline on real HW); observability/alerts check; support-email + feedback-triage flow; Railway load sanity; **prod backup cadence** confirmed. |

## ⚪ Post-launch bets (sketched, not committed)

- **School/teacher packaging** (highest-margin hedge) — start with 2–3 teacher chats during beta, zero code.
- **Android / Play Store launch** — billing built; needs device-QA matrix + listing.
- **Regional curriculum depth** — AU/CA localised content next.
- **AI Coach proactivity** — weekly personalised "your plan this week," premium-gated.
- **R2 self-hosted video** — parked; YouTube covers lessons. Enable Cloudflare R2 (5 env vars) only if/when self-hosted video is wanted; upload-size enforcement already in place.

---

## How items graduate

Non-trivial work runs the superpowers pipeline: **brainstorm → spec
(`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → TDD on `testing` →
gated promotion** (`testing → staging → main`; prod DB-snapshot ask before any
migration). Operational items (M1/M2/M5/M10/M11/M12) are runbooks/checklists with
little-to-no code. Mark items off here as they ship.
