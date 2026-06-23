# Avatar & Penny Cosmetics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an avatar showcase plus two new spendable cosmetic categories — Penny **scene backgrounds** and **colour skins** — with **per-category equip**, by growing the existing `/shop` page into "Penny's Shop & Avatar".

**Architecture:** Reuse the M8 cosmetics system. The only backend change is making equip/unequip scope to a `CosmeticItem.type` (one equipped item per category) and exposing `type` in the API; no data migration. The Penny SVG gains a **skin** (body-gradient recolour); a new **AvatarStage** wrapper renders the equipped **background** scene behind a large Penny on the showcase. Backgrounds + skins are hand-authored inline SVG (no binary assets, no R2).

**Tech Stack:** FastAPI + SQLAlchemy async (backend); React + Vite + TS + TanStack Query + react-i18next + Tailwind (frontend). CI: backend ruff + pytest; frontend tsc + eslint + vitest + vitest-axe + build.

**Reference spec:** `docs/superpowers/specs/2026-06-23-avatar-penny-cosmetics-design.md`

## Global Constraints

- **No DB migration.** `CosmeticItem.type` (String) and `UserCosmetic.equipped` already exist. New `type` values: `"background"`, `"skin"` (existing: `"accessory"`).
- **Per-category equip:** `POST /cosmetics/{id}/equip` unequips only the user's items of the **same type** as the target, then equips it → one equipped per category. `POST /cosmetics/unequip` takes a **required** `type` query param and unequips only that category. The old no-arg "clear all" is removed; the one frontend caller is updated.
- Coins (`UserProgress.virtual_coins`) and premium (`is_premium` / `usePremiumPaywall`) are reused **unchanged**. New items are a free/premium mix like today's 8 accessories.
- **Skin** = body-gradient recolour on the Penny SVG; mood still drives eyes/mouth. **Backgrounds** render **only on the showcase** (AvatarStage), never on the mini FAB/coach Penny. Skin + accessory render **everywhere** Penny appears.
- Kids' app, WCAG 2.2 AA: equip state conveyed by **text** (not colour alone); category tabs are a keyboard tablist; ≥44px targets; decorative art `aria-hidden`; `vitest-axe` on new/changed UI. iOS-visible → `npm run build && npx cap sync ios`.
- Backgrounds/skins are **hand-authored inline SVG** (no bundled binaries, no R2). Visual style references the sky-blue + Penny brand (a Nano Banana / Figma art-direction pass happens separately; the inline-SVG scenes match the agreed direction).
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + shared `client`/`db_session` fixtures (see `backend/tests/test_cosmetics_api.py`). Commit to `main`; messages end `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

**Backend modify:** `app/routers/cosmetics.py` (equip/unequip per-type + `type` in `CosmeticOut`/`_shop_state`); `app/seed/cosmetics.py` (add background + skin items). **Test:** `backend/tests/test_cosmetics_api.py` (+ per-category cases), `backend/tests/test_cosmetics_seed.py`.
**Frontend create:** `src/components/child/ui/AvatarStage.tsx` (background scene + layered Penny), `src/components/child/ui/pennyScenes.tsx` (the `BACKGROUND` scene map + `SKIN` palette map). **Tests** alongside.
**Frontend modify:** `src/api/cosmetics.ts` (add `type`; `useEquippedCosmetics()`; equip/unequip-by-type mutation); `src/components/child/ui/Penny.tsx` (`skin` prop + recolour); `src/pages/child/Shop.tsx` (showcase + category tabs); `src/components/child/PennyFAB.tsx` + `src/components/child/CoachPanel.tsx` (pass the equipped `skin`); `src/locales/en/child.json` (shop/avatar strings).

---

### Task 1: Backend — per-category equip + unequip-by-type + `type` in API

**Files:** Modify `backend/app/routers/cosmetics.py`. Test: `backend/tests/test_cosmetics_api.py`.

**Interfaces — Produces:** `CosmeticOut` gains `type: str`. `POST /cosmetics/{id}/equip` is type-scoped. `POST /cosmetics/unequip?type=<t>` unequips one category.

- [ ] **Step 1: Write failing tests** (add to `test_cosmetics_api.py`; mirror its existing seeding of `CosmeticItem` + `UserCosmetic`):

```python
async def test_equip_is_per_category(client, db_session):
    # Seed one accessory + one background, both owned by the logged-in user.
    # Equip the accessory, then equip the background.
    # ASSERT both remain equipped (different categories don't unequip each other).
    ...

async def test_equip_swaps_within_category(client, db_session):
    # Two backgrounds owned + equipped one; equip the second.
    # ASSERT only the second background is equipped (same-category swap).
    ...

async def test_unequip_by_type_only_clears_that_type(client, db_session):
    # Accessory + background both equipped; POST /cosmetics/unequip?type=background.
    # ASSERT background unequipped, accessory still equipped.
    ...

async def test_shop_item_exposes_type(client, db_session):
    r = await client.get("/cosmetics")
    assert all("type" in it for it in r.json()["items"])
```

> Build users/items exactly as the existing tests in this file do (copy the helper that creates a `User` + owned `UserCosmetic`); add a `type=` when creating the seed `CosmeticItem`s.

- [ ] **Step 2: Run** `cd backend && python -m pytest tests/test_cosmetics_api.py -v` → new tests FAIL.

- [ ] **Step 3: Implement.** Add `type` to `CosmeticOut` and `_shop_state`:

```python
# in class CosmeticOut(BaseModel): add
    type: str
# in _shop_state(...) CosmeticOut(...): add
        type=item.type,
```

Make equip type-scoped (replace the global unequip in `equip_item`):

```python
from app.models.cosmetics import CosmeticItem, UserCosmetic  # CosmeticItem already importable

    target = await session.get(CosmeticItem, item_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    # One equipped per category: unequip only the user's SAME-TYPE items.
    await session.execute(
        update(UserCosmetic)
        .where(
            UserCosmetic.user_id == current_user.id,
            UserCosmetic.item_id.in_(
                select(CosmeticItem.id).where(CosmeticItem.type == target.type)
            ),
        )
        .values(equipped=False)
    )
    owned.equipped = True
    await session.commit()
    return {"status": "ok"}
```

Replace `unequip_all` with a type-scoped version:

```python
@router.post("/unequip")
async def unequip_type(
    type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(UserCosmetic)
        .where(
            UserCosmetic.user_id == current_user.id,
            UserCosmetic.item_id.in_(
                select(CosmeticItem.id).where(CosmeticItem.type == type)
            ),
        )
        .values(equipped=False)
    )
    await session.commit()
    return {"status": "ok"}
```

- [ ] **Step 4: Run** the tests → PASS (confirm the existing `test_equip_is_exclusive` is updated/removed — global exclusivity is intentionally replaced by per-category; update that test to assert per-category behaviour).
- [ ] **Step 5: Commit** `feat(cosmetics): per-category equip + unequip-by-type + type in API`.

---

### Task 2: Backend — seed backgrounds + skins

**Files:** Modify `backend/app/seed/cosmetics.py`. Test: `backend/tests/test_cosmetics_seed.py`.

**Interfaces — Produces:** ~5 `background` + ~5 `skin` catalog items (idempotent upsert by slug). Slugs must match the frontend `BACKGROUND`/`SKIN` maps (Task 5/4): backgrounds `bg_beach,bg_space,bg_vault,bg_city,bg_forest`; skins `skin_pink,skin_sky,skin_mint,skin_gold,skin_lavender`.

- [ ] **Step 1: Write failing test** asserting the seed includes the new types and is idempotent:

```python
# backend/tests/test_cosmetics_seed.py
import pytest
from sqlalchemy import select
from app.models.cosmetics import CosmeticItem
from app.seed.cosmetics import seed_cosmetics

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_seed_has_new_categories_idempotent(db_session):
    await seed_cosmetics(db_session)
    await seed_cosmetics(db_session)  # idempotent
    rows = (await db_session.scalars(select(CosmeticItem))).all()
    types = {r.type for r in rows}
    assert {"accessory", "background", "skin"} <= types
    slugs = [r.slug for r in rows]
    assert len(slugs) == len(set(slugs))  # no dupes
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — extend `CATALOG` (each existing entry already lacks `type`; the seed sets `type="accessory"` today — see below) and add the new items with explicit `type`:

```python
# Existing accessory entries stay; add to CATALOG:
    {"slug": "bg_beach", "name": "Beach Day", "emoji": "🏖️", "coin_cost": 120, "is_premium": False, "type": "background"},
    {"slug": "bg_forest", "name": "Forest", "emoji": "🌲", "coin_cost": 120, "is_premium": False, "type": "background"},
    {"slug": "bg_city", "name": "City Lights", "emoji": "🏙️", "coin_cost": 180, "is_premium": False, "type": "background"},
    {"slug": "bg_space", "name": "Outer Space", "emoji": "🚀", "coin_cost": 250, "is_premium": False, "type": "background"},
    {"slug": "bg_vault", "name": "Money Vault", "emoji": "🏦", "coin_cost": 400, "is_premium": True, "type": "background"},
    {"slug": "skin_pink", "name": "Classic Pink", "emoji": "🩷", "coin_cost": 0, "is_premium": False, "type": "skin"},
    {"slug": "skin_sky", "name": "Sky Blue", "emoji": "🔵", "coin_cost": 90, "is_premium": False, "type": "skin"},
    {"slug": "skin_mint", "name": "Mint", "emoji": "🟢", "coin_cost": 90, "is_premium": False, "type": "skin"},
    {"slug": "skin_gold", "name": "Gold", "emoji": "🟡", "coin_cost": 300, "is_premium": False, "type": "skin"},
    {"slug": "skin_lavender", "name": "Lavender", "emoji": "🟣", "coin_cost": 250, "is_premium": True, "type": "skin"},
```

The existing `CATALOG` entries (accessories) must also carry `type="accessory"` explicitly (today `seed_cosmetics` sets it via `CosmeticItem(type="accessory", **spec)`). Refactor so `type` comes from each spec: change `session.add(CosmeticItem(type="accessory", **spec))` → `session.add(CosmeticItem(**spec))` and add `"type": "accessory"` to every existing accessory spec. Keep the upsert refreshing `type` too.

> `skin_pink` is the default look at cost 0 (a child can always "own" the classic). Confirm whether a 0-cost item is buyable with the existing buy flow; if cost 0 needs special handling, make `skin_pink` the implicit default (equipped-by-absence) instead and drop it from the catalog — the plan's frontend treats "no skin equipped" as classic pink anyway (Task 4), so a 0-cost catalog row is optional.

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(cosmetics): seed Penny backgrounds + skins`.

---

### Task 3: Frontend cosmetics API — `type`, per-category equipped hook, equip/unequip-by-type

**Files:** Modify `frontend/src/api/cosmetics.ts`. Test: `frontend/src/api/__tests__/cosmetics.test.ts` (create if absent).

**Interfaces — Produces:** `CosmeticItem` gains `type: string`. `useEquippedCosmetics(): { accessory: string|null; skin: string|null; background: string|null }`. `useEquipCosmetic()` mutation accepts `{ equip: string } | { unequip: string /* type */ }`.

- [ ] **Step 1: Write failing tests** (spy on `apiFetch`): equipping posts `/cosmetics/{id}/equip`; unequipping a type posts `/cosmetics/unequip?type=background`.
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/api/__tests__/cosmetics.test.ts` → FAIL.
- [ ] **Step 3: Implement:**

```typescript
export type CosmeticItem = {
  id: string; slug: string; name: string; emoji: string; type: string;
  coin_cost: number; is_premium: boolean; owned: boolean; equipped: boolean; can_buy: boolean;
};

export function useEquippedCosmetics(): { accessory: string | null; skin: string | null; background: string | null } {
  const { data } = useCosmetics();
  const bySlug = (type: string) => data?.items.find((i) => i.equipped && i.type === type)?.slug ?? null;
  return { accessory: bySlug('accessory'), skin: bySlug('skin'), background: bySlug('background') };
}

export function useEquipCosmetic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { equip: string } | { unequip: string }) =>
      'equip' in v
        ? apiFetch(`/cosmetics/${v.equip}/equip`, { method: 'POST' })
        : apiFetch(`/cosmetics/unequip?type=${encodeURIComponent(v.unequip)}`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SHOP_KEY }),
  });
}
```

Keep `useEquippedAccessory()` as a thin wrapper over `useEquippedCosmetics().accessory` (back-compat for current callers) OR migrate its callers in Task 6.

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(cosmetics): frontend type + per-category equipped hook + equip/unequip-by-type`.

---

### Task 4: Penny SVG — `skin` recolour

**Files:** Modify `frontend/src/components/child/ui/Penny.tsx`; create `frontend/src/components/child/ui/pennyScenes.tsx` (start it here with the `SKIN` map). Test: `frontend/src/components/child/ui/__tests__/Penny.skin.test.tsx`.

**Interfaces — Produces:** `Penny` gains `skin?: string | null`. `SKIN: Record<string,[string,string]>` in `pennyScenes.tsx`.

- [ ] **Step 1: Write failing test** — render `<Penny skin="skin_sky" />`; assert the body gradient stops use the sky palette (query the `<stop>` colours), and that mood still controls the eyes (e.g. `<Penny skin="skin_sky" mood="excited" />` still renders the excited markers).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — in `pennyScenes.tsx`:

```tsx
// Skin = Penny body-gradient recolour, keyed by CosmeticItem.slug. No skin → classic.
export const SKIN: Record<string, [string, string]> = {
  skin_pink: ['#f9a8d4', '#db2777'],      // classic pink
  skin_sky: ['#38bdf8', '#2563eb'],
  skin_mint: ['#6ee7b7', '#059669'],
  skin_gold: ['#fcd34d', '#d97706'],
  skin_lavender: ['#c4b5fd', '#7c3aed'],
};
```

In `Penny.tsx`, accept `skin?: string | null` and prefer it over the mood gradient for the BODY colour (mood keeps driving eyes/mouth):

```tsx
import { SKIN } from './pennyScenes';
// ...props add: skin?: string | null
  const skinPair = skin ? SKIN[skin] : undefined;
  const [from, to] = skinPair ?? MOOD_GRADIENT[mood];
```

(No other change; `accessory` and `mood` behaviour preserved.)

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(penny): skin body-recolour support`.

---

### Task 5: AvatarStage — background scene + layered Penny

**Files:** Create `frontend/src/components/child/ui/AvatarStage.tsx`; add the `BACKGROUND` scene map to `frontend/src/components/child/ui/pennyScenes.tsx`. Test: `frontend/src/components/child/ui/__tests__/AvatarStage.test.tsx`.

**Interfaces — Consumes:** `Penny` (Task 4), `BACKGROUND` map. **Produces:** `<AvatarStage background={slug|null} skin={slug|null} accessory={slug|null} />` — a framed stage rendering the background scene behind a large Penny.

- [ ] **Step 1: Write failing test** — `<AvatarStage background="bg_space" skin="skin_sky" accessory="crown" />` renders the Penny (role/test-id) over a scene element keyed to space; axe-clean; backgrounds are `aria-hidden` and the stage has an accessible label describing the look.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** `BACKGROUND` scenes are compact inline SVGs (designed with Nano Banana/Figma as reference; start with clean gradient scenes, polished in the art pass). Example two scenes — author all five in this shape:

```tsx
// pennyScenes.tsx — BACKGROUND scenes (viewBox 0 0 100 100, drawn behind Penny).
export const BACKGROUND: Record<string, React.ReactNode> = {
  bg_beach: (
    <>
      <rect width="100" height="100" fill="#7dd3fc" />
      <rect y="62" width="100" height="38" fill="#fde68a" />
      <circle cx="78" cy="22" r="12" fill="#fde047" />
    </>
  ),
  bg_space: (
    <>
      <rect width="100" height="100" fill="#1e1b4b" />
      <circle cx="20" cy="18" r="1.5" fill="white" />
      <circle cx="64" cy="12" r="1.5" fill="white" />
      <circle cx="82" cy="40" r="1.5" fill="white" />
      <circle cx="30" cy="70" r="10" fill="#a78bfa" />
    </>
  ),
  // bg_forest, bg_city, bg_vault follow the same shape (author each).
};
```

`AvatarStage.tsx`:

```tsx
import { Penny } from './Penny';
import { BACKGROUND } from './pennyScenes';

export function AvatarStage({
  background, skin, accessory, label,
}: { background?: string | null; skin?: string | null; accessory?: string | null; label: string }) {
  const scene = background ? BACKGROUND[background] : null;
  return (
    <div role="img" aria-label={label}
      className="relative mx-auto flex h-44 w-44 items-center justify-center overflow-hidden rounded-3xl border border-brand-200 bg-brand-50">
      {scene && (
        <svg viewBox="0 0 100 100" aria-hidden="true" className="absolute inset-0 h-full w-full">{scene}</svg>
      )}
      <Penny size={120} skin={skin} accessory={accessory} className="relative" />
    </div>
  );
}
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(avatar): AvatarStage with background scene + layered Penny`.

---

### Task 6: Shop → "Penny's Shop & Avatar" (showcase + category tabs) + skin everywhere

**Files:** Modify `frontend/src/pages/child/Shop.tsx`, `frontend/src/components/child/PennyFAB.tsx`, `frontend/src/components/child/CoachPanel.tsx`, `frontend/src/locales/en/child.json`. Test: `frontend/src/pages/child/__tests__/Shop.test.tsx` (extend existing if present).

**Interfaces — Consumes:** `useEquippedCosmetics` + `useEquipCosmetic` (Task 3), `AvatarStage` (Task 5).

- [ ] **Step 1: Write failing tests** — Shop renders `AvatarStage` from equipped state; renders three category tabs (Accessories/Backgrounds/Skins); switching a tab filters the grid by `type`; clicking "Take off" on an equipped item calls equip mutation with `{ unequip: <type> }`; axe-clean.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In `Shop.tsx`:
  - Replace `const equipped = ...single...` with `const eq = useEquippedCosmetics();`.
  - Render `<AvatarStage background={eq.background} skin={eq.skin} accessory={eq.accessory} label={t('shop.avatarLabel', ...)} />` under the title.
  - Add a tablist (`role="tablist"`) with three tabs; `const [tab, setTab] = useState<'accessory'|'background'|'skin'>('accessory')`; grid maps `data.items.filter(i => i.type === tab)`.
  - In `onAction`, change the equipped toggle from `equip.mutate(item.equipped ? null : item.id)` to:
    ```tsx
    equip.mutate(item.equipped ? { unequip: item.type } : { equip: item.id });
    ```
  - Add i18n keys: `shop.tabs.{accessory,background,skin}`, `shop.avatarLabel`, and reuse existing item-label keys.
- [ ] **Step 4: Show the equipped skin everywhere** — `PennyFAB.tsx` and `CoachPanel.tsx` currently render `<Penny accessory={useEquippedAccessory()} />` (or similar). Change them to pull `const { accessory, skin } = useEquippedCosmetics();` and pass `<Penny accessory={accessory} skin={skin} />` (NO background — those two are the mini contexts). Leave branding-only Penny instances (login/auth) unchanged.
- [ ] **Step 5: Run** `npx vitest run` for the touched tests + `npx tsc --noEmit && npm run lint && npm run build` → all clean. **Step 6: Commit** `feat(avatar): Penny's Shop & Avatar showcase + category tabs + skin everywhere`.

---

### Task 7: Verify + native sync + docs + push

- [ ] **Step 1: Backend gates** — `cd backend && ruff check . && python -m pytest -q` (report counts; isolate any pre-existing non-cosmetics failures).
- [ ] **Step 2: Frontend gates** — `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run build` (the ~70 `.env.local` local-only failures are pre-existing — report cosmetics/avatar tests distinctly).
- [ ] **Step 3:** `cd frontend && npx cap sync ios`.
- [ ] **Step 4: Docs** — `docs/MASTER-BACKLOG.md` entry (avatar showcase + per-category equip + backgrounds/skins, **no migration**, new shop tabs; note app themes are a separate future spec); mention in `AGENTS.md` if it lists cosmetics.
- [ ] **Step 5: Commit docs.**
- [ ] **Step 6 (controller, not the implementer):** there is **no migration** in this plan, so no prod-snapshot question is required — push, then the manual Vercel prod deploy + alias.

---

## Self-Review (completed)

- **Spec coverage:** per-category equip (Task 1), backgrounds+skins as categories (Tasks 2,4,5), avatar showcase = grown Shop + tabs (Task 6), skin everywhere / background showcase-only (Tasks 4–6), coins+premium reused (no change), a11y + tests throughout, **no migration**, app-themes excluded. The graphics are inline SVG (Task 5) per the spec's "lightweight, no R2"; the Nano Banana / Figma art-direction pass is a separate controller-driven polish, not a code task.
- **Placeholders:** none — code is concrete. The two "confirm" notes (0-cost `skin_pink` handling; `test_equip_is_exclusive` update) are explicit decisions for the implementer, not deferred work. Background scenes ship as functional inline SVG; the art pass replaces/refines them without changing the interface (`BACKGROUND` map keyed by slug).
- **Type consistency:** `type` field threads through `CosmeticOut` (Task 1) → `CosmeticItem` FE type (Task 3) → tab filter (Task 6); equipped slugs `{accessory,skin,background}` from `useEquippedCosmetics` (Task 3) feed `AvatarStage`/`Penny` (Tasks 4,5,6); equip mutation shape `{equip}|{unequip}` consistent Tasks 3 & 6; slugs match between seed (Task 2) and `BACKGROUND`/`SKIN` maps (Tasks 4,5).
