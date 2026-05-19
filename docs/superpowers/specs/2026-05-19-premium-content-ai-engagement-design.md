# Premium Content & AI Engagement — Design Spec (Sub-project 4b)

**Status:** Delivered — 2026-05-19 (sub-project 4b)
**Programme:** Invest-Ed hardening, sub-project 4b (follows 4a kid-safe moderation, LLM-03 closed)
**Working dir:** `/Users/leeashmore/Local Repo/invest-ed`

## Goal

Make AI-generated learning content non-repetitive and difficulty-adaptive, turn the
currently-dead `topic_path` field into a self-declared starting-interest signal, and
give the premium tier genuinely deeper content — without adding new behavioural data
about children and without weakening the AADC off-by-default profiling stance.

## Context (verified against code)

- `User.topic_path` — `String(20)`, nullable, set at signup (`auth.py:147`) and
  `PATCH /users/me` (`users.py:55-56`), exported (`export_service.py:25`), **consumed
  nowhere**. Currently unvalidated free text.
- `Module.is_premium` (bool) gates module access via
  `content_service.is_module_accessible()`; router 403 in `content.py:50-54`.
- `GeneratedContent` caches AI quizzes, unique `(lesson_id, concept, model_used)` —
  so the first generated quiz is **frozen forever** (the real staleness bug).
- `ai_content_service.generate_practice_quiz(session, lesson, *, topic, concept,
  premium, wrong_answer_index=None)` — cache lookup → prompt → LLM → validate →
  `moderate_output(surface="quiz")` (4a) → cache+return; deterministic `_fallback()`
  on failure.
- `User.profiling_enabled` — bool, `server_default false`, default opt-out (AADC).
  Only consumer: `recommendation_service` returns `{next_quest:None,
  suggested_modules:[]}` when false.
- `recommendation_service` — profiling-gated 4-factor scorer; `TOPIC_PREREQUISITES`
  + `TopicMastery` (threshold 0.5).
- `ModuleTopic` literal (`schemas/content.py:7-10`): `stocks, savings, real_estate,
  budgeting, risk, crypto, taxes, debt, entrepreneurship`.
- Frontend: `Lessons.tsx`/`Home.tsx` render server-computed module list +
  `locked`; `ModuleCard.tsx` shows the premium lock. Content via `contentApi`
  (`src/api/content.ts`).
- 4a moderation seam wraps every child-facing LLM surface; backend suite 302 green.

## Chosen approach

**Approach A** — extend the existing cache with a `variant_key`; derive variant
rotation and difficulty from data the app already stores (`LessonCompletion`,
`TopicMastery`); no new per-child table. One migration. The 4a moderation seam is
reused unchanged.

---

## Section 1 — Architecture & data model

**New unit:** `app/services/content_variety_service.py`. Single decision point:
`resolve_variant(session, user, lesson, concept) -> VariantSpec` where
`VariantSpec = (rung: str, ordinal: int, pool_size: int)`. DB reads only; no LLM
calls, no mutation. `ai_content_service.generate_practice_quiz` calls it to obtain
a `variant_key` *before* its existing cache lookup. Everything downstream (prompt,
LLM, 4a `moderate_output`, `_fallback`) is unchanged in behaviour.

**Migration (one):**
- `GeneratedContent` unique constraint → `(lesson_id, concept, model_used,
  variant_key)`. New column `variant_key: str` (`String(16)`, NOT NULL).
- `variant_key` format: `"{rung}:{ordinal}"`, `rung ∈ {easier, core, harder}`,
  `ordinal` small int.
- Backfill: existing rows → `variant_key = "core:0"` so 4a/quiz behaviour for
  already-cached content is preserved exactly.
- **No new per-child table.** Rotation/difficulty derive from existing
  `LessonCompletion` rows and `TopicMastery`.

**Pool bound:** `MAX_ORDINALS_PER_RUNG = 3` (module constant). Pool exhausted →
serve a random already-cached safe variant for that concept (no new LLM call).
Generation/validation/moderation failure → existing deterministic `_fallback()`.

## Section 2 — Variant selection logic & AADC gating

`resolve_variant` computes:

**Rung:**
- `profiling_enabled = False` (default) → rung is always `core`. The child's score
  signal is **not read** (no `LessonCompletion.score` / `TopicMastery` query on this
  path). Deterministic.
- `profiling_enabled = True` → from the child's most recent `LessonCompletion.score`
  for this lesson:
  - no prior attempt → `core`
  - last score `< 0.5` → `easier`
  - last score `>= 0.8` AND `TopicMastery(topic) >= 0.5` → `harder`
  - otherwise → `core`

**Ordinal (rotation; tier-independent, profiling-independent):**
`attempt_count = count(LessonCompletion for this user+lesson)`;
`ordinal = attempt_count % pool_size`. Uses only the child's own completion count
(not behavioural inference), so it runs regardless of `profiling_enabled`. Purpose:
avoid showing the identical quiz back-to-back.

**Tier gating (premium depth):**
- **Free:** `pool_size = 1`; rung forced to `core` (laddering disabled). Net effect
  = one `core` quiz per concept — status quo preserved, no extra LLM cost.
- **Premium:** `pool_size = 3`; all three rungs available; on a `harder`-rung
  mastery hit, a fresh variant is generated when that pool slot is empty.

**Fallback chain (fail-safe, mirrors 4a):**
1. Requested `variant_key` cached → serve it.
2. Not cached & within tier pool budget → generate → 4a `moderate_output` (as today).
3. Pool exhausted OR generation/moderation fails → random cached *safe* variant for
   that `(lesson, concept)`.
4. Nothing cached at all → existing deterministic `_fallback()`.

A child never sees an error or an empty quiz.

## Section 3 — `topic_path` starting-interest ordering

**Validation:** `topic_path` constrained to `ModuleTopic ∪ {null/empty}` at the
schema layer (signup + `PATCH /users/me`). Invalid → 422. No DB migration (column
unchanged; validation only). This is **self-declared**, therefore not profiling —
all effects below run even when `profiling_enabled = False`.

**Effects:**
- `GET /modules`: when `topic_path` set, accessible module list is **stably
  reordered** so `module.topic == topic_path` sorts first; remaining modules keep
  their existing `order_index` order. `is_module_accessible` / locked / premium
  state unchanged — presentation order only.
- "Next quest" seed: when `profiling_enabled = False` AND `topic_path` set AND the
  child has zero completions, `recommendation_service` returns `next_quest` = first
  incomplete lesson in the preferred topic (instead of `None`). Any completion, or
  `profiling_enabled = True`, hands over to the existing logic — the profiling-on
  code path is unchanged.

## Section 4 — API / frontend surface, error handling, testing

**API (backward-compatible):**
- `GET /modules` — same shape; ordering only changes when `topic_path` set.
- Quiz path (`/ai/practice-quiz` and lesson quiz) — unchanged signature; internally
  routes through `resolve_variant`. Response gains optional `variant_rung` so the UI
  can label rounds; free tier always `core`.
- `PATCH /users/me` / signup — `topic_path` validated; invalid → 422.

**Frontend (thin):**
- One-time interest picker (9 topics + "No preference") at signup, editable in
  profile. Reuse existing profile form + a chip selector; no new page/route.
- `Lessons.tsx` / `Home.tsx` consume the already-reordered list as-is (no client
  sort). Optional small "Challenge" / "Warm-up" badge when `variant_rung != core`.
- `ModuleCard` lock/premium UI unchanged.

**Error handling:** all content failures resolve via the Section-2 fallback chain
(silent degrade to cached or deterministic content). The only new user-visible
error is `topic_path` 422 at the API boundary — never reaches a child surface. No
new child-facing error states.

**Testing:**
- `content_variety_service` unit: rung matrix (profiling on/off × no-attempt / low /
  high score × free / premium), ordinal rotation, pool-exhaustion → random-cached,
  full fallback → `_fallback()`.
- AADC regression: `profiling_enabled = False` ⇒ rung always `core` AND no score /
  mastery query issued on that path (assert via spy / query count).
- `topic_path`: validation (valid / invalid / null), stable module reorder,
  profiling-off first-quest seed, profiling-on path unchanged.
- Premium gating: free = single `core`; premium = 3 rungs + fresh-on-mastery.
- 4a integration intact: every generated variant still passes `moderate_output`;
  full backend suite stays green (baseline 302).

## Out of scope

- Stripe / payments (deferred to programme end).
- Inferential recommendation changes beyond the profiling-off first-quest seed.
- New authored module *content* beyond marking a small number of existing seeded
  modules `is_premium=True` for breadth (exact set decided in the plan).
- Accessibility (sub-project 5) and mobile-first (sub-project 6).
- Input-side prompt-injection hardening (LLM-01, separate register item).
