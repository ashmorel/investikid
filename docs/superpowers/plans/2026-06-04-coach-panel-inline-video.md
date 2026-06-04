# Coach Panel Float + Inline iOS Video (SP-F) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the Coach Penny panel float (bottom sheet on mobile, side panel on desktop) and switch iOS lesson video back to an inline in-app player (B1). Frontend only.

**Tech Stack:** React + Tailwind v4 + shadcn `sheet.tsx` + Capacitor.

**Spec:** `docs/superpowers/specs/2026-06-04-coach-panel-inline-video-design.md`

**Conventions:** From `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` warning), `npm test`, `npm run build`. Backend untouched. Git from repo root; commit to `main`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. CI = 6 jobs (incl. iOS Capacitor compile). **READ each file before editing.**

**Verified:** `useMediaQuery(query)` (SSR-safe) at `src/hooks/useMediaQuery.ts`. `CoachChat` has `{ onNavigate?, showHeader? }`. `CoachPanel` currently a right `Sheet` with `w-full max-w-md`. `VideoLesson` branches on `isNativeApp()` (thumbnail vs iframe); `videoEmbed.ts` `buildYouTubeUrls` already returns a platform-tuned `embed` URL (native → `youtube.com/embed?...&playsinline=1`, web → nocookie) + `thumbnail` + `watch`.

---

### Task 1: Responsive CoachPanel (bottom sheet on mobile)

**Files:** Modify `src/components/child/CoachPanel.tsx`; Modify/add its test.

- [ ] **Step 1: READ** `CoachPanel.tsx` (current right-sheet) + a sibling test that mocks `useCoachGreeting`/`aiApi` (e.g. the CoachChat/Coach test).
- [ ] **Step 2: Implement** — pick the side by viewport:
```tsx
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';
import { CoachChat } from '@/components/child/CoachChat';
import { Penny } from '@/components/child/ui/Penny';
import { useMediaQuery } from '@/hooks/useMediaQuery';

type CoachPanelProps = { open: boolean; onOpenChange: (open: boolean) => void };

export function CoachPanel({ open, onOpenChange }: CoachPanelProps) {
  const isDesktop = useMediaQuery('(min-width: 640px)');
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={isDesktop ? 'right' : 'bottom'}
        className={
          isDesktop
            ? 'flex h-full w-full max-w-md flex-col gap-0 border-brand-100 bg-white p-0 sm:max-w-md'
            : 'flex h-[85svh] flex-col gap-0 rounded-t-2xl border-brand-100 bg-white p-0'
        }
      >
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <div>
            <SheetTitle>Coach Penny</SheetTitle>
            <SheetDescription>Ask Coach Penny for learning help.</SheetDescription>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-hidden px-4 py-3 pb-[calc(0.75rem+var(--safe-bottom))]">
          <CoachChat onNavigate={() => onOpenChange(false)} showHeader={false} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
```
- [ ] **Step 3: Test** `src/components/child/__tests__/CoachPanel.test.tsx` — mock `@/lib/...` chat deps (`useCoachGreeting`, `aiApi`) + `@/hooks/useMediaQuery`. Assert: with `useMediaQuery → false` (mobile), `open` renders "Coach Penny" + the chat and the `SheetContent` is the bottom variant (e.g. `getByRole('dialog')` has class containing `rounded-t-2xl`); with `→ true` (desktop) it renders the right variant (class contains `max-w-md`). Keep it simple/robust (class-substring checks are fine here since the side is the whole point).
- [ ] **Step 4: Verify** `npx tsc -b && npm run lint && npm test && npm run build`. Update the existing PennyFAB/Shell/CoachPanel tests if any assert the old single-variant class. Green.
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/CoachPanel.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/tests
git commit -m "fix(coach): bottom-sheet on mobile, side panel on desktop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Inline iOS video (B1)

**Files:** Modify `src/components/child/lesson/VideoLesson.tsx`; update `tests/unit/child-VideoLesson.native.test.tsx` (+ web test if needed).

- [ ] **Step 1: READ** `VideoLesson.tsx` + both video tests.
- [ ] **Step 2: Implement** — render the inline iframe for ALL platforms (drop the `nativeApp` thumbnail branch). Remove the now-unused `isNativeApp` import + `nativeApp` var + the `PlayCircle` import. Keep the `!youtubeUrls` fallback, the "Open video on YouTube" link, caption, transcript disclosure, "I watched this" checkbox, and "Mark complete". The media block becomes:
```tsx
<div className="aspect-video overflow-hidden rounded-md border">
  <iframe
    src={youtubeUrls.embed}
    title="Lesson video"
    referrerPolicy="strict-origin-when-cross-origin"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowFullScreen
    className="h-full w-full"
  />
</div>
```
(`youtubeUrls.embed` is already platform-tuned by `videoEmbed.ts` — native gets the `youtube.com/embed?...&playsinline=1` URL that plays inline in WKWebView; no change needed there.)
- [ ] **Step 3: Update tests.** `child-VideoLesson.native.test.tsx` currently asserts *no iframe* + a thumbnail — that behaviour is gone. Rewrite it to assert that **on native the inline iframe renders** with a YouTube embed `src` (keep the `vi.mock('@/lib/platform', () => ({ isNativeApp: () => true }))` to prove native no longer special-cases away the player, or simply assert the iframe + embed src). Keep the web test asserting the iframe + the "Open video on YouTube" fallback link.
- [ ] **Step 4: Verify** `npx tsc -b && npm run lint && npm test && npm run build`. Green (button.tsx warning only). Confirm no lingering `isNativeApp`/`PlayCircle` import in `VideoLesson.tsx`.
- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/lesson/VideoLesson.tsx invest-ed/frontend/tests
git commit -m "feat(video): inline in-app YouTube player on iOS (B1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Regression + push (+ simulator note)

- [ ] **Step 1: Full regression** from `invest-ed/frontend`: `npx tsc -b && npm run lint && npm test && npm run build`. Expected green.
- [ ] **Step 2: Push** from repo root: `git push origin main`.
- [ ] **Step 3: Confirm green CI** — all 6 jobs (incl. the iOS Capacitor compile job).
- [ ] **Step 4: Report + simulator follow-up.** Note to the user: verify on the iOS **simulator** that (a) the Coach FAB opens a bottom sheet (page dimmed behind, not full-screen) and (b) a video lesson plays **inline** (taps to play without forcing fullscreen, video visible). **If the video still forces fullscreen / doesn't load inline on the device**, the contingency is the Capacitor iOS WebView media setting — apply only then (don't add it blind): confirm Capacitor 8's iOS inline-media default and, if needed, set the appropriate `ios` WebView config in `capacitor.config.ts` (verify the exact key via Capacitor docs before adding), then `npx cap sync ios`.

---

## Self-Review
- **Spec coverage:** Coach responsive sheet → T1; inline iOS video B1 → T2; regression/push + simulator note → T3. ✓
- **Placeholders:** Full code for CoachPanel + the VideoLesson media block; the WKWebView config is an explicit conditional contingency (T3), not a vague TODO. ✓
- **Consistency:** `CoachPanel {open,onOpenChange}` unchanged; `CoachChat {onNavigate,showHeader}` reused; `useMediaQuery('(min-width: 640px)')` SSR-safe; `buildYouTubeUrls(...).embed` reused (no `videoEmbed.ts` change). ✓
