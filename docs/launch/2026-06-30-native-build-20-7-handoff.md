# Native build handoff — iOS 1.0 (20) + Android versionCode 7

**Date:** 2026-06-30 · **Owner from here:** 👤 you (archive/upload) + ⚙️ operator (store/content)

## ✅ What I already did (prep complete)
- `npm run build` (fresh prod web) + `npx cap sync ios` + `npx cap sync android` — the native
  projects now bundle **all the deferred Theme-A web work**: the **onboarding diagnostic** (A3),
  the **progress-check card** (U4), the **Progress concept drill-down** (U5), the **parent growth
  block** (U6), and the public **/how-we-measure** page (A5) — plus everything else since build 19.
- Bumped **iOS `CURRENT_PROJECT_VERSION` 19 → 20** and **Android `versionCode` 6 → 7** (both 1.0).
- Committed + pushed to `main` (`2ec141d2`). The synced web bundle is on disk in the native
  projects (gitignored, as usual) — Xcode/Gradle bundle it at archive time.

## 1️⃣ iOS → TestFlight (Xcode)
1. Open **`frontend/ios/App/App.xcodeproj`** in Xcode (this project uses Swift Package Manager —
   open the `.xcodeproj` directly, there's no workspace).
2. Scheme **App**, destination **Any iOS Device (arm64)**.
3. **Product → Archive** (signing is automatic, team **U2F5E8277U**).
4. In the Organizer: **Distribute App → App Store Connect → Upload**.
5. Once it finishes processing in App Store Connect: **TestFlight → add build (20) to your test
   group → assign testers**.

## 2️⃣ Android → Play Internal testing (signed AAB)
1. `cd frontend/android && ./gradlew :app:bundleRelease`
   (signs with the upload key from `keystore.properties` — already present).
2. Output: **`frontend/android/app/build/outputs/bundle/release/app-release.aab`**.
3. Play Console → **Internal testing → Create new release → upload the AAB (versionCode 7) →
   roll out**.

## 3️⃣ Device sign-off (before sharing widely)
On a real iPhone + Android device, smoke-test the new surfaces (per `docs/release-qa-checklist.md`):
- The **onboarding diagnostic** appears on a fresh child sign-in (or gracefully skips to Home if no
  items are approved yet), and submit/skip both reach Home — never traps you.
- **Progress** page opens; expanding a topic shows the concept drill-down.
- The **parent Mastery Report** renders (growth block shows once a child has a baseline + a progress
  check; otherwise the gentle "check back" state).
- Auth, video, progress-save, push, safe-areas, large-text all OK.

---

## 📋 Release notes (paste-ready, parent-facing)

**App Store "What's New" (build 20):**
> InvestiKid now shows what your child actually learns. A quick "what you already know" check sets a
> starting point, friendly progress checks reveal how much they've grown, and the Progress page
> drills into specific money concepts — strengths and what to practise next. Your parent report now
> leads with your child's growth, plus conversation prompts to keep the learning going.

**Google Play release notes (versionCode 7):**
> See real learning, not just streaks. A day-one check sets a baseline, progress checks show growth
> over time, and the Progress page now breaks mastery down concept-by-concept. The parent report
> leads with your child's growth + ideas to talk about together.

---

## ⚙️ Operator steps BEFORE you recruit the beta cohort (gates)
These make the new measurement features actually *do* something — see also
`docs/operations/2026-06-29-diagnostic-content-operator-runbook.md`:

1. **Approve diagnostic items** on `/admin/diagnostic-items` — generate + approve **≥2 per
   (topic × difficulty)** across GB/US/HK. Until then, the onboarding/progress checks gracefully
   skip (no measurement). **This is the gate** — without approved items, no baselines capture.
2. **Run the answer-verifier sweep** (Actions → "Concept taxonomy classify"… no — the
   **`diagnostic-verify`** workflow, tier `premium`) and re-review anything in the
   **"Needs review"** filter on `/admin/diagnostic-items` (the verifier flags wrong/ambiguous
   answers — a few genuine, some false positives; you adjudicate).
3. **Kids-app store declarations** (still outstanding from prior builds, gate wider tracks +
   App Store review): Families / target-audience, Data safety, content rating, privacy-policy URL.
4. **M5 pricing go-live** (Stripe/Apple/Google products) — only needed before any purchase transacts;
   not a blocker for a free beta.

## ✅ Then
Recruit the segmented beta (8–10 / 11–13 / 15–18), comp premium generously, share the TestFlight +
Play Internal opt-in links. The baseline→progress loop starts producing the **"+X%"** evidence —
which then surfaces in the parent report. **Do NOT publish a public "+X%" claim until beta data
validates the instrument** (OD4).

> After beta + this, the next *engineering* is **Theme B** (focus/retention: one canonical daily
> action, arcade-subordination rule, ratings-and-reviews flywheel, streak emotional beats).
