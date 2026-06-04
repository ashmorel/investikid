# Parent Social Login — Setup Guide

This document covers the one-time configuration steps needed to activate Apple and Google sign-in for parents in InvestiKid. It covers the Google Cloud Console, Apple Developer portal, Xcode capability, and environment variables.

---

## 1. Overview

- **Who can sign in**: parents only (child accounts use child credentials / PIN).
- **Providers**: Apple Sign In + Google Sign In.
- **Verification method**: ID-token only — the backend (`app/services/oidc.py`) verifies the JWT signature against the provider's JWKS endpoint. No client secrets, no server-side OAuth code exchange.
- **App Store Guideline 4.8**: because Google sign-in is offered, Apple sign-in must also be offered. Both are included.
- **Four identifiers** (public, not secret) drive the entire system:

| Variable | Description |
|---|---|
| `GOOGLE_WEB_CLIENT_ID` | OAuth 2.0 Web client ID from Google Cloud Console |
| `GOOGLE_IOS_CLIENT_ID` | OAuth 2.0 iOS client ID from Google Cloud Console |
| `APPLE_SERVICES_ID` | Apple Services ID (web/Vercel flow) |
| `APPLE_BUNDLE_ID` | `leeashmore.investikid.ai.app` — the native iOS app bundle |

If any of these are empty the backend raises `503 not_configured` for that provider. That is expected until setup is complete.

---

## 2. Google Cloud Console

### 2a. OAuth consent screen

1. Open [console.cloud.google.com](https://console.cloud.google.com) → select / create the InvestiKid project.
2. Navigate to **APIs & Services → OAuth consent screen**.
3. Choose **External** (allows any Google account to sign in).
4. Fill in:
   - **App name**: InvestiKid
   - **User support email**: your support address
   - **Developer contact email**: your developer address
5. On the **Scopes** step add `email` and `profile` (both are standard / non-sensitive).
6. Add yourself as a test user while in Testing mode; publish when ready.

### 2b. Web OAuth client ID

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Name: `InvestiKid Web`.
4. Authorised JavaScript origins:
   - `https://<your-vercel-domain>.vercel.app` (your production Vercel URL)
   - `http://localhost:5173` (Vite dev server)
5. Leave redirect URIs empty — token flow only.
6. Click **Create** and copy the **Client ID** (looks like `XXXXXXXXX.apps.googleusercontent.com`). This is `GOOGLE_WEB_CLIENT_ID`.

### 2c. iOS OAuth client ID

1. **Credentials → Create Credentials → OAuth client ID**.
2. Application type: **iOS**.
3. Bundle ID: `leeashmore.investikid.ai.app`.
4. Click **Create** and copy the **Client ID**. This is `GOOGLE_IOS_CLIENT_ID`.
5. Also note the **reversed client ID** — it looks like `com.googleusercontent.apps.XXXXXXXXX`. You will add this as a URL scheme in Xcode (step 4 below).

---

## 3. Apple Developer Portal

### 3a. Enable Sign in with Apple on the App ID

1. Sign in to [developer.apple.com](https://developer.apple.com) → **Certificates, Identifiers & Profiles → Identifiers**.
2. Select the App ID for `leeashmore.investikid.ai.app`.
3. Scroll to **Sign In with Apple** and tick **Enable**.
4. Leave group membership as the primary App ID (default).
5. Save and confirm.

### 3b. Create a Services ID (web / Vercel flow)

1. **Identifiers → +** → choose **Services IDs** → Continue.
2. Description: `InvestiKid Web`.
3. Identifier: choose a reverse-domain string, e.g. `leeashmore.investikid.web` — this becomes `APPLE_SERVICES_ID`.
4. After registering, select the new Services ID → enable **Sign In with Apple → Configure**.
5. Primary App ID: select `leeashmore.investikid.ai.app`.
6. Web domain: your Vercel domain (e.g. `investikid.vercel.app`).
7. Return URLs: `https://<vercel-domain>/parent/auth/apple/callback` (adjust to your actual callback path if different).
8. Save.

No `.p8` key file is needed — the backend uses the JWKS/ID-token verification path, not the client-secret code-exchange path.

---

## 4. Xcode configuration

These steps must be done manually in Xcode — they cannot be scripted by the CLI.

### 4a. Sign in with Apple capability

1. Open `invest-ed/frontend/ios/App/App.xcworkspace` in Xcode.
2. Select the **App** target → **Signing & Capabilities** tab.
3. Click **+ Capability** and add **Sign in with Apple**.

### 4b. Google URL scheme in Info.plist

The `@capgo/capacitor-social-login` plugin requires a URL scheme equal to the reversed iOS client ID so Google can hand back the token after the in-app browser redirect.

1. In the App target, open `Info.plist` (or select **Info** tab in target settings).
2. Add a new entry under **URL types**:
   - **Identifier**: `Google`
   - **URL Schemes**: the reversed iOS client ID, e.g. `com.googleusercontent.apps.XXXXXXXXX` (replace with the actual value from step 2c).
3. Save.

### 4c. Re-sync and rebuild

After making the Xcode changes, run from `invest-ed/frontend`:

```bash
npm run build
npx cap sync ios
```

Then rebuild and run the scheme in Xcode (or re-archive for TestFlight).

---

## 5. Environment variables

### Backend (Railway service + local `.env`)

Set these in the Railway dashboard under **Variables** and in your local `.env`:

```
GOOGLE_WEB_CLIENT_ID=<web client ID from step 2b>
GOOGLE_IOS_CLIENT_ID=<iOS client ID from step 2c>
APPLE_SERVICES_ID=<Services ID identifier from step 3b, e.g. leeashmore.investikid.web>
APPLE_BUNDLE_ID=leeashmore.investikid.ai.app
```

The backend verifies:
- Google tokens against `GOOGLE_WEB_CLIENT_ID` and `GOOGLE_IOS_CLIENT_ID` as allowed audiences.
- Apple tokens against `APPLE_SERVICES_ID` and `APPLE_BUNDLE_ID` as allowed audiences.

### Frontend (Vercel project + local `.env`)

Set these in the Vercel dashboard under **Environment Variables** and in your local `.env`:

```
VITE_GOOGLE_WEB_CLIENT_ID=<same web client ID>
VITE_GOOGLE_IOS_CLIENT_ID=<same iOS client ID>
VITE_APPLE_SERVICES_ID=<same Services ID identifier>
```

These are baked into the Vite build at compile time by `src/lib/socialLogin.ts` and used to initialise `@capgo/capacitor-social-login`.

**Important**: these are public client identifiers, not secrets. They are safe to expose in browser JavaScript. They must still be supplied via environment variables rather than committed to source, to keep per-environment configuration clean.

---

## 6. Testing

### Before IDs are set

The social login buttons are visible in the UI but will not complete: the backend returns `503 Service Unavailable` with `detail: "Provider not configured"` for any provider whose audience set is empty. This is expected.

### Testing sequence once configured

1. **Web — Google first**: open the Vercel deployment in a desktop browser, navigate to the parent login screen, click **Continue with Google**. Verify the Google OAuth popup opens, completes, and returns a parent session cookie.
2. **Web — Apple**: same screen, click **Continue with Apple**. Verify the Apple ID sheet appears and sign-in completes.
3. **Native iOS via TestFlight**: install the build, tap **Continue with Google** — verify the in-app browser opens Google's flow; then tap **Continue with Apple** — verify the native Apple ID sheet appears. Both should complete and land the parent on the dashboard.

### Linking vs. sign-in

- First time: the provider's verified email must match an existing `parent_email` in the database. If it does not match, the backend returns `404`. This is by design — parents must already have an account (created via magic link or admin).
- Once linked, subsequent sign-ins with the same provider go straight through.

---

## 7. App Store Guideline 4.8

Apple's Guideline 4.8 requires that if an app offers any third-party sign-in (such as Google), it must also offer Sign in with Apple. InvestiKid includes both Apple and Google social login, satisfying this requirement. Both buttons are shown together on the parent login screen.
