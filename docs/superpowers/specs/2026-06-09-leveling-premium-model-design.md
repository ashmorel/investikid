# Leveling + Premium-Tier Model — Design Spec

**Date:** 2026-06-09
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Context:** Keystone of a 4-part programme triggered by tester feedback ("completed Level 1, no Level 2 / how to progress"). Sibling pieces: **#1 Module UX clarity** (shipped, `8a75cd4`), **#3 AI-authored Level 2 pilot** (next), **#4 premium discoverability** (later brainstorm). This spec defines **#2** — the rules for how levels map to free vs premium.

## Goal
Codify a simple, consistent leveling/premium policy so authored content (and the upsell) has a predictable structure: **the first two levels of every module are free; the third level onward is premium**, derived automatically from level position.

## Decisions (from brainstorming)
1. **Structure:** every module targets **≥2 free levels** (Level 1, Level 2); a module **may** have one or more **premium levels (Level 3+)**, added as content is authored — premium depth is *variable* per module, not mandatory.
2. **Premium boundary = automatic by position:** a level at `order_index >= 2` (the 3rd level onward) is premium; `order_index` 0–1 (Level 1–2) are free. No per-level manual toggling.
3. **Naming:** generic **"Level N"** (matches ordering); no themed renames.

## Current state (verified)
- `app/models/content.py`: `Level` has `is_premium: bool`, `pass_threshold: float`, `content_source`, `icon`, `order_index`.
- `app/services/level_service.py`: `derive_level_states(...)` reads `LevelStateInput.is_premium`; a premium level for a non-premium user → `state="locked", locked_reason="premium"`. Progression: Level N+1 unlocks only when Level N is complete **and** avg score ≥ `pass_threshold` (free levels with no scored lessons pass on completion).
- `app/routers/content.py`: the public `GET /modules/{id}/levels` builds `LevelStateInput` from stored `Level.is_premium` and returns `LevelOut` (with `is_premium`, `state`, `locked_reason`).
- `app/routers/admin.py`: `AdminLevelCreate`/`AdminLevelUpdate`/`AdminLevelOut` + create/update endpoints let admins set `is_premium`, `pass_threshold`, etc. `generate_level_lessons` authors AI lessons into a level (used by #3).
- `app/seed/content.py`: creates a single `Level` per module — `title="Level 1", order_index=0, is_premium=False` — and inserts all lessons there. So today every module is one free level.
- Frontend: `LevelCard` already renders premium-locked levels and calls `openPaywall(...)` on tap; `Module.tsx` (post-#1) shows level/lesson progress + a "Module complete → next" CTA. **No FE change is required for this model** — the gate is already wired.

## The model (backend-only)
**Position is the source of truth for `is_premium`.** A level's premium status is fully determined by its `order_index`:

```
is_premium = (order_index >= 2)
```

Enforce this at every **write** site so the stored column never drifts from position:
1. **Admin create** (`AdminLevelCreate` path): ignore/override any client-supplied `is_premium`; set `is_premium = order_index >= 2`. (Keep `is_premium` out of the admin level **form** as an editable field — it's derived, shown read-only.)
2. **Admin update** (`AdminLevelUpdate` path): if `order_index` changes, recompute `is_premium`. Never let it be set independently of position.
3. **Reorder:** any endpoint/operation that changes a level's `order_index` recomputes `is_premium` for the affected levels.
4. **Seed:** when seeding/normalising levels, set `is_premium = order_index >= 2` (the current single "Level 1" stays free).

**Backfill:** a one-time, idempotent normalisation so existing rows match the rule — set `is_premium = (order_index >= 2)` for all `Level` rows. Implement as a hand-written Alembic **data migration** (chained off the current head; check `alembic heads` first), so it runs on each environment's DB on deploy (testing → staging → prod) per the standing migration flow. (No schema change — data only.)

**Defensive read (optional, low-cost):** when building `LevelStateInput` in the public levels endpoint, derive `is_premium = order_index >= 2` rather than trusting the stored flag, so a stray row can never mis-gate. Primary guarantee is enforce-on-write; this is belt-and-braces.

**No naming change**, no new columns, no FE change.

## Funnel behaviour (why this is the upsell point)
Because Level N+1 unlocks only after Level N is completed and passed, a child completes **two full free levels** before reaching the premium wall at **Level 3**. That earned moment is the natural hook for #4 (premium discoverability) — out of scope here but explicitly enabled.

## Testing
**Backend (pytest):**
- `is_premium` derivation: admin-create a level at order_index 0/1 → `is_premium False`; at order_index 2/3 → `True`, regardless of any `is_premium` value sent by the client.
- Admin-update that moves a level to order_index ≥ 2 flips it premium; moving back to ≤1 flips it free.
- A non-premium user calling `GET /modules/{id}/levels` on a module with a Level 3 sees that level `state="locked", locked_reason="premium"`; a premium user sees it unlocked (gated only by progression). (Reuse the existing levels-endpoint + premium-user test fixtures.)
- Seed/backfill: after normalisation, every `Level` row satisfies `is_premium == (order_index >= 2)`.
- Migration: `alembic upgrade head` then `downgrade` is clean; data migration is idempotent.

## Verification
Backend: `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest` + `alembic upgrade head`. Frontend: only if any FE touched (not expected) — `npx tsc -b && npm run lint && npm run test`. **STANDING RULE:** this introduces a data migration → when it reaches production promotion, ask about a DB snapshot first. No `cap sync`.

## Out of scope
Authoring the actual Level 2/3 lesson content (the **#3** AI pilot on "What is a stock"); premium-discovery UI (**#4**); themed level names; any change to the progression/`pass_threshold` rules; module-level premium gating (unchanged).
