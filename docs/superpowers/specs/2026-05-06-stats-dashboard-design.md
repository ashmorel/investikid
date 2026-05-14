# Plan 5D: Stats Dashboard — Gamification Page

## Goal

Build a gamification dashboard (Stats page) in the child SPA that surfaces badges, weekly challenges, and a leaderboard, giving kids 12–18 visible progress and motivation.

## Scope

- One small backend addition: `GET /badges` endpoint returning all badge definitions
- One new page in the child SPA at `/stats`
- Consumes 4 existing + 1 new backend endpoint
- Eliminates the last COMING_SOON item in TopNav

## Architecture

### Backend Change

Add `GET /badges` to `app/routers/gamification.py` — returns all badge definitions as `list[BadgeOut]` with `earned_at=None`. Authenticated (consistent with other endpoints). ~10 lines.

### New Frontend Files

| Path | Responsibility |
|------|---------------|
| `src/api/gamification.ts` | Typed fetch wrappers for 4 gamification endpoints |
| `src/hooks/useBadges.ts` | TanStack Query hook for `GET /users/me/badges` (earned) |
| `src/hooks/useAllBadges.ts` | TanStack Query hook for `GET /badges` (all definitions) |
| `src/hooks/useChallenges.ts` | TanStack Query hook for `GET /challenges` |
| `src/hooks/useLeaderboard.ts` | TanStack Query hook for `GET /leaderboard` |
| `src/components/child/stats/XpSummary.tsx` | XP/level/streak detail card with level progress bar |
| `src/components/child/stats/BadgeGrid.tsx` | Badge collection — earned (colour) + locked (grey) |
| `src/components/child/stats/ChallengeList.tsx` | Active challenges with progress bars |
| `src/components/child/stats/LeaderboardTable.tsx` | Weekly XP leaderboard with "You" highlight |
| `src/pages/child/Stats.tsx` | Stats page composing all 4 sections |

### Modified Files

| Path | Change |
|------|--------|
| `app/routers/gamification.py` | Add `GET /badges` endpoint |
| `src/App.tsx` | Add `/stats` route inside Shell |
| `src/components/child/TopNav.tsx` | Promote Stats to active NavLink, remove COMING_SOON array |
| `vite.config.ts` | Add `/challenges` and `/leaderboard` proxy entries |

### Route

| Route | Page | Data |
|-------|------|------|
| `/stats` | Stats dashboard | `GET /users/me/progress`, `GET /badges`, `GET /users/me/badges`, `GET /challenges`, `GET /leaderboard` |

## Page Layout

Single scrolling page, top → bottom:

### 1. Page Header

"Your Stats" title.

### 2. XpSummary Card

A richer version of the existing StatsBar chips, displayed as a card:

- **Level** with a progress bar showing XP toward next level. Level formula: `floor(xp / 100) + 1`. Progress within level: `xp % 100` out of 100.
- **Total XP** number displayed prominently.
- **Streak count** with active/inactive state. Reuses `isStreakActive()` from `src/lib/streak.ts`.
- Data from existing `useProgress()` hook — no new endpoint needed.

### 3. BadgeGrid

"Badges" section heading + grid of badge cards:

- **Earned badges:** Full colour, icon (from `icon_url`), name, description, "Earned {relative date}" subtitle.
- **Locked badges:** Greyed out with a lock overlay icon. Name visible. Condition text shown as the description (e.g. "Complete your first lesson"). No date.
- Earned vs locked determined by merging `GET /badges` (all definitions) with `GET /users/me/badges` (earned, with `earned_at`).
- Grid layout: 2-3 columns on desktop (`sm:grid-cols-2 lg:grid-cols-3`), single column on mobile.
- Badge `icon_url` values like `/badges/first-step.svg` won't resolve to real files — render a placeholder emoji or lucide icon based on `condition_type` instead:
  - `lesson_count` → BookOpen icon
  - `streak_days` → Flame icon
  - `trade_count` → TrendingUp icon
  - `total_xp` → Star icon

### 4. ChallengeList

"Weekly Challenges" section heading + challenge cards:

- Each card: title, description, progress bar (`progress / target_value`), percentage text, XP reward shown as "+50 XP".
- Progress bar uses `role="progressbar"` with `aria-valuenow={progress}` and `aria-valuemax={target_value}`.
- **Completed challenges:** Green checkmark icon, "Completed!" badge, progress bar full and green.
- **In-progress challenges:** Blue progress bar showing current fraction.
- **Empty state:** "No active challenges this week."

### 5. LeaderboardTable

"Weekly Leaderboard" section heading + table:

- Columns: Rank (#), Username, Country, XP This Week.
- Country displayed as flag emoji derived from `country_code` (e.g. "GB" → 🇬🇧). Flag supplemented with `aria-label` for the country code.
- **Current user highlight:** The row where `username` matches `useChildSession().data.username` gets a distinct background colour + a "You" badge next to the username.
- Proper `<table>` semantics with `<thead>`/`<tbody>`.
- **Empty state:** "No activity this week yet. Complete a lesson to get on the board!"
- Capped at 50 rows (backend `LIMIT 50`).

## Data Flow

| Hook | Endpoint | Query Key | Refetch Strategy |
|------|----------|-----------|-----------------|
| `useProgress()` (existing) | `GET /users/me/progress` | `['progress']` | staleTime 60s |
| `useAllBadges()` | `GET /badges` | `['badges-all']` | staleTime: Infinity (static data) |
| `useBadges()` | `GET /users/me/badges` | `['badges-earned']` | Window focus |
| `useChallenges()` | `GET /challenges` | `['challenges']` | Window focus |
| `useLeaderboard()` | `GET /leaderboard` | `['leaderboard']` | Window focus |

Each section loads independently — if one endpoint is slow, the others still render.

## Country Code to Flag Emoji

A pure utility function `countryFlag(code: string): string` — converts 2-letter ISO code to regional indicator emoji:

```
"GB" → 🇬🇧, "US" → 🇺🇸, etc.
```

Formula: each character offset by `0x1F1E6 - 0x41` (regional indicator base minus 'A').

Small enough to inline in `src/lib/country.ts`.

## Testing Strategy

### Backend Test

- Unit test for `GET /badges` endpoint: returns all seeded badges, each with `earned_at=None`.

### Frontend Unit Tests (Vitest + RTL)

- `XpSummary` — renders level, XP count, streak state, progress bar width calculation (xp % 100).
- `BadgeGrid` — earned badges show name + earned date, locked badges show greyed state + lock icon + condition text, all 5 render.
- `ChallengeList` — progress bar at correct width percentage, completed state with checkmark, empty state.
- `LeaderboardTable` — renders rows with rank numbers, highlights current user's row, empty state.

### E2E (Playwright)

One smoke test: register + log in → navigate to `/stats` → verify XP summary visible (Level 1, 0 XP), all 5 badges visible (all locked for new user), challenges section visible, leaderboard section visible.
