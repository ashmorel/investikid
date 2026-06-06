# Deployment Checkpoint

Use the GitHub Actions workflow **Deployment checkpoint** when you want an explicit pre-deploy or test-deploy validation run. The default path is **testing**; production should be selected only when you are deliberately releasing.

## What You Choose

The workflow asks for:
- `target_environment`: `testing` or `production`
- checks/builds to run:
  - web
  - backend
  - security
  - a11y
  - responsive
  - iOS
  - Android
- optional notes

Production checkpoints are guarded:
- they must run from `main`
- they require notes explaining the release intent

## Current Deployment Model

This workflow validates the selected environment and builds. It does not directly deploy Vercel or Railway by itself.

Current branch model:
- `testing` = default deployment/testing path
- `main` = production code path, but automatic Vercel Git deployments from `main` are disabled in `frontend/vercel.json`
- pull requests to `main` = pre-production validation

Default workflow:
1. Merge or push routine work to `testing`.
2. Let the test environment deploy and validate there.
3. Run **Deployment checkpoint** with `target_environment=production` only when you deliberately want a production release.
4. Merge/promote/deploy to production manually after the production checkpoint passes.

Vercel:
- `frontend/vercel.json` disables automatic Git deployments from `main`.
- `testing` remains enabled for test deployments.
- Production should be done only by an explicit manual promotion/deploy in Vercel.

Railway:
- Create or duplicate a `testing` environment.
- Configure the backend service in Railway so `testing` auto-deploys from the `testing` branch.
- Disable production auto-deploys from `main`, or require manual deploys/approvals for the production Railway environment.

This branch/environment mapping is platform configuration, not controlled by `railway.json`.

## Platform Builds

- iOS is available and runs only when selected. It uses `macos-latest`, so use it intentionally.
- Android is listed as a future option, but the repo does not yet contain a Capacitor Android project. Selecting Android will fail with setup guidance until `@capacitor/android` and `frontend/android/` exist.
