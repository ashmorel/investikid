# App Store Review Prep (iOS / TestFlight → App Store)

**Purpose:** What Apple's review looks for on a **kids' finance-education app with login + subscriptions**, the likely rejection reasons, and exactly what to have ready. Pair with [`2026-06-15-app-store-listing-kit.md`](2026-06-15-app-store-listing-kit.md) (metadata) and [`2026-06-22-pre-testflight-readiness-checklist.md`](2026-06-22-pre-testflight-readiness-checklist.md) (build gate).

App: **InvestiKid** · bundle id `leeashmore.investikid.ai.app` · v1.0.

## Must-haves before submission (most common rejections first)
- [ ] **Reviewer demo account (Guideline 2.1).** The app requires login, so Apple **will** reject without working credentials. Provide a **child/learner test account (DOB in 8–16)** AND a **parent account** in App Review notes — username + password. If the parental-consent email gate blocks the child account, pre-activate the demo child so the reviewer isn't stuck. Include any steps to reach premium content.
- [ ] **It's VIRTUAL / educational, not a real brokerage (Guideline 3.1.1 / financial-services scrutiny).** The simulator uses **virtual cash**, no real money, no real securities trading. Say so in the description AND the review notes, so it isn't mistaken for a regulated trading app.
- [ ] **In-app purchases use Apple IAP (3.1.1).** Subscriptions (monthly/annual) must be Apple IAP for digital content — they are. Don't link out to web payment for the digital subscription from inside the iOS app.
- [ ] **Subscription metadata (3.1.2).** In the binary + App Store Connect: price, duration, content per period, **auto-renew disclosure**, and functional links to **Privacy Policy** (`app.investikid.ai/privacy`) and **Terms/EULA**. Auto-renewable subs must show these on the paywall.
- [ ] **Sign in with Apple (4.8).** Because parent login offers Google, Apple Sign-In must also be offered (it is — keep it visible/equivalent on the parent auth screen).
- [ ] **Account deletion in-app (5.1.1(v)).** Apps with account creation must let users delete their account from within the app (not just deactivate). InvestiKid has the deletion → 30-day purge flow — confirm it's reachable in the UI.
- [ ] **Privacy nutrition labels (5.1.1).** Match what the app actually collects (see `docs/compliance/DPIA.md`): account data, usage, no third-party ad trackers. Don't over- or under-declare.
- [ ] **Privacy policy URL** live and child-appropriate: `app.investikid.ai/privacy` (now branded InvestiKid; contact `privacy@investikid.ai`).

## Kids-specific (decide the path — App Store Kit §7 has the open age-rating decision)
- [ ] **Age rating set** in App Store Connect questionnaire (matches actual content).
- [ ] **If listed in the Kids Category (Guideline 1.3 / 5.1.4):** stricter rules apply — **no third-party analytics or ads**, and any **external links, purchases, or "for parents" areas must be behind a parental gate** (age-appropriate challenge). Confirm: the parent dashboard / purchase flow / external links all sit behind the parental gate.
- [ ] If NOT using the Kids Category, you still must follow kids-data rules since the audience is minors.

## Likely rejection reasons & our coverage
| Risk | Guideline | Status / action |
|---|---|---|
| No reviewer login | 2.1 | **Action:** add demo child + parent creds to review notes |
| Looks like real trading | 2.3 / financial | **Action:** state "virtual/educational, no real money" in desc + notes |
| Web payment for digital sub | 3.1.1 | OK — Apple IAP used; keep it that way on iOS |
| Missing sub disclosures | 3.1.2 | **Action:** verify paywall shows price/terms/privacy + auto-renew |
| Google login without Apple | 4.8 | OK — Apple Sign-In present; keep equivalent |
| No in-app account deletion | 5.1.1(v) | OK — deletion flow exists; **confirm reachable** |
| Parental gate gaps (Kids cat.) | 1.3 / 5.1.4 | **Action:** verify gate on parent area + purchases + external links |
| Privacy label mismatch | 5.1.1 | **Action:** reconcile labels with DPIA before submit |

## Submission flow
1. Pass [`2026-06-22-pre-testflight-readiness-checklist.md`](2026-06-22-pre-testflight-readiness-checklist.md) on the **exact build** (device-QA sign-off committed).
2. TestFlight beta → fix issues → then submit that build for App Store review.
3. Fill App Store Connect: screenshots (from the real build), description, keywords, age rating, privacy labels, subscription metadata, **App Review notes with demo credentials + "virtual/educational" statement**.
4. Submit. If rejected, read the exact guideline cited, fix, reply in Resolution Center (don't just resubmit).

## If rejected (common appeals)
- Cite the specific change made; attach a screen recording of the fixed flow.
- For "looks like financial services": emphasise educational/virtual nature, no real funds, target audience.
- For Kids/privacy: point to the privacy notice + DPIA + parental gate.
