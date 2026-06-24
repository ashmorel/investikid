# Avatar Everywhere — Design

**Status:** Design (approved in brainstorming 2026-06-24) — pending spec review.

**Goal:** Make the child's Penny avatar prominent and show-off-able: render it (with their equipped skin + accessories) in the top-left of every page in place of the brand icon, and on every leaderboard row.

**Scope note:** This is the first of two features the user asked for. **Limited-edition collectables is a separate spec** (Feature B) and is explicitly out of scope here.

## Why

Cosmetics (skin + stacked accessories) already ship and render via the `Penny` component + `useEquippedCosmetics()`. But the only place a child sees their decorated Penny is the shop. Surfacing it in the always-visible nav and on the competitive leaderboard turns cosmetics into something kids see constantly and can show off — the payoff that makes collecting them worthwhile. The avatar is non-identifying (a customised pig), so it is safe to show on public boards where real names are not.

## Decisions (from brainstorming)

- Nav top-left shows the child's **Penny avatar + their name** (replacing the InvestiKid icon + wordmark); the element still links to `/home`.
- Leaderboard shows a **mini Penny on every row, on all scopes** (Market / Global / Friends).

## Architecture

### Backend — leaderboard rows carry the user's equipped cosmetics

`leaderboard_service.leaderboard(...)` already selects the top-N users per scope/metric. Extend it to attach each row's equipped cosmetics.

- New dataclass field on `LeaderboardRow`: `avatar: AvatarData` where
  ```python
  @dataclass
  class AvatarData:
      skin: str | None              # equipped skin slug, or None
      accessories: list[str]        # equipped accessory slugs (order stable)
  ```
- New helper `async _avatars_for(session, user_ids: list[uuid]) -> dict[uuid, AvatarData]`:
  one query — `select(UserCosmetic.user_id, CosmeticItem.type, CosmeticItem.slug)` joined on `item_id`, `where(UserCosmetic.equipped.is_(True), UserCosmetic.user_id.in_(user_ids))`. Build per-user `AvatarData` (skin = the single `type=="skin"` slug; accessories = all `type=="accessory"` slugs). Users with nothing equipped get `AvatarData(None, [])`. Backgrounds are ignored (the avatar is the Penny only, no scene, in nav/rows).
- After building the rows (in each of the public path, friends path, and own-row fallback), call `_avatars_for` once for the row user-ids and set `row.avatar`. The own-row fallback uses the viewer's own equipped cosmetics.
- This is **one extra query per leaderboard request** over ≤50 users — chosen over per-row fetches (N requests) and over denormalising a cached avatar onto `users` (premature migration).

**Schema:** `AvatarOut { skin: str | None, accessories: list[str] }`; `LeaderboardRowOut` gains `avatar: AvatarOut`. The endpoint maps `row.avatar` through.

**Privacy:** unchanged — public scopes still only include consented, non-hidden children (Task-3 invariant); the avatar adds no PII.

### Frontend

- **`Penny` component:** already accepts `accessories: string[]` and `skin: string | null`. No change.
- **`TopNav`** (`frontend/src/components/child/TopNav.tsx`): replace the `<img src="/icons/icon-192.png">` + brand wordmark with `<Penny size={32} accessories={…} skin={…} />` + the child's name. Source the cosmetics from `useEquippedCosmetics()` and the name from `useChildSession()` (`session.data?.username`). Keep the `<Link to="/home">` wrapper and an `aria-label` (e.g. "Home — <name>") since the Penny SVG is `aria-hidden`. If cosmetics/session are still loading, render a plain Penny (no accessories) + the name (or empty) — never a broken state.
- **Leaderboard client types** (`frontend/src/api/gamification.ts`): `LeaderboardRow` gains `avatar: { skin: string | null; accessories: string[] }`.
- **`LeaderboardTable`** (`frontend/src/components/child/stats/LeaderboardTable.tsx`): add a leading cell rendering `<Penny size={28} accessories={row.avatar.accessories} skin={row.avatar.skin} />` before the name column. The avatar is `aria-hidden`; the name remains the row's accessible label.

## Data flow

1. Child loads any page → `TopNav` reads `useEquippedCosmetics()` (cached) + `useChildSession()` → renders their Penny + name top-left.
2. Child opens Stats → `LeaderboardCard` → `useLeaderboard(scope, metric)` → the service returns rows each with `avatar` → `LeaderboardTable` renders a mini Penny per row.

## Error handling & edge cases

- A user with no equipped cosmetics → `AvatarData(None, [])` → a plain default Penny (never blank).
- Unknown/legacy slugs → `Penny` already ignores unknown accessory slugs and falls back to the mood gradient for an unknown skin (existing behaviour).
- TopNav before cosmetics load → plain Penny + name; no layout shift beyond the avatar gaining accessories once loaded.
- Leaderboard `avatar` always present in the response (never null); empty arrays are valid.

## Testing

- **Backend (`leaderboard_service`):** a user with an equipped skin + two accessories surfaces as `avatar.skin == slug` and `avatar.accessories == [..]`; a user with nothing equipped → `skin None, accessories []`; backgrounds are excluded from the avatar. Endpoint test: `/leaderboard` rows include an `avatar` object.
- **Frontend:** `TopNav` renders a Penny SVG + the child's name and links to `/home` (and shows equipped accessories when the hook returns them); `LeaderboardTable` renders one Penny per row from `row.avatar`; both `vitest-axe`-clean (avatars `aria-hidden`, names carry the accessible name).

## Out of scope (YAGNI)

- Limited-edition collectables (Feature B — own spec).
- Showing the scene **background** in the nav/leaderboard (avatar = Penny only; backgrounds stay in the shop showcase).
- Animated/large avatar popovers, profile pages, avatar zoom.
- Parent/admin nav avatars (this is the child nav).
