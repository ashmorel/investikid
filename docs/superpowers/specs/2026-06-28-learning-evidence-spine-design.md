# Learning-Evidence Spine — A1/A2/A3 design (Beta → 9.5 programme, Theme A)

**Date:** 2026-06-28
**Status:** Draft (design) — pending PM approval → spec review → implementation plan
**Scope:** A1 concept taxonomy · A2 pre/post concept checks · A3 onboarding diagnostic
(= the A2 pre-test). A4 (mastery-led parent report) and A5 (public evidence page) are
downstream consumers, sketched here but specced separately.

## Goal

Produce **credible evidence that children learn** from InvestiKid — the headline
*"mastery improved by X% after Y sessions"* — and use the same machinery to personalise
the day-one experience. This is the review's #1 path to 9.5 and the moat vs Zogo / FDIC
Money Smart. It is **not** more content; it is **measurement + a taxonomy to hang it on**.

## Context — what already exists (build on, don't replace)

- **9 fixed topics** (the de-facto top taxonomy): `Module.topic` /
  `TopicMastery.topic` ∈ `stocks, savings, real_estate, budgeting, risk, crypto, taxes,
  debt, entrepreneurship` (`frontend/src/api/content.ts`, `models/skill_profile.py`).
- **`TopicMastery`** (`models/skill_profile.py:19`) — `mastery_score =
  quizzes_correct / quizzes_attempted`, per `(user, topic, market)`. **Topic-level
  mastery already exists.**
- **Concepts are free-text, LLM-derived per lesson** — `_concept_of(lesson)` returns
  the lesson's `question`/`title` string (`revise_service.py:38`); stored as
  `WeakConcept.concept String(200)` only when a child answers wrong. **No normalized
  concept taxonomy; concepts are not scored, only flagged weak/resolved.**
- **SR engine (SM-2 lite)** on `SpacedRepetitionItem` keyed to `WeakConcept`
  (`spaced_repetition_service.py`) — the Revise loop.
- **`gap_detection_service.get_strengths_and_gaps()`** powers `/profile/strengths`
  (Progress page): per-topic `mastery_score` + `status` (`strong ≥0.8 / needs_practice
  / new`) + `weak_count` + `due_for_review`.
- **Parent Mastery Report** (`mastery_report_service.py`) is built off **`LevelMastery`**
  (immutable per-level pass) → learning objectives + **standards alignment**
  (`MaPS / CCSS` already on Level/Module). Level-mastery focused, **not concept-level**.
- **Onboarding** (`Signup.tsx`): DOB+country → email/username/currency/optional
  `topic_path` preference → `/home`. **No placement test. No baseline captured.**

**Conclusion:** we extend, not rebuild. We add a **normalized Concept layer between
Topic and Lesson**, give the diagnostic a home, and surface a per-concept mastery view.
Topic-level scoring + SR + standards alignment are reused as-is.

## Core design decisions

### D1 — Diagnose at TOPIC granularity; tag content at CONCEPT granularity
The scary failure mode is a 6-question quiz claiming per-concept mastery across 50
concepts — junk a teacher would dismiss. We avoid it by **separating the two jobs**:
- **Diagnostic (A2/A3)** measures the **9 topics** (or the subset on the child's path):
  ~1–2 calibrated questions per topic → a **topic-level baseline `mastery_score`**.
  Short (≤10 questions), credible, comparable pre/post.
- **Concept taxonomy (A1)** tags lessons/quizzes/missions to ~30–50 named concepts for
  the **learning loop** (Revise, gap detection) and the **report granularity that fills
  in over sessions** — not something the diagnostic tries to measure cold.

Per-concept mastery is *emergent from play*; topic mastery is *what we pre/post measure*.

### D2 — Concept taxonomy = a normalized table, seeded + curated, NOT LLM-free-text
Add a `Concept` table: `{id, topic (FK to the 9), slug, name, blurb, difficulty_tier
1–3, order}`. Seed ~30–50 (3–6 per topic). Add `Lesson.concept_id` (nullable FK) and a
`concept_slug` the LLM generator must emit + map to the taxonomy (fuzzy-match → admin
confirms unmapped). Existing free-text `WeakConcept.concept` strings keep working (back-
compat); a backfill maps the common ones. **The taxonomy is authored, finite, and
auditable** — that's what makes the evidence defensible.

### D3 — The onboarding diagnostic IS the pre-test (one build, three jobs)
A3 places a short diagnostic **after signup Step 2, before `/home`** (skippable, but
nudged). Its results: (a) **personalise** the path (seed `TopicMastery` so the child
starts where they are, set the first recommendation), (b) **first "aha"** ("Here's what
you already know 💡"), (c) **persist the A2 pre-test baseline**. **⏰ This is why A3 is
launch-critical: the pre-test must be captured on the child's first session or the
beta cohort's learning evidence is lost forever.** No second first-session.

### D4 — Pre/post is a stored snapshot, not a recomputation
Store an immutable `MasteryCheckpoint` row per child per checkpoint type
(`baseline` at onboarding; `progress` re-checks at session milestones). Each holds the
per-topic scores + overall at that moment + `session_count` + `taken_at`. The
**delta between `baseline` and the latest `progress`** is the evidence headline. Immutable
snapshots (like `LevelMastery`) keep the claim honest and auditable.

## Architecture (4 units)

### Unit 1 — `Concept` taxonomy (A1)
**Backend:** new `Concept` model + migration (additive table); `Lesson.concept_id`
nullable FK (additive col). A seed file (`seed_concepts.py`) with the curated 30–50.
Generator change: LLM emits `concept_slug`; a mapper resolves it to `concept_id`
(unmapped → admin review queue, lesson still publishes with `concept_id=NULL`).
**Admin:** a thin Concepts page (list/add/edit; reassign a lesson's concept). Reuses the
admin god-router split pattern (`admin_content`).
**Back-compat:** `_concept_of()` prefers `lesson.concept.name` when set, else the old
free-text path. `WeakConcept` keeps its string; a nullable `concept_id` is added and
backfilled best-effort.

### Unit 2 — Diagnostic engine + `MasteryCheckpoint` (A2)
**Backend:** `diagnostic_service` — builds a session of 1–2 questions per in-scope topic
(curated "diagnostic-flagged" lessons, NOT LLM-fresh, so pre/post use the *same*
calibrated items), scores it, writes a `MasteryCheckpoint`, and seeds/updates
`TopicMastery` from the result. New `MasteryCheckpoint` model + migration. Endpoints:
`POST /diagnostic/start`, `POST /diagnostic/submit` (→ checkpoint + per-topic results),
`GET /diagnostic/evidence` (baseline vs latest delta, for A4). Rate-limited; market-scoped.
**Question source:** add a `Lesson.is_diagnostic` flag (or a small curated `DiagnosticItem`
set) with an explicit `difficulty_tier` so items are stable and comparable. Authoring the
calibrated item bank is the real work here (operator + a generation pass, expert-reviewed).

### Unit 3 — Onboarding placement (A3)
**Frontend:** a post-signup `/onboarding/diagnostic` step (skippable) → renders the
diagnostic session (reuse the quiz components) → results screen ("Here's what you already
know" with per-topic chips) → `/home`. Writes the `baseline` checkpoint. A "skip"
still creates an empty baseline so the cohort is comparable (skippers = no-baseline bucket).
**Re-check trigger:** `progress` checkpoints fire at session-count milestones (e.g. 5 /
15 / 30 active days) — surfaced as a friendly "progress check" in the daily flow, reusing
the same item bank.

### Unit 4 — Surfacing (A4 seam, specced separately)
- **Parent report:** extend `mastery_report_service` with a **growth block** — baseline→
  now topic deltas ("Stocks 40%→75% ↑", standards touched, weakest topic + conversation
  prompt). Leads the subscription pitch. (A4 = its own spec; this unit just exposes the data.)
- **Child Progress page:** optional per-concept drill-down under each topic (taxonomy now
  exists), reusing `StrengthsGaps.tsx`.

## Mastery scoring model

- **Topic score** stays `correct/attempted` (reuse `TopicMastery`); diagnostic seeds it
  with the calibrated items so day-one isn't a cold 0.0.
- **Concept score (new, emergent):** per `(user, concept, market)` rolling accuracy over
  the last K attempts (cap to avoid ancient data dominating). Powers the report drill-down
  and smarter Revise targeting. Computed from quiz/Revise attempts as they happen.
- **Evidence headline:** `Δ = latest_progress.overall − baseline.overall`, plus per-topic
  deltas, with `session_count` for the "after Y sessions" half. Reported per child and
  aggregated across the beta cohort (segmented by the 8–10 / 11–13 / 15–18 bands).

## Non-goals (explicit)

- **Adaptive/IRT diagnostics** — fixed calibrated items first; adaptivity is a later bet.
- **Per-concept *diagnostic* measurement** — diagnostic stays topic-level (D1).
- **Replacing `LevelMastery`/standards** — they stay; the report *adds* a growth block.
- **A5 public evidence page** and **A4 full report redesign** — separate specs; this
  spine just produces the data they need.
- Changing the SR/Revise math.

## Riskiest assumptions & how we de-risk (cheap first)

1. **"A short topic-level diagnostic yields a credible baseline."** De-risk: pilot a 9-
   topic, ~10-question bank with the beta cohort; sanity-check that baseline correlates
   with later in-app performance before making any public/marketing claim.
2. **"The LLM generator can tag concepts to a fixed taxonomy reliably."** De-risk: ship
   the mapper with an admin confirm-unmapped queue; measure the auto-map hit-rate on the
   existing GB/US/HK corpus before trusting it.
3. **"Kids will complete a day-one diagnostic instead of bouncing."** De-risk: keep it
   ≤10 Qs, framed as a game ("let's see what you already know"), fully skippable; watch
   onboarding completion in the beta. If it depresses activation, shorten or defer to
   session 2.
4. **"Pre/post deltas will actually be positive and meaningful."** This is the real test
   of the product. If deltas are flat, that's a *content/pedagogy* finding the beta exists
   to surface — better to learn it from data than to assume.

## Decisions (locked 2026-06-28, PM)

- **OD1 — Diagnostic scope → chosen `topic_path` + 3 core topics** (budgeting / saving /
  risk). ~8–10 questions. Topics outside the set get their baseline lazily, captured the
  first time the child reaches that topic (a per-topic baseline-on-first-touch, not only
  at onboarding) — so the cohort comparison still holds per topic.
- **OD2 — Re-check cadence → session-count milestones** (5 / 15 / 30 active days).
- **OD3 — Skip policy → skippable**; skippers go into a `baseline=skipped` bucket (no
  scores) so the cohort stays segmentable. Don't tax activation.
- **OD4 — Item bank → generate-then-expert-review per market** (NOT hand-author-GB-first).
  **Implication (important):** an LLM-generated *measurement instrument* is only as
  credible as its calibration, so the build MUST include: (a) an explicit
  `difficulty_tier` + expert sign-off gate before an item is usable as diagnostic, (b)
  item-level answer-distribution monitoring in the beta (flag items everyone gets
  right/wrong — they measure nothing), and (c) **no public "mastery +X%" claim until the
  beta data shows baseline correlates with later in-app performance** (de-risk #1). This
  raises the bar on Unit 2's review/curation tooling vs the hand-authored path.

## Sequencing (proposed)

1. **A1 taxonomy** (table + seed + `Lesson.concept_id` + mapper + admin) — unblocks all.
2. **A2 diagnostic engine + `MasteryCheckpoint` + calibrated GB item bank** — the
   measurement core.
3. **A3 onboarding placement** (frontend) — **must land before beta cohorts start.**
4. **A4 report growth-block seam** — exposes the data (full report spec separate).

Migrations are additive (new tables + nullable cols) — but per the standing rule,
**ask before the prod migration whether to snapshot first.** TDD on `testing` →
gated promotion. Frontend onboarding step needs `npm run build && npx cap sync ios`
for the native beta build.
