# Live-Market Regeneration (staged build + atomic swap) — Design Spec

**Date:** 2026-06-21
**Status:** Draft for review
**Owner:** Lee Ashmore

## Goal

Let an operator regenerate the curriculum of an **already-live market** (today: GB/UK) through the per-market curriculum engine, without kids ever seeing half-built content. The new curriculum is designed and generated **invisibly**, reviewed, then **swapped live in one atomic step** that retires the previous modules. Reversible.

## Background / problem

The per-market curriculum engine (live 2026-06-21) designs a fresh, independent curriculum per market and materialises it on **Accept**. That works for the 9 *empty* markets because the market itself is gated by `markets.has_content` until publish. **GB is different:** it is already live (`has_content = true`, 15 hand-authored modules, real learners), so:

1. The Market Content admin UI **hides** the Brief + Curriculum panel for GB (`code !== 'GB'` gate in `MarketContent.tsx`) — there is literally no "regenerate UK" affordance; selecting GB shows only a static "GB is the source" note.
2. Even if un-gated, `accept_proposal` creates **live** `Module` rows immediately (no module-level visibility flag exists), so a regenerated GB curriculum would appear to kids as empty modules alongside the existing 15, and "live UK stays untouched until approved" would not hold.

GB also has **no `MarketBrief`** (the brief UI was GB-excluded too), which the designer needs to ground UK facts.

## Decisions (confirmed in brainstorming)

- **Approach:** design a brand-new **independent** UK curriculum (not a refresh-in-place of the existing modules).
- **Staging mechanism:** a per-module `published` flag — new modules are built invisible, swapped live atomically.
- **On publish:** the staged new modules go live and the previously-live modules are **soft-retired** (`published = false`, rows kept) in one transaction — reversible.
- **Progress:** global XP / coins / level / streak (which live on the user) are untouched; per-module/level **completion** on the retired curriculum is left behind (no meaningful mapping between two independent curricula), so learners start the new curriculum fresh.
- **Known caveat (recorded):** this path resets module-level progress for everyone in the market — acceptable in beta (34 completions), a real consideration for post-launch UK regeneration.

## Architecture

Four units.

### 1. `Module.published` flag + child-visibility sweep
- New column `Module.published` (`bool`, `NOT NULL`, `server_default true`). Existing rows (the 15 GB + all others) backfill to `true` via the server default. Seed content (`content.py`) and admin module CRUD create `published = true` by default.
- **Single visibility predicate** in `content_service.py`:
  `is_module_visible(module, active_market_code) -> bool` = `module.published and is_module_in_market(module.market_code, active_market_code)`.
- Apply it at **every child-facing module read path** (the highest-risk part — same "sweep every feeder" lesson as the C1/C2 market gating; missing one leaks a half-built module or keeps retired content visible). The feeders, all of which currently gate via `is_module_in_market`:
  - `content_service.py` (child module list + module detail)
  - `next_lesson_service.py`
  - `recommendation_service.py` (all three `select(Module)` sites)
  - `revise_service.py` and `spaced_repetition_service.py` (so retired content drops out of Revise)
  - `skill_profile_service.py`
  - `market_progress_service.py` (per-market progress / `is_market_complete` count only published modules)
  - `coach_service.py` (module context)
- **Admin paths keep seeing all modules** (must review staged content): `admin.py`, `admin_content_generation_service.py`, `market_scaffold_service.py`, `market_module_suggester.py`, `proposal_service.py`. These do **not** get the filter.
- A **coverage meta-test** asserts every child feeder that selects `Module` applies the visibility predicate (enumerated list), so a future feeder can't silently skip it.

### 2. Engine stages instead of going live
- `accept_proposal` creates its `Module` rows with `published = false`. Everything downstream (generate-native batch, inline draft review/approve) already operates by module/level id, unaffected by the flag.
- `accept_proposal` additionally records each created **module id** onto its module node in `proposal_json` (it already records level ids), so the publish step knows exactly which modules are "the staged new curriculum."

### 3. Atomic swap — `publish_market_curriculum`
- `publish_market_curriculum(session, market_code) -> {published: int, retired: int}` in `proposal_service.py` (or a sibling `curriculum_publish_service.py`):
  1. Load the market's active **accepted** proposal; resolve its staged module ids from `proposal_json`.
  2. **Guard:** every staged module must have ≥1 **published `Lesson`** (not just drafts) — else raise → 409 (never blank out the market).
  3. In one transaction: set the staged modules `published = true`; set **all other currently-published modules** for that market `published = false` (soft-retire); set `markets.has_content = true`; mark the proposal `status = "published"`.
- Reversible: because retire is a flag flip with rows intact, a later regeneration (or a manual flag flip) restores the prior set. No dedicated rollback UI in v1 (YAGNI; the data supports it).

### 4. UI — un-gate live markets
- In `MarketContent.tsx`, render the **Brief** section + **`CurriculumPanel`** for any selected market **including** `has_content` markets (GB). Keep the **scaffold-from-GB** step and the **module-suggestions** section hidden for GB (meaningless for the source market).
- Replace the static `gbNote` wall with the live flow.
- Add a **"Publish curriculum — replaces live content"** action (calls `publish_market_curriculum`) with a **confirm dialog** stating *"N new modules go live, M current modules retire — this cannot be auto-undone."* Gated/disabled until the staged modules have published lessons.
- Operator still must **generate + verify a GB brief first** (GB has none) — the existing brief UI, now visible for GB, handles this.

## Data flow

```
(GB) generate + verify MarketBrief        ← brief UI now visible for GB
   → design curriculum → accept            ← creates modules published=false (invisible)
   → generate-native batch → review drafts inline → approve (publishes Lessons)
   → Publish curriculum (atomic swap):     ← staged modules published=true,
        old live modules published=false      old 15 retired, has_content stays true
   → kids now see the new UK curriculum; global XP/coins/level/streak intact
```

## API endpoints (admin)

- `POST /admin/markets/{market_code}/curriculum/publish` → `publish_market_curriculum`; 409 if no accepted proposal or staged modules lack published lessons. (Admin-auth; not LLM, so not rate-limited.)
- Existing design/get/accept/generate-native-batch endpoints unchanged.
- The existing `POST /admin/markets/{code}/publish|unpublish` (E2 `has_content` flip) is left intact for the legacy empty-market path.

## Error handling

- Publish with no accepted proposal → 409 "no curriculum to publish".
- Publish where a staged module has zero published lessons → 409 "review and approve lessons first" (prevents blanking the market).
- The swap is one transaction — partial failure rolls back, leaving the live curriculum untouched.
- Designer/brief failures behave as today (502 / 409 unverified-brief).

## Testing

- `Module.published` migration backfills existing → true; model default true.
- `is_module_visible`: false when unpublished even if in-market; false when published but wrong market.
- **Feeder sweep:** for each child feeder, an unpublished module is excluded (and a meta-test enumerating child `select(Module)` sites asserts the predicate is applied); admin list still includes unpublished.
- `accept_proposal` creates modules `published = false` and records module ids in `proposal_json`.
- `publish_market_curriculum`: publishes staged + retires previously-live in one commit; 409 when a staged module has no published lessons; idempotency / re-publish behaviour.
- Endpoint: publish happy path returns `{published, retired}`; 409 paths.
- Frontend: GB now renders Brief + CurriculumPanel (not the gbNote wall); scaffold/suggestions hidden for GB; publish-curriculum confirm dialog; vitest-axe on changed UI.
- Regression: empty-market flow (scaffold/has_content publish) and existing child content behaviour unchanged for already-published modules.

## Rollout

1. Ship the `Module.published` migration + feeder sweep + staging + swap + UI (behind no flag; inert until used — all existing modules are `published = true`, so child behaviour is byte-identical).
2. Operator runs the **UK regeneration** with you: GB brief → design → accept → generate → review → **Publish curriculum** → verify kids see the new UK content and the old 15 are retired.

## Out of scope (YAGNI)

- A dedicated rollback/restore UI (data supports a manual flip; not building a button yet).
- Migrating old completion/progress onto the new curriculum (no meaningful mapping; global stats preserved).
- Re-using `published` to add per-module scheduling/visibility windows.
- Changing the empty-market (`has_content`) publish path.

## Open questions

None — approach (independent UK curriculum), staging (`Module.published`), swap (atomic + soft-retire), and progress semantics are all confirmed.
