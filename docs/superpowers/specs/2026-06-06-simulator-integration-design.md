# Simulator Integration (Item 4D) — Design Spec

**Date:** 2026-06-06
**Status:** Approved (design) — pending implementation plan
**Parent backlog item:** #4 (premium content & engagement), sub-project **4D**
**Sequence:** 4D (this) → 4B (free/premium clarity + paywall) → 4A (multi-channel payments) → 4C (subscription nudges)

## Goal

Weave the investment Simulator into the core app loop so it stops feeling like a
bolted-on tab. Trading should *count* like learning (XP, streak, levels, badges),
lessons should push kids into the simulator to apply what they learned, and the
simulator should have a daily presence on the home screen. Virtual cash becomes a
configurable, earnable resource that grows as the child progresses.

## Context (current state)

- **Simulator** lives at `/simulator` (+ `/simulator/market`, `/simulator/stock/:exchange/:ticker`),
  reachable only via the bottom tab / top nav. Backed by `Portfolio`, `Holding`,
  `Trade` (`app/models/simulator.py`), `simulator_service.py`, `routers/simulator.py`.
- **Starting cash** is a hardcoded constant `_STARTING_CASH` in `simulator_service.py:10`
  (`{GBP:1000, USD:1000, HKD:10000, EUR:1000}`), read at portfolio creation.
- **Progression**: `UserProgress` (`app/models/user.py`) holds `xp`, `level`,
  `streak_count`, `last_activity_date`, `virtual_coins`, `streak_freezes`. Today
  **only lesson completion** awards XP / advances the streak (`content_service.streak_after_activity`,
  the lesson-completion path). Trades award **nothing** except: a `trades_executed`
  challenge increment and `trade_count`-conditioned badges (only checked on lesson completion).
- **Settings store**: a generic `AppSetting` key/value table already exists, with
  `services/app_settings.py` (`get_setting`/`set_setting`) and an admin `/settings`
  endpoint (`routers/admin.py:444`). Reused here — no new settings table.
- **Premium**: simulator ticker access is already free/premium-gated
  (`provider.is_free_tier(...)`). 4D does **not** change any gating — payments are 4A.

## Design decisions (approved)

1. **Full progression integration** — trades award XP, extend the streak, and feed
   levels/badges, with anti-gaming caps.
2. **Targeted apply-missions** — a lesson can carry an optional "apply this in the
   simulator" action; completing it awards bonus XP / badge / cash.
3. **Home presence** — a compact portfolio snapshot card + the active apply-mission
   surfaced in the home quests/recommendations area.
4. **Anti-gaming** — most XP comes from one-time mission completions; routine trades
   award a small XP each up to a daily ceiling; the streak extends on the **first
   qualifying activity of the day (lesson OR trade)**.
5. **Configurable & earnable virtual cash** — starting cash is admin-editable at
   runtime; modules and missions can grant cash; all grants flow through one
   idempotent ledger.

---

## Section 1 — Data model & content authoring

### New models

**`ApplyMission`** (`app/models/apply_mission.py`) — authored "apply this" action, 0-or-1 per lesson.
- `id: UUID` (pk)
- `lesson_id: UUID` (FK `lessons.id`, unique → at most one mission per lesson)
- `mission_type: str` (enum, see registry below)
- `params_json: dict` (e.g. `{"n": 3}` or `{"amount": "500.00"}`)
- `title: str`
- `prompt: str` (Penny's CTA copy)
- `xp_reward: int` (default from config if 0)
- `cash_reward: Decimal | None` (optional virtual-cash grant on completion)
- `badge_id: UUID | None` (optional FK `badges.id`)
- `created_at`, `updated_at`

**`ApplyMissionCompletion`** (`app/models/apply_mission.py`)
- `id: UUID` (pk)
- `user_id: UUID` (FK `users.id`)
- `mission_id: UUID` (FK `apply_missions.id`)
- `completed_at: datetime`
- **Unique `(user_id, mission_id)`** — each mission completes once.

**`CashGrant`** (`app/models/cash_grant.py`) — idempotent ledger for all virtual-cash awards.
- `id: UUID` (pk)
- `user_id: UUID` (FK `users.id`)
- `source_type: str` (`"mission" | "module" | "admin"`)
- `source_id: UUID | None` (mission id / module id; null for ad-hoc admin top-up)
- `currency_code: str(3)`
- `amount: Decimal(12,2)`
- `granted_at: datetime`
- **Unique `(user_id, source_type, source_id)`** — a one-time source can never double-grant.
  (Admin ad-hoc top-ups use `source_id = NULL`; uniqueness does not constrain them — they are
  intentionally repeatable, audited by row.)

### New columns

- `Module.completion_cash_reward: Decimal | None` — granted **once on full module
  completion**. Edited in admin `ModuleForm`.
- `UserProgress.sim_xp_date: date | None` and `UserProgress.sim_xp_today: int` (default 0)
  — daily tally for the routine-trade XP cap (resets when the date rolls over).

### Settings (reuse `AppSetting`)

Starting cash stored under `AppSetting` key `simulator.starting_cash` as JSON, e.g.
`{"GBP": "1000.00", "USD": "1000.00", "HKD": "10000.00", "EUR": "1000.00"}`. New helpers
`get_starting_cash(session)` / `set_starting_cash(session, mapping)` in `services/app_settings.py`,
exposed via the existing admin `/settings` endpoint (extend `AdminSettingsOut` / the PUT body).
The `_STARTING_CASH` constant becomes the **seed default** when the key is unset.

### Mission-type registry (code-level)

A small, extensible registry in `services/simulator_rewards_config.py`. Each entry maps a
`mission_type` to a predicate `fn(portfolio, holdings, params) -> bool`. Initial set:
- `first_buy` — any holding exists (≥1 buy)
- `first_sell` — at least one sell trade has occurred
- `diversify` — number of distinct held tickers ≥ `params.n`
- `invest_amount` — total invested (sum of buy cost basis) ≥ `params.amount`

Mission predicates target **free-tier tickers** so every child can complete the missions
lessons hand them, regardless of premium status.

### Authoring & admin

- `ApplyMission` is edited inside the existing admin `LessonForm` as a collapsible
  "Apply mission" block (type, params, title, prompt, xp, cash, badge). Admin CRUD endpoints
  mirror the existing module/lesson pattern in `routers/admin.py`.
- `Module.completion_cash_reward` added to `ModuleForm` + admin module schemas.
- Starting cash editable on a "Simulator" section of the admin settings page.

### Migration & exports

All new models exported from `app/models/__init__.py` (conftest builds tables from
`Base.metadata`). One hand-written **chained** Alembic migration off head `f7a8b9c0d1e2`
(re-check `alembic heads` at implementation time): create `apply_missions`,
`apply_mission_completions`, `cash_grants`; add `modules.completion_cash_reward`,
`user_progress.sim_xp_date`, `user_progress.sim_xp_today`.

---

## Section 2 — Reward engine & where every tunable lives

### Shared daily-activity recorder

Extract `record_daily_activity(progress, today)` that wraps the existing
`streak_after_activity(...)` and is **idempotent per day** (no-op if
`last_activity_date == today`). Both the lesson-completion path **and** a qualifying trade
call it, so the streak extends on the first qualifying activity of the day (lesson or trade)
and never double-counts. Uses the same local-date notion as the streak (`ymdLocal` equivalent).

### Trade reward flow (added to the `place_trade` path, after a successful trade)

1. **Capped daily trade XP** — award `SIM_XP_PER_TRADE`, but only while
   `sim_xp_today < SIM_XP_DAILY_CAP` (resetting `sim_xp_today`/`sim_xp_date` on date rollover).
2. **Record daily activity** (streak) via the shared recorder.
3. **Evaluate apply-missions** — for the child's incomplete missions, test the predicate
   against current portfolio/holdings/trade state; on success write `ApplyMissionCompletion`
   (`begin_nested()` SAVEPOINT) and award its XP + optional badge + optional `CashGrant`.
4. Existing `trades_executed` challenge increment stays as-is.

The trade response is **enriched** to return what was earned this trade:
`xp_awarded`, `streak_extended`, `cash_granted`, `mission_completed` (id/title), `badges` (list).

### Module-completion reward flow (added to the lesson-completion path)

After a lesson is marked complete, detect whether it completed its module (reuse existing
progress signals — all lessons/levels in the module done). If so, and
`Module.completion_cash_reward` is set and unclaimed, write a `CashGrant`
(`source_type="module"`, SAVEPOINT) and add to `Portfolio.virtual_cash`.

### Three tiers of tunables

| Tier | Holds | Edited by |
|------|-------|-----------|
| **Code config** `services/simulator_rewards_config.py` | `SIM_XP_PER_TRADE`, `SIM_XP_DAILY_CAP`, default mission XP, mission-type predicate registry | developer (deploy) |
| **Admin DB** (`AppSetting`) | `simulator.starting_cash` per currency | admin panel (runtime) |
| **Authored per-content** | mission XP/cash/badge (`ApplyMission`), `Module.completion_cash_reward` | admin forms (runtime) |

All the *money amounts* are runtime-editable in the admin panel; only the anti-gaming
mechanics live in code.

### Feedback

XP/streak/cash surface through the **same** toast + animation lessons already use, so a
trade *feels* like progress.

---

## Section 3 — Frontend integration

- **`ApplyMissionCTA`** — on the lesson-completion screen, when the lesson carries a mission,
  Penny presents title + prompt + a "Try it in the simulator" button deep-linking to
  `/simulator?mission=<id>`.
- **`MissionBanner`** (Simulator page) — when a mission is active (via CTA or any incomplete
  mission), shows the goal + a progress hint ("Hold 3 different stocks — you have 1"); flips to
  a success state with the reward earned on completion. Server-side evaluation means organic
  completion still works — the banner is guidance, not the gate.
- **`PortfolioSnapshotCard`** (child home) — portfolio value, today's change (▲/▼ glyph + label,
  not colour alone), and a "Trade" CTA. Reuses `usePortfolio`. The active mission is also
  surfaced in the home quests/recommendations area.
- **Reward feedback** — the enriched trade response drives the shared XP/streak toast, then
  invalidates portfolio / stats / missions queries so everything refreshes.
- **API additions** — `simulator.ts` enriched trade-response types; a small `missions.ts`
  client with `GET /missions/active` (incomplete missions + deep-link context). `apiFetch`
  returns `T | null` as usual.
- **Accessibility** — new components carry `vitest-axe` coverage and keep WCAG 2.2 AA; status
  meaning never conveyed by colour alone.

---

## Section 4 — Edge cases, testing, scope boundary

### Edge cases & safety

- **Daily XP cap rollover** uses the same local-date notion as the streak, so cap and streak
  agree on "today".
- **Idempotency** — `ApplyMissionCompletion`, `CashGrant`, and module rewards are guarded by
  unique constraints + `begin_nested()` SAVEPOINTs; a double-tap or race can't double-grant.
- **Missions completable by everyone** — predicates target free-tier tickers (no payment dep).
- **Missions are one-time** — completion persists even if the child later sells.
- **Starting-cash changes apply to new portfolios only**; existing balances untouched. To bump
  an existing child, use the admin manual `CashGrant` top-up.
- **Missing `simulator.starting_cash`** falls back to the seeded default constant; reward
  amounts validate `≥ 0`.
- **No new PII** — missions and virtual cash are in-app play money only.

### Testing

- *Backend* — unit: capped-XP rollover, streak-unification idempotency, each mission predicate,
  module-completion-grants-once, cash-ledger uniqueness. Router: enriched trade response,
  `/missions/active`. Admin CRUD: mission block, `Module.completion_cash_reward`,
  `simulator.starting_cash`. Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")`
  + the `client`/`admin_client`/`db_session` fixtures.
- *Frontend* — unit + `vitest-axe` for `ApplyMissionCTA`, `MissionBanner`, `PortfolioSnapshotCard`,
  reward toast.
- *Close-out* — ruff + pytest; tsc + lint + test + build.

### Out of scope (own later sub-projects)

- Real payments / IAP — **4A**
- Free-vs-premium paywall surface — **4B**
- Subscription nudges — **4C**

### Future / backlog

- **Per-market (per-exchange) configurable invest amounts** — extend `simulator.starting_cash`
  (currently per-currency) to per-stock-market amounts, since the four markets (LSE/GBP,
  US/USD, HKEX/HKD, EU/EUR) are already modelled. Parked per user request.
