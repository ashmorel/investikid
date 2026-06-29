# Mastery Measurement — A2 (diagnostic + checkpoints) + A3 (onboarding placement) design

**Date:** 2026-06-29
**Status:** Approved (design) — AD1–AD4 locked 2026-06-29 → next: implementation plan (per unit)
**Scope:** A2 = the calibrated diagnostic engine + immutable `MasteryCheckpoint`
snapshots + the generate-then-expert-review item bank + per-concept mastery scoring.
A3 = the onboarding diagnostic (the baseline pre-test). A4 (parent-report growth block)
and A5 (public evidence page) are downstream consumers, specced separately.

## Goal

Turn the now-tagged curriculum into **evidence that children learn** — the headline
*"concept/topic mastery improved by X% after Y sessions."* This is the moat (vs Zogo /
FDIC Money Smart) and what makes the parent report sellable. A1 was the unblocker
(concepts tagged at ~93%); A2 is the measurement core; A3 captures the baseline that the
whole claim depends on.

## Context — what already exists (build on, don't replace)

- **`TopicMastery`** (`models/skill_profile.py`) — `mastery_score = quizzes_correct /
  quizzes_attempted` per `(user, topic, market)`; powers `/profile/strengths` (Progress
  page) via `gap_detection_service`. The 9 topics.
- **`Concept` taxonomy + `Lesson.concept_id`** — A1/A1.2/A1.3 shipped; **~1,171/1,260
  lessons tagged (~93%)**. `WeakConcept.concept_id` set on the learning loop.
- **SR engine** (`spaced_repetition_service`) on `WeakConcept` — the Revise loop.
- **`LevelMastery`** + standards alignment (`MaPS`/`CCSS`) → the **Mastery Report**
  (`mastery_report_service`). Level-mastery focused.
- **Content generation infra** — `admin_content_generation_service` (LLM gen + moderation
  + `with_generation_framing`), `lesson_approval_service` (draft → approve), the admin
  review surfaces, `llm_client.get_llm_client(tier)`.
- **Onboarding** (`Signup.tsx`) — DOB/country → email/username/currency/optional
  `topic_path` → `/home`. No placement; no baseline captured today.

**Conclusion:** A2 adds a *calibrated measurement instrument* (the diagnostic item bank +
checkpoints) alongside the existing live-learning signal (`TopicMastery`/SR). The two
axes stay distinct: **checkpoints = evidence; `TopicMastery`/SR = the learning loop.**

## Locked decisions (from the spine spec, 2026-06-28)

- **OD1 — scope:** the child's `topic_path` + 3 core topics (budgeting / saving / risk),
  ~8–10 items. Other topics get a **baseline-on-first-touch**.
- **OD2 — re-check cadence:** session-count milestones (5 / 15 / 30 active days).
- **OD3 — skip:** skippable; skippers → a `kind=skipped` checkpoint (no scores) so the
  cohort stays segmentable.
- **OD4 — item bank:** generate-then-expert-review per market, with a `difficulty_tier`
  + **expert sign-off gate** + **beta item-distribution monitoring**, and **no public
  "mastery +X%" claim until beta data shows the baseline predicts later performance.**

## Core design decisions (new)

### N1 — A dedicated `DiagnosticItem` table, NOT a flag on `Lesson`
Diagnostic items are a measurement instrument with different needs from lessons: a
`difficulty_tier`, calibration stats, an expert-approval lifecycle, and they must **never
award XP/streak/coins** or appear in the lesson track. A separate table keeps that clean
and keeps the lesson schema untouched.

### N2 — Measurement axis is self-contained (checkpoints), independent of `TopicMastery`
The "mastery +X%" claim = `baseline` checkpoint vs latest `progress` checkpoint, both
measured with the **same calibrated item bank**. This is independent of `TopicMastery`
(which mixes in normal quiz attempts), so the evidence is clean and auditable. The
diagnostic *additionally* warm-starts `TopicMastery` for personalization, but that never
feeds the evidence claim.

### N3 — Pre and post draw DIFFERENT items of the same calibrated difficulty
Re-using the same items at re-check inflates the post-score via memorization. So the bank
needs **≥2 approved items per (topic, difficulty_tier)** and the engine records which item
ids a child has seen, drawing unseen-same-difficulty items at re-check. (If the bank is
too thin, fall back to same-item with a logged caveat — never silently.)

### N4 — Diagnostic measures at TOPIC level; concepts power the report drill-down
A short diagnostic can't credibly score 47 concepts. It scores the in-scope **topics**
(per OD1). The now-tagged concepts power a **per-concept mastery** view (N5) that fills in
from normal play — the granular layer under the topic-level evidence.

## Architecture (6 units)

### Unit 1 — Calibrated item bank (`DiagnosticItem` + generation + expert review)
**Model** `DiagnosticItem`: `{id, market_code, topic, concept_id|None, difficulty_tier
(1–3), question, choices[], answer_index, explanation, status (draft|approved|retired),
source (generated|authored), times_shown, times_correct, created_at, approved_by|None,
approved_at|None}`. Additive migration.
**Generation:** an admin-triggered LLM pass generates candidate items per (market, topic,
difficulty) grounded in the taxonomy (reuse `get_llm_client` + `with_generation_framing`
+ `moderate_output`); lands as `status=draft`.
**Expert review (the OD4 gate):** an admin surface (`/admin/diagnostic-items`) to
preview / edit / **approve** / reject / retire; only `approved` items are ever served
live. `approved_by`/`approved_at` recorded. Mirrors the existing draft-review surfaces.
**Calibration:** `times_shown`/`times_correct` accrue from live use; a report flags items
with extreme pass rates (≈0 or ≈1 → measures nothing) for retirement.

### Unit 2 — Diagnostic engine + `MasteryCheckpoint`
**Model** `MasteryCheckpoint` (immutable): `{id, user_id, market_code, kind
(baseline|progress|skipped), session_count, overall_score|None, taken_at}` + child
`MasteryCheckpointTopic{checkpoint_id, topic, correct, attempted}`.
**Service** `diagnostic_service`: `start(user, scope)` → builds a session of approved
items (1–2 per in-scope topic, balanced difficulty, unseen-first per N3), records shown
item ids; `submit(user, answers)` → scores, writes the checkpoint (+ per-topic rows),
warm-starts `TopicMastery` (N2), updates item calibration stats. **Diagnostic answers
never award XP/streak/coins** (distinct from `/lessons/{id}/complete`).
**Endpoints:** `POST /diagnostic/start`, `POST /diagnostic/submit`,
`GET /diagnostic/evidence` (baseline vs latest delta — the A4 seam). Rate-limited;
market-scoped.

### Unit 3 — Onboarding placement (A3) — *launch-critical*
**Frontend:** a post-signup, pre-`/home` `/onboarding/diagnostic` step (skippable),
rendering the diagnostic session (reuse the quiz components) → a friendly results screen
("Here's what you already know 💡", per-topic chips) → `/home`. Writes the `baseline`
checkpoint. **Skip** still writes a `kind=skipped` baseline (comparable cohort).
**⏰ Gates beta research value — must ship before beta cohorts start** (no second
first-session).
**Baseline-on-first-touch:** when a child first opens a topic with no baseline captured,
a 1–2 item mini-check is presented before the first lesson, writing a per-topic baseline.
(Separable sub-unit — can land just after the core A3 flow if it risks slowing the MVP.)

### Unit 4 — Re-check trigger (progress checkpoints)
A child crossing a session-count milestone (5 / 15 / 30 **active days** — reuse the
streak/activity signal) is offered a short "progress check" in the daily flow, drawing
unseen-same-difficulty items (N3) and writing a `kind=progress` checkpoint. Non-blocking;
declinable.

### Unit 5 — Per-concept mastery scoring (the report drill-down)
A per-`(user, concept, market)` rolling accuracy over the last K attempts (from quiz +
Revise attempts on tagged lessons), computed as attempts happen. Powers the Progress-page
per-concept drill-down and smarter Revise targeting. Distinct from the topic-level
evidence. (Could defer to A4 if A2 is already large — but concepts are tagged now, so
it's cheap to start.)

### Unit 6 — Evidence surface (A4 seam — data only)
`GET /diagnostic/evidence` returns per-topic and overall **baseline→latest deltas** +
`session_count`, per child; an admin/aggregate version segments by the 8–10 / 11–13 /
15–18 bands for the beta. The full parent-report growth block + the public evidence page
are **A4/A5** (separate specs) — this unit just exposes the numbers.

## Mastery scoring model

- **Topic (evidence):** `correct/attempted` over the calibrated diagnostic items in a
  checkpoint. Δ = `latest_progress.overall − baseline.overall` (+ per-topic deltas), with
  `session_count` for "after Y sessions." Reported per child + cohort-aggregated.
- **Topic (live/personalization):** existing `TopicMastery`, warm-started by the
  baseline; unchanged role on the Progress page.
- **Concept (drill-down):** rolling per-concept accuracy (Unit 5).
- **Honesty gate (OD4):** no external/marketing "+X%" claim until beta data shows baseline
  correlates with later in-app performance, and item-distribution monitoring has retired
  the non-discriminating items.

## Non-goals (explicit)

- Adaptive/IRT diagnostics — fixed calibrated items first.
- Per-concept *diagnostic* measurement — diagnostic stays topic-level (N4).
- Replacing `LevelMastery`/standards or the Mastery Report — A4 *adds* a growth block.
- A4 full report redesign + A5 public evidence page — separate specs.
- Changing the SR/Revise math or the streak engine.
- Awarding any XP/coins/streak for diagnostic answers.

## Riskiest assumptions & cheap de-risks

1. **A short topic diagnostic yields a credible baseline.** De-risk: pilot the bank with
   the beta cohort; check baseline correlates with later in-app performance before any
   claim (OD4 honesty gate).
2. **Generated items are good measurement instruments.** De-risk: the expert sign-off
   gate (no unapproved item served) + beta item-distribution monitoring (retire ≈0/≈1
   pass-rate items). This is why OD4 chose generate-*then-review*, not generate-and-trust.
3. **Day-one diagnostic doesn't depress activation.** De-risk: ≤10 Qs, gamified framing,
   fully skippable; watch onboarding completion in beta; shorten/defer if it bites.
4. **Deltas are actually positive & meaningful.** This is the real product test — if flat,
   that's a pedagogy finding the beta exists to surface. Better measured than assumed.

## Decisions (locked 2026-06-29, PM)

- **AD1 — item bank → ALL 3 English markets (GB/US/HK) at once**, target **≥2 approved
  items per (topic, difficulty_tier)** so re-checks draw fresh items (N3). Implication:
  the Unit-1 generation + expert-review pass runs for all three markets before the
  diagnostic is "live" per market — more up-front authoring/review, fuller coverage. The
  generation pipeline is per-(market, topic, difficulty), so the 3 markets parallelize.
- **AD2 — baseline-on-first-touch → FAST-FOLLOW after core A3.** Ship the core onboarding
  diagnostic (path + 3 core topics) first (Unit 3 core); add per-topic first-touch
  baselines immediately after as a separable sub-unit. Keeps the launch-critical A3 lean.
- **AD3 — per-concept scoring (Unit 5) → INCLUDE a thin version in A2.** Concepts are
  ~93% tagged, so start accruing per-`(user, concept, market)` rolling accuracy now;
  powers the Progress drill-down + sharper Revise. Keep it thin (rolling accuracy only;
  fancier modelling later).
- **AD4 — expert sign-off → OPERATOR approves for beta; named educator before any public
  claim / wide launch.** The admin review surface gates live items; record `approved_by`.
  A named-educator pass is a pre-launch gate, not a beta blocker.

## Sequencing (proposed)

1. **Unit 1** — `DiagnosticItem` + generation + expert-review admin (the instrument).
2. **Unit 2** — `MasteryCheckpoint` + diagnostic engine + endpoints (the measurement).
3. **Unit 3** — onboarding placement (A3) — **before beta cohorts.**
4. **Unit 4** — re-check trigger. **Unit 5** — per-concept scoring. **Unit 6** — evidence seam.

Migrations are additive. TDD on a branch; opus cross-model review (as on A1.x); per the
standing rule, **ask before any prod migration whether to snapshot.** Onboarding is
native-visible → `npm run build && npx cap sync ios` for the beta build.
