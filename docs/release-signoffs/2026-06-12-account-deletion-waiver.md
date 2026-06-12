# Release waiver — 2026-06-12 promotion (parent account deletion)

**Decision (release owner, 2026-06-12):** promote `testing → staging → main` ahead of the
device-QA checklist ("let's go"); prod DB snapshot explicitly declined (no migrations in this
delta in any case).

**Batch covered:**
- Parent self-account deletion + delete-account UI with billing warning (Apple 5.1.1(v)) —
  web/backend surface only, no Alembic migration, fully unit/integration tested (CI green on
  `8a6c076`).
- iOS build-number bump to 1.0 (3) (`project.pbxproj` only).
- Docs: market-leader roadmap v2 (M1–M12).

**Conditions (carried forward from the 2026-06-11 build-3 waiver, unchanged):**
- The full checklist (`docs/release-qa-checklist.md`) will be run on **TestFlight build 3**
  on a real iPhone (and Android when available) and committed as a PASS sign-off here
  **before any external testers are invited**. That run should now also cover the
  delete-account flow (parent dashboard → Delete account → billing warning).
