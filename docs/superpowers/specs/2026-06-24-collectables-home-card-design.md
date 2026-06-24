# Collectables B3 — Home Featured-Drop Card — Design

**Status:** Approved design, ready for implementation planning
**Date:** 2026-06-24
**Sub-project:** B3 of the Limited-Edition Collectables programme — the **last** sub-project. B1 (earn-only drops engine) and B2 (admin drop scheduler) are both LIVE in prod.

## Goal

Surface the current limited-edition drop on the child's **Home** screen as a compact "featured drop" card with live progress, so kids see and chase active drops without first opening the shop. The B1 "Limited" shelf in the shop stays as the full surface; B3 is a Home spotlight that taps through to it.

## Scope

**Frontend-only.** No backend, no migration, no new endpoint. The card reuses the existing B1 `useCollectables()` hook (`GET /collectables`), which already returns `{ active, owned }` with each live drop's `goal {current, threshold}`, `ends_at`, `rarity`, `emoji`, `name`, and `earned`.

## Background (what already exists)

- `frontend/src/api/collectables.ts`: `useCollectables()` → `CollectablesState = { active: CollectableDrop[]; owned: OwnedCollectable[] }`.
  - `CollectableDrop = { slug; name; emoji; rarity: string | null; ends_at: string | null; goal: { type; threshold; current }; earned: boolean }`.
- `frontend/src/components/child/shop/LimitedShelf.tsx`: the B1 shelf. Contains three reusable pieces currently defined inline: `formatCountdown(endsAt, now, t)`, the rarity styling (`RARITY_STYLE` map + `rarityClass(rarity)`), and the progress-bar markup (`role="progressbar"` with aria values).
- `frontend/src/pages/child/Home.tsx`: composes the Home cards in order — `EventStrip`, `HomeHero`, `StatsCard`, `StreakReminderNudge`, `ReviseCard`, `QuickLinksRow`, `ArcadeDailyCard`, `ArcadeHomeCard`, `PremiumUpsellCard`.
- `frontend/src/components/child/home/ArcadeDailyCard.tsx`: the card-shell pattern to mirror — a single `<Link>` with `rounded-xl border border-line bg-card p-4 min-h-[44px]` and an `aria-label`.

## Core decisions (locked during brainstorming)

1. **Spotlight one drop.** Feature a single drop with emoji, name, rarity badge, countdown, and a live progress bar — not a summary chip.
2. **Selection = soonest-ending, not-yet-earned.** Among `active` drops, filter to `earned === false`, then pick the smallest `ends_at`. Drops with a null `ends_at` sort last (treated as "no deadline"). This is urgency/FOMO-driven, which is the point of limited drops.
3. **Hide when nothing to feature.** Render `null` when `data` is loading/undefined, when `active` is empty, or when every live drop is already earned. No empty state, no "already earned" state (B1 already fires an earn toast on completion).
4. **Taps to the shop.** The whole card is a `<Link to="/shop">` (the Limited shelf), like `ArcadeDailyCard` links to its game.
5. **Placement: above `ArcadeDailyCard`.** Limited drops are time-sensitive, so they take the higher slot among the daily cards. The card self-hides when nothing is live, so it adds no empty space.
6. **DRY refactor (in-scope):** extract `formatCountdown`, `rarityClass`/`RARITY_STYLE`, and the progress-bar into a shared module so `LimitedShelf` and the new card share them — not a duplicate copy.

## Architecture

### Shared extraction (behaviour-preserving refactor)

Create `frontend/src/components/child/shop/collectableBits.tsx` (co-located with `LimitedShelf`, since that's where these live today). Move, unchanged in behaviour:
- `RARITY_STYLE` (the rarity → tailwind-class map) and `rarityClass(rarity: string | null): string`.
- `formatCountdown(endsAt: string | null, now: number, t): string`.
- `ProgressBar` — a small component rendering the existing progress markup: a labelled `role="progressbar"` with `aria-valuenow={current}`, `aria-valuemin={0}`, `aria-valuemax={threshold}`, and the fill width `Math.min(100, (current / threshold) * 100)%`.

Update `LimitedShelf.tsx` to import these instead of its inline copies. `LimitedShelf`'s existing tests must pass unchanged (the refactor proves behaviour-preserving).

### The card

`frontend/src/components/child/home/FeaturedDropCard.tsx`:
- Calls `useCollectables()`; computes `active = data?.active ?? []`.
- `featured = active.filter(d => !d.earned).sort(byEndsAtAscNullsLast)[0]` (a pure helper; null `ends_at` sorts last).
- If `featured` is undefined → `return null`.
- Otherwise renders a `<Link to="/shop">` card (the `ArcadeDailyCard` shell) containing: emoji (`aria-hidden`) + name + rarity badge (`rarityClass`, text label not colour-only), a countdown line via `formatCountdown` (omit the line if it returns empty), and the shared `ProgressBar` for `featured.goal`.
- `aria-label` summarises the drop + progress, e.g. `t('featuredDrop.ariaLabel', { name, current, threshold })` → "Limited drop: Founder's Crown, 5 of 7 — see it in the shop".
- `now` captured once per mount via `useState(() => Date.now())` (same purity pattern as `LimitedShelf`, satisfying react-hooks/purity).

### Home mount

In `frontend/src/pages/child/Home.tsx`, mount `<FeaturedDropCard />` (wrapped in a `div.mt-4`) immediately **above** the `ArcadeDailyCard` block, inside the existing non-coming-soon `<>` branch. The card self-hides, so no surrounding conditional is needed.

### Copy

The card uses **two namespaces**, both via `useTranslation`:
- **`home`** for its own copy: add a `featuredDrop` block to `frontend/src/locales/en/home.json` with `title` and `ariaLabel` (the latter interpolating `{{name}}`/`{{current}}`/`{{threshold}}`).
- **`child`** for the countdown only: the shared `formatCountdown` already resolves `limited.endsInDays` / `limited.endsInHours` / `limited.endsInLessThanHour`, which exist in the `child` namespace used by `LimitedShelf`. The card passes the `child` `t` into `formatCountdown` (exactly as `LimitedShelf` does) — so no new countdown keys are added.

## Error handling / edge cases

- `data` undefined (loading/error) → `null` (no crash; same defensive `data?.active ?? []` guard hardened in `LimitedShelf`).
- `goal.threshold` of 0 → the progress width uses `Math.min(100, …)`; guard against divide-by-zero by treating `threshold <= 0` as 0% (the shared `ProgressBar` handles this).
- All live drops earned → `null`.
- A drop with null `ends_at` → still featurable (countdown line just renders empty); sorts after dated drops.

## Testing

`frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx` (vitest + `vitest-axe`, mocking `useCollectables`):
1. Renders the soonest-ending unearned live drop — asserts name, `current / threshold`, and a countdown string.
2. Given multiple live unearned drops, features the one with the smallest `ends_at`.
3. Renders nothing (`container` empty) when `active` is empty.
4. Renders nothing when every live drop has `earned === true`.
5. Renders nothing when `data` is undefined.
6. axe-clean.

Plus: a render assertion in `Home.test.tsx` that the card appears above `ArcadeDailyCard` when a live unearned drop is mocked.

Refactor safety: `LimitedShelf.tsx`'s existing test file passes unchanged after the shared extraction.

## Rollout

- Beta → straight to main. **No migration, no backend** → no prod-snapshot question.
- Frontend gate (tsc + lint + vitest incl. vitest-axe + build), CI green, Vercel two-step deploy + alias, verify live, `cap sync ios` (carry the card into the native shell).
- Update MASTER-BACKLOG + memory: B3 live → the limited-edition collectables programme (B1+B2+B3) is complete.

## Out of scope (future, not part of B3)

- Per-market drop targeting (a B-programme-wide future item).
- Multiple simultaneous featured drops / a carousel.
- Push notification when a new drop goes live.
- Any backend change.

## Files

**Create**
- `frontend/src/components/child/shop/collectableBits.tsx` — shared `RARITY_STYLE`/`rarityClass`, `formatCountdown`, `ProgressBar`.
- `frontend/src/components/child/home/FeaturedDropCard.tsx` — the card.
- `frontend/src/components/child/home/__tests__/FeaturedDropCard.test.tsx` — tests.

**Modify**
- `frontend/src/components/child/shop/LimitedShelf.tsx` — import shared bits instead of inline copies.
- `frontend/src/pages/child/Home.tsx` — mount `<FeaturedDropCard />` above `ArcadeDailyCard`.
- `frontend/src/locales/en/home.json` — `featuredDrop` copy.
- `frontend/src/pages/child/__tests__/Home.test.tsx` — assert the card mounts when a drop is live.
