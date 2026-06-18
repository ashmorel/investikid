# Multi-Market Backend — Design Spec (Sub-project C2a)

**Date:** 2026-06-18
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project C, part 2a of 2)

---

## Programme context

Predecessors live in prod: **0** Gemini lineup, **A** i18n, **B** AI-language, **C1** market foundation (the `Market` entity keyed by ISO code, `modules.market_code`, `users.home_market_code` — all on GB; content gated by home market across the content router, next-lesson, and recommendation paths).

Sub-project **C** (per-market progress + multi-market experience) is split:
- **C2a (this spec) — Multi-market backend (invisible):** per-market XP, an active-market concept, lazy enrollment, market-tagged Revise records, and the APIs. Invisible — active market defaults to home (GB), global engagement unchanged.
- **C2b — Multi-market frontend (later spec):** market picker (all 10, content vs "coming soon"), switcher, per-market home/stats, the coming-soon screen.

**Locked decisions (from the C/C2 brainstorm):**
- **Progress split:** learning is **per-market** (XP, lesson completions, Revise weak-concepts); engagement is **global** (one level from total XP, daily streak, coin wallet, daily goal, daily caps).
- **Progress model = Approach 1 (additive layer):** keep `UserProgress` as the global row (streak, coins, goal, caps, **global total XP**, level); add a `UserMarketProgress` table for per-market XP; tag Revise records with a market. One award seam keeps the global total and the per-market sum consistent (invariant test).
- **Empty markets = show all as "coming soon"** (C2b concern): all 10 markets are enrollable; markets with `has_content=false` will show a friendly coming-soon state. C2a exposes `has_content` and allows switching to any active market.
- **Active vs home:** `home_market_code` stays the registration-derived primary; new `active_market_code` is the switchable "currently studying" market (defaults to home) and drives content filtering.
- **Lazy enrollment:** switching to a market auto-creates its `UserMarketProgress` row (no separate enroll step).
- **Currency-follows-market deferred:** `user.currency_code` is untouched; the active market's currency *display* is a later follow-up.

## Goal

Track XP per market alongside the unchanged global total, add an active-market concept with lazy enrollment, tag Revise records by market, and expose the market/enrollment/progress APIs — with **zero behavior change** for current (GB) users (active defaults to home=GB; global engagement unchanged).

## Non-goals (deferred)

- Frontend (C2b). No UI in C2a.
- Currency-follows-active-market (later follow-up).
- Cross-market rewards (Sub-project D).
- Un-enroll / leave-market (switching active is enough; leaving deferred).
- Per-market streak/coins/goal/caps — these stay **global** on `UserProgress`.
- Changes to `LessonCompletion` — completions are already per-market via `module.market_code` (queryable by join); no new column.

---

## Architecture

### Unit 1 — `UserMarketProgress` model

New table; **presence of a row = the user is enrolled in that market**.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK (composite), FK `users.id` ON DELETE CASCADE | |
| `market_code` | String(2) PK (composite), FK `markets.code` | |
| `xp` | Integer, not-null, default 0 | per-market XP |
| `created_at` | timestamptz, not-null, default now | enrollment time |

Composite primary key `(user_id, market_code)`. Index on `user_id` (list a user's markets).

### Unit 2 — `User.active_market_code`

Add `active_market_code: Mapped[str]` — `String(2)`, FK `markets.code`, not-null, `server_default="GB"`. The currently-selected market for browsing/learning. (`home_market_code` from C1 remains the primary/default.)

### Unit 3 — `WeakConcept.market_code`

Add `market_code: Mapped[str]` — `String(2)`, FK `markets.code`, not-null, `default="GB"`, `server_default="GB"`, indexed. Revise weak-concepts become per-market; `SpacedRepetitionItem` inherits the market via its FK to `WeakConcept` (no column added to SR). Revise session-building and `record_answer` filter weak-concepts by the active market.

### Unit 4 — The XP award seam

New service function (e.g. in `app/services/xp_service.py` or a small `market_progress_service.py`):

```python
async def award_xp(session, user, progress, amount, *, today=None) -> XpResult:
    result = record_xp(progress, amount, today=today)        # global total + level + goal (unchanged)
    await _add_market_xp(session, user.id, user.active_market_code, amount)  # upsert UserMarketProgress
    return result
```

- `_add_market_xp` upserts the `(user_id, active_market_code)` row (`INSERT ... ON CONFLICT DO UPDATE xp = xp + amount`, or fetch-or-create then increment) — this also performs **lazy enrollment** (a row appears the first time XP is earned in a market).
- Route ALL **5** existing `record_xp(...)` award sites through `award_xp(...)`: `routers/content.py:439` (lesson completion), `services/revise_service.py:230`, `services/simulator_rewards.py:37` and `:128`, `services/gamification_service.py:174`. Each passes the user (whose `active_market_code` determines the market). Non-award readers of `UserProgress` are unchanged.
- `record_xp` itself stays as-is (still the global mutator) so any path not yet migrated still works; `award_xp` is the canonical seam going forward.

**Invariant:** for any user, `sum(UserMarketProgress.xp) == UserProgress.xp`. Enforced by funnelling awards through `award_xp` and asserted by a test.

### Unit 5 — Content gating → active market

The 5 market-gate call sites introduced in C1 switch `home_market_code` → `active_market_code`:
- `routers/content.py` `_get_accessible_module` + `list_modules`
- `services/next_lesson_service.py`
- `services/recommendation_service.py` (both gates)

`is_module_in_market(module.market_code, user.active_market_code)`. Since `active_market_code` defaults to `home_market_code` (= GB) for every current user, behavior is unchanged.

### Unit 6 — APIs

- `GET /markets` — list all markets: `code, name, currency_code, has_content`, plus per-user `enrolled` (a `UserMarketProgress` row exists) and `is_active` (`== active_market_code`). Only `is_active=True` markets in the catalog are listed.
- `POST /me/active-market` — body `{ "market_code": "<code>" }`. Validate the code is a known active market (422 otherwise). Set `user.active_market_code`; lazily create the `UserMarketProgress` row if absent. Return the updated profile.
- `GET /me/markets` (per-market progress) — for each enrolled market: `market_code`, `xp`; plus the global aggregate (`total_xp` = `UserProgress.xp`, `level`). Used by C2b for per-market display.
- `/users/me` (`UserProfile`) gains `active_market_code` (read).

### Unit 7 — Migration (hand-written, chained)

One Alembic revision (check `alembic heads`; chain to the current head `c2d3e4f5a6b7`):
1. `create_table("user_market_progress", …)` with composite PK + FKs + `user_id` index.
2. **Backfill:** for every existing user, insert `(user_id, "GB", xp = their user_progress.xp, now)`. Use an `INSERT ... SELECT` from `user_progress` (all current XP is GB, so the invariant holds post-migration). Users with no `user_progress` row get a `(user_id, "GB", 0)` row so every user is enrolled in GB.
3. `add_column("users", active_market_code String(2) NOT NULL server_default "GB")` + FK.
4. `add_column("weak_concepts", market_code String(2) NOT NULL server_default "GB")` + FK + index.
5. `downgrade`: drop the two columns (+ their FKs/index), then `drop_table("user_market_progress")`.

Additive + backfilled. FK order: `markets` already exists (C1); create `user_market_progress` before nothing depends on it.

---

## Data flow

```
Lesson/quiz/sim/challenge completion
  → award_xp(session, user, progress, amount)
       → record_xp(progress, amount)            # UserProgress.xp (global total) + level + goal
       → UserMarketProgress[user.active_market_code].xp += amount   # per-market (+ lazy enroll)
Content list/next-lesson/recommendation
  → gate by module.market_code == user.active_market_code
Switch market
  → POST /me/active-market → set active_market_code + ensure UserMarketProgress row
```

## Error handling / edge cases

- **Backfill invariant:** post-migration, `sum(per-market) == global` because all existing XP is GB. A test asserts it.
- **Unknown market on switch:** 422; no state change.
- **Active = a coming-soon market:** allowed; content gate returns an empty module list (C2b renders coming-soon). No error.
- **Lazy enroll race:** the upsert (`ON CONFLICT`/fetch-or-create) is idempotent; concurrent awards to the same market converge.
- **A user with no `UserProgress` row** earning XP: the existing code already creates `UserProgress` lazily; `award_xp` then also creates the market row.

## Testing strategy

- **Model:** `UserMarketProgress` composite PK; `WeakConcept.market_code`; `User.active_market_code`.
- **Award seam:** `award_xp` increments both global and the active market's row; **invariant** `sum(per-market) == global` after a sequence of awards across two active markets.
- **Switch + lazy enroll:** `POST /me/active-market` sets active + creates the row; 422 on unknown; switching mid-session attributes subsequent XP to the new market.
- **Content gating:** a user with `active_market_code='US'` sees US modules, not GB (and vice-versa) — proving the gate moved to active.
- **Revise per-market:** weak-concepts created carry the active market; Revise session build filters by active market.
- **Migration:** backfills one GB row per user with `xp == user_progress.xp`; invariant holds; downgrade clean.
- **Regression (the key guarantee):** for a current (GB, active=home) user, XP/level/streak/coins/goal behavior is byte-identical; existing xp/streak/digest/push tests stay green.
- **Full backend suite + ruff green;** CI authoritative.

## Definition of done

1. Per-market XP is tracked in `UserMarketProgress` alongside the unchanged global `UserProgress.xp`; the invariant holds (test green).
2. `active_market_code` exists (defaults home=GB), content gates by it, and `POST /me/active-market` switches it with lazy enrollment.
3. Revise weak-concepts are market-tagged and filtered by active market.
4. The `GET /markets`, `POST /me/active-market`, `GET /me/markets` APIs work and expose `has_content`/`enrolled`/`is_active`.
5. Current (GB) users see **byte-identical** XP/level/streak/coins behavior (regression green).
6. Migration additive + backfilled with a clean downgrade; all backend tests + ruff green; promoted testing → staging → main.

## Rollout / safety

- Migration adds a table + columns on `users` and `weak_concepts` in prod. **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- Behaviorally inert for the current all-GB user base (active = home = GB; global engagement unchanged).
- Promote testing → staging → main on green CI per the standard flow.
