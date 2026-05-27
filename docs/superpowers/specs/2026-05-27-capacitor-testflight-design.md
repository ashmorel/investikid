# Capacitor + TestFlight Distribution Design

## Goal

Wrap the existing React/Vite frontend as a native iOS app via Capacitor and deploy the FastAPI backend to Railway, enabling TestFlight distribution to a small group of iPhone testers.

## Architecture

The iOS app bundles the built frontend assets (HTML/JS/CSS) locally — no remote frontend hosting needed. API calls from the app hit the Railway-hosted backend over HTTPS. Capacitor provides the native iOS shell (WKWebView) with no custom native plugins required.

```
[iOS App (Capacitor WKWebView)]
  |— Built frontend assets (local, from dist/)
  |— API calls via apiFetch → https://<railway-app>.up.railway.app
  
[Railway]
  |— FastAPI backend (uvicorn)
  |— PostgreSQL (Railway-provisioned)
  |— Alembic migrations run on deploy
```

## Bundle ID

`leeashmore.investikid.ai.app`

## 1. API Client Base URL

### Problem

`apiFetch` in `frontend/src/api/client.ts` uses relative paths (`/auth`, `/users`). In the Capacitor app, the WebView origin is `capacitor://localhost` — relative paths resolve to nothing useful.

### Solution

Add a `VITE_API_BASE_URL` environment variable. `apiFetch` prepends it to every request path.

- **Dev (Vite proxy):** `VITE_API_BASE_URL` is empty string or unset — relative paths, Vite proxy handles routing. Zero change to dev workflow.
- **Capacitor / production:** `VITE_API_BASE_URL=https://<app>.up.railway.app` — absolute URLs to the deployed backend.

### Change

In `client.ts`, prefix `path` with `import.meta.env.VITE_API_BASE_URL || ''` in the `fetch()` call.

## 2. Backend CORS

### Current State

`main.py` allows `["http://localhost:5173"]` in development, `[]` in production.

### Required Change

In production, allow:
- `capacitor://localhost` — iOS Capacitor app origin
- `https://localhost` — Capacitor on some WebView versions

Keep `http://localhost:5173` for development.

### Implementation

Add a `cors_origins` config field (comma-separated string in env, parsed to list). Default to `http://localhost:5173` for development. In production, set via Railway env var to `capacitor://localhost,https://localhost`.

## 3. Cookie SameSite

### Problem

Access token cookie is set with `SameSite=Lax`. Cross-origin requests from `capacitor://localhost` to `https://<railway>.up.railway.app` won't send cookies with `Lax`.

### Solution

When `environment != "development"`, set `SameSite=None` and `Secure=True` on the access token cookie. This allows the cookie to be sent cross-origin over HTTPS.

`SameSite=None` requires `Secure=True` (HTTPS only) — Railway provides HTTPS by default.

### Security Note

`SameSite=None` weakens CSRF protection from cookies alone, but the app already has a double-submit CSRF token defence (`X-CSRF-Token` header) which remains effective regardless of SameSite policy.

## 4. Capacitor Configuration

### Packages

Install in `frontend/`:
- `@capacitor/core` — runtime
- `@capacitor/cli` — CLI tooling (dev dependency)
- `@capacitor/ios` — iOS platform

### `capacitor.config.ts`

```typescript
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'leeashmore.investikid.ai.app',
  appName: 'Invest-Ed',
  webDir: 'dist',
  server: {
    // Assets served locally from the app bundle.
    // API calls use VITE_API_BASE_URL baked into the build.
    androidScheme: 'https',
  },
};

export default config;
```

### iOS Platform

`npx cap add ios` generates `frontend/ios/` with the Xcode project.

### `.gitignore`

Add to `frontend/.gitignore`:
```
# Capacitor iOS build artifacts
ios/App/App/public/
ios/App/Pods/
```

Keep the Xcode project itself (`ios/App/App.xcodeproj`, `ios/App/App/`) tracked — it contains build settings, signing config, and Info.plist that should be versioned.

## 5. Safe Area Insets

### Problem

iOS devices have notches (Dynamic Island) and home indicators that overlap content. The Shell's fixed top bar and bottom tab bar need safe area padding.

### Changes

1. **`index.html`:** Add `viewport-fit=cover` to the viewport meta tag.
2. **Shell top bar:** Add `padding-top: env(safe-area-inset-top)` via Tailwind arbitrary value or inline style.
3. **Shell bottom tab bar:** Add `padding-bottom: env(safe-area-inset-bottom)`.
4. **These values are `0` on non-iOS browsers** — no impact on web usage.

## 6. App Icon

### Problem

iOS requires PNG app icons. Current icons are SVG only.

### Solution

Convert the existing 512×512 SVG to a 1024×1024 PNG. Use `@capacitor/assets` CLI tool to generate all required iOS icon sizes from the single source PNG and populate the Xcode asset catalog.

Alternatively, manually place a 1024×1024 PNG in the Xcode asset catalog — Xcode 15+ auto-generates all sizes from a single 1024×1024 source.

## 7. Railway Deployment

### Config

**Start command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**`railway.json`** (in `backend/`):
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Root directory in Railway dashboard:** Set to `invest-ed/backend` (since the repo root is `Local Repo`, not `invest-ed`).

### Environment Variables (set manually in Railway dashboard)

- `DATABASE_URL` — auto-injected by Railway Postgres plugin
- `SECRET_KEY` — generate a strong random string
- `ENVIRONMENT=production`
- `APP_BASE_URL=https://<app>.up.railway.app`
- `TOGETHER_API_KEY` — existing Together AI key
- `GROQ_API_KEY` — existing Groq key
- `OPENAI_API_KEY` — existing OpenAI key
- `RESEND_API_KEY` — existing Resend key
- `CORS_ORIGINS=capacitor://localhost,https://localhost`

### Postgres

Railway provisions Postgres via a plugin. `DATABASE_URL` is auto-populated. No manual setup.

### Content Seeding

After first deploy, seed modules/lessons via the admin panel (`/admin`). The admin account needs to be created manually or via a seed script.

## 8. TestFlight Distribution

### Prerequisites (manual, user-performed)

1. Enroll in Apple Developer Program ($99/year) at developer.apple.com/programs
2. Create App ID in App Store Connect with bundle ID `leeashmore.investikid.ai.app`
3. Configure automatic signing in Xcode with the developer team

### Build & Upload Flow

1. `cd frontend && npm run build` — Vite builds to `dist/`
2. `npx cap sync ios` — copies `dist/` + syncs Capacitor plugins into Xcode project
3. Open `ios/App/App.xcworkspace` in Xcode
4. Select "Any iOS Device" as destination
5. Product → Archive
6. Distribute App → App Store Connect (TestFlight)
7. Add internal testers by email in App Store Connect

### Internal Testing

- Up to 100 internal testers (team members in App Store Connect)
- No App Store review required
- Testers install via TestFlight app

## Out of Scope

- Android platform
- Push notifications
- Native plugins (camera, biometrics, haptics)
- Offline mode beyond existing PWA caching
- CI/CD for Capacitor builds
- App Store submission / public TestFlight (external testing)
- Frontend hosting (assets bundled in app)

## Testing

- **Unit tests:** Existing frontend tests continue to pass (Capacitor imports are no-ops in non-Capacitor environments)
- **Manual verification:** Build the iOS app in Xcode Simulator, verify all flows work against Railway backend
- **Regression:** Full backend + frontend test suites must pass before archiving
