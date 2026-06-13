# Release Sign-off — SP-Bio biometric login → production (2026-06-13)

**Promoted:** `main` merge `91d8694` (testing `df21f0b`, 19 commits) — SP-Bio biometric Face ID quick-login (parent + child), security-review hardening, and the iOS WKWebView crossorigin / native API-base fixes.

## Train
| Stage | Result |
|---|---|
| testing → staging (FF `df21f0b`) | CI 6/6 green · Railway staging deploy SUCCESS · health 200 · biometric_credentials table present (probe → 401, not 500) |
| **staging → main** (merge `91d8694`) | CI 6/6 green · **Railway prod deploy SUCCESS** · health 200 · short-secret → 422 (new code live) · 40-char wrong secret → 401 (**prod migration applied**) |
| Vercel production | `vercel deploy --prod --archive=tgz` from a clean `origin/main` worktree → target production, **aliased `app.investikid.ai`**, serving the new bundle (HTTP 200) |

## DB migration
One additive migration — `e2f3a4b5c6d7_biometric_credentials`: adds `users.biometric_allowed` (NOT NULL, server_default false) + creates `biometric_credentials` + 4 indexes. No drops, no data transforms. Applied cleanly on testing, staging, and prod. **Owner waived a pre-migration prod snapshot** (additive, low-risk, validated on two lower envs).

## Device-QA waiver
This promotion ships **backend + web only**. The biometric UI is native-only (the web `BiometricGate` is disabled on web; the lock screen / Face ID enrol toggles only render in the Capacitor app), so there is no new web-surface behaviour to device-QA beyond the parent's "Face ID sign-in" master switch. The iOS/Android apps are **not** shipped in this promotion — they ride the held iOS build 4 (and a future Android build). Native device-QA happens when those ship:
- **iOS:** add-a-face → forces password (the `.biometryCurrentSet` invalidation check) — pending at the build-4 TestFlight archive.
- **Android:** already verified end-to-end on a Pixel API 35 emulator (set / get / re-enrolment-invalidation) — see `2026-06-13-biometric-security-review.md`.

Backend biometric endpoints are live but inert until a native client enrols, so prod exposure of this change is limited to dormant endpoints + the parent master toggle.
