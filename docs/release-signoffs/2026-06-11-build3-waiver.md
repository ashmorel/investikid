# Release waiver — 2026-06-11 promotion (TestFlight build 3)

**Decision (release owner, 2026-06-11):** promote `testing → staging → main` ahead of the
device-QA checklist. Rationale: the full 15-row checklist requires the NEW TestFlight build,
which itself requires the updated production backend (solo-tester chicken-and-egg).

**Conditions:**
- The full checklist (`docs/release-qa-checklist.md`) will be run on **TestFlight build 3**
  on a real iPhone (and Android when available) and committed as a PASS sign-off here
  **before any external testers are invited**.
- Prod DB snapshot: explicitly declined by the release owner for this promotion
  (3 migrations: level_mastery+backfill, digest prefs, tier_override; prod holds test data).

**Batch covered:** W7 demo · security fixes (rate-limit keying, secret rotation) · P-1
performance/offline · simulator totals + formatting · P-2 juice pack (sounds/haptics/animations).
