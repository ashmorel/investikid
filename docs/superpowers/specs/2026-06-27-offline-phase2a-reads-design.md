# Offline support — Phase 2a (reads): PWA app-shell + content prefetch — design

**Date:** 2026-06-27
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Make the web app open offline (precached app-shell) and make a whole learning
level readable offline after one online visit (prefetch its lessons). Frontend
only. This is the first of two Phase-2 cycles; **2b (the offline-write sync
outbox) is separate.**

## Context

- Phase 1 already wired `@capacitor/network` → `onlineManager`, `useOnline()`,
  TanStack persistence with an allowlist that includes `modules`,
  `module-levels`, `level-lessons`, `lesson`, `module`.
- The current service worker `frontend/public/sw.js` is a **no-op install-only
  stub** (no caching, no fetch interception); `main.tsx` registers it manually.
  A `public/manifest.json` exists and is linked from `index.html`.
- The native app (Capacitor/WKWebView) already bundles the shell and opens
  offline; service workers do not run under `capacitor://localhost`.

## Non-goals

- Offline writes / sync outbox (that is Phase 2b).
- Prefetching an entire module (multiple levels) — one level at a time bounds
  localStorage use (still ~5MB until Phase 3's SQLite move).
- Native PWA behavior — the SW is web-only; native is unaffected.

## Architecture (2 units)

### Unit 1 — PWA app-shell (web)
**Files:** add dep `vite-plugin-pwa`; modify `frontend/vite.config.ts`,
`frontend/src/main.tsx`; delete `frontend/public/sw.js`.

- Add `VitePWA` to the Vite plugins with:
  - `registerType: 'autoUpdate'` (new SW activates + reloads to the new build —
    fine for a kids' app; the native app ignores the SW).
  - `injectRegister: 'auto'` (the plugin injects SW registration; no manual
    `navigator.serviceWorker.register` needed).
  - `manifest: false` (keep the existing `public/manifest.json` linked from
    `index.html`; don't generate a second one).
  - `workbox: { globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'] }` so the
    built app-shell + assets are precached.
  - `devOptions: { enabled: false }` (don't run the SW in dev).
- Remove the manual `if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js')`
  block from `main.tsx` `bootstrap()`, and delete `public/sw.js`.
- Coexists with the existing `stripCrossorigin` plugin and the `__API_BASE__` /
  `__WEB_ORIGIN__` define globals (no interaction).
- Result: in a browser, the app shell + JS/CSS load from the SW cache offline.
  On native, SW registration silently no-ops; the bundled shell is unaffected.

### Unit 2 — Content prefetch (a level's lessons)
**Files:** create `frontend/src/hooks/usePrefetchLevelLessons.ts`; modify
`frontend/src/pages/child/Level.tsx`.

- `usePrefetchLevelLessons(lessons: { id: string }[])`: a hook that, when
  `useOnline()` is true, schedules (via `requestIdleCallback`, `setTimeout`
  fallback) a `queryClient.prefetchQuery({ queryKey: ['lesson', id], queryFn: () => contentApi.getLesson(id), staleTime: 60 * 60 * 1000 })` (lessons are static
  content; a 1h staleTime avoids redundant refetches) for each lesson id. No-ops
  when offline or when the list is empty. Cleans up the idle callback on unmount
  / list change.
- `Level.tsx` already loads `['level-lessons', levelId]`; pass the resolved
  lessons to `usePrefetchLevelLessons`. Because `lesson` is in the Phase-1
  persist allowlist, each prefetched lesson persists to localStorage → the whole
  level is readable offline after one online visit.

## Data flow

1. Online, viewing a Level: the lesson list loads → the hook idle-prefetches each
   lesson's content → TanStack persists them (allowlisted) to localStorage.
2. Offline later: the Level + its lessons render from the persisted cache; the
   web shell loads from the SW precache.
3. The SW auto-updates the precache on the next online visit after a new deploy.

## Error handling

- SW registration / precache failure → the injected registration is best-effort;
  a failure leaves the app working online-only (no crash). Native: no-op.
- Prefetch is fire-and-forget and online-gated; a failed prefetch just means that
  lesson isn't cached (falls back to a live fetch when opened online).

## Testing

- **Prefetch hook:** with a mocked `queryClient` + `useOnline`, assert it calls
  `prefetchQuery` once per lesson id when online (and idle fires), and calls it
  zero times when offline. Assert idempotence isn't required (prefetchQuery is
  itself a no-op for fresh cache).
- **PWA build:** a build-time assertion — after `npm run build`, `dist/sw.js`
  exists and the Workbox precache manifest references the entry JS/CSS. (A SW
  cannot be meaningfully unit-tested in jsdom.)
- **Regression:** `npm run build` succeeds and `npx cap sync ios/android` still
  works (native unaffected); the existing `*.offline` suites still pass.

## Implementation phasing (single plan)

1. `vite-plugin-pwa` dep + `vite.config.ts` config + `main.tsx` cleanup + delete
   stub `sw.js`; verify `dist/sw.js` + precache manifest; `cap sync`.
2. `usePrefetchLevelLessons` hook + wire into `Level.tsx` + test.
3. Verify (tsc + lint + vitest + build) → ship (CI → Vercel; cap sync) → docs.

## Future (out of scope)

- Phase 2b — offline-write sync outbox (lesson completions, quiz/review answers
  queued offline + replayed with idempotency keys on reconnect).
- Phase 3 — move the cache to Capacitor Preferences / SQLite.
