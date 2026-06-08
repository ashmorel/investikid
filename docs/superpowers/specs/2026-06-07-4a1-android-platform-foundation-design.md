# Android Platform Foundation (Item 4A · Sub-project A1) — Design Spec

**Date:** 2026-06-07
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** premium content & pricing → **4A (multi-channel payments)**, sub-project **A1**
**Sequence within 4A:** A2 (payments + iOS) ✅ → **A1 (this — Android platform foundation)** → A3 (Android Play Billing)
**Builds on:** the existing React 18 + Vite + TS + Tailwind v4 + shadcn app with a shipping **Capacitor 8 iOS** app.

## Goal

Stand up the **Android platform** for InvestiKid at feature/visual parity with iOS+web: add `@capacitor/android` + a committed `android/` project, close the Android-specific code/UX gaps, generate Android icons/splash, wire an on-demand Android build in CI, and document the operator-only steps. This is the prerequisite for **A3 (Google Play Billing)**. **No payments** here.

## Hard environment constraint (shapes the whole sub-project)

The build environment has **no Android toolchain** (no JDK, Android SDK, Gradle, Android Studio, or emulator). Therefore:
- **In-repo work is verifiable here only** via `npx cap sync android` + web `npx tsc -b` / `npm run lint` / `npm run build`. The Android project **cannot be compiled, run, or device-tested here.**
- The **first real proof it compiles** is the manual CI Android build (below) or opening `android/` in Android Studio.
- A meaningful chunk of A1 is committed **without being built or run** — this is accepted (decided with the user); the plan isolates and flags the native bits.

## In-repo vs operator-side split

**In-repo (built now, committed to `testing`):**
- `@capacitor/android` dep + committed `android/` (Capacitor 8 template) with a scoped `.gitignore`.
- Android config + code parity that doesn't need a device (Sections 2–3).
- Android adaptive icons + splash from existing brand assets.
- The manual **Deployment checkpoint** Android build wired to compile.
- The operator runbook.

**Operator-side (documented in the runbook; cannot be done/verified here):**
- Install JDK 21 + Android SDK / Android Studio.
- Create the upload **keystore**; enrol in **Play App Signing**.
- Create the **Play Console** app + internal-testing track; first AAB upload.
- Google Cloud: add the **Android OAuth client** (needs the keystore **SHA-1/SHA-256**) for Google social login.
- Host `.well-known/assetlinks.json` for App Links verification.
- **On-device / emulator parity verification** (the real test).

---

## Section 1 — Architecture & boundary

A1 = "the Android app exists, is configured for parity, and is documented to build" — explicitly **not** payments (A3) and **no** iOS/backend changes. The split above is the architecture: a verifiable in-repo foundation plus a precise operator runbook for the device/account-bound parts.

## Section 2 — Native scaffold + config parity

- **Scaffold:** add `@capacitor/android` matching the existing `^8.3.x` Capacitor line; generate `android/` via `npx cap add android` + `npx cap sync android`. **Commit `android/`** (parity with the committed `ios/`) with a scoped `.gitignore`: `android/build/`, `android/app/build/`, `android/.gradle/`, `local.properties`, `*.keystore`, `*.jks`, and `google-services.json` (if ever used). Keep Capacitor 8 SDK defaults (minSdk 23, compile/target SDK 35) unless a plugin requires otherwise.
- **Shared config already Android-correct:** `appId leeashmore.investikid.ai.app`, `androidScheme: 'https'`, and `CapacitorHttp`+`CapacitorCookies` enabled — these make the cross-origin Railway auth cookie + CSRF double-submit work in the WebView (the same need iOS had). No change required.
- **AndroidManifest.xml:**
  - Permissions: `INTERNET` (default) + `POST_NOTIFICATIONS` (Android 13+, for local-notifications). Prefer **inexact** alarms for the streak reminder to avoid `SCHEDULE_EXACT_ALARM` Play-policy friction (confirm against `streakReminder.ts`; only add exact-alarm permissions if genuinely required).
  - `android:windowSoftInputMode="adjustResize"` on the main activity (keyboard parity).
  - **Deep-link intent filters** for the OAuth/magic-link return path, mirroring the iOS associated-domain setup — an **App Links** `<intent-filter android:autoVerify="true">` for the web origin (`app.investikid.ai`). The matching `.well-known/assetlinks.json` (needs the signing SHA-256) is operator-side.
- **Social login (Google) config:** capgo `@capgo/capacitor-social-login` already receives the Google **Web client ID** (`VITE_GOOGLE_WEB_CLIENT_ID`); the **Android OAuth client + SHA-1** is operator-side. Apple Sign-In on Android uses the existing web flow (no native config).

## Section 3 — Code / UX parity

The web layer is largely platform-agnostic already (`isNativeApp()` → `Capacitor.isNativePlatform()`; safe-areas via CSS `env(safe-area-inset-*)`). Android gaps to close:

- **Hardware back button (new — iOS has none):** add `@capacitor/app` with one listener doing in-app history back, minimizing/exiting only at a root route. Prevents the back button from abruptly closing the app. Highest-priority behavioural parity item.
- **Edge-to-edge insets + status bar:** Android 15 forces edge-to-edge. Ensure `viewport-fit=cover` is set and the existing `--safe-top/--safe-bottom` insets apply; add `@capacitor/status-bar` to overlay the status bar with a style matching the sky-blue theme so content isn't obscured. Main visual-parity risk → operator eyeballs on device.
- **Keyboard:** `windowSoftInputMode="adjustResize"` (manifest) so inputs aren't covered.
- **Local notifications:** request the Android 13+ `POST_NOTIFICATIONS` runtime permission and ensure the streak reminder creates a notification channel (verify against `streakReminder.ts`).
- **Inline video:** the iOS YouTube `Referer` proxy (`yt.html`) currently triggers on any native platform; confirm it works on Android (it should — valid https proxy) or scope it iOS-only. Add a small `isAndroid()` / `getPlatform()` helper to `platform.ts` for any such branch.
- **Social login:** no code change — `socialLogin.ts` already passes the Google Web client ID + Apple Services ID; Android Google relies on the operator Android OAuth client + SHA-1; Apple uses the web flow.

## Section 4 — Icons/splash, build validation, runbook

- **Icons & splash:** use `@capacitor/assets` to generate Android **adaptive icons** (foreground + sky-blue background), legacy icons, and the splash from the 1024 master in `docs/icon-mockups/`. Committed under `android/app/src/main/res/`.
- **Build validation (chosen gate — on-demand, no per-push cost):** extend the manual **Deployment checkpoint** workflow's `run_android` job to actually compile — `actions/setup-java` (JDK 21) + `android-actions/setup-android`, then `npm ci && npm run build && npx cap sync android && ./gradlew assembleDebug` (and `bundleRelease` for an AAB on demand). This is the first real compile-proof of the scaffold. (Per the user's standing preference, Android is **not** built on every push.)
- **Operator runbook** (`docs/`): JDK/SDK/Android Studio install; create upload keystore + enrol in Play App Signing; Play Console app + internal-testing track + first AAB; Google Cloud Android OAuth client using keystore SHA-1/SHA-256; host `.well-known/assetlinks.json`; and an **on-device parity checklist** (back button, insets/status bar, inline video, notifications + permission prompt, Google/Apple login, cookie-auth login end-to-end).

## Testing & verification

- **Here:** `npx cap sync android` succeeds; `npx tsc -b`, `npm run lint`, `npm run test`, `npm run build` stay green (the web/JS parity helpers — e.g. `getPlatform()`, back-button wiring guarded by `isNativeApp()` — get unit tests where they're plain functions). No Gradle/device verification possible.
- **Operator:** the checkpoint Android build compiles; the on-device parity checklist passes.

## Out of scope

Google Play Billing / payments (**A3**); any iOS or backend changes; actual Play Store publishing; Android-only features beyond parity.

## Promotion

In-repo changes ride the normal `testing → staging → main` flow. No DB migration in A1 (no backup-gate needed). The Android app only becomes installable after the operator runbook steps; nothing in A1 affects the live web/iOS apps.
