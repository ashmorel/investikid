# Avatar & Penny Cosmetics — Design Spec

**Date:** 2026-06-23
**Status:** Approved design → ready for implementation plan
**Scope:** An avatar showcase plus two new spendable cosmetic categories (**Penny scene backgrounds** and **Penny colour skins**) with **per-category equip**, built on the existing M8 cosmetics system. Gives arcade/lesson-earned coins a richer sink and lets a child show off their collection.

> **Out of scope (separate later spec):** **App/profile themes** — a whole theming engine (a theme context + CSS-variable overrides on `<html>` + load-time hydration + contrast care across every screen). There is no theme-switching mechanism today (only a dormant unused `.dark` stub), so this is its own riskier feature. Also out of scope: Penny "outfits" beyond a body recolour (art-heavy future add).

---

## 1. Goals & success criteria

- A child can **see their Penny dressed up** — background + skin + accessory layered together — in one prominent place.
- Coins have a **longer runway**: more to collect than today's 8 accessories.
- A child can wear **one of each category at once** (one accessory + one background + one skin).
- Reuses the existing coin economy and premium gate; no new currency, no real-money crossover (kids' app).
- Kids' app quality bar: WCAG 2.2 AA, ≥44px touch targets, crisp on retina, no heavy assets.

**Non-goals:** app/profile themes; full Penny outfits; any change to how coins are earned.

---

## 2. Architecture overview

Three pieces, all on the existing cosmetics system:
1. **Per-category equip** (small backend change) — equip scopes its "unequip others" to the same `type`.
2. **Two new cosmetic categories** — `background` and `skin`, rendered on the Penny SVG.
3. **The avatar showcase** — the existing `/shop` page grows into **"Penny's Shop & Avatar"**: a large layered Penny at the top + category tabs for buy/equip.

No data migration (the `type` column and `equipped` boolean already exist). Coins (`UserProgress.virtual_coins`) and premium (`is_premium` / `usePremiumPaywall`) are reused unchanged.

---

## 3. Data model & per-category equip (backend)

**Model (no migration):** `CosmeticItem.type` (String, exists; today only `"accessory"`) gains two values: **`"background"`** and **`"skin"`**. `UserCosmetic` (`(user_id, item_id)` PK, `equipped` bool, `unlocked_at`) is unchanged.

**Equip change** — `backend/app/routers/cosmetics.py`:
- Today `POST /cosmetics/{item_id}/equip` sets `equipped=False` on **all** the user's items, then equips the target (global single-slot; proven by `test_equip_is_exclusive`).
- New: it unequips **only the user's items whose `CosmeticItem.type` matches the target's type** (a join), then equips the target. Result: one equipped item **per category**.
- `POST /cosmetics/unequip` takes a **required** `type` query param and unequips only that category (e.g. `unequip?type=background`). The old no-arg "clear all" form is dropped (the Shop already toggles equip per item, so a global clear isn't needed).

**Shop response** — `GET /cosmetics` already returns each item with `type`, `owned`, `equipped`, `can_buy`. The frontend derives "equipped per category" by filtering `equipped` items by `type`; no response-shape change required beyond ensuring `type` is present in `CosmeticOut` (add it if absent).

**Seed** — `backend/app/seed/cosmetics.py`: extend `CATALOG` with ~5 `background` and ~5 `skin` entries (each `slug`, `name`, a representative `emoji` for the shop-card thumbnail, `coin_cost`, `is_premium`, `type`). A **free/premium mix** mirroring today's accessories (≈6 free / 2 premium across the new items). Idempotent upsert-by-slug as today.

---

## 4. Penny render (frontend)

`frontend/src/components/child/ui/Penny.tsx` is a hand-crafted SVG (`viewBox 0 0 56 56`) that already overlays the equipped accessory via an `ACCESSORY` slug→`{glyph,x,y,size}` map. Extend it:

- **Backgrounds:** a `BACKGROUND` slug→scene map rendering a self-contained scene **behind** the body group (a layered inline-SVG illustration, or a bundled optimized image drawn into an SVG `<image>` — see §6). Keyed by slug; unknown slug renders nothing (forward-compatible, like accessories).
- **Skins:** a `SKIN` slug→`{gradFrom, gradTo}` map that recolours Penny's body gradient `<defs>`. Default (no skin) keeps today's pink.
- **Props:** keep the existing `accessory?: string | null`; add optional `skin?: string | null` and `background?: string | null` (backwards-compatible — existing call sites keep working). 
- **Equipped → Penny:** a `useEquippedCosmetics()` hook returns `{ accessory, skin, background }` equipped slugs (derived from the cosmetics query). Penny instances that represent the child's look consume it.
  - **Skin + accessory render everywhere Penny appears** (the `PennyFAB`, `CoachPanel` header, showcase).
  - **Backgrounds render only on the avatar showcase** (and optionally the coach panel header) — a scene behind the small FAB Penny would be cluttered; the FAB passes `background={null}`.

---

## 5. The avatar showcase ("Penny's Shop & Avatar")

`frontend/src/pages/child/Shop.tsx` grows into the showcase (no new bottom tab; reached exactly like Shop today):
- **Top:** a **large layered Penny** rendering the child's equipped background + skin + accessory together — the "look at my Penny" moment. Carries an accessible description of what's equipped.
- **Category tabs:** **Accessories · Backgrounds · Skins** (a proper ARIA tablist). Each tab lists that `type`'s items using the existing item card (emoji/name/cost + Buy / Wear / Take off / premium-locked states), filtered by `type`. Buy + equip reuse the existing `useBuyCosmetic` / `useEquipCosmetic` mutations; equip is a toggle (equip, or unequip if already on).
- Coin balance stays in the header (existing).

This keeps one cohesive surface for admire + buy + dress-up and reuses the working buy/equip flow.

---

## 6. Graphics & assets

- **Skins:** pure **SVG gradient recolours** — asset-free, crisp at any size, trivial to theme. No external assets.
- **Backgrounds:** delivered as **lightweight, self-contained scene art keyed by slug** — preferably hand-authored **inline SVG scenes** (asset-free, retina-crisp, recolour-friendly); if a richer illustrated look is wanted, a small fixed set of **optimized bundled images** (WebP in the frontend build) is acceptable — **no R2 / object storage needed** for this fixed catalog. Keep each background small (target ≤~20 KB) so the showcase stays fast.
- **Visual design:** the actual background scenes and the skin palette will be designed/refined using **Google Nano Banana** (image generation) and/or **Figma** for visual quality and a coherent kid-friendly style; concept directions can be generated for selection before they're committed. The mascot and brand style (sky-blue + Penny) are the reference.

---

## 7. Accessibility, testing, boundaries

- **A11y (WCAG 2.2 AA):** the showcase Penny has an accessible text description of the equipped look; category tabs are a keyboard-operable tablist; equip state is conveyed by **text** ("Wear" / "Worn"), never colour alone; ≥44px tap targets; `vitest-axe` on the new/changed UI; backgrounds are decorative (`aria-hidden`) with the look summarised in the Penny description.
- **Backend tests:** equipping a `background` leaves the equipped `accessory` untouched; equipping a second `background` swaps it (one-per-type); cross-type independence; buy + premium-gate behaviour unchanged; seed idempotency for the new items.
- **Frontend tests:** showcase renders the layered Penny from equipped state; category tabs filter by `type`; equip/unequip toggles per category; premium-locked item routes to the paywall; axe-clean. iOS-visible → `npm run build && npx cap sync ios`.
- **Out of scope (restated):** app/profile themes (own spec); Penny outfits beyond recolour.

---

## 8. Decisions captured (from brainstorm)

- Scope: **avatar + backgrounds + skins now**; **app themes = separate later spec**.
- Home for the avatar: **grow `/shop` into "Penny's Shop & Avatar"** (no new tab).
- Equip: **per-category** (one accessory + one background + one skin at once) via type-scoped unequip; **no data migration**.
- Skins: **body-colour recolour** (not full outfits). Backgrounds: **showcase only**, not the mini FAB.
- New items: **free/premium mix** like today's accessories; coins + premium gate reused as-is.
- Graphics produced/refined with **Nano Banana / Figma**; backgrounds are bundled lightweight scene art (no R2).
