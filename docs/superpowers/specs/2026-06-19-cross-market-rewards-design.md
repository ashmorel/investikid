# Cross-Market Rewards — Design Spec (Sub-project D)

**Date:** 2026-06-19
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project D)

---

## Programme context

Predecessors live in prod: **0** Gemini lineup, **A** i18n, **B** AI-language, **C1** market foundation, **C2a** multi-market backend, **C2b** multi-market frontend. The market layer exists: `Market` (10 ISO markets, only GB `has_content`), `UserMarketProgress(user×market→xp)` (row presence = enrolled), `users.home_market_code` + `users.active_market_code`, the `award_xp` seam (global total + per-market row), and the `GET /markets` / `POST /me/active-market` / `GET /me/markets` APIs.

**D (this spec)** rewards learners for **breadth** (adding a new market) and **depth** (completing a market). Engagement stays **global** (coins/level/streak unchanged in nature); the reward currency is **coins** (the existing spendable `virtual_coins`), plus a collectible per-market completion **badge**.

**Locked decisions (from the D brainstorm):**
- **Two reward events:** an **enroll bonus** (one-time per market) when a learner adds a market, and a **completion bonus** when they finish a market's content.
- **Enroll bonus only for non-home markets:** everyone is auto-enrolled in their home market (GB) at registration, so the home market pays **no** enroll bonus (avoids a free/retroactive grant for a market the user didn't choose).
- **Reward = coins + a completion badge.** Coins via `virtual_coins` (global, standalone — no XP/level/invariant impact). Completion also grants a one-time per-market "Market Mastered: <name>" badge (reuses the existing badge system, extended).
- **Amounts admin-configurable** with defaults: enroll = **25** coins, completion = **250** coins.
- **Completion detected on the lesson-completion path** — when the last remaining lesson across a market's modules is completed.
- **Existing GB completers:** a one-time **backfill grants the GB badge only, no retroactive coins** (recognise effort without a coin windfall); the event fires badge + coins going forward.

## Goal

Grant coins when a learner adds a non-home market (one-time per market) and coins + a collectible badge when they complete a market, with admin-tunable amounts, celebratory in-app feedback, and zero change to the global XP/level/streak mechanics — earnable for GB today and automatically for the other 9 markets as content lands (Sub-project E).

## Non-goals (deferred)

- **Un-enroll / leave-market** — switching active markets is enough; leaving is deferred.
- **Per-market reward amounts** — amounts are global settings; no per-market overrides while only GB has content.
- **Streak / level / XP changes** — engagement stays global; D adds no XP and does not touch level or streak.
- **Rewards for partial market progress** — only enroll + full completion are rewarded; no per-module/percentage rewards.
- **Content localization (E)** — D ships the mechanics; the 9 empty markets become completable as E delivers content.

---

## Architecture

### Unit 1 — Per-(user, market) reward state (`UserMarketProgress` columns)

Add three nullable timestamps to `UserMarketProgress` (additive migration), making every grant idempotent and auditable:

| Column | Type | Meaning |
|---|---|---|
| `enroll_rewarded_at` | timestamptz, nullable | set when the enroll bonus is granted (one-time guard) |
| `completed_at` | timestamptz, nullable | set when the market's content was first fully completed |
| `completion_rewarded_at` | timestamptz, nullable | set when the completion coins + badge were granted (one-time guard) |

All default `NULL`. No backfill of these columns except the GB-completion backfill (Unit 7).

### Unit 2 — Per-market "Market Mastered" badges (`Badge.market_code`)

Extend `Badge` with a nullable `market_code: Mapped[str | None]` (FK `markets.code`). Seed **10** badges — one per market — `name = "Market Mastered: <market name>"`, `description` = a kid-friendly line, `icon_url` = the market's flag emoji, `condition_type = "market_completed"`, `condition_value = 0` (unused), `market_code = <code>`. Existing badges keep `market_code = NULL`.

These badges are awarded **directly** by the completion hook (Unit 5), **not** by the threshold evaluator. `gamification_service.is_badge_earned` returns `False` for unknown `condition_type`s (it only matches `_CONDITION_KEYS`), so `market_completed` badges are inert in `evaluate_and_award_badges` — no accidental or duplicate grants. The badge-listing endpoints already return all earned `UserBadge`s, so the new badges appear in the existing badge UI with no frontend model change.

### Unit 3 — Admin-tunable amounts (settings)

Two integer settings beside the existing reward settings (the same mechanism as the module cash reward / apply-mission fields):
- `market_enroll_bonus_coins` (default **25**)
- `market_completion_bonus_coins` (default **250**)

Surfaced in the admin settings form + its update endpoint. Read at grant time so changes take effect without a deploy. Coins only — never money (`virtual_coins` is the cosmetic currency).

### Unit 4 — Enroll-reward hook

Centralise in `market_progress_service`. When a `UserMarketProgress` row is **first created** for a market (the lazy-enroll path: `ensure_enrolled`, used by `POST /me/active-market` and registration) AND `market_code != user.home_market_code` AND `enroll_rewarded_at is None`:
1. add `market_enroll_bonus_coins` to `progress.virtual_coins`,
2. stamp `enroll_rewarded_at = now`.

One-time per market; the home market never qualifies. Registration's home-market enroll never triggers it (it equals `home_market_code`). Returns a `RewardGrant` so the switch endpoint can surface it. Concurrency-safe alongside the existing `begin_nested` enroll insert.

### Unit 5 — Completion-reward hook

Hook into the lesson-completion award path (`routers/content.py` completion, which already calls `award_xp`). After the completion is recorded, for the **active market**:
1. Compute market completion: the market has ≥1 module with lessons AND **every** lesson in **every** module of that market is in the user's `LessonCompletion` set. A market with no modules/lessons is **never** complete (guards the 9 empty markets). Reuses the existing "all lessons done = module complete" logic from `engagement_service`, lifted to market scope (a small `is_market_complete(session, user_id, market_code)` helper).
2. If complete AND `completion_rewarded_at is None`:
   - add `market_completion_bonus_coins` to `virtual_coins`,
   - insert the market's `UserBadge` (idempotent — skip if already owned),
   - stamp `completed_at` (if unset) and `completion_rewarded_at = now`.

Returns a `RewardGrant { coins, badge? }`. One-time per market.

### Unit 6 — Reward feedback (API + UI)

A small `RewardGrant` shape (`{ coins: int, badge: { name, icon_url } | None }`, `coins == 0` / `badge None` = nothing granted) threaded into:
- the `POST /me/active-market` response (enroll grant), and
- the lesson-completion response (completion grant).

The frontend surfaces it with the **existing reward-toast pattern** (the trade-reward toast): enroll → a coin toast (e.g. "🎉 +25 coins for exploring France!"); completion → a larger celebration + the badge reveal. All copy via i18n (the `markets`/rewards namespace); `no-literal-string` enforced.

### Unit 7 — Backfill migration (badge-only)

A one-time data migration: for every user whose GB `UserMarketProgress` exists and who already satisfies GB completion (all GB lessons completed), insert the GB "Market Mastered" `UserBadge` and stamp `completed_at` + `completion_rewarded_at` on the GB row — **no coins added**. Recognises past effort and prevents the completion event re-firing for them. Idempotent (skips users who already own the badge). Reversal is handled by the single migration's `downgrade` (Unit 8), which deletes the seeded market badges and cascades their `user_badges`, then drops the new columns.

### Unit 8 — Migration (hand-written, chained)

One Alembic revision (check `alembic heads`; chain to the current head):
1. `add_column` the three `user_market_progress` timestamps (nullable).
2. `add_column("badges", "market_code", String(2), nullable=True)` + FK to `markets.code`.
3. Seed the 10 per-market badges (idempotent by `name`).
4. Backfill (Unit 7): GB badge + stamps for existing GB completers, no coins.
5. `downgrade`: delete the seeded market badges (+ cascade `user_badges`), drop `badges.market_code`, drop the three columns.

Additive + backfilled. FK order: `markets` and `badges` already exist.

---

## Data flow

```
Switch to a new NON-home market (POST /me/active-market)
  → ensure_enrolled creates UserMarketProgress row
  → enroll hook: first time & market != home & not rewarded
       → virtual_coins += enroll_bonus ; stamp enroll_rewarded_at
       → response carries RewardGrant → coin toast

Complete the last lesson in a market's content (lesson completion)
  → award_xp (global + per-market xp, unchanged)
  → completion hook: is_market_complete(active market)?
       → if complete & not rewarded:
            virtual_coins += completion_bonus
            award "Market Mastered: <name>" UserBadge
            stamp completed_at + completion_rewarded_at
       → response carries RewardGrant → celebration + badge reveal

Settings: admin edits market_enroll_bonus_coins / market_completion_bonus_coins
  → read at grant time
```

## Error handling / edge cases

- **Re-enroll / re-switch to a rewarded market:** `enroll_rewarded_at` set → no second grant.
- **Home market:** never pays the enroll bonus (`market_code == home_market_code`).
- **Empty market (no content):** `is_market_complete` is `False` (requires ≥1 lesson) → completion never fires for the 9 empty markets until E adds content.
- **Extra activity after completion:** `completion_rewarded_at` set → no repeat grant.
- **Concurrency:** the enroll insert already uses `begin_nested` + `IntegrityError`; reward stamps are guarded by the timestamp checks; coin increments are on the user's own row.
- **Invariant:** coins are independent of XP, so `sum(per-market xp) == UserProgress.xp` and level/streak are unchanged.
- **Backfill fairness:** existing GB completers get badge only (no coins); non-completers get nothing.
- **Badge idempotency:** awarding skips if the `UserBadge` already exists (e.g. backfilled, then the event also fires — guarded by `completion_rewarded_at`, but the insert is defensive too).

## Testing strategy

- **Enroll reward:** switching to a new non-home market grants coins once + stamps `enroll_rewarded_at`; a second switch grants nothing; switching to home (GB) never grants; a coming-soon market still grants the enroll bonus (breadth is rewarded regardless of content).
- **Completion reward:** completing the last GB lesson grants completion coins + the GB badge + stamps; extra lessons/re-completion grant nothing; a market with no content is never complete.
- **Invariant/regression:** coin bonuses don't change XP/level/streak; `sum(per-market xp) == global xp` holds; existing xp/streak/badge tests stay green.
- **Admin settings:** changing the two amounts changes subsequent grants; defaults are 25 / 250.
- **Backfill migration:** a pre-existing GB completer gets badge + stamps, **no coins**; a non-completer gets nothing; idempotent; clean downgrade.
- **API/feedback:** the switch + completion responses carry the `RewardGrant`; the frontend toast renders and is a11y-clean (`vitest-axe`); i18n guard passes (no literal strings).
- **Full backend suite + ruff green; frontend tsc + lint + test + build green; CI authoritative.**

## Definition of done

1. Adding a non-home market grants the enroll coin bonus once (home never pays; idempotent per market).
2. Completing a market grants the completion coin bonus + a collectible "Market Mastered" badge once.
3. Amounts are admin-configurable (defaults 25 / 250) and read at grant time.
4. Reward grants surface as in-app feedback (coin toast / completion celebration + badge reveal), fully i18n'd + a11y-clean.
5. Global XP/level/streak and the per-market XP invariant are unchanged (regression green).
6. Existing GB completers are backfilled the GB badge (no coins); the event fires badge + coins going forward.
7. Migration additive + backfilled with a clean downgrade; backend + frontend + all CI jobs green; promoted testing → staging → main; Vercel prod for the UI.

## Rollout / safety

- Migration adds 3 columns to `user_market_progress` + `market_code` to `badges`, seeds 10 badges, and backfills the GB badge for existing completers. **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- Behaviorally: the enroll bonus is live for any non-home market immediately; the completion bonus is earnable where content exists (GB today) and activates automatically for the other 9 as Sub-project E ships content.
- Promote testing → staging → main on green CI; then the manual Vercel prod web deploy for the feedback UI.
