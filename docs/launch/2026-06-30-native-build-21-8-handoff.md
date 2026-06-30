# Native build handoff — iOS 1.0 (21) + Android versionCode 8

**Date:** 2026-06-30 · **Owner from here:** 👤 you (archive/upload)

## ✅ What I already did (prep complete — `0ecb832b`)
- `npm run build` (fresh prod web) + `npx cap sync ios` + `npx cap sync android`. The native
  projects now bundle **all the Theme-B web work since build 20**:
  - **B5 ratings flywheel** — native OS review prompt at a delight moment (7-day streak or first
    level mastery; ≤once/60 days, never first session). This build is the **first to carry the
    `@capacitor-community/in-app-review` native plugin** (registered on iOS via SPM `Package.swift`
    and Android via gradle) — so B5 actually fires on-device now.
  - **B6 streak beats** — "Streak saved!" toast, freeze countdown, coin-funded streak-repair card.
  - **B1 focused Home** — one dominant lesson hero (goal + streak + freeze countdown folded in),
    secondary content demoted.
  - The **onboarding-diagnostic copy fix** ("Check answer" → "Next" + clearer baseline framing).
- Bumped **iOS `CURRENT_PROJECT_VERSION` 20 → 21** and **Android `versionCode` 7 → 8** (both 1.0).
- **Android build fix:** the in-app-review plugin shipped a deprecated `proguard-android.txt`
  reference the project's Android Gradle Plugin rejects — patched to `-optimize.txt` via
  **`patch-package`** (added as a devDep + a `postinstall` hook + `frontend/patches/`), matching how
  the other Capacitor plugins are configured. **The signed AAB builds clean.** (Future `npm install`
  re-applies the patch automatically — nothing to remember.)
- Committed + pushed to `main`.

## 1️⃣ iOS → TestFlight (Xcode)
1. Open **`frontend/ios/App/App.xcodeproj`** in Xcode (SPM project — open the `.xcodeproj` directly,
   no workspace). Let Swift Package Manager resolve packages (it'll fetch in-app-review the first time).
2. Scheme **App**, destination **Any iOS Device (arm64)**.
3. **Product → Archive** (signing automatic, team **U2F5E8277U**).
4. Organizer: **Distribute App → App Store Connect → Upload**.
5. When it finishes processing: **TestFlight → add build (21) to your test group → assign testers**.

## 2️⃣ Android → Play Internal testing (AAB already built)
I already ran the signed build, so the upload file is ready:

```
frontend/android/app/build/outputs/bundle/release/app-release.aab   (versionCode 8)
```

Play Console → **Internal testing → Create new release → upload that AAB → roll out**.
(To rebuild yourself: `cd frontend/android && ./gradlew :app:bundleRelease`.)

## 3️⃣ Device sign-off (before sharing widely)
On a real iPhone + Android device (per `docs/release-qa-checklist.md`):
- **B5:** can't be forced (the OS throttles the review prompt) — just confirm nothing crashes around
  a lesson completion / streak milestone.
- **B6:** complete a lesson that uses a freeze → "Streak saved!" toast; StatsCard/hero shows the
  freeze countdown; if you let a streak lapse, the repair card offers to spend coins.
- **B1:** Home leads with one dominant lesson hero; goal + streak live inside it.
- Onboarding diagnostic, Progress drill-down, parent Mastery report, auth, push, safe-areas all OK.

---

## 📋 Release notes (paste-ready, parent-facing)

**App Store "What's New" (build 21):**
> A friendlier, more focused InvestiKid. The home screen now leads with one clear "what to do today"
> so kids aren't overwhelmed, streaks celebrate the moments that matter (including a "streak saved!"
> when a freeze kicks in), and they can spend earned coins to rescue a slipped streak. Games now
> steer practice toward the topics your child finds tricky.

**Google Play release notes (versionCode 8):**
> More focus, more delight. Home now centres on one clear daily action; streaks get celebratory
> moments and a coin-funded "rescue"; and the arcade now practises the concepts your child is still
> learning. Plus a clearer first-day check.

---

## ⚙️ Still gating a wide beta (operator, unchanged)
- **Approve diagnostic items** (≥2 per topic×difficulty × GB/US/HK) + run the `diagnostic-verify`
  sweep + adjudicate flags (you have both one-click paths: "Looks correct — keep published" and
  "Unpublish to edit"). GB coverage is green; US/HK still to do.
- **Kids-app store declarations** (Families/target-audience, Data safety, content rating, privacy URL).
- **M5 pricing** — only before purchases transact; not a free-beta blocker.

Then recruit the segmented beta (8–10 / 11–13 / 15–18) → the baseline→progress loop produces the
validated "+X%". Don't publish a public "+X%" claim until beta validates the instrument.
