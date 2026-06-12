# Penny Cosmetics Spend Loop (M8) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M8 of `docs/2026-06-12-market-leader-roadmap.md`.
Closes the earn→spend loop with a play-money cosmetics shop. **Zero crossover** with the
simulator portfolio (spending investing cash on hats would corrupt the learning metric)
and zero real-money/entitlement crossover.

## Economy: learning coins

- `user_progress.virtual_coins` (exists, currently unused) becomes the cosmetic currency.
- **Earn rule: 1 coin per XP**, granted inside `xp_service.record_xp` (one seam, all award
  sites, no new tuning surface).
- **Backfill** (data migration): `virtual_coins = xp` where `virtual_coins = 0` — existing
  beta kids open the shop with spending money proportional to what they've learned.
- Balance exposed on `GET /users/me/progress` (`virtual_coins`).

## Catalog

`CosmeticItem` (model exists; migration adds `slug` String(40) unique + `emoji` String(8) +
creates the two tables — they were never migrated). v1 type: `accessory` only (app themes
deferred). Seeded idempotently by slug (new `app/seed/cosmetics.py`, registered in the
seed runner):

| slug | name | emoji | coins | premium |
|---|---|---|---|---|
| party_hat | Party Hat | 🥳 | 50 | no |
| sunglasses | Cool Shades | 🕶️ | 75 | no |
| bow | Big Bow | 🎀 | 75 | no |
| headphones | Headphones | 🎧 | 100 | no |
| grad_cap | Graduation Cap | 🎓 | 150 | no |
| crown | Golden Crown | 👑 | 300 | no |
| monocle | Investor Monocle | 🧐 | 200 | yes |
| top_hat | Top Hat | 🎩 | 500 | yes |

Premium items are visible to everyone (with a ✨ marker) but purchasable only by premium
children (still coins — premium gates the catalogue breadth, never sells coins).

## API (`app/routers/cosmetics.py`, child session)

- `GET /cosmetics` → `{coins, items: [{id, slug, name, emoji, coin_cost, is_premium, owned, equipped, can_buy}]}`.
- `POST /cosmetics/{item_id}/buy` → 409 if owned, 402-style error if insufficient coins
  (`400 {detail: "not_enough_coins"}`), 403 premium item without premium; deducts coins +
  inserts `UserCosmetic` under a SAVEPOINT (race-safe like missions); returns new balance.
- `POST /cosmetics/{item_id}/equip` + `POST /cosmetics/unequip` → at most ONE equipped
  accessory (equipping unequips the rest); 404 if not owned.

## Frontend

- `Penny` gains `accessory?: string` (slug) — emoji rendered as an SVG `<text>` overlay
  positioned above the head (one anchor position; per-slug y-offsets where needed). Works
  at all sizes/moods, `aria-hidden` like the rest of Penny.
- `useCosmetics()` hook (catalog query) + equipped slug consumed by `HomeHero`'s Penny
  (single extra query on Home, cached 5 min).
- **Penny's Shop**: route `/shop` — coin balance header, grid of item cards (emoji, name,
  price chip, Owned/Equip/Buy button states, premium ✨ marker with gentle "ask my
  grown-up" paywall hook reusing `usePremiumPaywall` for non-premium children tapping a
  premium item). Confirm dialog before spending. Entry point: ProfileMenu link
  ("Penny's Shop" + coin balance). Investor tier: same shop, copy stays neutral
  ("Shop" header, no exclamation marks) via existing `chipEmoji`-style check only where
  emoji appear in copy (item emoji stay — they're the product).
- Buying/equipping invalidates the cosmetics + progress queries; equipped hat shows on
  Home immediately (the visible-ownership requirement).

## Analytics

None new in v1 (purchases are derivable later if needed; avoid event sprawl).

## Testing

Backend: coins earned with XP (record_xp), backfill migration content, catalog/owned/
equipped shape, buy (success, insufficient, duplicate race via SAVEPOINT, premium gate),
equip exclusivity, seed idempotency. Frontend: Penny accessory overlay render, shop page
(states, buy flow with confirm, premium gate → paywall, axe), ProfileMenu entry,
HomeHero equipped accessory. Full repo gates.

## Out of scope

App themes · coin packs / any purchase of coins · gifting · per-mood accessory art ·
seasonal rotation (M9 hooks could add later).
