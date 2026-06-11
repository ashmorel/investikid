# Release QA Checklist — physical-device gate

**Purpose:** A release MUST pass this on a **real iPhone and a real Android device** before promotion to production (`main`). Simulators and the web build do NOT satisfy this gate — App Store/Play behaviours (StoreKit, WKWebView, push permissions, background kill) only surface on hardware.

**How to use:** Copy this file to `docs/release-signoffs/YYYY-MM-DD-build<N>.md`, fill in the header + every row for both devices, and commit it. A row is **PASS** only if it behaves correctly; any **FAIL** blocks promotion until fixed and re-tested. See `docs/release-signoffs/README.md`.

---

## Sign-off header (fill in per release)
- **Date:**
- **Build / version:** e.g. `1.0 (2)`
- **Branch/commit under test:** e.g. `staging @ <sha>`
- **Tester:**
- **iPhone:** model + iOS version
- **Android:** device + Android version
- **Result:** PASS / FAIL (overall — must be PASS to promote)

---

## The matrix

Mark each cell **PASS / FAIL / N/A** with a note on any quirk.

| # | Flow | What "pass" looks like | iPhone | Android |
|---|------|------------------------|--------|---------|
| 1 | **App launch** | Cold launch ≤ ~3s to a usable screen; no white screen; safe-area insets correct (notch/home indicator). | | |
| 2 | **Parent sign-up + consent** | Account creation, guardian consent/attestation, email verification all complete; can reach the dashboard. | | |
| 3 | **Login (email + social)** | Email login works; **Google** and **Apple** sign-in complete in the native shell and return to the app authenticated. | | |
| 4 | **Child login / profile switch** | Child can log in / be selected; lands on the child home. | | |
| 5 | **Lesson — card & quiz** | Open a module → level → card and quiz lessons render; answers register; XP awarded. | | |
| 6 | **Lesson — video playback** | A curated YouTube lesson **plays** (no error 153); video **ends into the app's "Mark complete" panel**, not YouTube recommendations; a known-bad video shows the friendly fallback, not a raw error. | | |
| 7 | **Lesson completion + progress save** | Mark a lesson complete; **force-kill the app, relaunch** → progress/XP/streak persisted. | | |
| 8 | **Offline / network drop** | Mid-lesson, toggle airplane mode → graceful message, no crash/data loss; on reconnect, completing a lesson still saves. | | |
| 9 | **Simulator trade** | Place a buy and a sell with virtual cash; portfolio + XP (capped) update; reward toast shows. | | |
| 10 | **Coach Penny (premium)** | Non-premium child sees the gentle paywall; premium child can chat; responses are moderated/age-appropriate. | | |
| 11 | **Premium purchase** | "Ask my grown-up" → parent can subscribe via **StoreKit (iOS) / Play Billing (Android) sandbox**; entitlement unlocks premium content on the child side. | | |
| 12 | **Notifications** | Permission prompt appears; a test notification is received (and respects the parent's notification preferences). | | |
| 13 | **Parent dashboard** | Per-child analytics (levels, XP, module/level progress), premium requests, and session revocation all load and act correctly. | | |
| 14 | **Region** | Region selector reflects the child's content region; region-aware market/movers render. | | |
| 15 | **Accessibility spot-check** | Dynamic Type / large text doesn't break core screens; key controls are ≥44px and reachable; VoiceOver/TalkBack reads the home + a lesson. | | |

## Blocking rules
- Any **FAIL** on rows **2, 3, 6, 7, 11** is an automatic release block (auth, video, progress-save, billing are the "looks broken to a parent" risks).
- Rows 1, 8, 15 failing → fix or get an explicit, recorded waiver from the release owner before promoting.

## Notes / waivers
(record any quirks, environment caveats, or explicit waivers here)
