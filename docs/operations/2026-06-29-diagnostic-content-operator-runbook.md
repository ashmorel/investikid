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

## Answer-verifier review (catch wrong/ambiguous answers)

An automated **blind verifier** (the `diagnostic-verify` workflow, tier `premium`) re-solves each
item from scratch and flags any whose stored answer it disagrees with. It's **advisory** — it
catches genuine mistakes *and* throws some false positives (it can be wrong itself), so **you
adjudicate**.

1. Run the **`diagnostic-verify`** workflow (Actions), then open the **"Needs review"** filter on
   `/admin/diagnostic-items`. Each flagged item shows the verifier's note + its proposed answer.
2. For each flagged item, decide — one click each:
   - **False positive** (the stored answer is right) → click **"Looks correct — keep published."**
     This clears the advisory flag **in place** — the item stays **approved and live**, its answer
     untouched — and it drops out of "Needs review." Nothing breaks if you instead just leave it
     flagged: a flagged item is still served; the flag is only a review marker.
   - **Genuinely wrong** → fix it with **Unpublish to edit** (next paragraph).

**Fix-in-place path (Unpublish → fix → Approve).** To *correct* a flagged item: editing is
draft-only, so click **Unpublish to edit** (approved → draft), fix the answer (or
question/choices/explanation), then **Approve** again. Editing the content **clears the stale
verifier flag automatically**, so the corrected item drops out of "Needs review." (Use **Retire**
only if the item is unsalvageable — that removes it from the bank entirely.)

> **Two buttons, two cases:** *"Looks correct — keep published"* = false positive, keep it live and
> dismiss the flag. *"Unpublish to edit"* = genuinely wrong, take it down to fix. Both leave the
> "Needs review" list emptier; work it to zero before beta.

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
