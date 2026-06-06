# CI Environments and Cost Control Plan

## Task 1: Document CI Environment Shape

- [x] Write a concise design spec for regular web/backend CI, testing vs production labels, and manual iOS checks.
- [x] Write this implementation plan.

## Task 2: Update Regular CI

- [x] Keep `CI` triggered by pushes to `main`, pushes to `testing`, and pull requests to `main`.
- [x] Add workflow path filters so docs-only changes do not run CI.
- [x] Add environment labels: `production` for `main`, `testing` otherwise.
- [x] Remove the automatic iOS macOS job from `CI`.
- [x] Keep web/backend/security checks automatic.
- [x] Run a11y and responsive checks only when frontend-relevant files change.

## Task 3: Add Manual Deployment Checkpoint Workflow

- [x] Create `.github/workflows/deployment-checkpoint.yml`.
- [x] Add `workflow_dispatch` inputs for target environment, optional notes, and requested checks/builds.
- [x] Support web, backend, security, a11y, responsive, iOS, and Android selections.
- [x] Run the existing Capacitor sync and iOS simulator build on `macos-latest` only when iOS is selected.
- [x] Guard Android with an explicit setup error because no Capacitor Android project exists yet.
- [x] Use the selected `testing` or `production` GitHub environment label.

## Task 4: Default Deployments to Testing

- [x] Create a local `testing` branch from `main`.
- [x] Disable automatic Vercel Git deployments from `main`.
- [x] Keep Vercel Git deployments enabled for `testing`.
- [x] Document Railway dashboard setup for a `testing` environment and manually gated production.
- [x] Require notes for production deployment checkpoints.

## Task 5: Verify

- [x] Parse workflow YAML.
- [x] Inspect diff.
- [x] Confirm regular CI no longer uses macOS.
- [x] Confirm deployment checkpoint workflow contains the optional iOS simulator build.
