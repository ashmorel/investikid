# Operator runbook — getting content ready for the mastery / diagnostic enhancements

**Date:** 2026-06-29
**Audience:** operator/PM (no code). **Goal:** turn the now-live A1–A3 measurement spine
from *inert* into *producing real evidence*, before recruiting the beta cohort.

## What's live (and why it's currently silent)

- **A1 concept taxonomy** — ~1,171/1,260 lessons tagged (~93%). Powers the learning loop +
  the (future) Progress drill-down.
- **A2 U1 diagnostic item bank** — `/admin/diagnostic-items` (generate → expert-review → approve).
- **A2 U2 diagnostic engine + checkpoints** — `/diagnostic/start|submit|evidence` (the "+X%" data).
- **A3 onboarding diagnostic** — shown once between signup and Home, captures the baseline.

**Why it's silent:** the engine + onboarding serve ONLY operator-**approved** diagnostic items.
There are currently **zero approved items**, so every child gets a graceful *skip-to-Home* and a
`skipped` baseline (no real measurement). Approving items is what switches it on.

---

## THE ONE GATING TASK — approve diagnostic items

**Where:** `app.investikid.ai` → Admin → **Diagnostic Items** (`/admin/diagnostic-items`).

**Target (decision AD1):** **≥2 approved items per (topic × difficulty tier), per market.**
- 9 topics × 3 difficulty tiers = 27 cells per market; ×2 items = **54 items/market minimum**.
- 3 English markets (GB/US/HK) = **~162 approved items minimum.**
- Aim a bit higher (3–4 per cell) so the later re-check (post-test) can draw *fresh* unseen
  items instead of repeating the baseline questions.

**How, per (market → topic → difficulty):**
1. Choose market + topic + difficulty, set a count (e.g. 5–6), click **Generate**. The model
   drafts multiple-choice questions grounded in that topic's concepts, in the market's English,
   already safety-moderated. They land as **draft**.
2. **Review each draft (this is the expert sign-off):** is the question correct, fair,
   unambiguous, with exactly one right answer, age-appropriate, and market-correct? **Edit**
   drafts that are close; **reject** the rest.
3. **Approve** the good ones until each cell has ≥2.
4. Use the **coverage table** as your checklist — it shows approved counts per cell (green = met,
   amber/red = under-covered). Work the red/amber cells to green.

> **This is the "operator-approves-for-beta" gate (AD4).** A named educator review comes later,
> before any *public* "mastery" claim — not a beta blocker.

---

## Supporting (optional, not blocking)

- **Concept tagging tail:** ~89 lessons are untagged (the model found no clear concept, or
  they're no-text/video lessons). Check `/admin/concepts` → "*N lessons not yet tagged*". You can
  leave these — they don't block the diagnostic. (Tagging improves the future Progress drill-down,
  not the diagnostic.)

---

## Before you recruit the beta cohort — gates (in order)

1. **Approve the diagnostic items** (above). **Do this FIRST.** If you recruit testers before
   items exist, their *first session* — the one chance to capture a baseline — produces only a
   `skipped` baseline. That evidence can't be recovered (no second first-session).
2. **Native build for the onboarding UI.** A3 is live on the **web** but not yet on **devices**
   (the native sync was deferred). For app/TestFlight/Play beta testers to see the diagnostic,
   the next native build must be cut (`npm run build` → `npx cap sync ios`/`android` → archive in
   Xcode/Gradle → upload). *Ask me to prep this when you're ready — it's a ~one-step code task
   plus your archive/upload.*
3. **Verify with a fresh test child account:** sign up/in as a new child → you should now see the
   onboarding diagnostic with **real questions** (not an instant skip). Submit it, then confirm it
   does **not** show again on next launch.

---

## The honesty rule — don't over-claim yet

Do **not** publish a "mastery +X%" figure until ALL of:
- **Unit 4** (the re-check / *post*-test) is built and has run — it's the second half of the
  before/after. (Baselines captured now during beta are still valuable: they're the "before" the
  post-test compares against.)
- Beta data shows the baseline **predicts** later in-app performance (i.e. the instrument is valid).
- The **item-distribution monitoring** has retired any item that nearly everyone gets right or
  wrong (those measure nothing).
- A **named educator** has signed off the item bank.

---

## Sequence at a glance

1. ✅ Approve diagnostic items — ≥2 per cell, 3 markets (`/admin/diagnostic-items`). ← **the task**
2. (optional) Tidy the unmapped-concept tail (`/admin/concepts`).
3. Cut the native build so the onboarding reaches devices (ask me to prep).
4. Verify with a fresh test child account.
5. **Then** recruit the beta cohort (8–10 / 11–13 / 15–18 bands) → baselines capture from session 1.
6. (Engineering, later) Unit 4 post-test → Unit 5 per-concept scoring → A4 parent-report growth
   block → only then the validated "+X%" claim.
