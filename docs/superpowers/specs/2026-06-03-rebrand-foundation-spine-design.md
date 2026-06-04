# Rebrand Foundation & Spine (SP-A) — Design

**Status:** Draft for review.
**Date:** 2026-06-03
**Programme:** "Yasmin's Choice" rebrand — **SP-A of 6** (SP-0 Tailwind v4 ✅ shipped → **SP-A foundation/rebrand** → SP-B child core → SP-C simulator → SP-D auth/account → SP-E parent/admin).

## Goal

Re-skin InvestiKid from the amber/orange brand to the approved sky-blue "Yasmin's Choice" identity **across the whole app in one pass**, swap the mascot from **Eddie the robot** to **Penny the pig** (frontend + backend AI persona), and do it through a **semantic colour-token system** so future reskins are a token edit, not another sweep. Restyle only — no routes, data, IA, or behaviour change.

Reference design: the Figma Make export at `/tmp/yasminschoice` (`Layout`, `BottomNav`, `Dashboard`, `LearnPage`, `MascotTip`). Tokens authored in `src/index.css` `@theme` (v4 CSS-first, from SP-0).

## Why "full semantic + whole-app now" (approved)

The amber→orange family is currently the brand across ~56 frontend files; the app just shipped amber Phase 1. A half-blue/half-amber beta would look broken, so SP-A converts every screen's **colour** at once. SP-B–E then handle per-screen **layout/structure** (richer hero, learning-path, simulator, etc.), not colour. Representing colour as semantic roles (not literal shades) means the eventual next reskin — or dark mode — is changing `@theme`, not editing components.

## Colour-usage baseline (verified)

Brand today = `amber-50…900` + `orange-400…600` + the `from-amber-400 → to-orange-500` gradient (most-used: `border-amber-200` ×33, `bg-amber-50` ×25, `to-orange-500` ×22, `from-amber-400` ×22, `bg-amber-100` ×21, `text-amber-600/700/800/900`). Secondary families: blue (simulator/info), green/emerald/lime (gains/correct), red/rose (loss/danger), yellow (stars). The token system below covers every shade in use.

## 1. Semantic token vocabulary (`index.css` `@theme`)

Role-based scales. Concrete values from the Tailwind palette the prototype uses; tuned for WCAG AA (see §5).

```
/* Brand — replaces amber/orange. Sky→blue ramp. */
--color-brand-50:  #f0f9ff;  /* sky-50  (app tint / soft fills) */
--color-brand-100: #e0f2fe;  /* sky-100 */
--color-brand-200: #bae6fd;  /* sky-200 (borders) */
--color-brand-300: #7dd3fc;  /* sky-300 */
--color-brand-400: #38bdf8;  /* sky-400 (gradient start) */
--color-brand-500: #0ea5e9;  /* sky-500 (primary) */
--color-brand-600: #2563eb;  /* blue-600 (primary-strong, gradient mid) */
--color-brand-700: #1d4ed8;  /* blue-700 (text on light, AA) */
--color-brand-800: #1e40af;  /* blue-800 */
--color-brand-900: #0c4a6e;  /* sky-900 (headings) */
--color-brand-grad-from: #0ea5e9;  /* sky-500 */
--color-brand-grad-via:  #3b82f6;  /* blue-500 */
--color-brand-grad-to:   #4f46e5;  /* indigo-600 */

/* Accent — DEMOTED amber. Streaks, level, rewards, stars. */
--color-accent-50:  #fffbeb;  --color-accent-100: #fef3c7;
--color-accent-200: #fde68a;  --color-accent-400: #fbbf24;
--color-accent-500: #f59e0b;  --color-accent-700: #b45309; /* AA text on light */

/* Success — gains / correct. Emerald-led (AA on white). */
--color-success-50:  #ecfdf5;  --color-success-100: #d1fae5;
--color-success-500: #10b981;  --color-success-600: #059669; /* AA text */
--color-success-700: #047857;

/* Danger — loss / errors. Kept red/rose. */
--color-danger-50:  #fef2f2;  --color-danger-100: #fee2e2;
--color-danger-500: #ef4444;  --color-danger-600: #dc2626; /* AA text */
--color-danger-700: #b91c1c;

/* Info — non-brand blue for charts/simulator chrome where it must read
   as distinct from brand. Indigo-leaning so it separates from sky brand. */
--color-info-100: #e0e7ff;  --color-info-500: #6366f1;  --color-info-600: #4f46e5;

/* Neutrals / surfaces */
--color-surface: #f0f9ff;    /* sky-50 app background (replaces cream) */
--color-card:    #ffffff;
--color-ink:     #0f172a;    /* slate-900 body/heading text */
--color-muted:   #f1f5f9;    /* slate-100 */
--color-muted-foreground: #475569; /* slate-600 — AA on white */
--color-line:    #bae6fd;    /* sky-200 default border */
```

These also **repoint the existing shadcn tokens** in the `:root`/`@theme` so `--primary`→brand-500, `--primary-foreground`→white, `--background`→surface, `--ring`→brand-500, `--border`→line, `--accent`→accent-100, `--destructive`→danger-500. shadcn/ui components recolour automatically.

**Per-topic ModuleTile accents** (Home quest tiles) keep a topic palette but re-pitched into the new family (sky/blue/indigo/violet/teal/rose), defined as a small map — not literal hex scattered in the component.

## 2. The whole-app semantic refactor

Walk the ~56 files and replace literal colour utilities with the semantic token matching the **role** (judgement, not blind swap):
- `from-amber-400 to-orange-500` → `from-brand-grad-from to-brand-grad-to` (or a `.brand-gradient` utility).
- `bg-amber-50`→`bg-brand-50`; `border-amber-200`→`border-line`/`border-brand-200`; `text-amber-700`→`text-brand-700`.
- A streak/level/reward chip's amber → `accent-*` (NOT brand) — these stay warm by design.
- `text-green-600`→`text-success-600`; `bg-green-500/20`→`bg-success-500/20`.
- `text-red-*`→`text-danger-*`; chart/simulator blue that must stay distinct → `info-*`.
- Stars (`text-yellow-*`) → `accent-*`.

A short brand-gradient utility class (e.g. `bg-brand-gradient`) is added so the hero/CTA gradient is declared once.

## 3. Penny mascot

New `src/components/child/ui/Penny.tsx`: port the prototype's `MascotTip` pig SVG. API:
```ts
interface PennyProps { size?: number; mood?: 'happy' | 'thinking' | 'excited'; className?: string; }
```
- `aria-hidden` by default (decorative); callers supply accessible labels where Penny conveys meaning.
- `useId()` for unique SVG gradient ids (the RobotEddie duplicate-id fix carries over).
- Mood → context mapping: `PennyFAB` + Home greeting = `happy`; lesson help / "thinking" states = `thinking`; completion celebration = `excited`.
- **Retire `RobotEddie`** (delete file + test) once all callers move to `Penny`.

## 4. Eddie → Penny rebrand

**Frontend (19 files + tests):**
- Rename `EddieFAB`→`PennyFAB`, `CoachEddiePanel`→`CoachPennyPanel` (files, exports, imports).
- Copy: "Coach Eddie"→"Coach Penny", "Ask Coach Eddie"→"Ask Coach Penny", "Eddie"→"Penny" in visible strings; the mascot name shows "Penny 🐷" where the prototype does.
- Update component/a11y tests asserting the old names/copy.

**Backend (6 files + tests):** rewrite the AI persona — Penny, a warm, encouraging piggy-bank guide for kids — in `coach_service`, `tutor_service`, `chart_coach_service`, `home_greeting_service`, the persona constant in `core/config.py`, and any "Eddie" string in `alerting`. **Unchanged:** `moderate_output` on all LLM output, `is_premium` gating, rate limits, response schemas, endpoints. Update backend tests that assert "Eddie" persona text. This is persona-copy only — no behavioural/contract change.

## 5. Accessibility (correcting the prototype)

The prototype uses sub-AA choices we must not copy:
- Body/label text uses AA-contrast tokens: `ink` (slate-900), `muted-foreground` (slate-600), `brand-700`/`brand-900` — **never** `sky-400`/`brand-300` for text on white.
- Success text uses `success-600/700` (emerald), not lime-400.
- White text only on `brand-*`/gradient at large/bold sizes (AA large-text).
- Preserve: visible focus rings, quiz/scenario radiogroup semantics, decorative SVG/emoji `aria-hidden`, form controls ≥16px on touch, no `maximum-scale`, `viewport-fit=cover` + safe-area vars.
- Every new/changed primitive keeps its `vitest-axe` check; `Penny` adds one.

## 6. Scope, sequence & file structure

One sub-project, sequenced so the tree never half-breaks (each step green-CI-able):
1. **Token vocabulary** in `@theme` + repoint shadcn tokens + `bg-brand-gradient` utility (app still references old literal amber classes → still renders; new tokens available).
2. **Recolour shared primitives + shell** (`ui/*`, `Shell`, `TopNav`, `BottomTabBar`) to semantic tokens — re-skins Home + lessons (they consume primitives).
3. **Penny component** + retire RobotEddie; move `EddieFAB`/HomeHero/LessonChrome to Penny.
4. **Eddie→Penny FE** rename + copy + tests.
5. **Eddie→Penny BE** persona + tests.
6. **Sweep remaining feature-screen colours** (simulator, stats, progress, parent, admin, auth, coach) to semantic tokens.
7. **A11y + full regression** (contrast spot-checks, axe, before/after screenshots, all 5 CI jobs).

If de-risking is preferred later, steps 1–5 (the "spine") and steps 6–7 (the "sweep") can split into A1/A2 — but they're specced as one.

## 7. Testing

- New `Penny` unit + `vitest-axe`; update primitive/screen tests for new copy/markup/component names.
- Backend: update persona-asserting tests; confirm moderation/gating/rate-limit tests still pass.
- Visual: before/after mocked-API screenshots (Home + lesson + one simulator screen) — expect a deliberate, consistent blue/Penny change (not parity).
- Frontend: `tsc -b`, `npm run lint`, `npm test`, `npm run build`; Backend: `ruff`, `pytest`. All 5 CI jobs green. iOS rebuild deferred to programme end.

## Out of scope (SP-A)

- Per-screen **layout/structure** redesign (richer Dashboard hero, learning-path screen, simulator detail, etc.) — that's SP-B–E.
- No new routes/endpoints/data-model/IA changes. No mascot artwork beyond the in-code SVG Penny. No Tailwind/dependency changes (SP-0 done).

## Decisions captured

Whole-app colour now · full semantic token refactor · Penny with 3 moods · keep IA/routes · name "InvestiKid" · backend persona rewritten (behaviour unchanged).
