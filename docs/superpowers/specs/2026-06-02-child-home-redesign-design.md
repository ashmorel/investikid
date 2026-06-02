# Child Home Page Redesign — Design

**Status:** Approved design, pending spec review → implementation plan.
**Date:** 2026-06-02

## Goal

Make the post-login child home immediately answer "what do I do next?" with a clear,
engaging, Coach-Eddie-led hero that surfaces the actual next lesson — for brand-new
and returning kids alike. Replace the flat empty state ("Complete a lesson to get
recommendations") that a first-time tester currently sees.

## Current state

`src/pages/child/Home.tsx` shows a greeting, `StatsBar`, an XP-to-next-level bar, an
optional `ReviewBanner`, categorised recommendation sections (Continue / Practise /
Something New), and a "Browse all modules" button. For a child with no completions,
the recommendation area is an empty box with a "Complete a lesson…" message — no clear
starting action and visually flat. Coach Eddie already exists in-app as a 💡 avatar
(`EddieFAB`), and a templated, no-LLM `useCoachGreeting` hook already derives a friendly
line from recommendation state. A tiered LLM stack (`get_llm_client('premium')`),
output moderation (the Coach Eddie / LLM-03 pattern), and `is_premium(user)` gating all
exist.

## Scope

In scope:
- A new **`HomeHero`** at the top of the child home: Coach Eddie (💡) + a speech-bubble
  greeting, above a prominent gradient **hero card** showing the next lesson with a
  "Start →" / "Continue →" CTA linking to it.
- A **`useNextLesson`** hook (+ pure resolver) that determines the target lesson.
- A **tiered Eddie greeting**: instant templated for everyone; premium users get an
  AI-personalised line that progressively swaps in.
- A new premium-gated backend endpoint for the AI greeting.
- Keep StatsBar, XP bar, ReviewBanner, recommendation sections, and Browse button
  (moved below the hero). Remove only the empty-state box.

Out of scope: changing the lesson player, recommendation engine internals, or the
parent/admin surfaces. No new gamification mechanics.

## UX

**Layout (top → bottom):** HomeHero → StatsBar (XP/level/streak) → XP-to-next-level bar
→ ReviewBanner (if reviews due) → recommendation sections → "Browse all modules".

**HomeHero:**
- Eddie 💡 in a coloured circle + a speech bubble containing the greeting line.
- A gradient (amber→orange) hero card: module emoji, lesson title, and a white pill
  button "Start →" (new) or "Continue →" (returning) linking to
  `/lessons/{moduleId}/{levelId}/{lessonId}`. Subtle framer-motion entrance.
- "All caught up" variant: celebratory line + a review CTA (if reviews due) else an
  "Explore modules" CTA → `/lessons`.

## Next-lesson resolution (`useNextLesson`, frontend, deterministic, no AI)

Pure helper `pickNextLesson` operating on already-fetched data (modules list,
recommendations, and the chosen module's levels+lessons), returns
`{ mode: 'start' | 'continue' | 'caught_up', moduleId, levelId, lessonId, moduleTitle,
moduleIcon, lessonLabel } | caught_up`.

Module selection order:
1. `recommendations.continue_learning[0]` → resume (mode `continue`).
2. else `recommendations.something_new[0]` → mode `start`.
3. else the first **unlocked** module by `order_index` → mode `start` (guarantees a
   brand-new child always gets a concrete first lesson — the key fix).

Within the chosen module: fetch its levels (ordered by `order_index`); pick the first
unlocked, not-fully-complete level; within it the first lesson whose `completed` is
false (lessons ordered by `order_index`). Lesson label via the existing lesson-title
derivation. Only the chosen module's levels/lessons are fetched (≤2 extra queries,
React-Query-gated on the resolved moduleId).

`caught_up`: if no incomplete lesson exists anywhere reachable (all complete) → hero
shows the caught-up variant.

Loading: while resolving, the hero shows a lightweight skeleton (no layout shift).

## Tiered Eddie greeting

**Templated builder** — pure function `buildHeroGreeting(ctx)` where `ctx` = `{ name,
mode, lessonLabel, streakCount, dueCount }`. Returns one friendly, age-appropriate line:
- `start` (no progress): "Let's start your money journey! First up: {lessonLabel} 📈"
- `continue`: "Welcome back, {name}! Let's pick up {lessonLabel}." (mention streak when
  `streakCount > 0`)
- `dueCount > 0`: a review-aware nudge.
- `caught_up`: celebratory line.
Used directly by basic users and as the guaranteed fallback for premium.

**Render path (both tiers): instant-first.** The hero renders the templated line
immediately so it is never blank or laggy.

**Premium enhancement:** if `is_premium`, the frontend calls the AI endpoint in the
background; on success Eddie's line swaps to the AI line with a subtle fade. On error,
timeout, or moderation block, the templated line stays. Basic/free users make no AI call.

**Backend `POST /ai/home-greeting`** (in `app/routers/ai.py`, authed child):
- Premium-gate: non-premium → 403.
- Body: the greeting context (name, mode, lesson_label, streak_count, due_count).
- Builds an age-appropriate prompt, calls `get_llm_client('premium')`, runs the result
  through the **same moderation** wrapper Coach Eddie uses; returns `{ greeting }` on
  success. On provider failure or moderation block → non-200 (e.g. 503) so the frontend
  keeps the templated line. A short max-length is enforced.

**Cost control:** the AI greeting is cached client-side via React Query keyed on the
greeting context signature (name/mode/lesson/streak/dueCount) with a long session
`staleTime`, so navigating home repeatedly does not re-call the LLM; it regenerates only
when that context changes. (A per-day server cache is a possible future optimisation,
not in scope.)

**Safety:** children never see unmoderated AI text — moderation gates the AI path and
the templated line is the deterministic fallback.

## Files

Frontend:
- Create `src/lib/homeHero.ts` — pure `pickNextLesson` + `buildHeroGreeting`.
- Create `src/hooks/useNextLesson.ts` — resolves target lesson (modules + recs + chosen
  module's levels/lessons).
- Create `src/components/child/HomeHero.tsx` — Eddie + speech bubble + hero card; renders
  templated line first, swaps premium AI line on success.
- Create `src/api/ai.ts` addition — `homeGreeting(ctx)` call + `useHomeGreeting` hook
  (enabled only when premium).
- Modify `src/pages/child/Home.tsx` — render `HomeHero` on top; drop the empty-state box;
  keep the rest below.

Backend:
- Modify `app/routers/ai.py` — `POST /home-greeting` (premium-gated, moderated).
- Modify `app/schemas/ai.py` (or wherever AI schemas live) — request/response models.
- Reuse `app/services/llm_client.get_llm_client`, the moderation helper, and
  `is_premium`.

## Accessibility

- The CTA is a real `<Link>` (keyboard focusable, visible focus ring).
- Eddie 💡 is `aria-hidden`; the greeting is real text.
- Heading order preserved (a single `h1` greeting/region heading).
- White-on-gradient pill maintains AA contrast; body text stays dark on light.
- Hero respects the existing safe-area / no-horizontal-overflow rules.

## Testing

Frontend:
- Unit-test `pickNextLesson` (continue / something-new / first-unlocked fallback /
  caught-up / locked-level skip) and `buildHeroGreeting` (each mode + streak + reviews).
- Component-test `HomeHero`: renders templated line + correct CTA href and start-vs-
  continue label; for premium, shows templated first then swaps to a mocked AI line;
  vitest-axe a11y check.
- Update the Home page test for the new structure (no empty-state box).

Backend:
- `POST /home-greeting`: premium user → 200 with a (mocked-LLM) moderated greeting;
  free/basic user → 403; provider failure or moderation block → non-200 (frontend
  fallback path). Use existing `client`/`admin`/premium fixtures and mock the LLM +
  moderation as Coach Eddie tests do.

## Non-goals / future

- No per-day cross-session server cache (session-scoped client cache only).
- No streaming/typing animation for the greeting.
- No change to recommendation ranking.
