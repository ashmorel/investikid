# Pre-TestFlight / Launch Readiness Checklist

**Purpose:** A single go/no-go gate before promoting a build to TestFlight (and, later, App Store / Google Play). Copy this file per release, fill in the version-pairing block, tick every gate, and commit it before you upload. **Do not upload with an open blocker.**

> Companion docs: device QA → [`../release-qa-checklist.md`](../release-qa-checklist.md) + [`../release-signoffs/`](../release-signoffs/); store copy → [`2026-06-15-app-store-listing-kit.md`](2026-06-15-app-store-listing-kit.md); envs/deploy → [`../deployment-environments.md`](../deployment-environments.md); ops → [`../operations/monitoring-and-incident-runbook.md`](../operations/monitoring-and-incident-runbook.md).

## Version pairing (fill in — a sign-off is valid only for these exact versions)
| Component | Version / commit | Notes |
|---|---|---|
| Backend (Railway, prod) | `____` (main SHA) | `GET https://api.investikid.ai/health` → 200 |
| Web (Vercel, prod) | `____` (bundle hash) | bundle bakes `api.investikid.ai` (grep =1, railway =0) |
| iOS build | `____` (TestFlight build #) | `npm run build && npx cap sync ios` done from this commit |
| Android build | `____` (internal-testing build #) | `npx cap sync android` done from this commit |
| Alembic head | `____` | `alembic heads` = single head; prod migrated |

## Blocking gates (all must be ✅)
- [ ] **Health:** `api.investikid.ai/health` 200; `app.investikid.ai` 200 and serving the paired bundle.
- [ ] **Login (Safari + Chrome + native):** sign in persists across refresh; `/users/me` succeeds. (Same-site invariant: `VITE_API_BASE_URL=https://api.investikid.ai`.)
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
