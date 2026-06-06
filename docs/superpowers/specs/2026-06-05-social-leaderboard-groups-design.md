# Social Leaderboards — Parent-Mediated Groups (Design Spec)

**Date:** 2026-06-05
**Status:** Approved (design); ready for implementation plan
**Origin:** Product-review item 3, sub-project **3B** (engagement bets; after 3A re-engagement ✅ and 3C age-tier ✅). Replaces the demotivating global anonymous leaderboard with friends/class groups.
**Scope:** Backend (group model + parent-managed membership + scoped leaderboard) + frontend (parent group management UI + child group-board view). COPPA-sensitive — connecting children — so the privacy model is the foundation of the design.

---

## Problem

The only social surface is a **global, anonymous** weekly leaderboard (username + country + weekly XP, top 50). For 10–18s, "social" means friends/class, not strangers — and a global board you can never top demotivates. We want a friends/class leaderboard **without** connecting children to strangers or collecting new data.

## Decisions (locked with the user)

- **Adult-mediated groups, fully parent-managed.** Children never create, join, or discover anything; they only **view** a group leaderboard. Parents create groups and authorize membership.
- **Per-child authorization by that child's own parent.** Parent A creates a group + shares the code out-of-band; each other child's parent enters the code in **their** parent dashboard to add **their own** child. A parent can only add a child they own.
- **Minimal data shared:** group leaderboard shows only `username` + weekly XP (no PII, no country, no messaging, no profiles). Code-gated — only member families can see it.
- **Keep the existing global board** (below the group board on child Stats) — not replaced in v1.
- **Defaults:** group size cap 30, groups-per-parent cap 10 (centralized, retunable).

## Non-goals (deferred / rejected)

- No child-initiated action of any kind (no child code entry, no child-to-child invites, no discovery, no messaging).
- No group-scoped **challenges** in v1 (the leaderboard is the core; challenges are a later add-on).
- No teacher/admin classrooms (a later B2B channel).
- No new PII; no real names; the username (already child/parent-chosen) is the only identifier shown.

---

## Architecture

### Backend — data model + migration (two tables)

`LeaderboardGroup` (`app/models/group.py`):
| Column | Type | Notes |
|---|---|---|
| `id` | UUID | pk |
| `name` | String(60) | parent-chosen group name |
| `code` | String(12) | unique, indexed — short shareable join code |
| `owner_parent_email` | String(255) | indexed; the creating parent |
| `created_at` | DateTime(tz) | server default now() |

`GroupMembership` (same module):
| Column | Type | Notes |
|---|---|---|
| `id` | UUID | pk |
| `group_id` | UUID | FK → `leaderboard_groups.id` `ondelete=CASCADE`, indexed |
| `user_id` | UUID | FK → `users.id` `ondelete=CASCADE`, indexed (the child) |
| `added_by_parent_email` | String(255) | the parent who added this child |
| `created_at` | DateTime(tz) | server default now() |
| — | UniqueConstraint | `(group_id, user_id)` — no duplicate membership |

One hand-written, chained Alembic migration (check `alembic heads` first; current head `a1b2c3d4e5f7`) creating both tables + indexes.

### Backend — parent endpoints (`app/routers/parent.py`, gated by `get_current_parent`)

- `POST /parent/groups` — body `{name}`; generates a unique `code`; creates the group owned by `parent_email`; returns `{id, name, code}`. Enforces the groups-per-parent cap (owned groups).
- `POST /parent/groups/join` — body `{code, child_user_id}`; resolves the group by `code` (404 if unknown); verifies the child is owned by this parent (reuse `_get_owned_child`); enforces the group-size cap; inserts `GroupMembership` (idempotent on the unique constraint → 200/409 on duplicate). Returns the updated group.
- `GET /parent/groups` — groups the parent **owns** plus groups their **children** are in; each with `{id, name, code (owner only), members: [{child_user_id, username}]}`.
- `DELETE /parent/groups/{group_id}/members/{child_user_id}` — remove a child the parent owns from a group (their own child only).
- `DELETE /parent/groups/{group_id}` — owner-only: delete the group (cascade removes memberships).

All inputs validated; ownership enforced on every route (no IDOR — a parent can only touch groups they own or memberships of children they own). CSRF applies as for the rest of `/parent`.

### Backend — child endpoint (`app/routers/gamification.py` or a new `groups` router, `get_current_user`)

- `GET /groups/leaderboard` → for the authenticated **child**: find the groups they're a member of; for each, return `{group_id, group_name, entries: [{username, xp_this_week, is_me}]}` ordered by weekly XP desc. Reuses the existing weekly-XP computation (sum of `Lesson.xp_reward` from `LessonCompletion` since Monday) **filtered to the group's member `user_id`s**. Returns `[]` when the child is in no group.

### Frontend

- **Parent dashboard** (`frontend/src/pages/parent/...` + a new `GroupsCard`/section): create a group (name → reveals the code with a copy button + share hint), "Add a child to a group" (enter code + pick one of *my children*), list my groups + their members, remove a child, delete a group. Uses the parent API client.
- **Child Stats** (`frontend/src/pages/child/Stats.tsx` + a `GroupLeaderboard` component): render the child's group leaderboard(s) at the top (highlighting `is_me`); if the child is in no group, a gentle prompt: "Ask a parent to set up a group so you can compare with friends." Keep the existing global top-50 board below.

## Data flow

1. Parent A `POST /parent/groups {name}` → group + code; shares code out-of-band.
2. Parent B `POST /parent/groups/join {code, child_user_id}` (their own child) → membership row.
3. Child opens Stats → `GET /groups/leaderboard` → group boards scoped to members' weekly XP.

## Error handling & edge cases

- **Unknown code** → 404; **child not owned by parent** → 403/404 (mirror existing `_get_owned_child` behaviour); **duplicate membership** → idempotent (200) or 409, no dup row.
- **Caps exceeded** → 409 with a clear message (group full / too many groups).
- **Code collision** on create → regenerate (retry a few times) before failing.
- **Group with no recent activity** → members appear with `xp_this_week = 0` (left join), so the board still lists everyone, not just those who practised.
- **Child removed / group deleted** → `GET /groups/leaderboard` simply stops returning it; cascade deletes memberships.
- **A child in multiple groups** → multiple boards returned; the child UI lists each.

## Testing

**Backend (pytest, `loop_scope="session"` + `client`/`admin_client`/`db_session`):**
- Create group → returns a code; groups-per-parent cap enforced.
- Join: a parent can add their **own** child; **cannot** add another parent's child (403/404); duplicate join is idempotent; group-size cap enforced.
- `GET /groups/leaderboard` (child) returns ONLY that child's group members' weekly XP, ordered desc, with `is_me`; empty when in no group; a non-member's XP never leaks in.
- Remove member / delete group (owner-only; cascade).
- Code uniqueness/collision-regeneration.

**Frontend (vitest + vitest-axe):**
- Parent GroupsCard: create shows the code; add-child flow posts the code + child id; list renders members; axe-clean.
- Child GroupLeaderboard: renders entries with `is_me` highlighted; shows the no-group prompt when empty; axe-clean.

## Configurability (single source of truth — a hard requirement)

All tunables in one named place so future changes are one-line edits:

**Backend — `app/services/group_config.py` (new):**
```python
GROUP_SIZE_CAP = 30          # max children per group
GROUPS_PER_PARENT_CAP = 10   # max groups one parent may own
GROUP_CODE_LENGTH = 8        # join-code length
GROUP_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # unambiguous (no O/0/I/1/L)
LEADERBOARD_WEEK_START_WEEKDAY = 0  # Monday — when the weekly window resets
```
The group service + endpoints import these; no inline literals. The weekly-window constant is shared with (or mirrors) the existing global-leaderboard reset so both can be retuned together.

**Frontend — `src/lib/groupConfig.ts` (new):** any client-side caps/labels/empty-state copy referenced by the parent + child UIs live here (e.g. the no-group prompt text, max-name length), so copy/limits are retunable without touching components.

Tests reference these constants (e.g. import `GROUP_SIZE_CAP`) rather than duplicating the numbers, so retuning a value never silently breaks an expectation.

## Constraints

- DB change = hand-written, chained Alembic migration (check `alembic heads`). Async tests use `loop_scope="session")` + the `client`/`admin_client`/`db_session` fixtures.
- Object-level access control on every route (no IDOR); parents touch only their own groups/children. It's a kids' app — minimal data, code-gated, parent-authorized; **no new PII**.
- Backend verify: `ruff` + `pytest`. Frontend: `npx tsc -b`, `npm run lint`, `npm test` (vitest + vitest-axe), `npm run build`. WCAG 2.2 AA; iOS inputs ≥16px.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway + Vercel deploy on green CI (6 jobs). No `.env` access. iOS shows the same web bundle → a `cap sync ios` at close-out (no native change).

## Alternatives considered

- **Child-to-child friend invites:** richer but directly connects children — far higher COPPA burden (verifiable consent, discovery/safety, blocking). Rejected for v1.
- **Child joins by code (parent-enabled):** more child agency but adds a consent toggle + a child-enters-code surface. Rejected in favour of fully parent-mediated.
- **Teacher/admin classrooms:** a strong B2B channel but heavier and less aligned with a friends-and-family beta. Deferred.
- **Replacing the global board:** kept for v1 to minimise disruption; the group board sits above it.
