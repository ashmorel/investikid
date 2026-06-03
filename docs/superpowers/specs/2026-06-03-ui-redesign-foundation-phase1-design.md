# UI Redesign — Foundation + Phase 1 — Design

**Status:** Approved design, pending spec review → implementation plan.
**Date:** 2026-06-03

## Goal

Bring the approved InvestiKid Figma redesign into the live app, starting with a shared in-code design system (the "foundation") and the highest-impact screens (Home + the lesson-taking flow) so TestFlight testers immediately see the warmer, game-like look. Built on the existing design tokens, which already match the Figma.

Reference: the Figma "UI Redesign — Concepts" page (file `h5xrUTiNDZqqhu4pvYprqc`). Tokens: `src/index.css` + `tailwind.config.js`.

## Scope

**This spec = Foundation + Phase 1.** Later phases get their own spec → plan:
- **Phase 2:** Quests/all-modules, the module→level "learning path" screen, Stats/Profile, Progress (Strengths & Gaps), Coach Eddie chat.
- **Phase 3:** Login / Sign-up.

In scope now:
- A set of reusable presentational primitives in `src/components/child/ui/`.
- A `RobotEddie` mascot component (SVG/CSS), used app-wide (incl. replacing the 💡 in `EddieFAB`).
- Restyle of **Home** (`src/pages/child/Home.tsx` + `HomeHero`) and the **lesson flow**: the lesson renderers (`CardLesson`, `QuizLesson`, `ScenarioLesson`) and the **Correct / Not-quite / Lesson-complete** feedback states, under `src/components/child/lesson/` + `src/pages/child/Lesson.tsx`.

## Principles (load-bearing)

1. **Restyle, don't rewrite.** All existing behaviour, routes, data hooks (`useNextLesson`, `useProgress`, `useRecommendations`, content/level queries), APIs, and lesson logic stay unchanged. This is presentation only; the full existing test suite must keep passing (update only assertions tied to changed copy/markup).
2. **Faithful to the concepts, not pixel-perfect.** Adapt for real/variable data, empty and locked states, long text, and accessibility. The Figma is the visual north star, not a spec to trace.
3. **Keep the guardrails.** WCAG 2.2 AA — every new primitive/screen gets a `vitest-axe` check; preserve the quiz/scenario radiogroup semantics; decorative emoji/graphics `aria-hidden`; real focusable controls; visible focus. iOS: form controls stay ≥16px on touch, no `maximum-scale`; keep `viewport-fit=cover` + safe-area handling.
4. **Reuse tokens.** Colours/radii come from the CSS variables / Tailwind config (`hsl(var(--token))`), not hard-coded hex, so the app and Figma stay in lockstep. The brand gradient (amber→orange) and cream background are the through-line.
5. **TDD + green CI**, shipped per phase.

## Foundation components (`src/components/child/ui/`)

Each is presentational, typed, token-based, and unit + a11y tested.

- **`RobotEddie`** — SVG mascot (rounded head, screen-face with cyan eyes, antenna). Props: `size` (e.g. 40/56/64), optional `mood` (neutral/happy) for later. Replaces the `💡` in `EddieFAB`. `aria-hidden` by default (decorative); callers provide accessible label where Eddie conveys meaning.
- **`ScreenBackground`** — cream background + safe-area padding wrapper for child screens.
- **`GradientButton`** — amber→orange gradient CTA (full-width + inline variants), white extrabold label, focus ring; renders as `<button>` or, via `asChild`/`to`, a router `<Link>`. Used for all primary CTAs (Start, Check, Continue, Sign in).
- **`HeroCard`** — the gradient "Up Next" hero (icon slot, title, subtitle, CTA). Used on Home.
- **`StatChip`** / **`StatCard`** — XP / level / streak / accuracy display (chip = compact, card = grid tile).
- **`ModuleTile`** — coloured module tile (emoji circle in a per-topic accent, title, progress/locked state). Used in Home's "Your quests" grid (and Phase 2 Quests).
- **`OptionCard`** — a quiz/scenario answer option (letter badge + text, default/selected/correct/incorrect states), keyboard-operable, used inside the radiogroup.
- **`FeedbackPanel`** — the post-answer Correct (green) / Not-quite (coral) panel: status badge, title, optional correct-answer line, explanation; plus the celebratory Lesson-complete variant (medal, stars, earned-stat chips, confetti).
- **`BottomTabBar`** (restyle of the existing one) — Home / Quests / Progress / Stats with the polished active state.

## Phase 1 screens

**Home** (`Home.tsx` + `HomeHero.tsx`): re-present existing data — Eddie `HeroCard` (next lesson from `useNextLesson`) → `StatChip` row (XP/level/streak from `useProgress`) → XP-to-next bar → `ReviewBanner` (when due) → **"Your quests" `ModuleTile` grid** (all accessible modules with progress/locked, from the existing modules + level-state data; the top recommendation gets a subtle "recommended" marker) → restyled `BottomTabBar`. The verbose categorised recommendation lists are replaced by the hero + module grid (same underlying data; cleaner presentation). Keep the sr-only `<h1>` + heading order.

**Lesson flow** (`src/components/child/lesson/*` + `Lesson.tsx`): a shared lesson chrome (progress header: back + progress bar + count, Eddie speech bubble) wrapping each renderer:
- **`CardLesson`** — teaching concept card (illustration circle, title, body, "Got it").
- **`QuizLesson`** / **`ScenarioLesson`** — question card + `OptionCard` options (radiogroup preserved) + `GradientButton` "Check".
- **Feedback states** — `FeedbackPanel` for Correct / Not-quite (with explanation), and the Lesson-complete celebration. Wire to the existing completion logic and the existing auto-return behaviour.
`VideoLesson` keeps its current structure (transcript disclosure + captions) but adopts the shared chrome/buttons; no transcript-policy regression.

## Accessibility

- Each new primitive ships with a `vitest-axe` test.
- Quiz/scenario options remain a proper radiogroup (don't regress the prior a11y fix); `OptionCard` is keyboard-selectable with visible focus.
- White-on-gradient text stays in the large-bold range (meets AA large-text); body text stays dark on light.
- Decorative graphics (RobotEddie, confetti, emoji) are `aria-hidden`; meaningful text is real text.
- Honour `prefers-reduced-motion` for the celebration/confetti animation (reuse the existing `useReducedMotion` pattern).

## Testing

- New primitives: unit tests (render/props/states) + `vitest-axe`.
- Updated screens: adapt existing `Home`/lesson tests to the new structure/copy (keep them meaningful, don't weaken). Add tests for Home's module grid and the feedback states.
- Full regression each ship: `npx tsc -b`, `npm run lint`, `npm test`, `npm run build`; backend untouched (no backend changes in Phase 1). Then `npx cap sync ios` for the native build, and push on green CI.

## Out of scope (now)
- Phase 2 + 3 screens (above). No backend/API/data-model changes. No new mascot artwork (the SVG RobotEddie is the interim; commissioned art can swap in later behind the same component).
