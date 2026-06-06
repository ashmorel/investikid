# CI Environments and Cost Control

## Goal

Reduce GitHub Actions minute usage while keeping regular web app validation and preserving a manual path for iOS TestFlight-readiness checks.

## Scope

In scope:
- Keep regular web/backend CI on `main`, `testing`, and pull requests to `main`.
- Separate GitHub Actions environment labels for production and testing CI.
- Remove the macOS iOS simulator build from automatic CI.
- Add a manual deployment checkpoint workflow where the user chooses target environment and requested build/check types.
- Disable automatic Vercel Git deployments from `main` so the default web deployment path is `testing`.

Out of scope:
- Changing Vercel or Railway project settings.
- Creating GitHub environments through the GitHub UI.
- Changing runtime app configuration or secrets.
- Making Vercel/Railway deploys fully manual; this still depends on their platform settings.

## Environment Model

- `testing`: CI runs from pull requests and the `testing` branch. This is the default test deployment path.
- `production`: CI can run from `main`, but production deployment should be explicit/manual.
- Manual deployment checkpoint builds use the selected `testing` or `production` environment so any environment-specific approval rules still apply.

The deployment checkpoint validates selected builds and environments. It does not directly deploy Vercel or Railway unless those platforms are separately configured to deploy from the selected branch/ref.

Vercel automatic Git deployments from `main` are disabled with `git.deploymentEnabled.main = false` in `frontend/vercel.json`; `testing` remains enabled. Railway requires dashboard configuration: create/duplicate a `testing` environment, point it at the `testing` branch, and disable or manually gate production auto-deploys.

## CI Shape

The regular `CI` workflow remains the deploy gate for web/backend work and uses Ubuntu runners only:
- frontend lint, typecheck, unit tests, build
- backend lint and tests
- security checks
- a11y checks when frontend files change
- responsive checks when frontend files change

Optional/manual checks move to a separate `Deployment checkpoint` workflow:
- triggered only by `workflow_dispatch`
- selectable target environment: `testing` or `production`
- selectable checks: web, backend, security, a11y, responsive, iOS, Android
- uses `macos-latest` only when iOS is selected
- Android is guarded because this repo does not yet have a Capacitor Android project

## Edge Cases

- Docs-only changes should not run the regular CI workflow.
- Backend-only changes should not run frontend a11y/responsive browser suites.
- Pull requests still get the same production-gate checks before merging.
- Manual checkpoint checks can be run independently without affecting web deployment cadence.
- Production checkpoint runs are blocked unless triggered from `main`.

## Test Plan

- Validate workflow YAML parses.
- Confirm `CI` has no `macos-latest` runner.
- Confirm the deployment checkpoint workflow contains the only `macos-latest` usage.
- Confirm triggers include `main`, `testing`, and pull requests.
