# Limited-Edition Collectables — Core (B1) Design

**Status:** Design (approved in brainstorming 2026-06-24) — pending spec review.

**Goal:** Kids **earn** time-limited, rarity-tagged collectable cosmetics by hitting a goal during the drop's window. B1 delivers the engine end-to-end: the data model, a configurable grant engine, the child API, and a "Limited" shelf in Penny's Shop. Drops are authored via the code seed for now.

**Scope:** This is **B1 of three** sub-projects. **Out of scope here:** the admin drop-scheduler UI (B2) and the Home featured-drop card (B3).

## Decisions (from brainstorming)

- "Limited" = a **timed availability window** + a **rarity** label.
- Acquisition = **earned** (not bought) by meeting a per-drop **goal** during the window.
- Goal is shown as a **claimable goal with live progress** + countdown.
- Surfaced (B1) in a **"Limited" shelf in Penny's Shop** (Home card is B3).
- Items are **auto-granted** on meeting the goal — no manual "claim".

## Model (migration)

Add to `CosmeticItem` (migration chains off the current head):
- `available_from: datetime | None`, `available_until: datetime | None` — the drop window (UTC). Null = a normal always-available item.
- `rarity: str | None` — one of `common`/`rare`/`epic`/`legendary`; null for normal items.
- `unlock_type: str | None` — the goal kind (see engine); **null = a normal coin-buyable item**. NON-null = a limited, earned-only drop.
- `unlock_threshold: int | None` — the goal target (e.g. 7 for a 7-day streak).

**Discriminator:** an item is a **limited drop** iff `unlock_type IS NOT NULL`. A drop is **active** iff `unlock_type IS NOT NULL AND now ∈ [available_from, available_until]`.

`UserCosmetic` is unchanged — ownership of a collectable is the same `UserCosmetic(user_id, item_id, equipped=False)` row. Earned collectables equip through the existing equip flow (and stack/swap per the existing slot rules if they're accessories/skins).

## Grant engine (`backend/app/services/collectables_service.py`)

A registry mapping `unlock_type` → an evaluator that returns the child's **current progress** toward the goal (an int), given the drop's window:

- `streak_days` → `UserProgress.streak_count` (current streak; window-independent state).
- `window_xp` → Σ `Lesson.xp_reward` over `LessonCompletion` where `completed_at >= available_from` (XP earned since the drop opened).
- `window_lessons` → count of `LessonCompletion` where `completed_at >= available_from`.
- `window_arcade` → Σ `ArcadeScore.points` where `created_at >= available_from`.

The registry is the extension point: a future `event_completed` (seasonal-event) evaluator is added here without touching callers (deferred — the seasonal-event model isn't firmed; see Out of scope).

```python
async def progress_for(session, user, item) -> int      # current value for item.unlock_type
async def grant_eligible(session, user) -> list[str]     # grant any newly-met active drops; return granted slugs
```

`grant_eligible`: for each **active** drop the user does **not** already own, if `progress_for(...) >= unlock_threshold`, insert `UserCosmetic(user_id, item.id, equipped=False, unlocked_at=now())`. **Idempotent** (a `UserCosmetic` PK on (user_id, item_id) + an existence check prevents double-grant). Returns the slugs granted this call.

**Detection (two triggers):**
1. **At the `award_xp` seam** (`market_progress_service.award_xp`): after XP is persisted, call `grant_eligible` and return its result up the call chain. The existing reward-feedback surfaces (lesson-complete / quiz / revise, which already show XP/coin toasts) include `granted_collectables: [slug…]` so the child gets an **instant celebration toast**. This covers streak/xp/lessons/arcade goals the moment a learning action lands.
2. **Daily reconcile cron** `POST /internal/collectables/reconcile` (added to `_DEFAULT_EXEMPT_PATHS` in `csrf.py`, like the other `/internal/*` crons): sweeps active drops for all users with a streak/recent activity and grants any met — a safety net for streak-day rollovers and anything the seam missed. Idempotent.

## Child API (`backend/app/routers/collectables.py`)

- `GET /collectables` → `{ active: [DropOut], owned: [OwnedOut] }`
  - `DropOut { slug, name, emoji, type, rarity, ends_at, goal: { type, threshold, current }, earned: bool }` — every active drop, with the viewer's live `current` progress and whether they've earned it.
  - `OwnedOut { slug, name, emoji, type, rarity, equipped }` — the child's earned limited collection (so the shelf shows the collection even after windows close).
- Rate-limited like the other child read endpoints.

## Shop integration

- `_shop_state` (normal shelves) **excludes limited drops** (`unlock_type IS NOT NULL`) so earned-only items never appear in the coin-buy tabs.
- `POST /cosmetics/{id}/buy` **rejects** a limited item (`unlock_type` set) with `403 not_buyable` — collectables are earned, not bought.
- Frontend: a new **"Limited" shelf** in `Shop.tsx` (its own section, not a coin tab) driven by `GET /collectables`:
  - Active drops: rarity badge (colour per tier), a countdown to `ends_at`, and the goal as progress — "Earn the Golden Crown — reach a 7-day streak (3/7)". Earned drops show "Earned ✓ / Equip".
  - Owned limited collection below, each with its rarity badge; equip via the existing equip flow.

## Seed

`CATALOG` entries carry the new optional fields (normal items omit them). B1 seeds **one example active drop** (e.g. a `legendary` "Founder's Crown", `unlock_type=streak_days`, `unlock_threshold=7`, a window open now) so the earn-loop is testable end-to-end on deploy. Seed stays idempotent (upsert by slug, refreshing the new fields).

## Data flow

1. Child completes a lesson → `award_xp` persists XP → `grant_eligible` runs → if their streak/XP/etc. now meets an active drop, a `UserCosmetic` is inserted and the slug is returned → the lesson-complete response carries `granted_collectables` → the client toasts "You earned the Founder's Crown! ✨".
2. Child opens Shop → Limited shelf → `GET /collectables` shows active drops with live progress + countdown, and their earned collection.
3. Nightly `POST /internal/collectables/reconcile` grants any newly-eligible (e.g. a streak that ticked over at midnight).

## Error handling & edge cases

- Drop with a closed window → not active → not granted, not shown as active (owned ones still appear in the collection).
- Already-owned drop → skipped by `grant_eligible` (idempotent).
- `unlock_type` not in the registry → treated as never-eligible (defensive; logged once), never crashes a learning flow.
- Equipping an earned collectable accessory/skin obeys the existing slot rules (one hat at a time, etc.).
- A limited item must never be coin-buyable (buy endpoint guard + excluded from normal shelves).

## Testing

- **Engine:** each evaluator returns the right progress (streak from `streak_count`; window_xp/lessons/arcade counted only since `available_from`); `grant_eligible` grants exactly the met, active, un-owned drops and is idempotent (second call grants nothing); a closed-window drop is never granted.
- **Detection:** `award_xp` returns granted slugs when crossing a threshold; the reconcile endpoint grants eligible drops and is auth-gated/CSRF-exempt.
- **Shop:** normal shelves exclude limited items; buying a limited item → 403.
- **API:** `GET /collectables` returns active drops with correct `current`/`earned` and the owned collection.
- **Frontend:** Limited shelf renders active drops (badge + countdown + progress) and owned items; equip works; `vitest-axe`-clean.

## Out of scope (YAGNI / later sub-projects)

- **Admin drop-scheduler UI** → B2 (drops are seed-authored in B1).
- **Home featured-drop card** → B3.
- **`event_completed` / seasonal-event criterion** → added to the engine registry once the seasonal-event model is firmed (the four signal-based criteria ship in B1; the registry makes it a clean future addition).
- Trading, gifting, resale, or any real-money path (collectables are earned only).
