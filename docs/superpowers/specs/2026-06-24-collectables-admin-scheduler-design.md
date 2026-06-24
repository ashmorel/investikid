# Collectables B2 — Admin Drop Scheduler — Design

**Status:** Approved design, ready for implementation planning
**Date:** 2026-06-24
**Sub-project:** B2 of the Limited-Edition Collectables programme (B1 engine LIVE in prod; B3 Home featured-drop card is a separate, later sub-project).

## Goal

Give an admin a console page to **schedule limited-edition collectable drops** — choosing which cosmetic drops, its rarity, its unlock rule, and its availability window — instead of drops being seed-only as in B1. The B1 grant engine, read paths, and child UI are unchanged; B2 only adds an authoring surface that writes the same `cosmetic_items` columns B1 already reads.

## Background (what B1 shipped)

A "drop" is a `CosmeticItem` row with the B1 limited-drop columns set:
- `available_from` / `available_until` (tz-datetime, nullable)
- `rarity` (str(12): `legendary` / `epic` / `rare` / `common`)
- `unlock_type` (str(20): one of the B1 evaluator registry keys)
- `unlock_threshold` (int)

B1 read paths that consume those columns (must stay working, untouched):
- `collectables_service.is_drop_active(item, now)` — **sync**, inclusive null-window bounds.
- `collectables_service.grant_eligible(session, progress)` — idempotent, savepoint-isolated, fired on the `award_xp` seam + the nightly `POST /internal/collectables/reconcile` cron.
- `GET /collectables` → `{active, owned}`.
- `cosmetics.py` shop filter: today `unlock_type IS NULL` (excludes drops from the buyable shop).

The B1 unlock-evaluator registry keys (the only valid `unlock_type` values): `streak_days`, `window_xp`, `window_lessons`, `window_arcade`.

## Core decisions (locked during brainstorming)

1. **Authoring model = schedule over a dev-supplied art pool.** Devs ship "drop-ready" cosmetic art (flat SVG in `Penny.tsx`); the admin controls *which* item drops, its rarity, unlock rule, and window. This guarantees a dropped accessory always has avatar art and never renders blank.
2. **Lifecycle = edit-while-scheduled, end-early, never destroy earned.** Freely edit a not-yet-started drop; once live, only the end-date is editable (end-early closes the window now); earned items stay in kids' lockers forever; no hard-delete of anything earned (the `CosmeticItem`/`UserCosmetic` cascade is never triggered).
3. **Data model = schedule in-place on `cosmetic_items` + a `drop_eligible` marker** (Approach A). One additive boolean column; zero changes to B1 read paths. (Rejected: a separate `collectable_drops` table — would force rewriting every B1 read; YAGNI.)
4. **Drops are global** (all markets) for B2. Cosmetics aren't market-scoped today; per-market drops are a future column. Out of scope here.

## Architecture

### Data model

One new column on `cosmetic_items`:

```
drop_eligible BOOLEAN NOT NULL DEFAULT false
```

Migration off head `c4d5e6f7a8b9` (additive, default false → backfills every existing row safely).

Item states (all on `cosmetic_items`, no new table):

| State | `drop_eligible` | `unlock_type` | Window | Visible where |
|---|---|---|---|---|
| Buyable shop item | false | NULL | — | Free/coin shop |
| **Pool item** (dev art, unscheduled) | true | NULL | none | **Nowhere** (inert) |
| **Scheduled / live / ended drop** | true | set | set | Limited shelf (B1), admin page |

**Shop filter tightens** in `cosmetics.py` `_shop_state`: from `unlock_type IS NULL` to `unlock_type IS NULL AND drop_eligible == false`, so unscheduled pool art never leaks into the buyable shop.

**Drop status** is computed (not stored), from the window vs. now (the `POST` always sets both bounds, so a scheduled drop always has a window):
- `scheduled` — `now < available_from`.
- `live` — `available_from <= now <= available_until`.
- `ended` — `now > available_until`.

### Backend API

New router `backend/app/routers/collectables_admin.py`, prefix `/admin/collectables`, `dependencies=[Depends(get_current_admin)]` (mirrors `arcade_words_admin.py`), registered in `main.py`. Logic in a thin `backend/app/services/collectables_admin_service.py`. Validation reuses the B1 evaluator registry (`collectables_service._EVALUATORS` keys) so an admin can only pick a real `unlock_type`.

| Method & path | Purpose |
|---|---|
| `GET /admin/collectables/pool` | List `drop_eligible` items **not currently scheduled** (`unlock_type IS NULL`) — the art available to drop. Each: `{item_id, slug, name, emoji, type}`. |
| `GET /admin/collectables` | List all scheduled/live/ended drops, each with computed `status` and `owned_count`. |
| `POST /admin/collectables` | Schedule a pool item. Body `{item_id, rarity, unlock_type, unlock_threshold, available_from, available_until}`. 404 if item not found; 400 if item not `drop_eligible` or already scheduled. |
| `PATCH /admin/collectables/{item_id}` | Edit. **Scheduled**: any field. **Live**: only `available_until` (end-early = set to ≤ now). Unlock rule frozen once live. |
| `POST /admin/collectables/{item_id}/unschedule` | Revert a **scheduled** (not started, **zero owners**) drop to a plain pool item — clears `unlock_type`/`unlock_threshold`/`rarity`/window. Blocked (409) once live or owned. |

**Server-enforced guardrails (not UI-only):**
- `unlock_type` ∈ B1 registry; `unlock_threshold` a positive int; `available_until > available_from` → else 422/400.
- No hard-delete endpoint exists — earned items can never be destroyed.
- A **live** drop rejects every change except `available_until` (so the unlock rule can't retroactively re-qualify kids mid-window).
- `owned_count` = a `UserCosmetic` count per drop, returned so the UI can warn before edits.

### Frontend admin UI

New page `frontend/src/components/admin/CollectablesAdmin.tsx`, lazy-routed at `/admin/collectables`, plus a **"Collectables"** `NavLink` in `AdminSidebar.tsx`. Client lib `frontend/src/api/adminCollectables.ts` (react-query hooks mirroring `useBadges`/`useCreateBadge`/`useUpdateBadge`). Copy in `frontend/src/locales/en/admin.json`.

One page, two zones (follows `ArcadeWordBank` + `BadgeForm` patterns):

- **Scheduled drops list** (top). Each row: Penny art preview, name, rarity badge (text label, not colour-only), unlock rule (e.g. "Streak ≥ 7"), window, a **status chip** (Scheduled / Live / Ended), and `owned_count`. Row actions by status:
  - *Scheduled* → Edit · Unschedule
  - *Live* → "End early" (`ConfirmDialog`, kid-visible action) · edit end-date
  - *Ended* → view-only
- **"Schedule a drop" form** (`BadgeForm`-style panel): pick a **pool item** from a dropdown (shows art + name; empty-state explains devs haven't shipped drop art yet) → set rarity, unlock type (the 4 registry options), threshold, from/until window → Save.

**Safety in UI:** End-early and Unschedule confirms display `owned_count` ("3 kids already earned this — they keep it"). Editing a live drop disables every field except end-date.

## Error handling

- All write endpoints validate server-side and return 4xx with a stable error string (`not_drop_eligible`, `already_scheduled`, `live_locked`, `owned_cannot_unschedule`, `bad_unlock_type`, `bad_window`) the UI maps to friendly copy.
- The shop-filter change is the only B1-touching edit; it is covered by a regression test asserting unscheduled pool items never appear in `GET /cosmetics`.

## Testing

**Backend** (`tests/test_collectables_admin.py`; async `client`/`admin_client`/`db_session` fixtures, `pytestmark = pytest.mark.asyncio(loop_scope="session")`):
- Schedule a pool item → appears in `GET /admin/collectables` as `scheduled`, leaves `GET /admin/collectables/pool`, and is **excluded from the buyable shop** (`GET /cosmetics`).
- Live-drop edit rejects unlock-rule changes (only `available_until` allowed); end-early closes the window but `UserCosmetic` rows survive.
- Unschedule blocked (409) once owned or live; allowed when scheduled + zero owners.
- Validation: bad `unlock_type`, non-positive threshold, inverted window → 422/400.
- Auth: non-admin → 401.
- B1 integration: schedule a drop, drive `award_xp` past the threshold → the item is granted (proves B2 output feeds the B1 engine unchanged).

**Frontend** (vitest + `vitest-axe`): list renders status chips; schedule form posts the correct body; live-drop form disables non-end-date fields; page is axe-clean.

## Seed & rollout

- **Seed:** mark the B1 `founders_crown` item `drop_eligible=true` so one pool item exists to demo immediately; keep its existing scheduled window so B1 doesn't regress.
- **Rollout:** beta → straight to main. The `drop_eligible` migration is additive (boolean default false); still ask about a prod snapshot at ship time (standing rule). `cap sync ios` to keep native current (admin is web-only).
- No new external services.

## Out of scope (future)

- Per-market drops (a future `market_code` column on the drop).
- Re-dropping the same art over multiple windows (Approach B's separate `collectable_drops` table).
- LLM-suggested drop ideas.
- Drop performance analytics.
- **B3 — Home featured-drop card** (separate sub-project).

## Files

**Backend**
- Modify: `backend/app/models/cosmetics.py` (add `drop_eligible`).
- Create: `backend/alembic/versions/<rev>_drop_eligible.py` (off `c4d5e6f7a8b9`).
- Create: `backend/app/routers/collectables_admin.py`.
- Create: `backend/app/services/collectables_admin_service.py`.
- Modify: `backend/app/routers/cosmetics.py` (shop filter `+ drop_eligible == false`).
- Modify: `backend/app/main.py` (register router).
- Modify: `backend/app/seed/cosmetics.py` (`founders_crown` → `drop_eligible=true`).
- Create: `backend/tests/test_collectables_admin.py`.

**Frontend**
- Create: `frontend/src/api/adminCollectables.ts`.
- Create: `frontend/src/components/admin/CollectablesAdmin.tsx`.
- Modify: `frontend/src/components/admin/AdminSidebar.tsx` (nav item).
- Modify: app route table (lazy route `/admin/collectables`).
- Modify: `frontend/src/locales/en/admin.json` (copy).
- Create: `frontend/src/components/admin/__tests__/CollectablesAdmin.test.tsx`.
