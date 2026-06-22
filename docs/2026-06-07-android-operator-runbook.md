# InvestiKid — Android Operator Runbook

**Date:** 2026-06-07 (production cutover 2026-06-08)
**Branch:** `main` is production; `testing`/`staging` for development (in beta, work commits straight to `main`)
**Design spec:** [`docs/superpowers/specs/2026-06-07-4a1-android-platform-foundation-design.md`](superpowers/specs/2026-06-07-4a1-android-platform-foundation-design.md) (Item 4A · Sub-project A1 — Android Platform Foundation)

This runbook covers the **device- and account-bound steps that cannot be performed in the headless build environment** (no JDK, Android SDK, Gradle, Android Studio, or emulator). Everything here requires a real machine with the Android toolchain, plus access to the Google Cloud Console, the Google Play Console, and the production web origin.

> **Payments.** A1 stands up the Android platform at parity with iOS/web only — no in-app purchases. Google Play Billing is **Sub-project A3**; its operator steps now live in [Section 9 — A3 — Google Play Billing](#9-a3--google-play-billing) below.

## Reference values for this project

| Thing | Value |
| --- | --- |
| App name | InvestiKid |
| Android application ID / package name | `leeashmore.investikid.ai.app` |
| Web origin (App Links host) | `app.investikid.ai` |
| Google **Web** OAuth client ID env var | `VITE_GOOGLE_WEB_CLIENT_ID` (used as `serverClientId` by `@capgo/capacitor-social-login`) |
| Capacitor version | 8 |
| App root (Capacitor + web) | `frontend/` |
| Committed native project | `frontend/android/` |
| On-demand CI Android build | GitHub → Actions → **Deployment checkpoint** → Run workflow with `run_android = true` |

All commands below assume the repo root of `ashmorel/investikid` checked out on branch `testing`.

---

## 1. Local tooling

Install the toolchain on the operator machine (one-time):

1. **JDK 21 (Temurin / Eclipse Adoptium).**
   - macOS (Homebrew): `brew install --cask temurin@21`
   - Or download from <https://adoptium.net/temurin/releases/?version=21>.
2. **Android Studio** (bundles the Android SDK, platform-tools, and an emulator): <https://developer.android.com/studio>. On first launch, let the SDK Manager install **Android SDK Platform 35**, **Android SDK Build-Tools 35**, **Platform-Tools**, and **Android Emulator**.
3. **Set environment variables** (add to `~/.zshrc` / `~/.bash_profile`):
   ```bash
   export JAVA_HOME="$(/usr/libexec/java_home -v 21)"        # macOS
   export ANDROID_HOME="$HOME/Library/Android/sdk"           # macOS default
   export PATH="$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator"
   ```
   (On Linux, `ANDROID_HOME` is typically `$HOME/Android/Sdk` and `JAVA_HOME` points at the Temurin install dir.)
   Verify: `java -version` shows 21, and `adb --version` works.

**Build locally and open in Android Studio:**
```bash
cd frontend
npm ci
npm run build
npx cap sync android
npx cap open android      # opens the android/ project in Android Studio
```

**Build a debug APK from the CLI** (no Android Studio needed once the SDK is installed):
```bash
cd frontend/android
./gradlew assembleDebug
# output: app/build/outputs/apk/debug/app-debug.apk
```
Install it on a connected device/emulator with `adb install -r app/build/outputs/apk/debug/app-debug.apk`.

---

## 2. Signing & Play App Signing

Releases on Google Play use **Play App Signing**: Google holds the *app signing key*; you hold the *upload key* and sign every upload with it. Google re-signs the artifact with the app signing key before distributing to users.

**Create an upload keystore** (one-time; keep it forever — losing it means resetting the upload key with Google):
```bash
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 9125 -alias upload
```
- Store `upload-keystore.jks` **outside the git repo** (e.g. a password manager / secure vault). `android/.gitignore` already ignores `*.jks` and `*.keystore`, but never rely on that as the only safeguard — keep the keystore out of the working tree entirely.
- Record the **store password**, **key password**, and **alias** (`upload`) in a secret manager.

**Configure release signing.** Either reference a non-committed `keystore.properties` from `android/app/build.gradle`, or wire the signing config directly. Recommended `frontend/android/keystore.properties` (NOT committed — add to `.gitignore` if not already covered):
```properties
storeFile=/absolute/path/to/upload-keystore.jks
storePassword=********
keyAlias=upload
keyPassword=********
```
And in `frontend/android/app/build.gradle`:
```gradle
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file("keystore.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
            // ... existing release config ...
        }
    }
}
```

**Enrol in Play App Signing.** When you create the app in the Play Console (Section 6), choose **Use Play App Signing** (the default). On the first AAB upload, Google generates and stores the app signing key; your upload key is the one above.

**Build a release bundle (AAB):**
```bash
cd frontend/android
./gradlew bundleRelease
# output: app/build/outputs/bundle/release/app-release.aab
```

---

## 3. SHA fingerprints

You need fingerprints from **both** keys, because users' installs are signed with the **Play App Signing** key, not your upload key.

**Upload key** (SHA-1 + SHA-256):
```bash
keytool -list -v -keystore upload-keystore.jks -alias upload
```
Copy the `SHA1:` and `SHA256:` lines from the output.

**Play App Signing key** (SHA-1 + SHA-256): in the **Play Console** → your app → **Setup → App signing**. Copy both the *App signing key certificate* SHA-1/SHA-256 **and** the *Upload key certificate* SHA-1/SHA-256 shown there.

You will register the relevant fingerprints in two places:
- **Google Cloud Console Android OAuth client** (Section 4) — SHA-1 of **both** keys.
- **`assetlinks.json`** (Section 5) — SHA-256 of the **Play App Signing** key.

---

## 4. Google sign-in on Android

Native Google sign-in via `@capgo/capacitor-social-login` needs an **Android OAuth client** registered in Google Cloud, in addition to the existing Web client.

1. Google Cloud Console → **APIs & Services → Credentials** → **Create credentials → OAuth client ID** → **Android**.
2. **Package name:** `leeashmore.investikid.ai.app`
3. **SHA-1 certificate fingerprint:** add **both** the upload key SHA-1 **and** the Play App Signing key SHA-1 (create the client with one, then add the second under the same client, or create two Android clients — both are valid; using one client with both fingerprints is simplest).
4. **Keep the existing Web client ID** (`VITE_GOOGLE_WEB_CLIENT_ID`) unchanged — it remains the `serverClientId` passed to `@capgo/capacitor-social-login`. The Android OAuth client does **not** replace it; it authorises the native app to obtain an ID token that the Web client (and backend) trust.

**Apple Sign-In on Android** uses the existing **web** OAuth flow — there is **no** native Android config to add.

---

## 5. App Links verification

The Android manifest declares an `<intent-filter android:autoVerify="true">` for host `app.investikid.ai`. For Android to verify the link and route `https://app.investikid.ai/...` into the app (deep links, OAuth/magic-link return), you must host a Digital Asset Links file at:

```
https://app.investikid.ai/.well-known/assetlinks.json
```

It must be served over HTTPS, with `Content-Type: application/json`, **no redirects**, and publicly reachable (no auth). Exact shape:

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "leeashmore.investikid.ai.app",
    "sha256_cert_fingerprints": ["<PLAY APP SIGNING SHA-256>"]
  }
}]
```

- Use the **Play App Signing** SHA-256 (from Section 3) — this is what end users' installs are actually signed with. Do **not** use the upload key SHA-256.
- For local/internal builds signed only with the upload key, you may temporarily add the upload key SHA-256 as a second entry in the `sha256_cert_fingerprints` array so debug installs also verify; remove it or keep both as needed.
- Verify after deploy:
  ```bash
  curl -sS https://app.investikid.ai/.well-known/assetlinks.json | jq .
  ```
  and on a device with the app installed: `adb shell pm verify-app-links --re-verify leeashmore.investikid.ai.app` then `adb shell pm get-app-links leeashmore.investikid.ai.app` (status should be `verified`).

---

## 6. Play Console

In the **Google Play Console** (<https://play.google.com/console>):

1. **Create app** → name **InvestiKid**, default language, app type **App**, **Free**.
2. Confirm **Play App Signing** is enabled (default — see Section 2).
3. Complete the policy declarations — this is a **children's app**:
   - **App content → Target audience and content:** select the child age bands; opt into **Designed for Families** / Google Play Families policies.
   - **Data safety:** declare what data is collected/shared and how (align with the app's privacy policy and the compliance docs).
   - **Content rating:** complete the IARC questionnaire (children's category).
   - Privacy policy URL, ads declaration (no ads), and any other required **App content** items.
4. **Testing → Internal testing:** create an **internal testing** track.
5. **Upload the first AAB** (`app-release.aab` from `bundleRelease`, Section 2) to the internal testing track and roll out.
6. **Testers:** add tester email addresses (or an email list) to the internal testing track.
7. **Share the opt-in link** with testers so they can install from Play.

---

## 7. On-demand CI build

The Android compile is gated on demand (no per-push cost):

1. GitHub → **Actions** → **Deployment checkpoint** workflow.
2. **Run workflow** with input **`run_android = true`**.
3. This runs `npm ci && npm run build && npx cap sync android && ./gradlew assembleDebug` on CI (JDK 21 + Android SDK), which is the build gate / first compile-proof of the scaffold. `bundleRelease` can be produced the same way when an AAB is needed.

---

## 8. On-device parity checklist

The headless environment cannot run the app, so this on-device pass (a notch + gesture-nav physical device or emulator) is **the real test**. Tick every item:

- [ ] **Cold start** loads the app to the first screen without a blank/white hang.
- [ ] **Parent login** works via **magic-link**, **Google**, and **Apple**, and the auth cookie **persists across requests** (navigate to an authenticated screen, background/foreground, confirm still logged in).
- [ ] **Child signup → parent consent → email-verify** flow completes end-to-end.
- [ ] **Hardware back button** does in-app back navigation and only **exits the app at a root route** (does not abruptly close mid-flow).
- [ ] **Status bar / safe-area insets** do not overlap content — test on a **notch + gesture-navigation** device (top status bar and bottom gesture bar both clear of UI).
- [ ] **Inline YouTube video** plays inside the app.
- [ ] **Local-notification permission** prompt appears (Android 13+ `POST_NOTIFICATIONS`), and a **scheduled streak reminder fires in its notification channel**.
- [ ] **Social-login buttons** (Google + Apple) work from the native UI.
- [ ] **Coach Penny** replies (moderated LLM response renders).
- [ ] **Premium paywall** "ask my grown-up" flow works.
- [ ] **Deep link** to `https://app.investikid.ai/...` opens the app (once `assetlinks.json` is hosted and verified — Section 5).
- [ ] **Premium subscribe** via Google Play Billing completes (license-test account), the **7-day free trial** shows, and the child's premium entitlement flips on after server-side acknowledge (Section 9).

---

## 9. A3 — Google Play Billing

> **What the code already does.** The Android subscribe/restore path is in-repo: `SubscriptionCard` has an **Android branch** (gated by `isAndroid()`) that drives a custom Kotlin `@CapacitorPlugin` (Play Billing client) → sends the purchase token to the backend `POST /billing/google/verify`, which validates it against the **Play Developer API** and **acknowledges** the purchase server-side. Live status is kept current by **Real-time developer notifications (RTDN)** delivered to `POST /billing/google/notifications` (CSRF-exempt). A **7-day free trial** is configured as a Play offer (mirrors Stripe/Apple). The steps below are the **operator-side** setup that no code or `cap sync` performs.

### 9.1 Play Console — subscription product + free trial
1. Play Console → your app → **Monetize → Products → Subscriptions** → **Create subscription**.
2. **Product ID:** `premium_monthly` (must match the backend `GOOGLE_PLAY_PRODUCT_ID`).
3. Add a **base plan** (auto-renewing, monthly), set price, and activate it.
4. On the base plan, add a **7-day free-trial offer** (offer type *Free trial*, eligibility *new customers*, phase = 7 days free). Activate the offer.

### 9.2 Google Cloud — service account for the Play Developer API
1. Google Cloud Console → the project linked to Play → **IAM & Admin → Service Accounts** → **Create service account** (e.g. `play-billing-validator`).
2. Create a **JSON key** for it (Keys → Add key → JSON) and download it — this is the `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` value. Store it in a secret manager; never commit it.
3. Play Console → **Users & permissions** (or **Setup → API access**) → **Invite / grant access** to the service-account email. Grant at least **View financial data** and **Manage orders and subscriptions** so it can read and acknowledge purchases.

### 9.3 Backend env (per environment)
Set on the backend host (Railway), once per environment (`testing` / `production`):
```bash
GOOGLE_PLAY_PACKAGE_NAME=leeashmore.investikid.ai.app
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=<full JSON key file contents>
GOOGLE_PLAY_PRODUCT_ID=premium_monthly
```
(These map to `backend/.env.example` lines 40–42. The service-account JSON is multi-line — paste it as a single env value exactly as downloaded.)

### 9.4 Real-time developer notifications (RTDN) via Pub/Sub
1. Google Cloud → **Pub/Sub** → enable the API, then **create a topic** (e.g. `play-rtdn`).
2. On that topic, **create a push subscription** whose **endpoint URL** is your backend RTDN route:
   ```
   {backend}/billing/google/notifications
   ```
   (e.g. `https://<railway-backend-host>/billing/google/notifications`). Push delivery, JSON.
3. Grant **Google Play's service account** permission to publish to the topic: add `google-play-developer-notifications@system.gserviceaccount.com` as **Pub/Sub Publisher** on the topic.
4. Play Console → **Monetize → Monetization setup → Real-time developer notifications** → set the **Topic name** to the full resource name `projects/<gcp-project>/topics/play-rtdn` → **Send test notification** to confirm delivery.

### 9.5 Sandbox / license testing
1. Play Console → **Setup → License testing** → add the **license-test account** email addresses (testers buy without being charged; renewals are accelerated).
2. Those same accounts must also be on the **internal testing** track (Section 6) and have **opted in** via the track link.

### 9.6 Device test
1. Install the build from the **internal testing** track on a device signed in with a **license-test account**.
2. Open the premium paywall → **Subscribe** → confirm the **7-day free trial** is shown, complete the purchase, and verify the child's premium entitlement flips on (the backend acknowledges + RTDN keeps it live). Test **restore** and a **cancel** (cancel in Play → confirm RTDN downgrades status).

> **Build note.** The Play Billing plugin is a custom Kotlin `@CapacitorPlugin`, so it is **not** listed in `capacitor.plugins.json` and does **not** appear in `npx cap ls` — it is registered in native code via `registerPlugin(PlayBillingPlugin.class)` in `MainActivity.onCreate` (before `super.onCreate`). Its **first compile** happens via the checkpoint `run_android` build / Android Studio (Section 7), not in default CI.
