# Flow Cleanup — Vocabulary, Home "Next", Progress Re-skin (Design Spec)

**Date:** 2026-06-05
**Status:** Approved (design); ready for implementation plan
**Origin:** Product review item 2 (see `docs/2026-06-05-product-review-and-backlog.md` §1, "Flow snags").
**Scope:** Frontend only (`invest-ed/frontend`). No backend, API, or DB changes.

---

## Problem

Three confusion points surfaced in the UX review:

1. **Vocabulary collision.** "quest" means *a single lesson* almost everywhere
   (`LessonChrome` "Quest N of M", `ModuleCard`/`Level` "X / Y quests",
   `CoachPennyPanel` "about this quest"), yet the nav tab **"Quests"** opens the
   *module list* (`Lessons.tsx`), whose subtitle mixes both ("{n} modules · {n} quests"),
   and Home's **"Your quests"** heading sits over a grid of *modules*. The same word
   labels two different tiers.
2. **Two competing "what's next" on Home.** `HomeHero` shows the resolved next lesson via
   `useNextLesson`, while the module grid separately highlights a `recommendedModuleId`
   derived from `useRecommendations` — the two can point at different modules.
3. **Progress screen theme break.** `StrengthsGaps.tsx` ("My Progress") is hard-coded dark
   (`bg-slate-800`, `text-slate-400/500`, `bg-slate-600`, SVG ring `stroke="#334155"`)
   against the otherwise light sky-blue app — it reads as a different app.

Plus a trivial brand vestige: the `TopNav` logo monogram still reads **"IE"**.

## Decisions (locked with the user)

- **Vocabulary:** literal **Module → Level → Lesson** everywhere. Drop the "quest" metaphor
  from user-facing copy.
- **Nav tab:** the tab that opens the module list is labelled **"Learn"** (it names the
  learning area; the route `/lessons` is unchanged).
- **Home "what's next":** keep both surfaces but make the grid's highlighted tile derive
  from the **same** next-lesson resolver the hero uses, so they always agree.
- **Progress re-skin:** map onto the app's existing semantic light tokens (no new design).
- **Out of scope (deferred):** the locked-premium "ask a grown-up" dead-end (overlaps the
  pricing/paywall work, item 4). No new engagement features here.

## Non-goals

- No backend/API/schema changes; `useRecommendations` is retained (still powers the
  review-due banner) — only its use as the Home highlight source is removed.
- No route changes (`/lessons`, `/lessons/:moduleId`, etc. unchanged).
- No content/data changes.

## Changes

### Part 1 — Literal vocabulary (Module / Level / Lesson)

User-facing string edits (exact files):

| File | Current | New |
|---|---|---|
| `components/child/BottomTabBar.tsx` | tab label `Quests` | `Learn` |
| `components/child/TopNav.tsx` | tab label `Quests` | `Learn` |
| `pages/child/Lessons.tsx` | H1 `Quests` | `Modules` |
| `pages/child/Lessons.tsx` | subtitle `{n} modules · {n} quests` | `{n} modules · {n} lessons` |
| `pages/child/Home.tsx` | section heading + `aria-label` `Your quests` | `Your modules` |
| `components/child/ModuleCard.tsx` | `{c} / {t} quests` | `{c} / {t} lessons` |
| `pages/child/Level.tsx` | `{c} / {n} quests` | `{c} / {n} lessons` |
| `pages/child/Module.tsx` | BackButton `label="Quests"` (×2) | `label="Modules"` |
| `components/child/lesson/LessonChrome.tsx` | `aria-label` `Quest {position} of {total}` / `Quest {position}` | `Lesson {position} of {total}` / `Lesson {position}` |
| `components/child/lesson/CoachPennyPanel.tsx` | "Ask me anything about this quest! 🎯" | "…about this lesson! 🎯" |

Implementation also performs a sweep for any remaining **user-facing** `quest`/`Quest`
strings in `pages/child` and `components/child` and converts them to `lesson`/`module` as
appropriate, **excluding** code identifiers and unrelated words (`request`, `question`,
`querystring`, `requestAnimationFrame`, etc.). Route paths, query keys, and prop/variable
names are NOT renamed (no behavioural change).

Test fixtures that assert on the changed labels are updated:
- `components/child/__tests__/BottomTabBar.test.tsx` — expects `Learn` (was `Quests`).
- `components/child/__tests__/BackButton.test.tsx` — label fixture `Modules` (was `Quests`).

### Part 2 — Home: single source of truth for "what's next"

In `pages/child/Home.tsx`:
- Add `const next = useNextLesson();` and set
  `const recommendedModuleId = next.moduleId;` (replacing the value previously derived from
  `recs.continue_learning[0].module_id ?? recs.something_new[0].module_id`).
- `ModuleTile`'s `recommended={m.id === recommendedModuleId}` is unchanged in shape — it now
  highlights the module the hero points at.
- `useRecommendations` is retained ONLY for `recs.review_summary.due_count` (the
  `ReviewBanner`). Remove the now-dead recommendation-based `recommendedModuleId` derivation.
- No extra network cost: `HomeHero` already issues the `['next-lesson']` query; React Query
  dedupes it.

### Part 3 — Progress (`StrengthsGaps.tsx`) re-skin to light brand

Map the dark palette onto the app's semantic tokens (the same ones used by
`LevelProgressCard` and the Stats cards), preserving the ring + progress-bar semantics:
- card `bg-slate-800` → light surface (`bg-white` with `border border-line`, matching
  sibling cards);
- `text-slate-400` / `text-slate-500` → `text-muted-foreground`;
- progress track `bg-slate-600` → `bg-line` (or `bg-brand-100`);
- SVG ring track `stroke="#334155"` → a light token value consistent with `line`
  (e.g. `#e2e8f0`), ring fill stays the category/brand colour;
- the `new` category accent `border-l-slate-500` / `text-slate-400` → neutral brand-aligned
  tokens.

Implementation reads the full file first and maps every dark class. The result must keep
**WCAG 2.2 AA** text contrast on the new light surface (verified by the component's
vitest-axe test).

### Part 4 — `TopNav` monogram

`components/child/TopNav.tsx`: change the logo monogram text from `IE` to `IK` (InvestiKid).

## Testing

- `components/child/__tests__/BottomTabBar.test.tsx` and `.../BackButton.test.tsx` updated to
  the new labels.
- `StrengthsGaps` vitest-axe test: keep (or add if absent) an `axe`-clean assertion against
  the re-skinned light component.
- A small Home test asserting the highlighted `ModuleTile` corresponds to the next-lesson
  module (the recommended ring tracks `useNextLesson().moduleId`).
- Full verify: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` warning is
  acceptable), `npm test` (vitest + vitest-axe), `npm run build`.

## Constraints

- WCAG 2.2 AA; iOS form controls ≥16px and no `maximum-scale` (unaffected — copy/colour only).
- The iOS app loads the same web bundle, so after the frontend build a
  `npm run build && npx cap sync ios` is run once at the end (no native code change; called
  out at close-out, not per task).
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  Vercel auto-deploys the frontend; Railway backend unaffected. CI must stay green (6 jobs).

## Alternatives considered

- **Quest-forward metaphor** (rename module→"Topic", keep "quest"=lesson): friendlier but
  more churn and the user chose the literal scheme for clarity / the older audience.
- **Drop the Home highlight ring entirely** (hero is the only "next"): simplest, but the user
  chose to keep the at-a-glance highlight, aligned to the hero.
