# InvestiKid — Master Backlog

**Updated:** 2026-06-20 (pre-TestFlight hardening + native child-purchase shipped)
**Purpose:** the single go-forward list of what's left. Strategic context + per-M
detail live in [`docs/2026-06-12-market-leader-roadmap.md`](2026-06-12-market-leader-roadmap.md);
this is the actionable tracker. Update it as items ship — **and update it (plus any
relevant `docs/superpowers/PROGRESS.md` / roadmap entry) immediately after every push
to `main`, as part of shipping.**

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
- **Cron hardening** — ✅ in prod 2026-06-16 (`video-health-cron` per-endpoint isolation + retries + corrected default URL; validated by manual run).
- **Frontend Dependabot — 0 open** — ✅ 2026-06-16 (vite/form-data/@babel/core patched within Vite 6, then **Vite 6→7** major upgrade shipped to prod; the 2 remaining esbuild alerts dismissed as `not_used` — Deno-install-path #17 and Windows-dev-server #22, neither reachable in our Node/Vite/macOS-Linux setup).
- **Revision / spaced-repetition ("Revise")** — ✅ shipped to prod 2026-06-16 (home card + Revise tab/hub + capped-5 weak-first sessions with mastered-concept refreshers; LLM-generated cached/moderated questions; per-correct XP feeds the daily goal/streak; wrong refresher re-enters the SR loop; reuses the existing SR engine — **no migration**; WCAG 2.2 AA, vitest-axe).
- **Seamless onboarding + native child-initiated purchase (Ask-to-Buy)** — ✅ shipped to prod 2026-06-20 (main, **no migration**; Railway + Vercel `app.investikid.ai` 200, `/billing/child/*` 401-unauth = live). Makes the kids' app more Duolingo-like AND lets a child start a subscription themselves on native, mediated by Apple **Ask to Buy** / Google Play **family approval** — instead of the internal email request (kept for **web**). (1) **Onboarding** verify+polish — signup already collects `parent_email` only where the child's country+age requires it (`resolve_policy`); locked with a regression test, consent copy made threshold-agnostic ("the rule where you live") for the EU-16 markets. (2) **Backend** `household_key(user)` (parent_email, or a self-managed teen's own email) + `recompute_household_premium` generalized for the teen self-household (behavior-neutral for normal households); **child-scoped** `/billing/child/*` endpoints (account-token, apple/google verify, plans) authed by `get_current_user`, scoped solely from the authenticated child (no request field can cross households), reusing the existing verify services unchanged. (3) **Lightweight parental gate** (arithmetic, friction-not-auth) before the native purchase sheet. (4) **`runNativePurchase`** shared helper (discriminated-union per-platform deps; pending-aware) — SubscriptionCard refactored onto it. (5) **Child paywall** native path: gate → purchase → `active` (unlock) / **`pending`** ("asked your grown-up" — Ask-to-Buy deferred, NO early unlock; entitlement flips later via webhook + the daily reconcile) / `cancelled`; web keeps the email flow + a native "ask a grown-up" fallback link. Self-managed teens can self-purchase. Backend ruff + 39 billing/consent tests; frontend tsc+lint+**1064 tests**+build; `cap sync ios` (native path rides the next TestFlight build). Spec/plan `docs/superpowers/{specs,plans}/2026-06-20-seamless-onboarding-native-purchase*`. **⚙️ OPERATOR/App-Store before this transacts:** the gate + OS Ask-to-Buy are the consent mechanisms (Ask-to-Buy only mediates on a Family-Sharing **child** Apple ID — otherwise the OS sheet's own Apple-ID auth applies); kids-category review of the parental-gate-before-purchase flow; and the M5 pricing go-live (Stripe/Apple/Google products) is still required for ANY purchase to complete. A legal review of the consent-age matrix + kids-purchase flow is recommended before public launch.
- **Pre-TestFlight hardening** — ✅ shipped to prod 2026-06-20 (main, **no migration**; Railway + Vercel `app.investikid.ai` 200). Three fixes from a pre-TestFlight review: (1) **persistent login** — silent single-flight refresh-on-401 + retry-once in `apiFetch` using the existing 30-day refresh token, so non-biometric users stay logged in for the refresh window instead of being bounced every ~15 min (no backend change; entitlement still checked server-side per request); (2) **subscription freshness** — `recompute_household_premium` now requires an unexpired `current_period_end` (null still entitles), PLUS a daily `subscription_reconcile_service` cron (`/internal/subscriptions/reconcile`, CSRF-exempt, `X-Cron-Secret`) that re-pulls authoritative Stripe/Apple/Google state for at-risk rows so a missed webhook self-heals without falsely revoking auto-renewals; (3) **streak-reminder nudge** — a one-time native `StreakReminderNudge` on Home prompting an engaged kid (live streak) to enable the off-by-default reminder, OS-permission-respecting. Backend ruff+tests, frontend tsc+lint+1048 tests+build, `cap sync ios` done (Units 1 & 3 ride the next native build). A deploy-verification probe caught + fixed a CSRF-allowlist miss on the new cron endpoint (would've left the reconcile unreachable). Spec/plan `docs/superpowers/{specs,plans}/2026-06-20-pre-testflight-hardening*`.
- **Localization + multi-market programme** — ✅ **ENGINEERING COMPLETE, all live in prod** (2026-06-17 → 2026-06-20). Global rollout engine across 10 markets (GB/US/AU/CA/IE/ES/FR/DE/HK/SG) + 6 UI languages (en/es/fr/de/zh-Hant/zh-Hans). Sub-projects, each spec'd/planned/TDD'd/promoted: **0** Gemini model lineup (lite=Flash-Lite, standard=Flash, premium+verifier=gpt-5-mini, Together fallback) · **A** i18n foundation (`users.language`, react-i18next, no-literal-string lint) · **B** AI replies in the user's language (+ multilingual moderation) · **C1** `Market` entity + market-based content gating · **C2a** per-market progress (`UserMarketProgress`, switchable active market, invariant-safe XP) · **C2b** multi-market kids' UI (picker, switcher, per-market home/stats, coming-soon) · **D** cross-market rewards (coins + "Market Mastered" badges) · **E1** content-translation pipeline (stored, moderated, curated-overridable) · **multi-market premium gate** (free users get ONE started market; premium unlocks all) · **E2** per-market content-wave pipeline (verified `MarketBrief` → scaffold from GB → market-grounded generation → review → publish) · **E2.1** intelligent market content (UK-residue adaptation guard on drafts + model-proposed market-specific modules with one-click create + market-native generation). Ships **INERT** for current users (everyone on GB); the gate/new markets only bite once an operator publishes non-GB content. Specs/plans: `docs/superpowers/{specs,plans}/2026-06-1[7-9]-*`. **Remaining = operator content production** (see post-launch bets) — no localization engineering outstanding.

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
| **M10 teen-testing prep** | 💻 | Figma visual-direction mockups (darker/flatter theme, dialled-back mascot, denser simulator) for the teen sessions — *before* any Investor-Mode code change. Then one iteration pass from findings. Needs the beta cohort recruited first. |
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
- **Regional curriculum depth** — the **engine is built and live** (localization + multi-market programme, incl. the E2/E2.1 per-market content pipeline). What remains is **operator content production**: per empty market run brief → verify → (suggest/scaffold) → generate → expert-review → publish, then enable content languages via E1. This is a content/ops effort on shipped tooling, not new code.
- **AI Coach proactivity** — weekly personalised "your plan this week," premium-gated.
- **R2 self-hosted video** — parked; YouTube covers lessons. Enable Cloudflare R2 (5 env vars) only if/when self-hosted video is wanted; upload-size enforcement already in place.

---

## How items graduate

Non-trivial work runs the superpowers pipeline: **brainstorm → spec
(`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → TDD on `testing` →
gated promotion** (`testing → staging → main`; prod DB-snapshot ask before any
migration). Operational items (M1/M2/M5/M10/M11/M12) are runbooks/checklists with
little-to-no code. Mark items off here as they ship.

**After every push to `main`, update the progress docs as part of the same task** —
move the shipped item into "Live in prod" here, and refresh `docs/superpowers/PROGRESS.md`
and the relevant roadmap entry. Shipping isn't done until the trackers reflect it.
