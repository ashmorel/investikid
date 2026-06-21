# Lesson Depth → 10 / 15 / 20 Per Level — Design

**Date:** 2026-06-21
**Status:** Approved (brainstorm)
**Branch/flow:** `main` (beta straight-to-main)

## Problem
Each level currently has only ~3 lessons — too light. Today `lessons-per-level ==
concepts-per-level` (1:1): `generate_native_level_lessons` makes exactly one lesson per
concept (alternating card → quiz), and the designer emits ~3 concepts per level.

## Goal
Richer levels on a deepening curve: **tier 1 → 10, tier 2 → 15, tier 3 → 20** lessons per
level, generated with quality (not 20 thin one-off topics).

## Decision (locked)
- Counts **10 / 15 / 20** per tier (1/2/3).
- **Blended** generation: keep a sane set of concepts per level; produce a **teach-card +
  practice-quiz per concept** to reach the target — volume + a natural card/quiz rhythm,
  no filler.

## Engine changes (this spec) vs content (operator, later)
This spec changes the **generation engine** only. Applying it to live GB content is an
operator run afterwards: re-design GB's curriculum → regenerate (Opus pipeline) → review →
approve-replace.

## Config
`LESSONS_PER_TIER = {1: 10, 2: 15, 3: 20}` — a module-level constant in
`app/services/admin_content_generation_service.py` (single source of truth; no env knob
needed). Helper `target_lessons_for_tier(tier: int) -> int` defaulting to the tier-2 value
for any unexpected tier.

## Generator — `generate_native_level_lessons`
(`app/services/admin_content_generation_service.py`)
- Compute `target = target_lessons_for_tier(complexity_tier)`.
- Produce **exactly `target`** lessons by round-robin over `(concept, lesson_type)` pairs,
  `lesson_type` cycling `["card", "quiz"]`:
  - order: concept0-card, concept0-quiz, concept1-card, concept1-quiz, … stop at `target`.
  - so each concept yields a teach-card + practice-quiz (~2 lessons/concept); an odd target
    (15) leaves the last concept with just a card.
- Requires `>= ceil(target / 2)` concepts to avoid reusing a concept >2×. The designer is
  asked for that many (below); if a level comes back short, the generator wraps concepts
  (logged) rather than failing — never produces fewer than `target` while concepts exist,
  and never more.
- Per-lesson failures stay isolated (existing per-concept handling); the level still
  yields as many of `target` as succeed.

## Designer — `app/services/market_curriculum/designer.py`
- Prompt instructs concept counts per tier: **tier 1 → 5, tier 2 → 8, tier 3 → 10**
  concepts per level (≈ `ceil(target/2)`), each a distinct sub-idea, still spiral-deepening.
- **Token-budget risk:** the whole-tree JSON is now much larger (up to 10 concepts × 3
  levels × 9 modules). The designer call's `max_tokens` (currently 4000) will truncate.
  Fix: raise the designer `max_tokens` to a safe ceiling for the authoring (Opus) model
  (e.g. 16000), OR design per-module and stitch. Plan picks one; **raise max_tokens** is
  the default (Opus supports it; simplest).

## Compatibility
- Concision rules (45–65 words/card, reading-age guidance) are unchanged and apply
  per-lesson — more lessons, each still short.
- Lesson types stay `card` + `quiz` (no new types — YAGNI).
- The native-batch / draft-review / approve-replace flow is unchanged; it just produces
  more drafts per level.

## Testing
- `target_lessons_for_tier`: 1→10, 2→15, 3→20, fallback for other input.
- `generate_native_level_lessons` (mocked `_generate_one`): with tier 3 + ≥10 concepts,
  creates exactly 20 lessons alternating card/quiz; tier 1 → 10; an odd target (15) ends on
  a card; too-few concepts → wraps to still hit the target (and logs).
- Designer prompt asserts the per-tier concept-count instruction is present.
- Regression: existing native-batch test updated for the new per-level counts.

## Out of scope
New lesson types (video/sim); per-market count overrides; auto-regenerating live content
(operator-run). Backfilling counts onto already-published lessons happens via the normal
regenerate → approve-replace flow, not a migration.
