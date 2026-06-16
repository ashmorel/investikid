# Revision / spaced-repetition ("Revise") — design

**Date:** 2026-06-16
**Status:** Approved (design)
**Owner:** 💻 code
**Reuses:** the existing SR engine (`spaced_repetition_service`), weak-concept tracking
(`skill_profile`), quiz generation (`ai_content_service.generate_practice_quiz`),
and XP/streak (`xp_service.record_xp`). **No DB migration.**

## Problem

InvestiKid already has a spaced-repetition *engine* but no user-facing loop:
`SpacedRepetitionItem` + `WeakConcept` models, SM-2-lite scheduling
(`calculate_next_review`, `record_review`), `get_due_items` / `get_due_count`,
weak concepts auto-created when a child answers a practice quiz wrong, and
`due_count` already surfaced in the home greeting + Coach context. There is no
"Revise" surface that turns "you have N due items" into a session that resurfaces
concepts, records the result (advancing/resetting each SM-2 schedule), and rewards
the child. This feature builds that loop to improve retention and daily return
(a pre-beta stickiness item).

## Decisions (locked in brainstorming)

- **Scope: hybrid** — sessions lead with due *weak* concepts and top up with
  *mastered-concept refreshers*.
- **Question source: LLM-generated variants** via `generate_practice_quiz`
  (already cached in `GeneratedContent` and run through `moderate_output` + the
  guardrail preamble). Free users → standard tier (Llama); premium → gpt-4o-mini.
  Increases token usage (ties to the open "confirm OpenAI spend cap" item).
- **Session size: capped 5**, weak-first then refreshers (≤5 LLM calls/session,
  most served from cache).
- **Rewards: per-correct XP** (5) via `record_xp`, so revision **counts toward the
  daily goal and can keep a streak** (≤25 XP/session; coins follow 1:1 as today).
- **Availability: always-on (sub-decision B)** — Revise is offered whenever there
  is anything revisable (≥1 completed concept), not only when weak items are due,
  so a child who has mastered everything can still revise to keep a streak.
- **Two entry points:** a home-screen card (daily smart session) **and** a
  permanent Revise tab/hub (browse + pick a module to revise).
- **Architecture: stateless (Approach A)** — no server-side session row; the
  frontend walks the items and posts each answer. Per-answer recording makes an
  abandoned session safe.

## Architecture

```
Home card ─┐                              ┌─ GET  /revise/modules   (hub data)
           ├─→ Revise page (frontend) ──→ ├─ GET  /revise/session?module_id=…
Revise tab ┘   (walks ≤5 items)           └─ POST /revise/answer
                                                      │
        revise_service.build_session() / record_answer()
                                                      │
   get_due_items ─ record_review (SM-2) ─ generate_practice_quiz (cached+moderated) ─ record_xp
```

A new `app/services/revise_service.py` owns selection + answer handling. A small
router (`app/routers/revise.py`, or a `/revise` section in `ai.py`) exposes the
three endpoints. `generate_practice_quiz`, `record_review`, `record_xp`,
`get_due_items` are reused unchanged.

### Concept → lesson resolution

`WeakConcept` is keyed by `(user_id, topic, concept)` with **no `lesson_id`**.
`generate_practice_quiz` needs a `Lesson`. The service resolves a due weak concept
to its lesson by matching, within the concept's `topic`, a lesson whose derived
concept string (`content_json.question | title | prompt`, the same derivation the
practice flow uses) equals `WeakConcept.concept`. Concepts that cannot be resolved
to a lesson are **skipped** (logged, not surfaced). Refreshers start *from* completed
lessons, so their lesson is already known.

## Backend

### `revise_service.build_session(session, user, *, module_id=None) -> ReviseSession`

1. **Weak-first:** `get_due_items(session, user.id)` → their `WeakConcept`s
   (ordered by due-ness: `next_review_at` asc, then `times_wrong` desc). If
   `module_id` is set, keep only concepts whose resolved lesson is in that module.
   Resolve each to a lesson; drop unresolved.
2. **Refresher top-up (to 5):** completed lessons (in the child's topics, or in
   `module_id` when set) whose derived concept is **not** a current unresolved weak
   concept. Rotate for day-to-day variety (e.g. order by a stable per-day rotation
   over `completed_at`), take enough to reach 5 total.
3. For each selected concept, call `generate_practice_quiz(session, lesson,
   user=…, topic=…, concept=…, premium=is_premium(user))` (cache + moderation
   already inside). On generation failure for an item, skip it.
4. Return up to 5 items, **weak items first**, each:
   `{ ref, kind: "weak"|"refresher", module_id, lesson_id, concept, question,
   choices, answer_index, explanation }`. `ref` encodes enough to record the answer
   (`kind` + `topic` + `concept` + `lesson_id`; for weak, the `weak_concept_id`).

Empty result (nothing revisable) → empty session; the frontend shows an
encouraging empty state and the home card hides.

### `revise_service.record_answer(session, user, ref, selected_index) -> AnswerResult`

- `correct = selected_index == answer_index`.
- **weak** → `record_review(session, user.id, weak_concept_id, correct=correct)`
  (advances on correct, resets on wrong; existing SM-2).
- **refresher + wrong** → find-or-create a `WeakConcept` for `(user, topic,
  concept)` then `record_review(correct=False)` so a missed refresher re-enters the
  SR loop (symmetric with the practice flow). **refresher + correct** → no
  scheduling in v1.
- **on correct** → `record_xp(progress, 5)`; caller commits. Capture the
  `XpResult` (`goal_met_now`) for celebration.
- Return `{ correct, answer_index, explanation, xp_awarded, goal_met }`.

### `revise_service.list_revisable_modules(session, user) -> list[ReviseModule]`

Completed modules for the child, each with `{ module_id, title, icon,
due_weak_count, revisable: true }`. **Sorted weak-first** (modules with
`due_weak_count > 0` on top, by count desc). Drives the hub.

### Endpoints (`app/routers/revise.py`)

- `GET /revise/modules` → `list[ReviseModule]` (hub).
- `GET /revise/session?module_id=<uuid?>` → `ReviseSession` (≤5 items). Rate-limited
  (e.g. `@limiter.limit("20/hour")` — a session is one call; cache covers repeats).
- `POST /revise/answer` → body `{ ref, selected_index }` → `AnswerResult`.

All require `get_current_user`; premium tier flows through to `generate_practice_quiz`.

## Frontend

- **`revise.ts`** (TanStack Query): `getRevisableModules()`, `getSession(moduleId?)`,
  `postAnswer(ref, selectedIndex)`.
- **`ReviseCard`** (home): shown when there is anything revisable. Copy leads with
  the weak count when present — *"N concepts to practice"* (+ "and a refresher" when
  topped up) vs *"Keep your learning fresh"* when refresher-only. Tap → `/revise/session`
  (daily smart session, no `module_id`).
- **`Revise` hub page** (`/revise`, permanent nav entry): a "**Daily revise**" button
  at top (weak-first cross-module smart session) + a list of module cards from
  `/revise/modules`; modules with due weak concepts sort to the top with a distinct
  **"N to practice"** badge; mastered-only modules read as lower-weight "Refresh."
  Tapping a module → `/revise/session?module=<id>`. Encouraging empty state when
  nothing is revisable yet (no completed lessons).
- **`Revise` session page**: fetch the session, present each question **one at a
  time** reusing the existing quiz question UI; **each question badged "Needs
  practice" (weak) vs "Quick refresher" (mastered)**; post each answer, show
  correct/explanation + XP feedback; end on a summary (X/5 correct, XP earned,
  "🔥 streak kept!" when `goal_met`). Weak items are always presented first.
- **A11y (WCAG 2.2 AA):** keyboard operable, visible focus, `aria-live` for
  correct/incorrect feedback, options as real buttons/radios, touch targets ≥16px
  (no `maximum-scale`). vitest-axe on the hub, card, and session page.

## Weak-prominence (explicit)

1. Weak concepts ordered first in **every** session. 2. Per-question "Needs
practice" vs "Quick refresher" badge. 3. Hub sorts weak modules to top + "N to
practice" badge. 4. Home-card copy leads with the weak count. 5. "Daily revise" is
the weak-first cross-module path, so weak items are never buried regardless of how
the child browses. Module sessions stay scoped to the chosen module (no surprise
cross-module items).

## Rewards, safety, edge cases

- ≤25 XP/session (5×5), via `record_xp` → daily goal + streak; coins 1:1.
- Safety: questions come from `generate_practice_quiz`, which already runs
  `moderate_output` + the guardrail preamble — no new LLM surface to harden.
- Edge cases: unresolved concept→lesson skipped; per-item generation failure
  skipped (session may be <5); empty session → encouraging state + card hidden;
  rate-limit → friendly retry message; abandon-safe (per-answer recording);
  brand-new child with 0 completed lessons → hub empty state, no card.

## Out of scope (v1)

- Multi-module selection in one session (single module per session; "Daily revise"
  covers cross-module). Easy future add.
- A dedicated server-side `ReviseSession` row / cross-device resume (Approach B).
- Full SM-2 scheduling for *correct* answers on mastered concepts (refreshers use a
  lightweight rotation selector, not per-concept scheduling). A future enhancement
  if data shows it's needed.
- Swapping question source between stored vs LLM per tier (we chose LLM; the cache
  already makes repeats cheap).

## Testing

- **Backend** (`tests/`): `build_session` weak-first ordering + refresher top-up to
  cap 5 + `module_id` filter + unresolved-concept skip; `record_answer` SM-2 advance
  (correct) / reset (wrong) + XP+goal on correct + **wrong-refresher creates a weak
  concept**; `list_revisable_modules` weak-first sort + due counts; endpoints
  (auth, rate-limit, premium tier). Use the `client`/`db_session` fixtures +
  `pytest.mark.asyncio(loop_scope="session")`; patch the LLM client.
- **Frontend** (vitest + **vitest-axe**): `ReviseCard` copy variants + hidden when
  nothing due; hub sort/badges + empty state; session page one-at-a-time flow,
  weak/refresher badges, correct/XP feedback, summary; axe on hub/card/session.

## Rollback

All additive (new service/router/endpoints + new frontend pages/card/nav entry).
Hiding the nav entry + home card disables the feature; the reused engine is
untouched. No migration to revert.
