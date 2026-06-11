# P-2 — Juice Pack (sounds · haptics · animations) — Design Spec + Plan

**Date:** 2026-06-11 · **Status:** Approved · **Branch:** `testing`
**Goal:** Duolingo-grade feedback at meaningful moments. Decisions: sounds ON by default + profile-menu mute; Web Audio synthesis (no assets/licensing); full pack in one pass.

## A. Sound service — `frontend/src/lib/sound.ts`
- Web Audio synthesis: 8 named recipes via oscillator+gain envelopes — `correct` (bright two-note ding), `wrong` (soft low "doot", NEVER harsh), `lessonComplete` (3-note rising), `mastery` (bigger 4-note fanfare), `xpTick` (tiny click, rapid-fire safe), `streak` (whoosh-pop), `badge` (sparkle arpeggio), `trade` (click-chime).
- `playSound(name)`: lazily creates a single `AudioContext` on first call (user-gesture safe — all triggers are taps); resumes if suspended; total silence (no-op) when AudioContext unavailable (jsdom/old browsers) or muted.
- Mute: `isSoundEnabled()` / `setSoundEnabled(bool)` persisted in localStorage (`investikid-sound`, default enabled), try/catch-guarded.
- iOS ring/silent switch is respected automatically by WKWebView audio. No autoplay anywhere.

## B. Haptics — `frontend/src/lib/haptics.ts`
- `@capacitor/haptics` (^8.x to match Capacitor 8). `haptic(kind)` with kinds `success` | `warning` | `medium` | `heavy` mapped to NotificationType.Success/Warning, ImpactStyle.Medium/Heavy. Native-only (`isNativeApp()` guard); silent no-op on web/jsdom; dynamic import so web bundles don't pay for it.
- ⚠️ New native plugin → needs `npx cap sync ios` + Xcode rebuild before haptics work on device (note in commit + report).

## C. Moment wiring (sound + haptic + motion fire together)
| Moment | Where | Sound | Haptic | Motion |
|---|---|---|---|---|
| Correct answer | QuizLesson/ScenarioLesson on judge | correct | success | green check pop (scale spring) |
| Wrong answer | same | wrong | warning | gentle shake (x wiggle) |
| Lesson complete | CompletionPanel mount | lessonComplete | success | **XP count-up** (animated number) |
| Module complete / level mastered | Module.tsx banner / mastered state appears | mastery | heavy | **confetti burst** (explorer only) |
| Trade executed | trade success path (Stock/TradeForm onSubmit resolve) | trade | medium | existing reward toast |
| Streak shown extended | CompletionPanel (if streak data present) or skip | streak | — | flame pulse |
| Badge earned | wherever badge award surfaces client-side (investigate; skip if not surfaced) | badge | success | — |

## D. Animations
- `XpCountUp` component (framer `animate`/`useMotionValue` number roll, ~0.8s; reduced-motion → render final instantly). Used in CompletionPanel (and Try demo completion).
- Confetti: `canvas-confetti` (~5KB) single burst helper `celebrate()`; fired ONLY when `tierConfig[tier].celebration === 'big'` (explorers) AND not reduced-motion. Investors: no confetti (consistent with W5a).
- Check pop / wrong wiggle in quiz feedback; progress-bar spring on the Level page lesson progress; streak pulse. All `useReducedMotion`-gated.

## E. Settings
- "Sounds" toggle in the child ProfileMenu (find real component; mirror existing menu-item patterns), wired to `setSoundEnabled`, shows current state, axe-clean.

## F. Tests
- sound.ts: default on; mute persists; playSound no-ops when muted/no AudioContext (jsdom = no AudioContext → assert no throw); recipes registry complete.
- haptics: no-op on web (spy dynamic import not called when !isNative).
- XpCountUp: renders final value; reduced-motion renders instantly.
- Quiz: correct answer triggers playSound('correct') + haptic('success') (module spies); wrong likewise.
- CompletionPanel: lessonComplete fired once on mount; XP count-up shows.
- Confetti: fired for explorer big-celebration, NOT for investor, NOT under reduced motion (mock canvas-confetti).
- Toggle: renders, flips, persists. Full suites + build.

## Out of scope
Background music; sound packs/themes; Android-specific haptic tuning; web vibration API; per-sound volume settings.
