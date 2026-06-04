# Child App UX Fixes — Next-Quest Resolver + Consistent Back Navigation — Design

**Status:** Approach approved (both); pending spec review.
**Date:** 2026-06-04
**Context:** Two post-launch UX fixes in the child app, found after the rebrand programme shipped. Bundled into one sub-project (both are child-facing UX, one backend + one FE) for a single spec → plan → CI cycle.

## Fix 1 — Next-quest resolver (bug: false "You've finished everything")

### Problem (root cause, confirmed)
The Home hero shows "You've finished everything for now!" while modules remain incomplete. `useNextLesson()` (`src/hooks/useNextLesson.ts`) picks a **single** `target` module via `pickTargetModule()` (continue_learning rec → something_new rec → else **first unlocked module by `order_index`**), then derives global `caught_up` from *that one module's* level state (`useNextLesson.ts:45-49`) — it never considers other unlocked, incomplete modules. Two triggers:
1. **Dominant:** `get_recommendations` returns empty `continue_learning`/`something_new` whenever `user.profiling_enabled` is false — and that column **defaults to false** (`models/user.py:60-61`). So recs are usually empty, `pickTargetModule` falls to "first module by order", and once module 1 is complete the hero falsely reports "caught up".
2. A started module whose only *remaining* levels are locked (premium/progression) yields a null target level → same false "caught up", ignoring `something_new`.

### Solution — server-side resolver (single source of truth)
The server already owns completion + level-locking truth (`level_service.derive_level_states`, used by `list_levels`). Compute the next actionable lesson there, across all modules.

- **New** `app/services/next_lesson_service.py` → `resolve_next_lesson(session, user) -> NextLessonOut | None`:
  - Load modules ordered by `order_index`. For each, skip if not accessible per `is_module_accessible(content_region_for(user), is_premium(user), module.country_codes, module.is_premium)` (same gate as `list_modules`).
  - For each accessible module, derive level states exactly as `list_levels` does (`derive_level_states` with the module's levels + the user's completions/scores + premium). Find the **first level by `order_index` with `state != 'locked'` and `lessons_completed < lessons_total`**.
  - In that level, find the **first incomplete lesson** by `order_index` (lessons where the user has no completion).
  - Return `{ module_id, module_title, module_icon, level_id, lesson_id, lesson_title, mode }`, `mode = 'continue'` if the user has any completed lesson in that module else `'start'`.
  - Return `None` only when **no** accessible module yields an actionable lesson → genuinely caught up.
  - Short-circuit on first hit (most users resolve at module 1–2). Reuse existing completion-loading helpers from `content.py`/`level_service` rather than duplicating queries.
- **New schema** `NextLessonOut` (`schemas/content.py`): `module_id: UUID, module_title: str, module_icon: str | None, level_id: UUID, lesson_id: UUID, lesson_title: str, mode: Literal['start','continue']`.
- **New endpoint** `GET /content/next-lesson` → `{ "next": NextLessonOut | None }` (auth = current child user; reuse the content router's `get_current_user`).

### Frontend
- `useNextLesson` collapses to a single query against `GET /content/next-lesson` (replacing the recs→modules→levels→lessons chain). It returns the existing `NextLesson` shape: `mode`, `to = /lessons/{module_id}/{level_id}/{lesson_id}`, `lessonLabel = lesson_title`, `moduleTitle`, `moduleIcon`, `isLoading`. `caught_up` ⇔ resolver returns `null`.
- `HomeHero` is otherwise unchanged; the review/`dueCount` path (`useRecommendations().review_summary`) stays as-is and still takes priority in the greeting.
- Retire the now-unused `pickTargetModule/pickTargetLevel/pickTargetLesson` helpers + their tests **after verifying nothing else imports them** (grep first; the Home recommendation *sections* use `useRecommendations` directly, not these helpers).

### Tests (backend)
- New child user (no completions) → resolver returns module 1's first level's first lesson, `mode='start'`.
- **Module 1 fully complete, module 2 unlocked & incomplete → returns module 2's first lesson** (the reported bug), `mode='start'`.
- Partially-complete module → returns the next incomplete lesson, `mode='continue'`.
- A module whose remaining levels are all locked → skipped; resolver moves to the next accessible incomplete module.
- All accessible modules complete → returns `None`.
- Respects premium/age/prerequisite/`content_region` gating (a premium-locked level/module is skipped for a free user).
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `client`/`db_session` fixtures.

### Tests (frontend)
- `useNextLesson`/`HomeHero`: resolver returns a lesson → hero shows Start/Continue card with the right `to`; resolver returns `null` → "All caught up" state. Mock the new endpoint.

## Fix 2 — Consistent Back navigation on sub-pages

### Problem
Drill-down pages have inconsistent, easy-to-miss **underlined text** back links (Module/Level/Lesson/Stock/Coach), and the **Market** page (`/simulator/market`) has none. Users feel stuck on sub-pages.

### Solution
- **New** `src/components/child/BackButton.tsx` — `{ to: string; label: string; className?: string }`. Renders a real `<Link>` styled as a button: left-arrow icon (`aria-hidden`) + visible text label, min touch target **44px**, text **≥16px** (`text-base`), brand styling (`text-brand-700 hover:bg-brand-50 rounded-lg`), visible focus ring, and an `aria-label` (e.g. `Back to {label}`). Deterministic up-one-level target (not browser-back).
- **Mount** it in a consistent sub-header slot at the top of each drill-down page, **replacing** the existing text back-links:
  - `Module.tsx` → `to="/lessons"`, label "Quests".
  - `Level.tsx` → `to="/lessons/{moduleId}"`, label "Levels" (module).
  - `Lesson.tsx` → `to="/lessons/{moduleId}/{levelId}"`, label "Lessons" (the level). (LessonPlayer's in-player `onBack` stays.)
  - `Market.tsx` → `to="/simulator"`, label "Simulator" (**fills the gap**).
  - `Stock.tsx` → `to="/simulator/market"`, label "Market".
  - `Coach.tsx` is a kept route but primarily a panel now; leave its existing back as-is (out of scope) OR swap to BackButton `to="/home"` — **decision: leave Coach as-is** (YAGNI; it's the panel path now).
- Top-level tab roots (Home/Quests/Simulator/Stats/Progress) get **no** Back button — they're reachable via the tab bar; Back is only for drill-down pages.

### Tests (frontend)
- `BackButton` component test: renders with accessible name, links to `to`, has the label text, ≥44px/≥16px classes present; `vitest-axe` clean.
- Keep existing Module/Level/Lesson/Market/Stock page tests green (update any that asserted on the old text-link markup).

## Out of scope
- Changing the bottom tab bar or TopNav structure (the TopNav logo→/home stays; its stale "IE" monogram is a separate small cleanup, not part of this).
- Browser-history Back semantics (we use deterministic `to` targets for predictability in a kids' app).
- Recommendation algorithm changes / enabling profiling by default (the resolver makes recs non-load-bearing for "next quest").

## Constraints
- Layout/UX + one new read-only endpoint; no data-model/migration change. WCAG 2.2 AA (labelled controls, focus, ≥44px, ≥16px). Kids' app safety unaffected. Commit to `main`; CI's 6 jobs gate the Railway deploy.

## Plan shape
Backend first: T1 `NextLessonOut` schema + `next_lesson_service.resolve_next_lesson` + tests → T2 `GET /content/next-lesson` endpoint + tests → T3 FE api client + `useNextLesson` rewire + HomeHero verify + retire dead helpers + tests → T4 `BackButton` component + tests → T5 mount BackButton across the 5 drill-down pages (replace text links, fill Market) + keep page tests green → T6 regression + push.

## Decisions captured
- Next-quest: **backend resolver** (single source of truth) over FE multi-candidate or minimal patch — fixes both triggers and always deep-links the true next quest.
- Back nav: **consistent Back button on all drill-down sub-pages** (deterministic up-one-level), not a persistent Home button (Home already reachable via tab bar/logo). Coach left as-is.
