# Pre-TestFlight / Launch Readiness Checklist

**Purpose:** A single go/no-go gate before promoting a build to TestFlight (and, later, App Store / Google Play). Copy this file per release, fill in the version-pairing block, tick every gate, and commit it before you upload. **Do not upload with an open blocker.**

> Companion docs: device QA → [`../release-qa-checklist.md`](../release-qa-checklist.md) + [`../release-signoffs/`](../release-signoffs/); store copy → [`2026-06-15-app-store-listing-kit.md`](2026-06-15-app-store-listing-kit.md); envs/deploy → [`../deployment-environments.md`](../deployment-environments.md); ops → [`../operations/monitoring-and-incident-runbook.md`](../operations/monitoring-and-incident-runbook.md).

## Version pairing — this release (filled 2026-06-22)
| Component | Version / commit | Notes |
|---|---|---|
| Backend (Railway, prod) | `acacd65` (main HEAD; backend code unchanged since `80a0421`) | `GET https://api.investikid.ai/health` → **200** ✅ |
| Web (Vercel, prod) | bundle `index-DbAij6eY.js` (deploy `frontend-6ps4qbxjn`) | bakes `api.investikid.ai` (grep **=1**, railway **=0**) ✅ |
| iOS build | **14** (MARKETING_VERSION 1.0) | synced from `7474004`; `npx cap sync ios` done; native bundle bakes `api.investikid.ai` ✅ |
| Android build | **versionCode 2** (versionName 1.0) | synced from `7474004`; `npx cap sync android` done; native bundle bakes `api.investikid.ai` ✅ |
| Alembic head | `d4f6b8c0e2a1` | single head; **no new migration** this release |

**What ships in build 14 / versionCode 2** (all verified live on web first): Learn-tab market switcher (drives `active_market_code` in place); Home market chip + Learn picker correct after the `has_content` reconcile fix; route-level **ErrorBoundary** (a page crash can't blank the app); **scroll-to-top on route change** (header stays visible on Stats/Progress/Simulator); unified **"Back to App"** control in admin + parent; **native API base = `api.investikid.ai`** (was the Railway subdomain) baked via `frontend/.env.local`.

> **Native API base check (run before archiving):** `grep -roh "api.investikid.ai" frontend/ios/App/App/public/assets/*.js | head -1` and the Android equivalent should each print `api.investikid.ai` (and **no** `railway.app`). This bakes from `frontend/.env.local` → `VITE_API_BASE_URL=https://api.investikid.ai`; a plain `npm run build && npx cap sync` reproduces it.

## Blocking gates (all must be ✅)
- [x] **Health:** `api.investikid.ai/health` 200; `app.investikid.ai` 200 and serving the paired bundle (`index-DbAij6eY.js`, bakes `api.investikid.ai`). Verified 2026-06-22.
- [ ] **Native smoke-test on build 14 / versionCode 2 (NEW — API base changed to `api.investikid.ai`):** on a real install, log in → load lessons → trigger one AI reply (chart insight or Coach). Confirms the native backend-domain switch is clean.
- [ ] **Login (Safari + Chrome + native):** sign in persists across refresh; `/users/me` succeeds. (Same-site invariant: web `VITE_API_BASE_URL=https://api.investikid.ai`; native bakes the same via `frontend/.env.local`.)
- [ ] **Biometric:** Face ID enrol + unlock on a real iPhone; fingerprint on a real Android device. Re-enrolling a face/finger invalidates the stored secret (OS-enforced).
- [ ] **Billing — all three rails tested on real accounts:** Stripe (web), Apple IAP (sandbox), Google Play Billing (license tester). Purchase → premium unlocks; restore works; a missed webhook self-heals via the daily reconcile cron (see runbook).
- [ ] **Content:** the child's market shows live modules/lessons (GB/US/HK currently); simulator loads and a trade executes; an investing lesson's simulator mission CTA appears.
- [ ] **Device QA sign-off committed** in [`../release-signoffs/`](../release-signoffs/) for the exact build above, run on **real devices** (not simulators). Any FAIL = blocker.
- [ ] **Crons green:** last daily run (06:00 UTC) of all 7 internal jobs returned 200 (see runbook for the list).
- [ ] **Privacy notice live + correct** at `app.investikid.ai/privacy`, version matches what's declared in App Store Connect / Play Data Safety.
- [ ] **No secrets in the build**; `.env` untouched; CRON_SECRET / JWT / API keys current per `deployment-environments.md`.

## Known launch gaps to clear before public store submission
- [x] **Email SENDER on `investikid.ai`** — prod sends from `noreply@investikid.ai` (Railway `EMAIL_FROM` env var; `investikid.ai` verified in Resend). Code default in `config.py` matched 2026-06-22.
- [x] **Contact INBOX on `investikid.ai`** — `privacy@investikid.ai` inbox live (Cloudflare Email Routing forwarding, verified 2026-06-22). Contact address flipped in `docs/compliance/privacy-notice.md` + the live app copy `frontend/src/locales/en/parent.json`. (Live web shows it after the next manual Vercel deploy.)
- [ ] **Compliance review** of `docs/compliance/privacy-notice.md` + `DPIA.md` (renamed to InvestiKid 2026-06-22) by legal before submission.
- [ ] **App age-rating decision** (App Store Kit §7) confirmed; Play "Designed for Families" decision made.
- [ ] **Store listing kit** finalised (screenshots from the paired build, not mockups).

## Sign-off
| Role | Name | Date | Verdict (GO / NO-GO) |
|---|---|---|---|
| Release owner | | | |
| Device QA | | | |

**Decision:** ____  ·  **Build uploaded:** ____
