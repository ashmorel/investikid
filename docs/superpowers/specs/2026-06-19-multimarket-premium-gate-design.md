# Multi-Market Premium Gate — Design Spec

**Date:** 2026-06-19
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (monetization layer; sits between D and E2)

---

## Context

The multi-market layer is live: `Market` (10 ISO markets, GB has content), `UserMarketProgress(user×market→xp)` (row = enrolled), `users.home_market_code`/`active_market_code`, lazy-enroll switch (`POST /me/active-market`), D's enroll/completion coin rewards, and per-module/level `is_premium` gating. Premium is checked via `is_premium(user)` (`app/services/entitlements.py`); paywalls are raised with `premium_required_error(kind, label)` → a 403 whose body (`code: "premium_required"`, `context: {kind, label}`) the frontend already uses to open the paywall modal.

**This sub-project** makes **access to more than one market premium-only**: a free user may make progress in exactly **one** market — the first they *start* — while the current free/premium split *within* a market is unchanged (free users keep their full free sample). Premium unlocks unlimited markets. It is independent of **E2** (per-market content authoring) and can ship now, inert, ahead of it.

**Locked decisions (from the brainstorm):**
- **Free user's one market = the first they actively start** (not forced to home), where "start" = **first lesson completion** in a market.
- **Trigger = first progress** (lesson completion / XP earned), recorded in a new nullable `users.started_market_code`.
- **Surfacing = proactive marking + hard completion gate**: the picker marks other markets "Premium" and a content-area unlock prompt shows, but previewing is allowed; **completing** a lesson in a non-started market is the hard server gate.

## Goal

Limit free users to progress in a single market (their first-started one) while letting them preview others, with proactive premium marking and a hard server-side gate at lesson completion — and zero behavior change for current users (everyone is GB/active=GB today, so post-backfill `started_market_code=GB` and all their GB content stays accessible).

## Non-goals (deferred)

- **No change to within-market free/premium gating** (module/level `is_premium` stays as-is — the free sample within a market is preserved).
- **No simulator-region gating** — the simulator's trading region (`content_region`) is a separate axis, untouched.
- **No un-start/reset** of the chosen market (support-only if ever needed).
- **E2 per-market content authoring** is separate.

---

## Architecture

### Unit 1 — `users.started_market_code`

Add `started_market_code: Mapped[str | None]` — `String(2)`, FK `markets.code`, **nullable** (additive migration). The single market a user has committed to.
- **Set lazily** on a user's *first* lesson completion (`started_market_code is None`), to that lesson's `module.market_code` — for **everyone** (free and premium), so it's stable across a later downgrade.
- Null until the first completion (a brand-new user can begin in any market).

### Unit 2 — The gate predicate

One helper (e.g. in `app/services/entitlements.py` or a small `market_access.py`):

```python
def market_locked_for(user, market_code: str) -> bool:
    if is_premium(user):
        return False
    if user.started_market_code is None:
        return False
    return market_code != user.started_market_code
```

- Premium → never locked.
- Free + no started market → nothing locked (first completion sets it).
- Free + started market → every *other* market locked.

This single predicate drives both the hard enforcement (Unit 3) and the proactive UI flag (Unit 4) so they cannot drift.

### Unit 3 — Hard gate at lesson completion (source of truth)

In `complete_lesson` (`POST /lessons/{lesson_id}/complete`), after resolving the lesson's module (its `market_code`) and **before** awarding:
- `started_market_code is None` → first start: set `user.started_market_code = module.market_code`; proceed (award, D rewards, etc.).
- else if `market_locked_for(current_user, module.market_code)` → `raise premium_required_error("market", market.name)` **before** any award — no XP, no `LessonCompletion` row, no D reward.
- else (same market, or premium) → proceed unchanged.

The market name for the paywall label comes from the `Market` row (load it or join). The gate sits at the start of the award region so a locked completion is fully inert.

### Unit 4 — Proactive marking on `/markets`

Add `locked: bool` to `MarketOut` (`GET /markets`) = `market_locked_for(current_user, m.code)`. The C2b picker reads it: a free user with a started market sees their started market open ("Learning") and every other market with a **"Premium"** lock chip (shown alongside/instead of the "Coming soon" pill). Locked markets remain tappable (preview), but the lock is visible up front. Premium users / not-yet-started free users see no locks.

### Unit 5 — Content-area unlock prompt

When a free user's **active** market is locked (they switched to preview a non-started market), the Home/lessons area shows a premium-unlock panel ("Unlock all markets with Premium") — reusing the existing premium-upsell component(s). Previewing lessons is allowed; **completing** one triggers the paywall modal via the Unit 3 403. **Detection needs no new field:** the frontend already loads `/markets`; the active market is the entry with `is_selected === true`, so the panel renders when that entry's new `locked` flag (Unit 4) is true. No profile/schema addition beyond `MarketOut.locked`.

### Unit 6 — Picker copy ("first start is free")

Before a free user has started any market, the picker shows **no** locks (they can begin anywhere) and i18n'd copy making the one-free-market deal clear, so the choice is informed. All new strings via the `markets` i18n namespace.

### Unit 7 — Backfill migration

One additive Alembic revision: add `users.started_market_code` (nullable, FK) + a one-time backfill — for every user with existing progress, set `started_market_code` to the market where they have the **most XP** (`UserMarketProgress` row with the highest `xp`; tie-break earliest `created_at`). Today this resolves to **GB** for essentially everyone. This pre-claims the correct slot so an existing GB-heavy free user's first *post-deploy* completion in another market can't wrongly steal their free market. Users with no progress stay null. `downgrade` drops the column (+ FK).

---

## Data flow

```
Free user completes a lesson in market M (module.market_code)
  → started_market_code is None?  set = M ; award normally
  → else market_locked_for(user, M)?  → 403 premium_required (no award)
  → else (M == started, or premium) → award normally

GET /markets (free user, started=GB)
  → each MarketOut.locked = market_locked_for(user, code)
       GB → false (open) ; US/AU/... → true (Premium chip)

Switch active to a locked market (preview)
  → allowed ; Home shows the "Unlock all markets" panel
  → opening a lesson allowed ; completing it → paywall modal
```

## Error handling / edge cases

- **Premium → free downgrade:** `started_market_code` was set on first progress → the downgraded user is locked to that one market; others lock. Standard.
- **Grandfathered multi-market free progress:** cannot occur today (only GB has content); the backfill picks the dominant market and there's nothing else to revoke. The gate is forward-looking (blocks *new* starts), never retroactively revoking earned progress.
- **Same-market re-completion / repeats:** always allowed.
- **Concurrent first completions in two markets (race):** the gate reads + sets `started_market_code` within the completion handler's transaction; the first commit wins and the second sees the set value → one is awarded, the other 403s. Acceptable and safe (no double-claim).
- **D enroll reward:** still fires on switch/preview (a deliberate upsell hook); the D **completion** reward can't fire in a locked market because completion is blocked first.

## Testing strategy

- **Predicate:** premium never locked; free+null → nothing locked; free+started=GB → GB open, others locked.
- **First completion sets `started_market_code`** for free and premium users.
- **Second-market completion:** free → `premium_required` 403 with **no XP / no LessonCompletion / no reward**; premium → allowed (and would set started on their first-ever completion).
- **Same-market completion always allowed**; **regression:** a default GB user's completion flow is byte-identical (started=GB after first; all GB lessons allowed; XP/level/streak unchanged).
- **`/markets` `locked` flag** matches the predicate per user/market (premium all-false; free shows others locked).
- **Backfill:** dominant-market resolution (GB) for users with progress; null for no-progress; clean downgrade.
- **Frontend:** picker Premium chips + the unlock panel render for a locked free user, not for premium / not-yet-started; tapping a locked market previews; completing → paywall; a11y; i18n guard.
- **Full backend + frontend suites + ruff; CI authoritative.**

## Definition of done

1. `users.started_market_code` exists (nullable), set on first lesson completion, backfilled to the dominant market for existing users.
2. `market_locked_for` predicate drives both enforcement and UI.
3. Completing a lesson in a non-started market as a free user is blocked (403 premium_required, no award); same-market and premium always allowed.
4. `/markets` exposes `locked`; the picker marks locked markets Premium and the content area shows an unlock prompt for a locked active market.
5. Current (GB, active=GB) users see no behavior change; existing GB content stays fully accessible.
6. Additive migration + backfill with clean downgrade; backend + frontend + all CI jobs green; promoted testing → staging → main; Vercel prod.

## Rollout / safety

- Additive migration adds `users.started_market_code` + a backfill. **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- **Inert for current users:** everyone is GB/active=GB, so post-backfill `started_market_code=GB` and their GB content stays fully accessible — the gate only bites when a free user tries to *progress in a second market*, which only becomes meaningful once E2 gives other markets content. Safe to ship now, ahead of E2.
- Promote testing → staging → main on green CI; then the manual Vercel prod web deploy for the picker chips + unlock panel.
