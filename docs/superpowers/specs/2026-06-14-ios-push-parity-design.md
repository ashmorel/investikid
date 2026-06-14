# iOS Push Parity — Design

**Date:** 2026-06-14
**Status:** Approved
**Author:** Lee Ashmore (with Claude)

## Problem

The streak-risk push pipeline (M7) is verified end-to-end on **Android**: the
backend selects an at-risk child, sends via FCM HTTP v1, and the device shows a
banner. On **iOS** it does not work. The client (`frontend/src/lib/push.ts`)
registers via `@capacitor/push-notifications`. On Android that plugin is
Firebase-backed and yields an **FCM registration token**, which our backend
(`backend/app/services/push_service.py`, FCM HTTP v1) can deliver to. On iOS the
same plugin yields the raw **APNs device token**, which the FCM v1 endpoint
cannot use — so any iOS token registered to the backend is undeliverable.

**Goal:** make the iOS app obtain an **FCM registration token** instead of the
raw APNs token, so the existing backend delivers push to iOS exactly as it does
to Android. **Android and the JS layer stay untouched.**

## Non-Goals

- No change to the backend, the streak-risk cron, or `push_service`.
- No change to `push.ts` or its tests.
- No change to the Android native app (its FCM path is already verified).
- No new push *content* or scheduling — this is transport parity only.

## Approach (chosen)

**Native bridge.** Add the Firebase iOS SDK (FirebaseMessaging) to the iOS app
via Swift Package Manager. `AppDelegate` initialises Firebase and acts as the
Messaging delegate. When iOS hands over the APNs token, AppDelegate passes it to
Firebase, retrieves the FCM token, and re-posts that token **as a `String`**
through the `NSNotification.Name.capacitorDidRegisterForRemoteNotifications`
notification. The installed `@capacitor/push-notifications` plugin (v8.1.1)
already accepts a `String` notification object and forwards it to the
`registration` event (`PushNotificationsPlugin.swift:191-192`), which `push.ts`
already listens for. The token therefore reaches `push.ts` as an FCM token with
no JS or plugin changes.

### Rejected alternative

Replacing `@capacitor/push-notifications` with `@capacitor-firebase/messaging`
(uniform `getToken()` on both platforms) was rejected: it rewrites the
just-verified Android path (forcing a full Android re-test) and changes `push.ts`
and its tests — more surface area and risk for a platform that already works.

## Components / Changes (all iOS-native)

1. **SPM dependency.** Add `firebase-ios-sdk` to the **App** target, selecting the
   `FirebaseMessaging` product (which pulls `FirebaseCore`). Firebase is added to
   the App target, not Capacitor's `CapApp-SPM` package.

2. **`GoogleService-Info.plist`.** Added to the App target so
   `FirebaseApp.configure()` can read it. Treated as a secret-bearing config file:
   **gitignored**, consistent with how `android/app/google-services.json` is
   handled.

3. **`frontend/ios/App/App/AppDelegate.swift`** (~40 lines added):
   - `import FirebaseCore`, `import FirebaseMessaging`.
   - In `didFinishLaunchingWithOptions`: call `FirebaseApp.configure()` **guarded**
     by the presence of `GoogleService-Info.plist` in the bundle, then set
     `Messaging.messaging().delegate = self`. The guard ensures a build *without*
     the plist still launches (it simply never produces an FCM token) rather than
     crashing — mirroring the "harmless no-op until configured" stance already
     documented in `push.ts`.
   - Implement `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`:
     set `Messaging.messaging().apnsToken = deviceToken`, fetch the FCM token, and
     on success post it as a `String` via
     `NotificationCenter.default.post(name: .capacitorDidRegisterForRemoteNotifications, object: fcmToken)`.
     On error, post `.capacitorDidFailToRegisterForRemoteNotifications`.
   - Implement `application(_:didFailToRegisterForRemoteNotificationsWithError:)`
     to post `.capacitorDidFailToRegisterForRemoteNotifications` so `push.ts`
     resolves `'unavailable'`.
   - Leave the existing `relayoutWebView` / WKWebView logic untouched.

4. **No JS changes.** `push.ts` and `push.test.ts` are unmodified.

## Data Flow

```
child toggles push  → push.ts enablePush(parentEnabled)
  → PushNotifications.register()
  → iOS APNs registration
  → AppDelegate didRegisterForRemoteNotificationsWithDeviceToken
      → Messaging.messaging().apnsToken = deviceToken
      → Messaging.messaging().token { fcmToken }
      → post .capacitorDidRegisterForRemoteNotifications (object: fcmToken String)
  → plugin emits "registration" event { value: fcmToken }
  → push.ts POST /users/me/push-devices { platform: "ios", token: fcmToken }
  → backend stores PushDevice
  → streak-risk cron → push_service → FCM HTTP v1 → APNs → device banner
```

Downstream of the registration event this is identical to Android.

## Error Handling

- **FCM token fetch fails** → AppDelegate posts
  `.capacitorDidFailToRegisterForRemoteNotifications` → `push.ts` already resolves
  `'unavailable'` (existing `registrationError` listener). No user-visible crash.
- **Missing `GoogleService-Info.plist`** → guarded `FirebaseApp.configure()` is
  skipped → no FCM token is ever produced → push silently stays unavailable on
  that build. App launches normally.
- **APNs not provisioned in Firebase** (operator gap) → token is obtained but FCM
  delivery fails server-side; backend already logs `push: send failed` and prunes
  dead tokens. No client impact.

## Operator Prerequisites (human; gate real delivery, not the code)

These do not block writing/merging the code, but real iOS delivery needs all of
them:

1. Register an **iOS app** in Firebase project `investikid-8c598` with bundle id
   `leeashmore.investikid.ai.app`; download `GoogleService-Info.plist` and place
   it in the App target.
2. Create an **APNs Authentication Key (.p8)** in the Apple Developer account and
   upload it to Firebase → Project Settings → Cloud Messaging, so FCM can deliver
   to APNs.
3. Set `FIREBASE_SERVICE_ACCOUNT_JSON` on the **production** backend (the same
   service-account key already set on testing — FCM credentials are project-wide,
   so one key serves both platforms).
4. Push Notifications capability — **already enabled** (`aps-environment` present
   in `App.entitlements`); no action.

## Testing

iOS push cannot be exercised on the simulator (APNs requires a real device), so
verification mirrors how SP-Bio native work was validated:

1. **JS unchanged** — existing `frontend/src/lib/__tests__/push.test.ts` stays
   green (regression guard that the registration contract is unchanged).
2. **Build gate** — the iOS app archives in Xcode with the Firebase SPM package
   resolved and `GoogleService-Info.plist` present.
3. **Real-device E2E** — on a physical iPhone: enable push in-app, confirm an FCM
   token is registered to the backend (a `push_devices` row / the
   `POST /users/me/push-devices` call), fire the streak-risk cron, and observe the
   banner — the same loop verified on Android.

The native Swift in `AppDelegate` is not unit-tested (this repo has no iOS test
harness for the app delegate); the test gates above are the contract.

## Files

- Modify: `frontend/ios/App/App/AppDelegate.swift`
- Add (build config): `firebase-ios-sdk` SPM package reference on the App target
  (`frontend/ios/App/App.xcodeproj/project.pbxproj` + `Package.resolved`)
- Add (gitignored, operator-supplied): `frontend/ios/App/App/GoogleService-Info.plist`
- Update: `frontend/ios/.gitignore` (or repo root) to ignore `GoogleService-Info.plist`
- Unchanged: `frontend/src/lib/push.ts`, `frontend/src/lib/__tests__/push.test.ts`,
  all backend files, all Android files

## Verification (2026-06-14)

Verified end-to-end on a physical iPhone against the **testing** backend:

1. **Token registration** — enabling push in-app registered an FCM token to the
   backend: `push_devices` row `platform=ios`, length 142 (FCM token, not raw
   APNs). Confirms the AppDelegate APNs→FCM bridge works.
2. **APNs configuration** — initial sends returned FCM `THIRD_PARTY_AUTH_ERROR`
   (HTTP 401) because the APNs Auth Key was not yet uploaded to Firebase. After
   uploading the `.p8` (Key ID + Team ID) to Firebase → Cloud Messaging, a direct
   FCM v1 send to the iOS token returned **HTTP 200** with a message ID.
3. **Device delivery** — the **"Keep your streak"** banner appeared on the iPhone
   (app backgrounded). Foreground sends route to the app's JS handler instead of
   the tray (correct Capacitor behaviour), matching Android.

iOS push parity is functionally complete. Build/test gates: `push.test.ts` green
(JS unchanged), app archives with the Firebase SPM package, real-device banner
delivered.

### Operator items still outstanding for production delivery
- Set `FIREBASE_SERVICE_ACCOUNT_JSON` on the **production** backend (only testing
  has it). Until then push no-ops in prod.
- Rebuild the iOS app with **no** `VITE_API_BASE_URL` (prod default) before any
  TestFlight/App Store archive — the verified build above is testing-pointed.
