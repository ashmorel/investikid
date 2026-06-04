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

## New components (presentational, in `src/components/child/`; each unit-tested + `vitest-axe`)

- **`LevelCard`** — `{ level, xp }`. Penny/level avatar + "Level N Investor", XP-to-next, gradient progress bar, "X XP to go" pill. Pure; computes `xpInLevel = xp % 100`, `xpForNext = 100` (same maths as today's Home bar).
- **`AchievementsStrip`** — `{ badges, earnedIds }`. Horizontal, scrollable, accessible list of earned/locked badges (emoji or `badgeIcon()` fallback + label; locked shows a lock, `aria-hidden` on decorative glyphs, real text labels), with a "See all →" link to `/stats`. Overflow-x scroll must not trigger page bleed (respect the existing `overflow-x-hidden` body rule — scroll lives in an inner container).
- **`PathLevelCard`** — `{ level: LevelOut, to }`. A level row for the Module screen: icon, title, `lessons_completed/lessons_total` progress, state (in_progress/completed/locked), `locked_reason` (premium/progression), passed ✓. Locked → non-link `div` (matches `ModuleTile` locked pattern).
- **`LessonRow`** — `{ lesson: LessonSummary, to, locked }`. A lesson row for the Level screen: type icon (card/quiz/scenario/video), title, XP reward, completed ✓ or lock.

## Per-screen layout direction

**Home (`Home.tsx`)** — keep education-first order: Penny greeting + next-lesson `HeroCard` stay at top. Then: `LevelCard` (replaces the thin inline XP bar), existing stat chips, `ReviewBanner` (when due), `AchievementsStrip` (teaser → Stats), then the "Your quests" `ModuleTile` grid (light spacing polish). Keep the sr-only `<h1>` + heading order.

**Quests (`Lessons.tsx`)** — add a header band with overall progress ("N of M modules started" + brand progress bar derived from existing module/level-state data) above a richer module grid. Consolidate onto the SP-A `ModuleTile` (per-topic accent, progress, locked, recommended marker); retire `ModuleCard` if it has no other consumer (verify with a grep; if used elsewhere, leave it).

**Module (`Module.tsx`)** — present the module's levels as a vertical **learning path** of `PathLevelCard` rows with a module progress header. Keep the existing level data/links.

**Level (`Level.tsx`)** — present the level's lessons as `LessonRow` items under a level progress header (lessons complete/total). Keep existing lesson links + locked logic.

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
