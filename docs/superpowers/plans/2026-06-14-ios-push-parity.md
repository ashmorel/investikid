# iOS Push Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the iOS Capacitor app obtain an FCM registration token (not the raw APNs token) so the existing FCM HTTP v1 backend delivers push to iOS exactly as it already does to Android.

**Architecture:** Add the Firebase iOS SDK (FirebaseMessaging) to the iOS App target via Swift Package Manager. `AppDelegate` configures Firebase and, when iOS hands over the APNs token, passes it to Firebase, fetches the FCM token, and posts that token as a `String` through the Capacitor registration notification. The installed `@capacitor/push-notifications` plugin (v8.1.1) already forwards a `String` notification object to the `registration` event that `push.ts` listens for. Android and all JS are untouched.

**Tech Stack:** Swift, Capacitor 8 (SPM-based iOS project), Firebase iOS SDK 11.x (FirebaseMessaging), `@capacitor/push-notifications` 8.1.1.

**Reference spec:** `docs/superpowers/specs/2026-06-14-ios-push-parity-design.md`

---

## Owner legend

- 🤖 **Code** — an editor/subagent can do this (file edits, git, running JS tests).
- 👤 **Manual** — you perform this in Xcode, the Firebase console, or the Apple Developer portal (no CLI/automation path).

## Testing reality (read first)

iOS push **cannot** be exercised on the simulator — APNs requires a physical
device. The native Swift in `AppDelegate` has no unit-test harness in this repo.
Therefore:

- The only automated gate is the **existing** `frontend/src/lib/__tests__/push.test.ts`,
  which must stay green (proves the JS registration→POST contract is unchanged).
- The real correctness gate is a **manual real-device E2E** (Task 7), identical to
  the loop already run on Android.

This is consistent with how SP-Bio native work was verified. Do not invent Swift
unit tests; there is no runner for them here.

## File Structure

- `frontend/ios/App/App/AppDelegate.swift` — **modify.** Add Firebase configure +
  the APNs→FCM token bridge. Existing WKWebView relayout logic stays.
- `frontend/ios/App/.gitignore` — **modify.** Ignore `GoogleService-Info.plist`.
- `frontend/ios/App/App/GoogleService-Info.plist` — **add (gitignored, you supply).**
  Firebase iOS app config, downloaded from the Firebase console.
- `frontend/ios/App/App.xcodeproj/project.pbxproj` + `…/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`
  — **changed by Xcode** when you add the SPM package (do not hand-edit).
- Unchanged: `frontend/src/lib/push.ts`, its test, all backend, all Android.

---

### Task 1: Gitignore the iOS Firebase config 🤖

**Files:**
- Modify: `frontend/ios/App/.gitignore`

The plist carries project-identifying config and is the iOS counterpart to
`android/app/google-services.json`, which is already gitignored
(`frontend/android/.gitignore:10`). Mirror that so the plist is never committed.

- [ ] **Step 1: Append the ignore rule**

Add this line to the end of `frontend/ios/App/.gitignore`:

```gitignore
# Firebase iOS app config (operator-supplied, like android/app/google-services.json)
GoogleService-Info.plist
```

- [ ] **Step 2: Verify it is ignored**

Run from `frontend/ios`:
```bash
touch App/App/GoogleService-Info.plist
git check-ignore -v App/App/GoogleService-Info.plist
rm App/App/GoogleService-Info.plist
```
Expected: prints a match line referencing `App/.gitignore` and the
`GoogleService-Info.plist` pattern (confirms it would be ignored).

- [ ] **Step 3: Commit**

```bash
git add frontend/ios/App/.gitignore
git commit -m "chore(ios): gitignore GoogleService-Info.plist

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Register the iOS app in Firebase & add the plist 👤

**Files:**
- Add (gitignored): `frontend/ios/App/App/GoogleService-Info.plist`

This produces the config `FirebaseApp.configure()` reads. Without it the app
still launches (Task 3 guards on its presence) but never produces an FCM token.

- [ ] **Step 1: Register the iOS app**

In the [Firebase console](https://console.firebase.google.com/) → project
**investikid-8c598** → ⚙️ Project settings → **General** → *Your apps* → **Add app**
→ **iOS**. Apple bundle ID: `leeashmore.investikid.ai.app` (must match exactly —
this is the `appId` in `frontend/capacitor.config.ts`). App nickname: `InvestiKid iOS`.

- [ ] **Step 2: Download the plist**

Download `GoogleService-Info.plist` from that flow (or later from Project settings
→ Your apps → the iOS app → `GoogleService-Info.plist`).

- [ ] **Step 3: Add it to the App target in Xcode**

Open `frontend/ios/App/App.xcworkspace` in Xcode. Drag
`GoogleService-Info.plist` into the **App/App** group. In the dialog: tick
**Copy items if needed**, and tick the **App** target under *Add to targets*.
Confirm the file lands at `frontend/ios/App/App/GoogleService-Info.plist`.

- [ ] **Step 4: Confirm it is NOT staged by git**

Run from `frontend/ios`:
```bash
git status --porcelain App/App/GoogleService-Info.plist
```
Expected: **no output** (Task 1 ignores it). If it shows as untracked-but-ignored
that is correct; if it shows as staged, stop and re-check Task 1.

> No commit — the plist is intentionally untracked.

---

### Task 3: Add the Firebase iOS SDK via Swift Package Manager 👤

**Files:**
- Changed automatically by Xcode: `frontend/ios/App/App.xcodeproj/project.pbxproj`,
  `frontend/ios/App/App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`

The iOS project is SPM-based (no Podfile). Adding the package by hand-editing
`project.pbxproj` risks corrupting the project; use Xcode's resolver. This must
happen **before** Task 4, because `import FirebaseMessaging` won't compile until
the package is present.

- [ ] **Step 1: Add the package**

In Xcode (workspace open) → **File → Add Package Dependencies…** → enter URL:
```
https://github.com/firebase/firebase-ios-sdk
```
Dependency Rule: **Up to Next Major Version**, starting at the latest 11.x Xcode
offers. Click **Add Package** and wait for resolution.

- [ ] **Step 2: Select the FirebaseMessaging product**

In the product picker, tick **FirebaseMessaging** only (it pulls FirebaseCore
transitively). Ensure the target column shows **App**. Click **Add Package**.

- [ ] **Step 3: Verify the package resolved**

Run from `frontend/ios`:
```bash
grep -c "firebase-ios-sdk" App/App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
```
Expected: `1` or more (the package is recorded).

- [ ] **Step 4: Commit the resolved-package metadata**

```bash
git add frontend/ios/App/App.xcodeproj/project.pbxproj \
        frontend/ios/App/App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
git commit -m "build(ios): add firebase-ios-sdk (FirebaseMessaging) via SPM

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: AppDelegate — Firebase configure + APNs→FCM token bridge 🤖

**Files:**
- Modify: `frontend/ios/App/App/AppDelegate.swift`

This is the core change. When iOS registers for remote notifications, hand the
APNs token to Firebase, fetch the FCM token, and post it as a `String` so the
push plugin emits it on the `registration` event. Everything is guarded on
Firebase being configured, so a build without the plist launches and simply never
produces a token (mirrors the "harmless until configured" note in `push.ts`).

> Will not compile until Task 3 is done (the `import` lines need the package).
> That is expected; the build is verified in Task 6.

- [ ] **Step 1: Add the Firebase imports**

At the top of `frontend/ios/App/App/AppDelegate.swift`, after the existing
imports (`import UIKit`, `import Capacitor`, `import WebKit`), add:

```swift
import FirebaseCore
import FirebaseMessaging
```

- [ ] **Step 2: Configure Firebase on launch (guarded)**

Replace the body of `application(_:didFinishLaunchingWithOptions:)` so it reads:

```swift
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Configure Firebase only when GoogleService-Info.plist is bundled, so a
        // build without it still launches (push simply never yields a token).
        if Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") != nil {
            FirebaseApp.configure()
        }
        return true
    }
```

- [ ] **Step 3: Add the APNs→FCM registration bridge**

Add these two methods to the `AppDelegate` class (place them just after
`application(_:didFinishLaunchingWithOptions:)`):

```swift
    // iOS delivered the APNs token. Hand it to Firebase, fetch the FCM
    // registration token, and post it as a String so @capacitor/push-notifications
    // emits it on the "registration" event (push.ts then registers it). FCM tokens
    // — not raw APNs tokens — are what the backend's FCM HTTP v1 sender requires.
    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        guard FirebaseApp.app() != nil else {
            // No GoogleService-Info.plist in this build → no FCM token available.
            NotificationCenter.default.post(
                name: .capacitorDidFailToRegisterForRemoteNotifications,
                object: NSError(domain: "InvestiKidPush", code: -1,
                                userInfo: [NSLocalizedDescriptionKey: "Firebase not configured"])
            )
            return
        }
        Messaging.messaging().apnsToken = deviceToken
        Messaging.messaging().token { token, error in
            if let token = token {
                NotificationCenter.default.post(
                    name: .capacitorDidRegisterForRemoteNotifications,
                    object: token
                )
            } else {
                NotificationCenter.default.post(
                    name: .capacitorDidFailToRegisterForRemoteNotifications,
                    object: error
                )
            }
        }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        NotificationCenter.default.post(
            name: .capacitorDidFailToRegisterForRemoteNotifications,
            object: error
        )
    }
```

- [ ] **Step 4: Confirm the existing logic is intact**

Visually verify `applicationDidBecomeActive`, `relayoutWebView`, `findWebView`,
the `open url` and `continue userActivity` handlers, and the other lifecycle
stubs are unchanged. The only additions are the two imports, the guarded
`FirebaseApp.configure()`, and the two new push methods.

- [ ] **Step 5: Commit**

```bash
git add frontend/ios/App/App/AppDelegate.swift
git commit -m "feat(ios): bridge APNs token to FCM for push parity

AppDelegate configures Firebase (guarded on GoogleService-Info.plist) and,
on remote-notification registration, hands the APNs token to Firebase and
posts the FCM token as a String — which @capacitor/push-notifications forwards
to the registration event push.ts already consumes. Android and JS untouched.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Regression-guard the unchanged JS contract 🤖

**Files:**
- Run only: `frontend/src/lib/__tests__/push.test.ts`

No JS changes are made; this task is the explicit regression gate that the
registration→`POST /users/me/push-devices` contract (with `platform: "ios"`) the
native side now feeds is still exactly what `push.ts` expects.

- [ ] **Step 1: Run the push tests**

Run from `frontend`:
```bash
npm run test -- src/lib/__tests__/push.test.ts
```
Expected: PASS (all existing cases green). If anything fails, the JS contract was
inadvertently changed — stop and investigate; the spec requires JS untouched.

- [ ] **Step 2: Run typecheck + lint (no-regression)**

Run from `frontend`:
```bash
npx tsc -b && npm run lint
```
Expected: no new errors.

> No commit — nothing changed in this task; it is a verification gate.

---

### Task 6: Operator setup for real delivery 👤

These gate real iOS delivery but not the build. Do them before Task 7.

- [ ] **Step 1: Create & upload the APNs Auth Key**

In the [Apple Developer portal](https://developer.apple.com/account/resources/authkeys/list)
→ **Keys** → **+** → enable **Apple Push Notifications service (APNs)** → register →
download the `.p8` (one-time download; keep it safe). Note the **Key ID** and your
**Team ID**.

In the Firebase console → project **investikid-8c598** → Project settings →
**Cloud Messaging** → *Apple app configuration* → **APNs Authentication Key** →
**Upload** the `.p8` with its Key ID and Team ID.

- [ ] **Step 2: Set the backend credential on production**

The production backend needs `FIREBASE_SERVICE_ACCOUNT_JSON` (the same
service-account key already set on testing — FCM credentials are project-wide).
In Railway → `InvestiKid` service → **production** environment → Variables, set
`FIREBASE_SERVICE_ACCOUNT_JSON` to the service-account key JSON. Railway redeploys.

> Verification of this var (presence/shape) can be done the same way as on testing.

- [ ] **Step 3: Confirm Push capability (already enabled)**

`frontend/ios/App/App/App.entitlements` already has `aps-environment`. In Xcode →
App target → **Signing & Capabilities**, confirm **Push Notifications** is listed.
No change expected.

---

### Task 7: Real-device E2E verification 👤 (+ 🤖 for the cron fire)

The correctness gate. Mirrors the Android loop already run.

- [ ] **Step 1: Build to a physical device**

In Xcode, select a physical iPhone (signed-in Apple ID / provisioning), and
**Run** (or Archive). Confirm the app launches without crashing (proves
`FirebaseApp.configure()` found the plist and the Firebase package linked).

- [ ] **Step 2: Enable push in-app and confirm registration**

On the device: sign in, ensure the parent master switch is on, toggle the child's
push on. This drives `push.ts enablePush` → native registration. Confirm a device
row was created — query the relevant DB (testing) for a `push_devices` row with
`platform = 'ios'` for that user, or watch the backend log for the
`POST /users/me/push-devices` 200.

- [ ] **Step 3: Fire the streak-risk cron 🤖**

With the child set as streak-at-risk (as in the Android test), fire:
```bash
curl -s -X POST "https://investikid-testing.up.railway.app/internal/push-streak-risk/run" \
  -H "X-Cron-Secret: $CRON_SECRET" -H "Content-Type: application/json"
```
Expected: `{"candidates":1,"sent":1}` (the credential present + token valid).

- [ ] **Step 4: Observe the banner**

Background the app; confirm the **Keep your streak** notification appears on the
device. This closes the E2E: backend → FCM → APNs → iOS device.

- [ ] **Step 5: Record the result**

Append a short verification note (date, device, `sent:1`, banner screenshot
reference) to `docs/superpowers/specs/2026-06-14-ios-push-parity-design.md` under a
new `## Verification` section, and commit:

```bash
git add docs/superpowers/specs/2026-06-14-ios-push-parity-design.md
git commit -m "docs(push): record iOS push E2E verification

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- FCM token instead of APNs on iOS → Task 4 (bridge). ✅
- Add firebase-ios-sdk via SPM to App target → Task 3. ✅
- GoogleService-Info.plist added + gitignored → Tasks 1, 2. ✅
- Guarded `FirebaseApp.configure()` (no crash without plist) → Task 4 Step 2 + the
  `FirebaseApp.app() != nil` guard in Step 3. ✅
- Fail handler → `registrationError` path → Task 4 Step 3 (both failure posts). ✅
- Android + push.ts untouched → no task modifies them; Task 5 guards JS. ✅
- Operator prereqs (iOS app reg, APNs .p8, prod var) → Tasks 2, 6. ✅
- Push capability already enabled → Task 6 Step 3 (confirm only). ✅
- Testing: JS green + build + device E2E → Tasks 5, 7. ✅

**Placeholder scan:** none — every code/command step is concrete.

**Consistency:** bundle id `leeashmore.investikid.ai.app` matches `capacitor.config.ts`;
notification names `.capacitorDidRegisterForRemoteNotifications` /
`.capacitorDidFailToRegisterForRemoteNotifications` match the plugin observers
(`PushNotificationsPlugin.swift:39-47`); String token path matches
`PushNotificationsPlugin.swift:191-192`; testing URL + cron contract match the
verified Android run.
