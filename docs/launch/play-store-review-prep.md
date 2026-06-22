# Google Play Review Prep (Android / Internal testing → Production)

**Purpose:** What Google Play review looks for on a **kids' finance-education app with login + subscriptions**, likely rejection reasons, and what to prepare. Pair with [`2026-06-15-app-store-listing-kit.md`](2026-06-15-app-store-listing-kit.md), the [`../2026-06-07-android-operator-runbook.md`](../2026-06-07-android-operator-runbook.md) (signing/Play Console/Billing setup), and the [`2026-06-22-pre-testflight-readiness-checklist.md`](2026-06-22-pre-testflight-readiness-checklist.md).

App: **InvestiKid** · applicationId `leeashmore.investikid.ai.app`.

## Must-haves before submission (Play-specific)
- [ ] **Target audience & content declaration (Families policy).** In Play Console → Policy → declare the target age groups. Because the audience includes children, the app falls under the **Families / Designed for Families** policy: privacy policy required, ads (if any) must be families-appropriate (we have none), and any SDKs must be on Google's approved list.
- [ ] **Data safety form.** Declare exactly what's collected/shared and why (reconcile with `docs/compliance/DPIA.md`): account data, app activity; **no data sold; no third-party ad tracking.** Mismatches with actual behaviour are a top rejection cause.
- [ ] **Content rating (IARC questionnaire).** Complete honestly; an unrated app can't publish.
- [ ] **Account + data deletion (required).** Play requires both in-app deletion AND a **publicly reachable URL** to request account/data deletion. We have in-app deletion (→ 30-day purge); ensure a deletion-request URL/section is linked (can live on `app.investikid.ai/privacy` or a dedicated page).
- [ ] **Privacy policy URL** live: `app.investikid.ai/privacy` (InvestiKid-branded; contact `privacy@investikid.ai`).
- [ ] **Play Billing for subscriptions.** Digital subscriptions must use **Google Play Billing** (we use a custom Kotlin Play Billing plugin — see Android runbook §9). Don't take web payment for the digital sub inside the Android app.
- [ ] **Reviewer test account.** Provide a working **learner (DOB 8–16)** + **parent** login in the review notes; pre-activate the demo child if the consent gate would block the reviewer.
- [ ] **Virtual / educational, not real trading.** State clearly (Play scrutinises financial apps): the simulator is **virtual cash, no real money or securities**.
- [ ] **Target API level** meets Play's current requirement for new apps/updates (check the Android runbook / Play Console warning).
- [ ] **App signing** via Play App Signing; verify `assetlinks.json` is live for App Links after first upload (runbook §3/§5).

## Likely rejection reasons & coverage
| Risk | Policy | Status / action |
|---|---|---|
| Data safety form mismatch | Data safety | **Action:** fill to match DPIA exactly |
| No/incomplete deletion path | Account deletion | OK in-app; **Action:** add public deletion-request URL |
| Families policy / SDKs | Designed for Families | **Action:** confirm SDKs approved; no ads |
| Web payment for digital sub | Payments | OK — Play Billing used; keep it on Android |
| No reviewer login | Functionality | **Action:** add demo learner + parent creds |
| Looks like real trading | Financial services | **Action:** state "virtual/educational, no real money" |
| Missing content rating | IARC | **Action:** complete questionnaire |
| Stale target API level | Target API | **Action:** verify against current requirement |

## Submission flow
1. Pass the readiness checklist on the exact AAB; device-QA sign-off committed (incl. **Android biometric on a real device** — only emulator-verified so far per `docs/release-signoffs/`).
2. Upload AAB → **Internal testing** track → verify on device (runbook §8 parity checklist) → promote to closed/open testing → Production.
3. Complete: store listing, data safety, content rating, target audience, privacy policy + deletion URL, subscription details.
4. Consider a **staged rollout** (e.g. 10% → 100%) for production so issues surface before full exposure.

## Notes
- RTDN (real-time developer notifications) can miss; the daily `subscriptions/reconcile` cron self-heals entitlements (see `../operations/monitoring-and-incident-runbook.md`).
- If rejected, Play cites the specific policy — fix and resubmit with a note describing the change.
