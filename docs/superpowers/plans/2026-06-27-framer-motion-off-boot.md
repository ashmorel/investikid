# framer-motion Off The Boot Path — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Remove `framer-motion` from the cold-boot bundle by replacing the three eager boot-path animations (Shell route transition, HomeHero entrance, BottomSheet) with CSS, so the library only loads via the already-lazy route chunks.

**Architecture:** The boot chunk pulls framer-motion through three eager import chains — `App→Shell`, `App→Home→HomeHero`, and `BottomSheet` (used by ProfileMenu/FeedbackDialog/TradeForm on eager pages). Re-implement each animation with CSS keyframes/transitions (respecting `prefers-reduced-motion` via the Tailwind `motion-reduce`/`motion-safe` variants), and drop the framer-motion import from those three files. The other six framer-motion consumers (Stats/BadgeGrid, Lesson/CompletionPanel, ChildAnalytics, FeedbackPanel, HeroCard, XpCountUp, Module's `useReducedMotion`) are already on lazy/off-boot paths and are LEFT UNTOUCHED — framer-motion stays available to them in their lazy chunks.

**Tech Stack:** React 18, Vite 7, Tailwind, framer-motion (kept as a dep — only removed from the 3 boot-path files), vitest + vitest-axe.

## Global Constraints

- **Behaviour-preserving:** the animations should look essentially the same (fade/slide of the same direction/magnitude/timing). The Shell route transition becomes **enter-only** (no exit animation — `AnimatePresence mode="wait"` exit is dropped; an enter-only CSS fade is the standard CSS equivalent and removes the exit-wait latency). Note this minor UX change in the task.
- **Reduced motion:** every replaced animation must be disabled under `prefers-reduced-motion` — use Tailwind's `motion-reduce:animate-none` / `motion-safe:` variants (or a CSS `@media (prefers-reduced-motion: reduce)` block). Do NOT use framer-motion's `useReducedMotion` in the three boot-path files (that re-imports the lib).
- **Do NOT touch** the six already-lazy framer-motion files. Keep `framer-motion` in `package.json` (still used by them).
- **No `as any`** (CI: `npm run lint` = `eslint .`, error-level on no-explicit-any). i18n: these components already use `useTranslation`; any new visible string must go through `t()` (none expected — this is animation-only).
- **Preserve all non-animation behaviour** in BottomSheet: the portal-to-`body`, `role="dialog"`/`aria-modal`/`aria-label`, focus-on-open, body-scroll-lock, the touch-drag-to-dismiss (`onTouchStart`/`onTouchEnd`, delta > 100 → close), the `data-testid="bottom-sheet-backdrop"`, backdrop click-to-close, the desktop fallback branch, and `env(safe-area-inset-bottom)` padding.
- **Verify per task** from `frontend/`: `npx tsc --noEmit`, `npm run lint`, `npx vitest run <touched tests>` green, and the FULL `npx vitest run` shows NO NEW failures vs the ~68 local-env baseline. Final task also `npm run build` + a bundle check.
- Commit straight to `main`; body ends `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. iOS-visible (WKWebView) → final task runs `npm run build && npx cap sync`.

## File Structure

- `frontend/src/index.css` (or the project's global CSS) — add shared keyframes: `route-in` (opacity 0→1, translateY 8px→0), `hero-in` (the HomeHero entrance), `sheet-in` (translateY 100%→0), `backdrop-in` (opacity 0→1). (Confirm the global CSS file the project uses.)
- `frontend/src/components/child/Shell.tsx` — replace `AnimatePresence`/`motion.main` with a keyed `<main>` + CSS class; drop framer-motion import + `useReducedMotion`.
- `frontend/src/components/child/HomeHero.tsx` — replace `motion` with CSS entrance; drop framer-motion import.
- `frontend/src/components/mobile/BottomSheet.tsx` — replace `AnimatePresence`/`motion` with CSS + an open/closing state machine; drop framer-motion import + `useReducedMotion`.

---

### Task 1: Shared CSS keyframes + Shell route transition

**Files:** Modify the global CSS (find it — likely `frontend/src/index.css`); Modify `frontend/src/components/child/Shell.tsx`; Test `frontend/src/components/child/__tests__/Shell.test.tsx` (create if absent, or extend).

- [ ] **Step 1:** In the global CSS, add keyframes + a utility class for the route enter, reduced-motion-aware:

```css
@keyframes route-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-route-in { animation: route-in 0.15s ease-out both; }
@media (prefers-reduced-motion: reduce) {
  .animate-route-in { animation: none; }
}
```

- [ ] **Step 2 (failing test):** Add/extend a Shell test asserting the `<main id="main">` renders the Outlet and carries the `animate-route-in` class, and that Shell no longer depends on framer-motion (e.g. the test renders without a framer-motion mock and the main element is keyed by pathname). Run → fails (Shell still uses motion.main).

- [ ] **Step 3:** In `Shell.tsx`: remove `import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'` and the `const prefersReducedMotion = useReducedMotion()` line. Replace the `<AnimatePresence mode="wait"><motion.main …>` block with:

```tsx
<main
  key={location.pathname}
  id="main"
  tabIndex={-1}
  className="pb-20 md:pb-0 outline-none animate-route-in"
  style={{ paddingLeft: 'var(--safe-left)', paddingRight: 'var(--safe-right)' }}
>
  <RouteErrorBoundary>
    <Outlet />
  </RouteErrorBoundary>
</main>
```

(The `key={location.pathname}` remounts `<main>` on each navigation, replaying the CSS animation. `location` is already in scope.)

- [ ] **Step 4:** Run the Shell test → green. `npx tsc --noEmit` + `npm run lint` clean. Full `npx vitest run` → no new failures.
- [ ] **Step 5:** Commit `perf(boot): CSS route transition in Shell (drop framer-motion)`.

---

### Task 2: HomeHero CSS entrance

**Files:** Modify `frontend/src/components/child/HomeHero.tsx`; the global CSS (add `hero-in` keyframes if its entrance differs from `route-in`); Test the HomeHero test (extend/create).

- [ ] **Step 1:** Read `HomeHero.tsx` to see its exact `motion` usage (which element, what initial/animate values). Add a matching CSS keyframe+class in the global CSS if it differs from `route-in` (reduced-motion-aware, same pattern as Task 1).
- [ ] **Step 2 (failing test):** Assert HomeHero renders its content with the CSS entrance class and without importing framer-motion. Run → fails.
- [ ] **Step 3:** Replace the `motion.<el>` with a plain `<el className="… animate-hero-in">` (or reuse `animate-route-in` if the entrance matches); remove the framer-motion import. Preserve all props/content/layout.
- [ ] **Step 4:** Test green; tsc + lint clean; full suite no new failures.
- [ ] **Step 5:** Commit `perf(boot): CSS entrance in HomeHero (drop framer-motion)`.

---

### Task 3: BottomSheet CSS slide + exit state machine

**Files:** Modify `frontend/src/components/mobile/BottomSheet.tsx`; the global CSS (`sheet-in`/`backdrop-in`); Test `frontend/src/components/mobile/__tests__/BottomSheet.test.tsx` (extend the existing test).

**Interfaces:** Public props unchanged: `{ open, onOpenChange, title, children, desktopFallback }`.

- [ ] **Step 1:** Add CSS for the sheet + backdrop enter (reduced-motion-aware):

```css
@keyframes sheet-in { from { transform: translateY(100%); } to { transform: translateY(0); } }
@keyframes sheet-out { from { transform: translateY(0); } to { transform: translateY(100%); } }
@keyframes backdrop-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes backdrop-out { from { opacity: 1; } to { opacity: 0; } }
.sheet-enter { animation: sheet-in 0.3s cubic-bezier(0.32, 0.72, 0, 1) both; }
.sheet-exit  { animation: sheet-out 0.25s ease-in both; }
.backdrop-enter { animation: backdrop-in 0.2s ease-out both; }
.backdrop-exit  { animation: backdrop-out 0.2s ease-in both; }
@media (prefers-reduced-motion: reduce) {
  .sheet-enter, .sheet-exit, .backdrop-enter, .backdrop-exit { animation: none; }
}
```

- [ ] **Step 2 (failing test):** Extend the BottomSheet test: opening renders the dialog (role=dialog, aria-label) + backdrop (`data-testid="bottom-sheet-backdrop"`); clicking the backdrop calls `onOpenChange(false)`; a touch drag down > 100px calls `onOpenChange(false)`; after `open` goes false the sheet unmounts (after its exit animation / a fake-timer tick); rendering does NOT require a framer-motion mock. Run → fails.

- [ ] **Step 3:** Reimplement without framer-motion. Replace the `AnimatePresence`/`motion.div` pair with plain `<div>`s using the CSS classes, and add a small mount-during-exit state machine so the exit animation can play before unmount:

```tsx
// remove: import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useRef, useEffect, useState, type ReactNode } from 'react';
// ...
const [rendered, setRendered] = useState(open);
useEffect(() => {
  if (open) setRendered(true);
}, [open]);
// when closing, unmount after the exit animation ends (or immediately under reduced motion)
const handleSheetAnimEnd = () => { if (!open) setRendered(false); };
// ...
if (isDesktop) { /* unchanged desktop branch */ }
if (!rendered) return null;
return createPortal(
  <>
    <div
      data-testid="bottom-sheet-backdrop"
      className={`fixed inset-0 z-40 bg-black/40 ${open ? 'backdrop-enter' : 'backdrop-exit'}`}
      onClick={() => onOpenChange(false)}
    />
    <div
      ref={sheetRef}
      role="dialog" aria-modal="true" aria-label={title} tabIndex={-1}
      className={`fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-white shadow-xl outline-none ${open ? 'sheet-enter' : 'sheet-exit'}`}
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      onAnimationEnd={handleSheetAnimEnd}
      onTouchStart={(e) => { dragStartY.current = e.touches[0].clientY; }}
      onTouchEnd={(e) => { const d = e.changedTouches[0].clientY - dragStartY.current; if (d > 100) onOpenChange(false); }}
    >
      {/* drag handle, title, content — unchanged */}
    </div>
  </>,
  document.body,
);
```

Keep the focus-on-open effect and the body-scroll-lock effect (gate scroll-lock on `open`, not `rendered`). Under reduced motion the exit animation is `none`, so `onAnimationEnd` may not fire — guard unmount with a fallback: if `!open` and reduced motion, set `rendered=false` directly (e.g. a `useEffect` that, when `!open`, schedules `setRendered(false)` via a short `setTimeout` matching the animation duration as a backstop). Ensure the test (which may not run real animations in jsdom) can still unmount — drive it via the timeout backstop or fire `animationend`.

- [ ] **Step 4:** BottomSheet test green (open/close/backdrop-click/touch-dismiss/unmount/a11y, vitest-axe clean). tsc + lint clean. Full suite no new failures. Manually confirm the ProfileMenu/FeedbackDialog/TradeForm consumers still typecheck (they pass the same props).
- [ ] **Step 5:** Commit `perf(boot): CSS BottomSheet (drop framer-motion)`.

---

### Task 4: Verify framer-motion off the boot chunk + ship

**Files:** Modify `docs/MASTER-BACKLOG.md`.

- [ ] **Step 1:** `npx tsc --noEmit` clean; `npm run lint` 0 errors; full `npx vitest run` = no new failures vs baseline; `npm run build` succeeds.
- [ ] **Step 2 (bundle proof):** Confirm framer-motion is no longer in the entry/boot chunk. Two checks: (a) `grep -rl "from 'framer-motion'" frontend/src` returns ONLY the six already-lazy files (Shell/HomeHero/BottomSheet absent). (b) In `frontend/dist/assets`, confirm the framer-motion code is NOT in the main entry chunk — e.g. identify the entry chunk from `dist/index.html`, and grep the built JS for a framer-motion marker (e.g. `framer-motion` source string / a known export) to confirm it sits only in lazy route chunks, not the entry. Report which chunk(s) contain it.
- [ ] **Step 3:** `npx cap sync` (iOS-visible change). Confirm no tracked native changes (web copies are gitignored).
- [ ] **Step 4:** Push → watch CI (`gh run view <id> --json status,conclusion,jobs`; Frontend job is the gate) → all green. Then Vercel two-step: `vercel --prod --yes` (from `frontend/`) → `vercel alias set <hash>-investikid.vercel.app app.investikid.ai` → `curl` the domain → 200.
- [ ] **Step 5:** Update `docs/MASTER-BACKLOG.md` (mark the framer-motion-off-boot refactor done + that both P3 refactors are now complete; only the deferred paid-quote-API remains). Commit `docs: framer-motion off boot path shipped` + push.

---

## Notes for the executor

- Find the project's global CSS file first (where Tailwind directives + existing keyframes live) — put all new keyframes there, once.
- The route transition intentionally becomes enter-only (no exit). This is the standard CSS equivalent of `AnimatePresence mode="wait"` and is a minor, acceptable UX change (less latency).
- Keep `framer-motion` in package.json — six other components still use it on lazy paths.
- Reduced-motion must be honoured in every replacement (CSS `@media (prefers-reduced-motion: reduce)`), matching the prior `useReducedMotion` gating.
- iOS-visible: the final task runs `npm run build && npx cap sync`; native rebuild (Xcode/Gradle) to ship on device is an operator follow-up (web is live via Vercel).
