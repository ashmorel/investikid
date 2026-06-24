# Leaderboard Scope & Privacy — Design

**Status:** Design (approved in brainstorming 2026-06-24) — pending spec review.

**Goal:** Give children one leaderboard they can view at three scopes — **My Market**, **Global**, and **Friends** — ranked by **XP** or **Arcade Points**, while making public visibility safe for a kids' app: a non-identifying auto-generated handle, parent-granted consent, and a child hide switch.

## Why

Two leaderboards already ship and are live in the Stats page:
- **Global weekly-XP board** (`gamification.py::weekly_leaderboard`, `GET /leaderboard`) — top 50 across **all markets**, exposing each child's real **username + country**, with **no opt-in**.
- **Friends board** (`group_service.group_leaderboard_for_child`) — XP within a parent-created group, shows username.

Plus a per-market Arcade Points board (`arcade_service.weekly_leaderboard`, `GET /arcade/leaderboard`).

So a global board already exists — but it publishes every child's username + country to the world with no consent, which is the real risk for a COPPA / UK Age-Appropriate-Design-Code product. This work unifies the scopes behind one UI **and** fixes that exposure. The user explicitly asked for the privacy posture ("unless a regulation prevents it").

## Privacy model (the core of this design)

- **Display handle, not username, on public boards.** Add `User.display_handle`: a non-identifying handle auto-generated from curated word lists (`<Adjective><Animal><2-digit>`, e.g. `CleverOtter42`). **Zero free text → no moderation surface.** A child can reroll it. Generated lazily on first need (signup backfill or first leaderboard view).
- **Parent-granted consent, child can hide.** Two booleans on the child user:
  - `leaderboard_consent` — set by the **parent** (default **false**).
  - `leaderboard_hidden` — set by the **child** (default false).
  - A child appears on **public** (Market/Global) boards **iff `leaderboard_consent && !leaderboard_hidden`**.
- **Friends boards are exempt from consent and show the username.** Friend groups are closed and parent-created; members already know each other. Friends scope shows `username` (today's behaviour) and lists all group members regardless of public consent.
- **Country flag** stays (country-level, not individually identifying) on public boards for colour/context.
- **Deletion/erasure:** the existing child-erasure path must also clear the handle and drop the child from boards (covered by deleting the user rows; handle lives on `User`).

## Architecture

One service function + one endpoint replace the three ad-hoc queries.

### Backend

**Migration** (chains off head `a2b3c4d5e6f7`), all on `users`:
- `display_handle TEXT NULL` (unique when set).
- `leaderboard_consent BOOLEAN NOT NULL DEFAULT false`.
- `leaderboard_hidden BOOLEAN NOT NULL DEFAULT false`.

**Handle generator** (`app/services/handles.py`): curated `ADJECTIVES` + `ANIMALS` lists (kid-safe, reviewed) + 2 digits. `generate_handle()` returns a candidate; caller retries on unique collision. `ensure_handle(session, user)` assigns one if missing. No LLM, no free text.

**Unified leaderboard service** (`app/services/leaderboard_service.py`):
```
async def leaderboard(
    session, *, viewer: User, scope: Literal["market","global","friends"],
    metric: Literal["xp","arcade"], limit: int = 50,
) -> list[LeaderboardRow]
```
- `metric` selects the SUM source: **xp** = `Lesson.xp_reward` over `LessonCompletion` since Monday UTC (today's gamification query); **arcade** = `ArcadeScore.points` since Monday UTC (today's arcade query).
- `scope` selects the population + filter:
  - **market** — users with `active_market_code == viewer.active_market_code`, public-visible only.
  - **global** — all users, public-visible only.
  - **friends** — members of the viewer's group(s) (reuse `group_service`), no consent filter.
- **Identity per row:** friends → `username`; market/global → `display_handle`. Both include `country_code`, `points`, and `is_me`.
- "Public-visible" = `leaderboard_consent AND NOT leaderboard_hidden`. The viewer always sees their own row even if not public, marked `is_me` (so a kid who hasn't opted in still sees where they'd rank — their row only).

**Endpoints:**
- `GET /leaderboard?scope=&metric=` → `list[LeaderboardRow]`. Same path as today's `/leaderboard`, now with query params (defaults `scope=market`, `metric=xp`). The **response shape changes** (`username` → `name` which is handle-or-username, plus `points`, `is_me`), so the frontend `useLeaderboard` hook + table are updated in the same change — there is no external API consumer to preserve.
- `GET /me/handle` / `POST /me/handle/reroll` → child views / rerolls handle.
- `PATCH /me/leaderboard-visibility {hidden: bool}` → child hide switch.
- Parent consent: `PATCH /parent/children/{id}/leaderboard-consent {consent: bool}` in `parent.py`, guarded by the existing parental gate.
- Rate-limit the public board reads (reuse existing limiter pattern).

### Frontend

- **`LeaderboardCard`** (replaces the separate `LeaderboardTable` + `GroupLeaderboard` placement in `Stats.tsx`): a scope segmented control (My Market · Global · Friends) + a metric toggle (XP · Arcade). Defaults **Market + XP**. Highlights the `is_me` row. Friends scope renders the group board; if the child is in no group, show the existing "create/join a group" empty state.
- **Child handle UI** (in `ProfileMenu` or Stats): shows the handle with a "New name" reroll and a "Hide me from public leaderboards" switch.
- **Parent dashboard:** a "Show my child on public leaderboards" toggle (off by default) on the child's parent-controls card.

## Data flow

1. Child opens Stats → `LeaderboardCard` requests `scope=market&metric=xp`.
2. Service computes the weekly SUM for the chosen metric, filters by scope + public-visibility, joins identity (handle/username + country), marks `is_me`, returns top N (+ the viewer's own row if outside the top N / not public).
3. Toggling scope/metric refetches with new query params (React Query keys include scope+metric).
4. Parent toggles consent → child becomes eligible for public boards next request. Child hide switch removes them immediately.

## Error handling & edge cases

- No group → Friends scope returns empty + UI empty state (not an error).
- Child not opted in → public boards omit them except their own `is_me` row.
- Handle collision → regenerate (bounded retries) before insert.
- Missing handle at query time → `ensure_handle` backfills.
- Ties → deterministic order (points desc, then handle/username asc) so ranks are stable.

## Testing

- **Generator:** handles match `<Adj><Animal><NN>`, only safe words, uniqueness retry.
- **Service (per scope × metric):** market filters by market; global spans markets; friends = group members; xp vs arcade pull the right metric; **public scopes exclude non-consented / hidden children**; viewer always sees own row; ties deterministic.
- **Consent/visibility:** parent consent on → child appears; child hidden → disappears from public but visible in Friends; identity is handle in public, username in Friends.
- **Endpoints:** auth required; query-param defaults; parent consent endpoint behind the parental gate.
- **Frontend:** scope/metric toggles change the query + highlight is_me; parent + child toggles; `vitest-axe` on the new card.

## Out of scope (YAGNI)

- All-time / monthly boards (weekly only, as today).
- Handle history, vanity handles, or handle marketplace.
- Per-metric separate opt-ins (one consent covers public visibility).
- Notifications about rank changes.

## Open compliance note

This reduces exposure substantially (handle + opt-in), but a **global public board for under-13s should get a compliance review** before launch. The design supports turning public scopes off centrally (consent defaults false; a kill option is just "ignore consent → nobody public") if review demands it.
