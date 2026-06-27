# Offline Phase 2a (reads) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the web app open offline (Workbox-precached app-shell) and make a whole learning level readable offline after one online visit (prefetch its lessons).

**Architecture:** Replace the no-op stub service worker with `vite-plugin-pwa` (Workbox precaches the build); add an online+idle hook that prefetches a level's lessons into the Phase-1-persisted `lesson` cache.

**Tech Stack:** React 18, TanStack Query 5 (persistence + prefetch), Vite 7, `vite-plugin-pwa`/Workbox, TypeScript, vitest.

## Global Constraints

- Frontend-only; one new dev dependency: `vite-plugin-pwa` (must be Vite-7-compatible — install latest).
- The service worker is **web-only**; it must be inert + harmless on native (`capacitor://localhost` doesn't run SWs; the native app bundles the shell). The native build (`npm run build` + `npx cap sync`) MUST stay green.
- `VitePWA` config: `registerType: 'autoUpdate'`, `injectRegister: 'auto'`, `manifest: false` (keep the existing `public/manifest.json` linked from `index.html`), `workbox.globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}']`, `devOptions.enabled: false`.
- Remove the manual `navigator.serviceWorker.register('/sw.js')` from `main.tsx` and delete `public/sw.js`.
- Prefetch is **online-gated** (`useOnline()`) + idle (`requestIdleCallback`, `setTimeout(…, 800)` fallback), one level at a time, `staleTime: 60 * 60 * 1000`. Reuses the Phase-1 `lesson` persist allowlist key.
- Verify: `npx tsc --noEmit` + `npx eslint <files>` (0 errors) + `npx vitest run <files>` + `npm run build`. Known baseline `api-*`/MSW `child-*` failures are pre-existing local-env (prod-API-base `.env`) — verify only target files; compare against clean HEAD if unsure.
- Commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- `frontend/package.json` (modify) — add `vite-plugin-pwa` (devDependency).
- `frontend/vite.config.ts` (modify) — add `VitePWA`.
- `frontend/src/main.tsx` (modify) — remove manual SW registration.
- `frontend/public/sw.js` (delete) — stub removed.
- `frontend/src/hooks/usePrefetchLevelLessons.ts` (create) — online+idle lesson prefetch.
- `frontend/src/pages/child/Level.tsx` (modify) — call the hook.
- Test alongside the hook.

---

## Task 1: PWA app-shell via vite-plugin-pwa

**Files:**
- Modify: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/main.tsx`
- Delete: `frontend/public/sw.js`

**Interfaces:**
- Produces: a generated `dist/sw.js` (Workbox) that precaches the build; no exported symbols.

- [ ] **Step 1: Install the dependency**

```bash
cd frontend && npm install -D vite-plugin-pwa
```
Expected: `vite-plugin-pwa` in `devDependencies` (a Vite-7-compatible version).

- [ ] **Step 2: Add VitePWA to `vite.config.ts`**

Add the import near the other plugin imports:
```ts
import { VitePWA } from 'vite-plugin-pwa';
```
Change the plugins array (currently `plugins: [react(), tailwindcss(), stripCrossorigin()],`) to:
```ts
  plugins: [
    react(),
    tailwindcss(),
    stripCrossorigin(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: false,
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
      devOptions: { enabled: false },
    }),
  ],
```

- [ ] **Step 3: Remove the stub SW registration from `main.tsx`**

Delete this block from `bootstrap()`:
```ts
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
```
(Leave the rest of `bootstrap()` — `registerBackButton()`, `initNativeChrome()`, `ensureAndroidChannel()` — untouched.)

- [ ] **Step 4: Delete the stub service worker**

```bash
cd frontend && git rm public/sw.js
```

- [ ] **Step 5: Build + verify the SW is generated and precaches the entry**

Run: `cd frontend && npm run build`
Expected: build succeeds; then verify:
```bash
test -f dist/sw.js && echo "sw.js present"
# Workbox writes the precache manifest into the SW (or a sibling); confirm it references the built JS:
grep -rqE "precache|\.js" dist/sw.js && echo "precache manifest present"
ls dist/workbox-*.js 2>/dev/null && echo "workbox runtime present"
```
Expected: `sw.js present`, `precache manifest present`. (A service worker can't be unit-tested in jsdom; this build assertion is the verification.)

- [ ] **Step 6: Verify native build path unaffected**

Run: `cd frontend && npx cap sync ios && npx cap sync android`
Expected: `Sync finished` on both (the SW is a web artifact; native bundles the shell). Also confirm `npx tsc --noEmit` is clean and `npx eslint vite.config.ts src/main.tsx` reports 0 errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/main.tsx frontend/public/sw.js frontend/ios frontend/android
git commit -m "feat(offline): vite-plugin-pwa app-shell precache, drop stub sw.js (Goal4 P2a)"
```

---

## Task 2: Prefetch a level's lessons (online + idle)

**Files:**
- Create: `frontend/src/hooks/usePrefetchLevelLessons.ts`
- Modify: `frontend/src/pages/child/Level.tsx`
- Test: `frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx` (create)

**Interfaces:**
- Consumes: `useOnline()` (`@/hooks/useOnline`); `useQueryClient` (`@tanstack/react-query`); `contentApi.getLesson(id)` and `type LessonSummary` (`@/api/content`).
- Produces: `usePrefetchLevelLessons(lessons: LessonSummary[] | null | undefined): void`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx
import { renderHook } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

const prefetchQuery = vi.fn();
vi.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ prefetchQuery }) }));
vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn() }));
vi.mock('@/api/content', () => ({ contentApi: { getLesson: vi.fn(async () => ({})) } }));

import { useOnline } from '@/hooks/useOnline';
import { usePrefetchLevelLessons } from '../usePrefetchLevelLessons';
const mockOnline = vi.mocked(useOnline);

const lessons = [{ id: 'a' }, { id: 'b' }] as any;

beforeEach(() => {
  prefetchQuery.mockClear();
  // run idle callbacks synchronously
  vi.stubGlobal('requestIdleCallback', (cb: () => void) => { cb(); return 1; });
  vi.stubGlobal('cancelIdleCallback', vi.fn());
});
afterEach(() => vi.unstubAllGlobals());

describe('usePrefetchLevelLessons', () => {
  it('prefetches each lesson when online', () => {
    mockOnline.mockReturnValue(true);
    renderHook(() => usePrefetchLevelLessons(lessons));
    expect(prefetchQuery).toHaveBeenCalledTimes(2);
    expect(prefetchQuery.mock.calls[0][0].queryKey).toEqual(['lesson', 'a']);
    expect(prefetchQuery.mock.calls[1][0].queryKey).toEqual(['lesson', 'b']);
  });

  it('does nothing when offline', () => {
    mockOnline.mockReturnValue(false);
    renderHook(() => usePrefetchLevelLessons(lessons));
    expect(prefetchQuery).not.toHaveBeenCalled();
  });

  it('does nothing for empty/null lessons', () => {
    mockOnline.mockReturnValue(true);
    renderHook(() => usePrefetchLevelLessons(null));
    expect(prefetchQuery).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run src/hooks/__tests__/usePrefetchLevelLessons.test.tsx`
Expected: FAIL (`../usePrefetchLevelLessons` not found).

- [ ] **Step 3: Implement the hook**

```ts
// frontend/src/hooks/usePrefetchLevelLessons.ts
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { contentApi, type LessonSummary } from '@/api/content';
import { useOnline } from '@/hooks/useOnline';

/**
 * When online + idle, prefetch each lesson's content into the (Phase-1
 * persisted) ['lesson', id] cache so a whole level is readable offline after
 * one online visit. No-ops offline or for an empty list.
 */
export function usePrefetchLevelLessons(lessons: LessonSummary[] | null | undefined): void {
  const queryClient = useQueryClient();
  const online = useOnline();

  useEffect(() => {
    if (!online || !lessons || lessons.length === 0) return;
    const run = () => {
      for (const lesson of lessons) {
        void queryClient.prefetchQuery({
          queryKey: ['lesson', lesson.id],
          queryFn: () => contentApi.getLesson(lesson.id),
          staleTime: 60 * 60 * 1000,
        });
      }
    };
    const ric = typeof window.requestIdleCallback === 'function' ? window.requestIdleCallback : null;
    const id = ric ? ric(run) : window.setTimeout(run, 800);
    return () => {
      if (ric && typeof window.cancelIdleCallback === 'function') window.cancelIdleCallback(id as number);
      else clearTimeout(id as number);
    };
  }, [online, lessons, queryClient]);
}
```

- [ ] **Step 4: Wire into `Level.tsx`**

Add the import and call the hook with the loaded lessons (`lessonsQ.data`):
```ts
import { usePrefetchLevelLessons } from '@/hooks/usePrefetchLevelLessons';
// inside the component, after lessonsQ is declared:
usePrefetchLevelLessons(lessonsQ.data);
```
(Place the call at the top level of the component body, not inside a conditional — `lessonsQ.data` is `undefined` until loaded, which the hook handles.)

- [ ] **Step 5: Run tests + tsc + lint + build**

Run: `cd frontend && npx vitest run src/hooks/__tests__/usePrefetchLevelLessons.test.tsx && npx tsc --noEmit && npx eslint src/hooks/usePrefetchLevelLessons.ts src/pages/child/Level.tsx && npm run build`
Expected: PASS / clean / built.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/usePrefetchLevelLessons.ts frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx frontend/src/pages/child/Level.tsx
git commit -m "feat(offline): prefetch a level's lessons online+idle for offline reads (Goal4 P2a)"
```

---

## Task 3: Verify + ship + docs

**Files:** modify `docs/MASTER-BACKLOG.md`.

- [ ] **Step 1: Full frontend verify**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run src/hooks src/pages/child/__tests__/Level.test.tsx 2>/dev/null; npm run build`
Expected: tsc clean, eslint 0 errors, target tests PASS, build ok (with `dist/sw.js`). Known `api-*`/MSW `child-*` baseline failures are pre-existing — compare to clean HEAD if unsure.

- [ ] **Step 2: Push + watch CI**

```bash
git push
# poll: gh run view <id> -R ashmorel/investikid --json conclusion,jobs   (NOT `gh run watch | tail`)
```
Expected: all 6 jobs green.

- [ ] **Step 3: Manual Vercel prod + confirm native synced**

```bash
cd frontend && vercel --prod --yes
vercel alias set <new-hash>-investikid.vercel.app app.investikid.ai
curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai   # expect 200
# Verify the SW is served on prod:
curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai/sw.js   # expect 200
# cap sync already run in Task 1.
```

- [ ] **Step 4: Docs + commit**

Update `docs/MASTER-BACKLOG.md` Goal 4: mark Phase 2a done (PWA app-shell precache + level-lesson prefetch); note Phase 2b (sync outbox) + Phase 3 remain, and that a native rebuild is unnecessary for 2a (web-only SW; native already opens offline).
```bash
git add docs/MASTER-BACKLOG.md
git commit -m "docs: offline Phase 2a (reads) shipped"
git push
```

---

## Notes / decisions baked in

- The SW is web-only; on native (`capacitor://localhost`) `injectRegister`'s registration silently no-ops and the bundled shell is unaffected — so no native rebuild is needed for 2a.
- `manifest: false` keeps the single existing `public/manifest.json` (no duplicate manifest).
- `autoUpdate` means a new deploy's SW activates and reloads the web app to the new build automatically — acceptable for a kids' app and avoids stale-asset bugs.
- Prefetch is one level at a time + online-gated to bound localStorage (~5MB until Phase 3) and avoid offline waste.
