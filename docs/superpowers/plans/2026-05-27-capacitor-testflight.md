# Capacitor + TestFlight Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the React/Vite frontend as a native iOS app via Capacitor and prepare Railway deployment config, enabling TestFlight distribution.

**Architecture:** Capacitor bundles the built frontend assets locally in a WKWebView. API calls hit the Railway-hosted FastAPI backend via `VITE_API_BASE_URL`. Cookie SameSite policy is environment-dependent to support cross-origin requests from the Capacitor origin.

**Tech Stack:** Capacitor 7, @capacitor/ios, Vite, FastAPI, Railway (Nixpacks)

**Spec:** `docs/superpowers/specs/2026-05-27-capacitor-testflight-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/core/config.py` | Add `cors_origins` field |
| Modify | `backend/app/main.py` | Use `cors_origins` from config |
| Modify | `backend/app/routers/auth.py` | Environment-dependent SameSite on cookies |
| Modify | `backend/app/routers/parent_auth.py` | Same SameSite fix for parent cookie |
| Create | `backend/tests/test_cors_config.py` | CORS + cookie SameSite tests |
| Create | `backend/railway.json` | Railway deploy config |
| Modify | `frontend/src/api/client.ts` | Prepend `VITE_API_BASE_URL` to paths |
| Create | `frontend/capacitor.config.ts` | Capacitor project config |
| Modify | `frontend/.gitignore` | Ignore Capacitor build artifacts |
| Modify | `frontend/package.json` | Capacitor dependencies (via npm install) |
| Create | `frontend/ios/` | Generated Xcode project (via `npx cap add ios`) |

---

### Task 1: Backend — CORS Config + Cookie SameSite

**Files:**
- Modify: `backend/app/core/config.py:12` (add `cors_origins` field)
- Modify: `backend/app/main.py:110-118` (use `settings.cors_origins`)
- Modify: `backend/app/routers/auth.py:51,94-102,285-293` (environment-dependent SameSite)
- Modify: `backend/app/routers/parent_auth.py:71` (same SameSite fix)
- Create: `backend/tests/test_cors_config.py`

- [ ] **Step 1: Write tests for CORS config parsing and cookie SameSite**

Create `backend/tests/test_cors_config.py`:

```python
"""Tests for CORS config and environment-dependent cookie SameSite."""
import pytest
from unittest.mock import patch

from app.core.config import Settings


class TestCorsConfig:
    def test_cors_origins_default_is_dev_localhost(self):
        """Default cors_origins should be localhost:5173 for development."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            test_database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret="test",
            _env_file=None,
        )
        assert s.cors_origins == "http://localhost:5173"

    def test_cors_origins_parsed_from_comma_separated(self):
        """cors_origins should parse comma-separated string to list."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            test_database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret="test",
            cors_origins="capacitor://localhost,https://localhost",
            _env_file=None,
        )
        result = [o.strip() for o in s.cors_origins.split(",") if o.strip()]
        assert result == ["capacitor://localhost", "https://localhost"]


class TestCookieSameSite:
    def test_cookie_opts_lax_in_development(self):
        """In development, cookie SameSite should be 'lax'."""
        from app.routers.auth import _cookie_samesite
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.environment = "development"
            assert _cookie_samesite() == "lax"

    def test_cookie_opts_none_in_production(self):
        """In production, cookie SameSite should be 'none' for cross-origin Capacitor."""
        from app.routers.auth import _cookie_samesite
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.environment = "production"
            assert _cookie_samesite() == "none"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_cors_config.py -v`

Expected: FAIL — `cors_origins` field doesn't exist on `Settings`, `_cookie_samesite` function doesn't exist.

- [ ] **Step 3: Add `cors_origins` to config**

In `backend/app/core/config.py`, add after line 12 (`environment: str = "development"`):

```python
    cors_origins: str = "http://localhost:5173"
```

- [ ] **Step 4: Update `main.py` to use `cors_origins` from config**

In `backend/app/main.py`, replace lines 110-118:

```python
    application.add_middleware(
        CORSMiddleware,
        allow_origins=(
            ["http://localhost:5173"] if settings.environment == "development" else []
        ),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    )
```

With:

```python
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    )
```

- [ ] **Step 5: Add `_cookie_samesite` helper and update cookie opts in `auth.py`**

In `backend/app/routers/auth.py`, replace line 51:

```python
_COOKIE_OPTS = dict(httponly=True, samesite="lax")
```

With:

```python
def _cookie_samesite() -> str:
    """Return 'none' in production (cross-origin Capacitor), 'lax' in development."""
    return "none" if settings.environment != "development" else "lax"
```

Update `_set_access_cookie` (line 62-66) — replace:

```python
    response.set_cookie(
        "access_token", access,
        max_age=settings.access_token_expire_minutes * 60,
        secure=secure, path="/", **_COOKIE_OPTS,
    )
```

With:

```python
    response.set_cookie(
        "access_token", access,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True, samesite=_cookie_samesite(),
        secure=secure, path="/",
    )
```

Update `_issue_refresh_token` (line 87-91) — replace:

```python
    response.set_cookie(
        "refresh_token", token,
        max_age=settings.refresh_token_expire_days * 86400,
        secure=secure, path="/", **_COOKIE_OPTS,
    )
```

With:

```python
    response.set_cookie(
        "refresh_token", token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True, samesite=_cookie_samesite(),
        secure=secure, path="/",
    )
```

Update `_set_csrf_cookie` (line 94-102) — replace:

```python
def _set_csrf_cookie(response: Response, secure: bool) -> None:
    response.set_cookie(
        "csrf_token", generate_csrf_token(),
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,  # JS must read it
        samesite="lax",
        secure=secure,
        path="/",
    )
```

With:

```python
def _set_csrf_cookie(response: Response, secure: bool) -> None:
    response.set_cookie(
        "csrf_token", generate_csrf_token(),
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,  # JS must read it
        samesite=_cookie_samesite(),
        secure=secure,
        path="/",
    )
```

Update `logout` delete_cookie calls (lines 285-293) — replace:

```python
    response.delete_cookie(
        "access_token", httponly=True, samesite="lax", secure=secure, path="/"
    )
    response.delete_cookie(
        "refresh_token", httponly=True, samesite="lax", secure=secure, path="/"
    )
    response.delete_cookie(
        "csrf_token", httponly=False, samesite="lax", secure=secure, path="/"
    )
```

With:

```python
    samesite = _cookie_samesite()
    response.delete_cookie(
        "access_token", httponly=True, samesite=samesite, secure=secure, path="/"
    )
    response.delete_cookie(
        "refresh_token", httponly=True, samesite=samesite, secure=secure, path="/"
    )
    response.delete_cookie(
        "csrf_token", httponly=False, samesite=samesite, secure=secure, path="/"
    )
```

- [ ] **Step 6: Update parent_auth.py cookie SameSite**

In `backend/app/routers/parent_auth.py`, add import at top:

```python
from app.routers.auth import _cookie_samesite
```

Replace the parent session cookie line (line 71):

```python
        max_age=7 * 86400, httponly=True, samesite="lax", secure=secure, path="/",
```

With:

```python
        max_age=7 * 86400, httponly=True, samesite=_cookie_samesite(), secure=secure, path="/",
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_cors_config.py -v`

Expected: 4 passed

- [ ] **Step 8: Run full backend regression**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest --timeout=30 -x -q`

Expected: 463+ passed (4 pre-existing failures)

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/config.py backend/app/main.py backend/app/routers/auth.py backend/app/routers/parent_auth.py backend/tests/test_cors_config.py
git commit -m "feat: configurable CORS origins + environment-dependent cookie SameSite

CORS origins now read from CORS_ORIGINS env var (comma-separated).
Cookie SameSite is 'none' in production for cross-origin Capacitor
requests, 'lax' in development. CSRF double-submit still effective."
```

---

### Task 2: Frontend — API Base URL

**Files:**
- Modify: `frontend/src/api/client.ts:23`

- [ ] **Step 1: Write test for base URL prepending**

Create `frontend/src/api/__tests__/client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('apiFetch base URL', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL;

  afterEach(() => {
    vi.restoreAllMocks();
    // Reset env
    import.meta.env.VITE_API_BASE_URL = originalEnv;
  });

  it('uses relative path when VITE_API_BASE_URL is unset', async () => {
    import.meta.env.VITE_API_BASE_URL = '';
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const { apiFetch } = await import('@/api/client');
    await apiFetch('/health');
    expect(fetchSpy.mock.calls[0][0]).toBe('/health');
  });

  it('prepends base URL when VITE_API_BASE_URL is set', async () => {
    import.meta.env.VITE_API_BASE_URL = 'https://api.example.com';
    // Force re-import to pick up the new env value
    vi.resetModules();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const { apiFetch } = await import('@/api/client');
    await apiFetch('/health');
    expect(fetchSpy.mock.calls[0][0]).toBe('https://api.example.com/health');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/api/__tests__/client.test.ts`

Expected: The "prepends base URL" test fails (fetch receives `/health` not `https://api.example.com/health`).

- [ ] **Step 3: Update `client.ts` to prepend base URL**

In `frontend/src/api/client.ts`, add at the top of the file (after imports):

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
```

Then replace line 23:

```typescript
  const res = await fetch(path, { credentials: 'include', ...init, method, headers });
```

With:

```typescript
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init, method, headers });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run src/api/__tests__/client.test.ts`

Expected: 2 passed

- [ ] **Step 5: Run full frontend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`

Expected: 382+ passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts
git commit -m "feat: support VITE_API_BASE_URL for Capacitor builds

apiFetch prepends VITE_API_BASE_URL to all request paths. Empty/unset
means relative paths (existing dev behavior unchanged)."
```

---

### Task 3: Railway Deploy Config

**Files:**
- Create: `backend/railway.json`

- [ ] **Step 1: Create `railway.json`**

Create `backend/railway.json`:

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

- [ ] **Step 2: Verify JSON is valid**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && python -m json.tool railway.json > /dev/null && echo "Valid JSON"`

Expected: `Valid JSON`

- [ ] **Step 3: Commit**

```bash
git add backend/railway.json
git commit -m "chore: add Railway deploy config

Start command runs Alembic migrations then uvicorn. Nixpacks builder
auto-detects Python from requirements.txt."
```

---

### Task 4: Capacitor Init + iOS Platform

**Files:**
- Create: `frontend/capacitor.config.ts`
- Modify: `frontend/package.json` (via npm install)
- Modify: `frontend/.gitignore`
- Create: `frontend/ios/` (generated by `npx cap add ios`)

- [ ] **Step 1: Install Capacitor packages**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
npm install @capacitor/core
npm install -D @capacitor/cli @capacitor/ios
```

- [ ] **Step 2: Create `capacitor.config.ts`**

Create `frontend/capacitor.config.ts`:

```typescript
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'leeashmore.investikid.ai.app',
  appName: 'Invest-Ed',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
```

- [ ] **Step 3: Build frontend assets**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
npm run build
```

Expected: `dist/` directory created with `index.html` and bundled assets.

- [ ] **Step 4: Add iOS platform**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
npx cap add ios
```

Expected: `ios/` directory created with Xcode project. Output includes "✔ Adding native Xcode project".

- [ ] **Step 5: Sync web assets into iOS project**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
npx cap sync ios
```

Expected: Copies `dist/` into iOS project and syncs any Capacitor plugins.

- [ ] **Step 6: Update `.gitignore`**

Append to `frontend/.gitignore`:

```
# Capacitor iOS build artifacts
ios/App/App/public/
ios/App/Pods/
```

- [ ] **Step 7: Run frontend tests to verify no breakage**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`

Expected: 382+ passed (Capacitor packages are no-ops in non-Capacitor environments)

- [ ] **Step 8: Verify TypeScript still compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc -b`

Expected: Clean (no errors)

- [ ] **Step 9: Commit**

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
git add capacitor.config.ts .gitignore package.json package-lock.json ios/
git commit -m "feat: add Capacitor iOS platform

Bundle ID: leeashmore.investikid.ai.app
Xcode project generated at frontend/ios/.
Build artifacts (ios/App/App/public/, ios/App/Pods/) gitignored."
```

---

### Task 5: App Icon — PNG Generation

**Files:**
- Modify: `frontend/ios/App/App/Assets.xcassets/AppIcon.appiconset/` (generated)

- [ ] **Step 1: Convert SVG to 1024×1024 PNG**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend

# Use sips (macOS built-in) — first export SVG to PNG via a temp route
# sips doesn't handle SVG directly, so use the qlmanage approach:
qlmanage -t -s 1024 -o /tmp/ public/icons/icon-512.svg
# This creates /tmp/icon-512.svg.png — rename and copy
cp /tmp/icon-512.svg.png ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

If `qlmanage` doesn't produce clean output, use Python as fallback:

```bash
pip install cairosvg 2>/dev/null || true
python -c "
import cairosvg
cairosvg.svg2png(url='public/icons/icon-512.svg', write_to='ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png', output_width=1024, output_height=1024)
"
```

- [ ] **Step 2: Update Xcode asset catalog JSON**

Replace `frontend/ios/App/App/Assets.xcassets/AppIcon.appiconset/Contents.json` with:

```json
{
  "images" : [
    {
      "filename" : "AppIcon-1024.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
```

Xcode 15+ auto-generates all required sizes from the single 1024×1024 source.

- [ ] **Step 3: Verify the PNG exists and is 1024×1024**

Run:

```bash
sips -g pixelWidth -g pixelHeight /Users/leeashmore/Local\ Repo/invest-ed/frontend/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

Expected: `pixelWidth: 1024` and `pixelHeight: 1024`

- [ ] **Step 4: Commit**

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
git add ios/App/App/Assets.xcassets/AppIcon.appiconset/
git commit -m "feat: add 1024x1024 PNG app icon for iOS

Generated from existing SVG. Xcode 15+ auto-generates all sizes
from the single source image."
```

---

### Task 6: Full Regression + Verify Build

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest --timeout=30 -x -q`

Expected: 467+ passed (463 baseline + 4 new CORS/cookie tests, minus 4 pre-existing failures)

- [ ] **Step 2: Run full frontend test suite**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx vitest run`

Expected: 384+ passed (382 baseline + 2 new client tests)

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npx tsc -b`

Expected: Clean

- [ ] **Step 4: Verify Vite build**

Run: `cd /Users/leeashmore/Local\ Repo/invest-ed/frontend && npm run build`

Expected: Clean build into `dist/`

- [ ] **Step 5: Sync and verify Capacitor**

Run:

```bash
cd /Users/leeashmore/Local\ Repo/invest-ed/frontend
npx cap sync ios
```

Expected: No errors. Web assets copied to iOS project.

- [ ] **Step 6: Report results**

Report test counts, any failures, and confirm the iOS project is ready for Xcode.

---

## Post-Implementation: Manual Steps (User-Performed)

These steps cannot be automated and are documented here for reference:

1. **Enroll in Apple Developer Program** ($99/year) at https://developer.apple.com/programs — takes 24-48hrs
2. **Deploy backend to Railway:**
   - Create Railway project, add Postgres plugin
   - Connect GitHub repo, set root directory to `invest-ed/backend`
   - Set environment variables: `DATABASE_URL` (auto), `JWT_SECRET`, `ENVIRONMENT=production`, `APP_BASE_URL`, `CORS_ORIGINS=capacitor://localhost,https://localhost`, LLM keys, `RESEND_API_KEY`
3. **Set frontend env for Capacitor build:**
   - Create `frontend/.env.production` with `VITE_API_BASE_URL=https://<your-app>.up.railway.app`
   - Rebuild: `npm run build && npx cap sync ios`
4. **Open Xcode project:** `frontend/ios/App/App.xcworkspace`
   - Set signing team (automatic signing recommended)
   - Set deployment target (iOS 16.0+ recommended)
5. **Archive + Upload:** Product → Archive → Distribute App → App Store Connect
6. **Add TestFlight testers:** In App Store Connect, add tester emails
7. **Seed content:** Use admin panel at `https://<your-app>.up.railway.app/admin` to create modules/lessons
