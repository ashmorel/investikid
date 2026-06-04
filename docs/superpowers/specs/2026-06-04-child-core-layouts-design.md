# Child Core Screen Layouts (SP-B) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-B of 6** (SP-0 v4 ✅ · SP-A foundation/rebrand ✅ · **SP-B child core** · SP-C simulator · SP-D auth/account · SP-E parent/admin).

## Goal

Bring the child **core screens'** layout/structure up to the richer "Yasmin's Choice" look, reusing all existing data hooks, routes, and the SP-A sky-blue tokens/Penny mascot/primitives. **Layout & presentation only** — no routes, queries, endpoints, data shapes, IA, or behaviour change. The app is already cohesively blue with Penny (SP-A); SP-B is about structure: a gamified Home, a proper learning-path, and consistent card styling.

Reference: prototype `/tmp/yasminschoice/src/app/components/` (`Dashboard.tsx`, `LearnPage.tsx`). Current screens: `invest-ed/frontend/src/pages/child/`.

## Scope (approved)

One sub-project, **all six core screens**, a task per screen. Effort is deliberately uneven — Home and the learning-path screens get real layout work; Stats is a card restyle; Progress and Coach are light polish (they're already good — YAGNI).

In scope: `Home`, `Lessons` (Quests), `Module`, `Level`, `Stats`, `StrengthsGaps` (Progress), `Coach`, plus four new presentational components.

Out of scope: Simulator suite (SP-C), auth/account (SP-D), parent/admin (SP-E). No backend changes. No new data/endpoints — everything is fed by existing hooks.

## Data sources (all existing — reused, not changed)

- `useProgress()` → `{ xp, level, streak_count, last_activity_date }`
- `gamificationApi.getEarnedBadges()` (`/users/me/badges`) + `/badges` (all) — for achievements
- `contentApi.listModules()`, `listLevels(moduleId)`, `listLevelLessons(levelId)` — learning path
- `useRecommendations()`, mastery/strengths hooks — already wired on Home/Progress

## Components

**Reality check (verified in code):** `LevelCard` (the module's level cards, props `{level,onOpen,onLockedClick}`), `LessonRow` (the lesson list, props `{moduleId,levelId,lesson,status}`), and `ModuleCard` (the Quests grid, with a progress bar) **already exist** from the earlier leveled-progression work. SP-B **enhances** these toward the prototype — it does not recreate them. Only two components are genuinely new.

**New (presentational, in `src/components/child/`; each unit-tested + `vitest-axe`):**
- **`LevelProgressCard`** — `{ level, xp }`. The Home "Level N Investor" card: level badge + XP-to-next + gradient progress bar + "X XP to go" pill. Named `LevelProgressCard` to avoid colliding with the existing module-level `LevelCard`. Pure; `xpInLevel = xp % 100`, `xpForNext = 100` (same maths as today's Home bar). Progress bar uses `role="progressbar"` + aria-value*.
- **`AchievementsStrip`** — `{ allBadges, earnedBadges }` (from `useAllBadges()` + `useBadges()`). Horizontal, scrollable, accessible list of earned/locked badges (`badgeIcon()` for the glyph + name label; locked shows a lock; `aria-hidden` on decorative glyphs, real text labels), with a "See all →" link to `/stats`. Overflow-x scroll lives in an inner container (respect the body `overflow-x-hidden`).

**Enhanced (existing, restyled toward the prototype):**
- **`LevelCard`** (module levels) — add a `lessons_completed/lessons_total` progress bar + richer prototype styling; keep its `{level,onOpen,onLockedClick}` API and states.
- **`LessonRow`** (lessons) — richer row styling (clearer type icon, XP), keep `{moduleId,levelId,lesson,status}` API.
- **`ModuleCard`** (Quests) — restyle toward the prototype's card; **keep** it (it already has a progress bar — richer than `ModuleTile`, so do NOT consolidate/retire).

## Per-screen layout direction

**Home (`Home.tsx`)** — keep education-first order: Penny greeting + next-lesson `HeroCard` stay at top. Then: `LevelProgressCard` (replaces the thin inline XP bar), existing stat chips, `ReviewBanner` (when due), `AchievementsStrip` (teaser → Stats), then the "Your quests" `ModuleTile` grid (light spacing polish). Keep the sr-only `<h1>` + heading order.

**Quests (`Lessons.tsx`)** — add a header band with overall progress ("N of M modules started" + brand progress bar derived from existing module/level-state data) above the module grid, and restyle the existing `ModuleCard` toward the prototype's richer card. Keep `ModuleCard` (it has the per-module progress bar `ModuleTile` lacks).

**Module (`Module.tsx`)** — restyle the existing `LevelCard` rows toward the prototype's learning-path look (add the level progress bar) and add a module progress header above them. Keep the existing banner, level data, and links.

**Level (`Level.tsx`)** — restyle the existing `LessonRow` list toward the prototype and add a level progress header (lessons complete/total + bar). Keep existing lesson links, status logic, and locked handling.

**Stats (`Stats.tsx`)** — wrap the existing sections (XP summary, badges, weekly challenges, leaderboard) in the prototype card aesthetic (`rounded-2xl border border-brand-100 bg-card shadow-sm`, sectioned headers). Present badges as an **achievements grid** (reuse `BadgeGrid`). Same data/child components.

**Progress (`StrengthsGaps.tsx`)** — light polish only: align card styling with the new system; resolve the leftover `slate-600/400` tones (keep as intentional dark cards OR shift to neutral `muted`/`ink` if they read as stray). No structural change to the mastery ring or topic cards.

**Coach (`Coach.tsx`)** — light polish only: add a `Penny` avatar (`mood="happy"`) in the header; tidy message-bubble + suggested-prompt-chip spacing. No behaviour/payload change.

## Accessibility

- New components ship a `vitest-axe` test; decorative emoji/badge glyphs `aria-hidden`, meaningful labels are real text; horizontal strips are keyboard-scrollable and don't trap focus.
- Preserve: visible focus rings, heading order, ≥16px touch inputs, no `maximum-scale`, `viewport-fit=cover` + safe-area, quiz/scenario radiogroup semantics (untouched here).
- Progress bars expose `role="progressbar"` + `aria-valuenow/min/max` (follow the existing `LessonChrome` pattern).

## Testing

- New components: unit (render/props/states) + `vitest-axe`.
- Updated screens: adapt existing tests to new structure/copy; keep them meaningful (don't weaken). Add tests for Home's `LevelCard`/`AchievementsStrip` and the learning-path rows.
- Before/after mocked-API screenshots (Home, Quests, a Module, a Level, Stats) — expect a deliberate layout change.
- `npx tsc -b`, `npm run lint`, `npm test`, `npm run build`; backend untouched. All 5 CI jobs green. iOS rebuild deferred to programme end.

## Plan shape

Task per screen, sequenced low-risk: shared new components land with their first consumer (Home first → `LevelCard`/`AchievementsStrip`; Module → `PathLevelCard`; Level → `LessonRow`). Order: Home → Quests → Module → Level → Stats → Progress → Coach → final a11y/regression. Each task is a green-CI checkpoint.

## Decisions captured

All six core screens in one SP-B · Home gains Level card + achievements (next-lesson hero stays primary) · Progress & Coach = light polish (YAGNI) · achievements appear on Home as a teaser + full on Stats · layout-only, no data/route/behaviour change.
