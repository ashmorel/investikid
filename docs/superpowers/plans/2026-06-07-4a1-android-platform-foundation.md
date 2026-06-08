# 4A·A1 — Android Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Capacitor Android platform for InvestiKid at parity with iOS/web (scaffold + config + UX parity + icons + on-demand build + operator runbook), as the prerequisite for A3 (Play Billing). No payments.

**Architecture:** Add `@capacitor/android` and commit a scaffolded `android/` project. Close Android-only gaps with small, unit-tested JS helpers (platform detection, back-button decision) wired through `@capacitor/app` + `@capacitor/status-bar`, plus AndroidManifest parity and adaptive icons. The actual Gradle compile is an on-demand GitHub Actions job; device parity is an operator runbook.

**Tech Stack:** Capacitor 8 (`@capacitor/android`, `@capacitor/app`, `@capacitor/status-bar`), `@capacitor/assets`, React 18 + Vite + TS, Vitest. **No Android toolchain in the dev env** — verify only via `npx cap sync android` + `npx tsc -b` / `npm run lint` / `npm run test` / `npm run build`.

**Working dir:** `/Users/leeashmore/investikid/frontend` unless noted. Branch `testing` (never main). Do NOT `git add -A` (an unrelated root `.gitignore` change is present) — stage explicit paths per task.

---

## File Structure

- `frontend/package.json` — add `@capacitor/android`, `@capacitor/app`, `@capacitor/status-bar` (match `^8.x`); `@capacitor/assets` as devDep.
- `frontend/android/` — generated Capacitor Android project (committed), with `frontend/android/.gitignore` for build artifacts.
- `frontend/src/lib/platform.ts` — add `getPlatform()` + `isAndroid()` (extend existing file).
- `frontend/src/lib/backButton.ts` (new) — pure `decideBackAction()` + `registerBackButton()` wiring.
- `frontend/src/lib/nativeChrome.ts` (new) — status-bar/edge-to-edge init (`initNativeChrome()`).
- `frontend/src/lib/notifications.ts` (new) — `ensureAndroidChannel()` (Android notification channel).
- `frontend/src/main.tsx` — call `registerBackButton()`, `initNativeChrome()`, `ensureAndroidChannel()` on native.
- `frontend/index.html` — theme-color → sky-blue.
- `frontend/src/components/child/lesson/videoEmbed.ts` — scope the iOS `yt.html` proxy correctly for Android.
- `frontend/android/app/src/main/AndroidManifest.xml` — permissions, `windowSoftInputMode`, App Links intent filter.
- `.github/workflows/deployment-checkpoint.yml` — make `run_android` actually build.
- `docs/2026-06-07-android-operator-runbook.md` (new) — operator steps + parity checklist.
- Tests: `frontend/src/lib/__tests__/platform.test.ts`, `backButton.test.ts`.

---

## Task 1: Scaffold the Android platform

**Files:** `frontend/package.json`, `frontend/android/**` (generated), `frontend/android/.gitignore`

- [ ] **Step 1: Install the Android platform package**

Run (from `frontend/`): `npm install @capacitor/android@^8.3.4`
Expected: added to dependencies, no peer-dep errors (matches `@capacitor/core ^8.3.4`).

- [ ] **Step 2: Scaffold + sync the native project**

Run: `npx cap add android` then `npx cap sync android`
Expected: creates `frontend/android/` and reports "sync finished". (This does NOT run Gradle; it scaffolds + copies web assets + installs plugin Android code. No JDK/SDK needed for scaffolding.) If `cap add android` errors for a reason other than missing SDK (e.g. it tries to run Gradle and fails on missing Java), report BLOCKED with the exact error — do not hand-fabricate the android/ tree.

- [ ] **Step 3: Add a scoped `.gitignore` so build artifacts aren't committed**

Create `frontend/android/.gitignore`:
```gitignore
# Capacitor Android — ignore build artifacts & local/secret files
/build/
/app/build/
/.gradle/
/capacitor-cordova-android-plugins/build/
local.properties
*.keystore
*.jks
google-services.json
.DS_Store
```

- [ ] **Step 4: Verify nothing secret/binary-huge is staged**

Run: `git status --porcelain frontend/android | head -50` and `git check-ignore frontend/android/app/build 2>/dev/null` (should print the path = ignored). Confirm no `local.properties`, `*.jks`, or `app/build/` appear in `git status`.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/android
git commit -m "feat(android): scaffold Capacitor Android platform (committed android/)"
```
(If `git add frontend/android` would include ignored files, the `.gitignore` from Step 3 prevents it — confirm with `git status` first. Commit message body may note the file count.)

---

## Task 2: `getPlatform()` + `isAndroid()` helpers

**Files:** Modify `frontend/src/lib/platform.ts`; Test `frontend/src/lib/__tests__/platform.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/__tests__/platform.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@capacitor/core', () => ({
  Capacitor: { getPlatform: vi.fn(), isNativePlatform: vi.fn() },
}));
import { Capacitor } from '@capacitor/core';
import { getPlatform, isAndroid, isNativeApp } from '../platform';

describe('platform helpers', () => {
  beforeEach(() => vi.clearAllMocks());
  it('getPlatform returns the Capacitor platform', () => {
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('android');
    expect(getPlatform()).toBe('android');
  });
  it('isAndroid true only on android', () => {
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('android');
    expect(isAndroid()).toBe(true);
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('ios');
    expect(isAndroid()).toBe(false);
  });
  it('isNativeApp delegates to Capacitor.isNativePlatform', () => {
    (Capacitor.isNativePlatform as ReturnType<typeof vi.fn>).mockReturnValue(true);
    expect(isNativeApp()).toBe(true);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/lib/__tests__/platform.test.ts`
Expected: FAIL (`getPlatform`/`isAndroid` not exported).

- [ ] **Step 3: Implement in `src/lib/platform.ts`** (keep the existing `isNativeApp`)

```ts
/** The runtime platform: 'web' | 'ios' | 'android'. */
export function getPlatform(): string {
  return Capacitor.getPlatform();
}

/** True when running in the native Android shell. */
export function isAndroid(): boolean {
  return Capacitor.getPlatform() === 'android';
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run src/lib/__tests__/platform.test.ts` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/platform.ts src/lib/__tests__/platform.test.ts
git commit -m "feat(android): getPlatform/isAndroid platform helpers"
```

---

## Task 3: Hardware back button

**Files:** Create `frontend/src/lib/backButton.ts`; Test `frontend/src/lib/__tests__/backButton.test.ts`; Modify `frontend/src/main.tsx`; add `@capacitor/app`.

- [ ] **Step 1: Install `@capacitor/app`**

Run: `npm install @capacitor/app@^8.0.0` then `npx cap sync android` (registers the plugin).

- [ ] **Step 2: Write the failing test** (pure decision function — no native deps)

```ts
// frontend/src/lib/__tests__/backButton.test.ts
import { describe, it, expect } from 'vitest';
import { decideBackAction, ROOT_PATHS } from '../backButton';

describe('decideBackAction', () => {
  it('exits at a root path with no history to pop', () => {
    expect(decideBackAction({ path: '/home', canGoBack: false })).toBe('exit');
  });
  it('goes back when there is web history', () => {
    expect(decideBackAction({ path: '/home', canGoBack: true })).toBe('back');
  });
  it('goes back on a non-root path even without canGoBack', () => {
    expect(decideBackAction({ path: '/lesson/42', canGoBack: false })).toBe('back');
  });
  it('treats every declared root path as an exit point', () => {
    for (const p of ROOT_PATHS) {
      expect(decideBackAction({ path: p, canGoBack: false })).toBe('exit');
    }
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `npx vitest run src/lib/__tests__/backButton.test.ts`
Expected: FAIL (module missing).

- [ ] **Step 4: Implement `src/lib/backButton.ts`**

```ts
import { App } from '@capacitor/app';
import { isNativeApp } from './platform';

/** Routes considered "top level" — pressing back here exits the app. */
export const ROOT_PATHS = ['/', '/home', '/parent', '/parent/login'] as const;

export type BackAction = 'back' | 'exit';

/** Pure decision: go back in history, or exit the app. */
export function decideBackAction(args: { path: string; canGoBack: boolean }): BackAction {
  const atRoot = (ROOT_PATHS as readonly string[]).includes(args.path);
  if (!atRoot) return 'back';
  return args.canGoBack ? 'back' : 'exit';
}

/** Wire the Android hardware back button. No-op on web/iOS. Idempotent-safe to call once at startup. */
export function registerBackButton(): void {
  if (!isNativeApp()) return;
  App.addListener('backButton', ({ canGoBack }) => {
    const action = decideBackAction({ path: window.location.pathname, canGoBack });
    if (action === 'exit') {
      App.exitApp();
    } else {
      window.history.back();
    }
  });
}
```

- [ ] **Step 5: Wire into `src/main.tsx`**

After the `ReactDOM.createRoot(...).render(...)` call, add:
```ts
import { registerBackButton } from './lib/backButton';
registerBackButton();
```
(Place the import with the other imports; call `registerBackButton()` near the service-worker registration block.)

- [ ] **Step 6: Verify**

Run: `npx vitest run src/lib/__tests__/backButton.test.ts` → PASS. `npx tsc -b` → clean. `npx cap sync android` → ok.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json src/lib/backButton.ts src/lib/__tests__/backButton.test.ts src/main.tsx
git commit -m "feat(android): hardware back-button handling (@capacitor/app)"
```

---

## Task 4: Status bar + edge-to-edge chrome

**Files:** Create `frontend/src/lib/nativeChrome.ts`; Modify `frontend/src/main.tsx`, `frontend/index.html`; add `@capacitor/status-bar`.

- [ ] **Step 1: Install `@capacitor/status-bar`**

Run: `npm install @capacitor/status-bar@^8.0.0` then `npx cap sync android`.

- [ ] **Step 2: Implement `src/lib/nativeChrome.ts`**

```ts
import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeApp, isAndroid } from './platform';

// Sky-blue brand surface behind the status bar (matches theme-color).
const STATUS_BAR_BG = '#38bdf8';

/** Configure native status bar / edge-to-edge. No-op on web. */
export async function initNativeChrome(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    // Content draws under the status bar; our CSS --safe-top inset reserves space.
    await StatusBar.setOverlaysWebView({ overlay: true });
    await StatusBar.setStyle({ style: Style.Light }); // light icons on the blue bar
    if (isAndroid()) {
      await StatusBar.setBackgroundColor({ color: STATUS_BAR_BG });
    }
  } catch {
    // StatusBar can throw on unsupported surfaces; non-fatal.
  }
}
```

- [ ] **Step 3: Wire into `src/main.tsx`**

Add import + call alongside `registerBackButton()`:
```ts
import { initNativeChrome } from './lib/nativeChrome';
void initNativeChrome();
```

- [ ] **Step 4: Update theme-color in `index.html`**

Change line 6 from `<meta name="theme-color" content="#f59e0b" />` to:
```html
    <meta name="theme-color" content="#38bdf8" />
```
(Sky-blue, matching the rebrand + the native status bar background. `viewport-fit=cover` is already present on line 5 — leave it.)

- [ ] **Step 5: Verify**

Run: `npx tsc -b` → clean. `npm run build` → succeeds. `npx cap sync android` → ok. (Visual correctness is operator/device — note in report.)

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json src/lib/nativeChrome.ts src/main.tsx index.html
git commit -m "feat(android): status bar + edge-to-edge chrome init"
```

---

## Task 5: AndroidManifest parity

**Files:** Modify `frontend/android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Read the generated manifest**

Open `frontend/android/app/src/main/AndroidManifest.xml`. Capacitor's template already declares the `MainActivity` and `INTERNET` permission. You will ADD: the notifications permission, keyboard resize, and an App Links intent filter. Keep all existing template content.

- [ ] **Step 2: Add the POST_NOTIFICATIONS permission**

Inside `<manifest>` (next to the existing `<uses-permission android:name="android.permission.INTERNET" />`), add:
```xml
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

- [ ] **Step 3: Set keyboard resize on MainActivity**

On the `<activity android:name=".MainActivity" ...>` element, add the attribute:
```xml
        android:windowSoftInputMode="adjustResize"
```

- [ ] **Step 4: Add an App Links intent filter** (for the OAuth/magic-link return on the web origin)

Inside the `MainActivity` `<activity>`, after the existing launcher `<intent-filter>`, add:
```xml
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="app.investikid.ai" />
            </intent-filter>
```

- [ ] **Step 5: Verify**

Run: `npx cap sync android` → ok (no manifest-merge complaints reported by sync). `xmllint --noout frontend/android/app/src/main/AndroidManifest.xml 2>/dev/null || python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('frontend/android/app/src/main/AndroidManifest.xml'); print('xml ok')"` → well-formed.

- [ ] **Step 6: Commit**

```bash
git add frontend/android/app/src/main/AndroidManifest.xml
git commit -m "feat(android): manifest parity (notifications, adjustResize, App Links)"
```

---

## Task 6: Android notification channel

**Files:** Create `frontend/src/lib/notifications.ts`; Modify `frontend/src/main.tsx`

> `streakReminder.ts` already calls `LocalNotifications.requestPermissions()` (this triggers the Android 13+ POST_NOTIFICATIONS prompt now that the manifest declares it). Android 8+ also needs a notification **channel** or notifications silently fail to display.

- [ ] **Step 1: Implement `src/lib/notifications.ts`**

```ts
import { LocalNotifications } from '@capacitor/local-notifications';
import { isAndroid } from './platform';

export const REMINDER_CHANNEL_ID = 'streak-reminders';

/** Create the Android notification channel for streak reminders. No-op off Android. */
export async function ensureAndroidChannel(): Promise<void> {
  if (!isAndroid()) return;
  try {
    await LocalNotifications.createChannel({
      id: REMINDER_CHANNEL_ID,
      name: 'Streak reminders',
      description: 'Gentle nudges to keep your learning streak going',
      importance: 3,
    });
  } catch {
    // createChannel is Android-only and can throw on older webviews; non-fatal.
  }
}
```

- [ ] **Step 2: Wire into `src/main.tsx`**

```ts
import { ensureAndroidChannel } from './lib/notifications';
void ensureAndroidChannel();
```

- [ ] **Step 3: Point scheduled reminders at the channel**

In `frontend/src/lib/streakReminder.ts`, in `applyStreakReminder` where it builds the `LocalNotifications.schedule({ notifications: [ ... ] })` payload, add `channelId: REMINDER_CHANNEL_ID` to the notification object (import `REMINDER_CHANNEL_ID` from `./notifications`). Read the function body first to place it correctly; `channelId` is ignored on iOS so it's safe cross-platform.

- [ ] **Step 4: Verify**

Run: `npx tsc -b` → clean. `npx vitest run src/lib` → existing streak-reminder tests still pass. `npm run build` → ok.

- [ ] **Step 5: Commit**

```bash
git add src/lib/notifications.ts src/lib/streakReminder.ts src/main.tsx
git commit -m "feat(android): local-notifications channel for streak reminders"
```

---

## Task 7: Inline-video platform check

**Files:** Modify `frontend/src/components/child/lesson/videoEmbed.ts`; Test (extend existing `videoEmbed.test.ts`)

> The YouTube `Referer` proxy (`yt.html`) was an iOS WKWebView workaround but currently triggers on any native platform. On Android WebView the standard embed works and the proxy is unnecessary. Scope the proxy to iOS to keep Android on the simpler path.

- [ ] **Step 1: Read `videoEmbed.ts` + its test**

Identify where it branches on `isNativeApp()` / `isNative` to choose the proxy vs the direct embed. Confirm the existing test file `src/components/child/lesson/__tests__/videoEmbed.test.ts` and its `BuildYouTubeOptions` (it accepts `isNative`).

- [ ] **Step 2: Add a failing test for Android using the direct (non-proxy) path**

Add to the existing test file a case that calls `buildYouTubeUrls(id, { isNative: true, isAndroid: true })` (you will add an `isAndroid` option) and asserts the resulting embed URL is the direct `youtube-nocookie.com` embed (NOT the `/yt.html` proxy). Mirror the existing iOS test that asserts the proxy IS used when `isNative: true` (iOS).

- [ ] **Step 3: Run to verify it fails**

Run: `npx vitest run src/components/child/lesson/__tests__/videoEmbed.test.ts` → FAIL.

- [ ] **Step 4: Implement**

In `buildYouTubeUrls`, extend `BuildYouTubeOptions` with `isAndroid?: boolean` (default via `isAndroid()` from `@/lib/platform`), and use the `yt.html` proxy only when native AND NOT Android (i.e. iOS). On Android use the same direct embed path as web. Keep iOS behavior identical.

- [ ] **Step 5: Run to verify pass**

Run: `npx vitest run src/components/child/lesson/__tests__/videoEmbed.test.ts` → PASS (iOS proxy case + new Android direct case both green).

- [ ] **Step 6: Commit**

```bash
git add src/components/child/lesson/videoEmbed.ts src/components/child/lesson/__tests__/videoEmbed.test.ts
git commit -m "feat(android): use direct YouTube embed on Android (iOS keeps Referer proxy)"
```

---

## Task 8: Android adaptive icons + splash

**Files:** `frontend/android/app/src/main/res/**` (generated); `frontend/package.json` (devDep)

- [ ] **Step 1: Locate the master asset**

The 1024×1024 production icon lives under `docs/icon-mockups/` (the same master used for iOS). Identify the exact PNG path (e.g. the production export). `@capacitor/assets` expects a source at `frontend/assets/icon.png` (and optionally `splash.png`). Copy the master into `frontend/assets/icon.png` (create `frontend/assets/`); for the splash, use the same icon centered on a sky-blue (`#38bdf8`) background — create `frontend/assets/splash.png` (2732×2732, icon centered) if a splash source isn't already present. If producing a 2732 splash isn't feasible from the available master, generate icons only and note splash as a follow-up.

- [ ] **Step 2: Generate Android assets**

Run: `npx @capacitor/assets generate --android` (this installs `@capacitor/assets` on first run via npx, or `npm i -D @capacitor/assets` first). Expected: writes adaptive icon foreground/background + legacy icons + splash into `frontend/android/app/src/main/res/`.

- [ ] **Step 3: Sync + verify**

Run: `npx cap sync android` → ok. Confirm `frontend/android/app/src/main/res/mipmap-*/` and `drawable*/` now contain the generated assets and the adaptive `ic_launcher` XMLs reference sky-blue background.

- [ ] **Step 4: Commit**

```bash
git add frontend/assets frontend/package.json frontend/package-lock.json frontend/android/app/src/main/res
git commit -m "feat(android): adaptive icons + splash from brand master"
```

---

## Task 9: On-demand Android build in the checkpoint workflow

**Files:** Modify `.github/workflows/deployment-checkpoint.yml`

- [ ] **Step 1: Read the workflow**

Open `.github/workflows/deployment-checkpoint.yml`. Find the existing `run_android` input/flag and its job (the spec notes it currently fails with setup guidance because no android project existed). You will make that job actually build. Match the workflow's existing job/step style (checkout, node setup, working-directory `frontend`).

- [ ] **Step 2: Make the `run_android` job build the app**

Ensure the Android job runs only when the `run_android` input is true, and contains these steps (ubuntu-latest):
```yaml
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
      - uses: android-actions/setup-android@v3
      - name: Install deps
        working-directory: frontend
        run: npm ci
      - name: Build web + sync Android
        working-directory: frontend
        run: |
          npm run build
          npx cap sync android
      - name: Gradle assembleDebug
        working-directory: frontend/android
        run: ./gradlew assembleDebug --no-daemon
```
(If the user wants a release AAB, a follow-up step `./gradlew bundleRelease` can be added with signing secrets — out of scope for A1; debug build is the compile gate.) Keep the production-checkpoint guards already in the workflow intact.

- [ ] **Step 3: Lint the workflow YAML**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deployment-checkpoint.yml')); print('yaml ok')"` → `yaml ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deployment-checkpoint.yml
git commit -m "ci(android): on-demand Android build in deployment checkpoint (run_android)"
```

---

## Task 10: Operator runbook

**Files:** Create `docs/2026-06-07-android-operator-runbook.md`

- [ ] **Step 1: Write the runbook**

Create `docs/2026-06-07-android-operator-runbook.md` with concrete, ordered operator steps (no placeholders). It MUST cover:
1. **Local tooling:** install JDK 21 (Temurin) + Android Studio / Android SDK; `ANDROID_HOME`; `cd frontend && npm ci && npm run build && npx cap sync android && npx cap open android`.
2. **Signing:** create an upload keystore (`keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 9125 -alias upload`); store it OUT of git; enrol in **Play App Signing** (Google holds the app signing key, you hold the upload key).
3. **Get the SHA-1/SHA-256** of the upload key (`keytool -list -v -keystore upload-keystore.jks -alias upload`) AND the Play App Signing key (from Play Console → Setup → App signing).
4. **Google Cloud:** create an **Android OAuth client** (package `leeashmore.investikid.ai.app` + both SHA-1s) so `@capgo/capacitor-social-login` Google sign-in works on Android; keep the existing Web client ID (`VITE_GOOGLE_WEB_CLIENT_ID`) as serverClientId.
5. **App Links:** host `https://app.investikid.ai/.well-known/assetlinks.json` containing the package name + the Play App Signing SHA-256 (so the `autoVerify` intent filter verifies). Include the exact JSON shape.
6. **Play Console:** create the app, complete the data-safety + content-rating (kids/Families policy!) forms, create an **internal testing** track, upload the first AAB (`./gradlew bundleRelease`), add testers.
7. **On-device parity checklist** (the real test): cold start; parent magic-link/Google/Apple login (cookie auth persists); child signup + consent; hardware **back button** behaves (in-app back, exits at root); **status bar / insets** don't overlap content; **inline video** plays; **local-notification permission prompt** + a scheduled streak reminder fires; safe-area on a notch/gesture-nav device.

- [ ] **Step 2: Commit**

```bash
git add docs/2026-06-07-android-operator-runbook.md
git commit -m "docs(android): operator runbook (tooling, signing, Play Console, parity checklist)"
```

---

## Task 11: Regression + close-out

- [ ] **Step 1: Full frontend gates**

Run (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`
Expected: tsc clean; lint no NEW errors (pre-existing react-refresh warnings OK); all vitest green; build succeeds.

- [ ] **Step 2: Android sync sanity**

Run: `npx cap sync android` → ok; `npx cap ls` shows the android platform with the installed plugins (`@capacitor/app`, `@capacitor/status-bar`, local-notifications, social-login).

- [ ] **Step 3: Update PROGRESS docs**

In `docs/superpowers/PROGRESS.md`, add a row noting **4A·A1 Android platform foundation** is implemented in-repo on `testing` (scaffold + parity + icons + on-demand checkpoint build + runbook), with the caveat that the first real compile/device-test is the operator runbook + checkpoint `run_android`. Cross-link the runbook.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/PROGRESS.md
git commit -m "docs: mark 4A·A1 Android platform foundation implemented (in-repo)"
```

---

## Self-Review (completed)

- **Spec coverage:** scaffold+`.gitignore` → T1; config parity (manifest perms/resize/App Links) → T5; shared capacitor config already correct (noted, no task needed); code/UX parity → back button T3, status bar/edge-to-edge T4, platform helper T2, notifications channel/permission T6, inline video T7; icons/splash → T8; on-demand CI build → T9; operator runbook → T10; verification limits → every task verifies via cap sync + tsc/lint/build, real build deferred to T9 job/operator (restated T11).
- **Placeholder scan:** the only conditional is T8 splash ("if 2732 master infeasible, icons-only + follow-up") — that's an explicit, bounded fallback, not a vague TODO. No "handle edge cases"/"TBD" left.
- **Type/naming consistency:** `getPlatform`/`isAndroid` (T2) used in T4/T6/T7; `decideBackAction`/`ROOT_PATHS`/`registerBackButton` (T3) consistent; `initNativeChrome` (T4), `ensureAndroidChannel`/`REMINDER_CHANNEL_ID` (T6) consistent across their wiring in `main.tsx`.
- **Known operator dependencies flagged inline:** SHA-1/assetlinks/Play Console/OAuth client all in T10; no in-repo task depends on them.
