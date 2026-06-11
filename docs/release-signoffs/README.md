# Release sign-offs

Each production release records a completed device-QA sign-off here. This is the **hard gate**: do not promote `staging → main` without a committed, PASS sign-off for the build being promoted.

## Process
1. When a build is ready to promote, copy the template `docs/release-qa-checklist.md` to a new file in this directory named `YYYY-MM-DD-build<N>.md` (e.g. `2026-06-15-build3.md`).
2. Run the full matrix on a **real iPhone and a real Android device**, filling in every cell + the header (build, tester, devices).
3. Overall **Result** must be **PASS** (with no FAIL on the blocking rows) — or carry an explicit, written waiver from the release owner.
4. Commit the filled sign-off **before** promoting to `main`.

## Why a real device (not simulator/web)
StoreKit/Play billing, WKWebView video (error 153), push-permission prompts, background app-kill persistence, and safe-area layout only behave truthfully on hardware. A green CI + web build is necessary but **not** sufficient for a production release.

## Index
| Date | Build | Result | File |
|------|-------|--------|------|
| _none yet_ | | | |
