# Offline support — Phase 2b (writes): lesson-completion sync outbox — design

**Date:** 2026-06-27
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Let a child complete a lesson while offline: the lesson is optimistically marked
done, the completion is queued, and it syncs automatically when the connection
returns (surviving an app restart). Built on TanStack Query's native
paused/persisted mutations — no hand-rolled outbox. Frontend only.

## Context

- Phase 1 wired `@capacitor/network` → TanStack `onlineManager` (`useOnline`),
  and TanStack persistence (`PersistQueryClientProvider` in `main.tsx`,
  `shouldDehydrateQuery` + a key allowlist in `lib/queryPersistence.ts`).
- `Lesson.tsx` completes a lesson via `useMutation({ mutationFn: (score) =>
  contentApi.completeLesson(lessonId!, score) })` with an `onSuccess` that
  handles navigation/toast and reads `LessonCompletionResult`.
- The backend `POST /lessons/{id}/complete` is **idempotent**: `_award_completion`
  returns `already` and grants no duplicate XP on a repeat; the response carries
  `already_completed`. So replaying a queued completion is safe by construction.
- The persister currently dehydrates **queries only** (`dehydrateOptions` has no
  `shouldDehydrateMutation`); mutations are not persisted today.

## Non-goals

- Quiz / practice / review answers offline — quizzes are LLM-generated, which
  needs a connection. Online-only.
- Trades offline — need live prices to validate. Online-only.
- A visible "pending sync" indicator — optimistic completion + the existing
  `OfflineNotice` banner are the agreed UX. No new sync UI.
- Phase 3 (SQLite). The outbox rides on the existing localStorage persistence.

## Architecture (4 units)

### Unit 1 — Completion as a resumable mutation default
**Files:** create `frontend/src/lib/offlineMutations.ts`.

- `registerOfflineMutations(queryClient: QueryClient): void` calls
  `queryClient.setMutationDefaults(['completeLesson'], { mutationFn, onMutate,
  onSuccess, retry })`.
- `mutationFn: ({ lessonId, score }: CompleteLessonVars) =>
  contentApi.completeLesson(lessonId, score)`. Variables are the serializable
  `CompleteLessonVars = { lessonId: string; levelId: string | null; score: number | null }`.
  A *keyed default* (not an inline closure) is what lets a persisted/paused
  mutation resume after an app restart — functions aren't serialized; TanStack
  recovers the fn by mutation key.
- `retry: (failureCount, error) => failureCount < 3 && !(error instanceof ApiError)`
  — retry transient network failures up to 3×; do NOT retry an `ApiError` (a real
  HTTP error response, e.g. 403 market-locked / 404 deleted), so one bad item
  drops from the queue instead of blocking it.

### Unit 2 — Optimistic offline completion
**Files:** `offlineMutations.ts` (the `onMutate`/`onSuccess` above).

- `onMutate({ lessonId, levelId })`: snapshot then optimistically patch the
  caches that carry a `completed: boolean` flag so the kid sees completion
  immediately offline:
  - `['level-lessons', levelId]` (when `levelId` present) → set `completed: true`
    on the matching `LessonSummary` in the list (this is what the Level view
    renders — `LessonSummary.completed` exists).
  - `['lesson', lessonId]` → set `completed: true` only if `LessonOut` carries
    that field (the plan verifies the type; skip if absent).
  - `['progress']` → no optimistic change (authoritative XP/streak comes from the
    server on resume); only completion flags are optimistic.
  Returns a rollback context (the snapshots) for `onError`.
- `onError(_e, _vars, ctx)`: restore the snapshots (definitive failure only;
  network failures are retried/paused, not errored).
- `onSuccess(_data, { levelId })`: `invalidateQueries` for `['level-lessons',
  levelId]`, `['progress']`, `['modules']` (and `['lesson', lessonId]`) to pull
  authoritative server state. This `onSuccess` lives on the DEFAULT so it fires
  even on a background resume with no Lesson component mounted.

### Unit 3 — Wire `Lesson.tsx` to the default
**Files:** modify `frontend/src/pages/child/Lesson.tsx`.

- Change the `useMutation` to `useMutation({ mutationKey: ['completeLesson'] })`
  (drop the inline `mutationFn` — the default supplies it). Call site becomes
  `complete.mutate({ lessonId: lessonId!, levelId, score })`.
- Keep the component's own `onSuccess` (navigation, XP toast — reads
  `LessonCompletionResult`); it fires alongside the default's onSuccess when the
  mutation runs interactively. `levelId` comes from the route/lesson.

### Unit 4 — Persist + resume paused mutations
**Files:** modify `frontend/src/main.tsx`, `frontend/src/lib/queryPersistence.ts`.

- `queryPersistence.ts`: add `shouldDehydrateMutation(m: Mutation): boolean`
  returning `m.state.isPaused && m.options.mutationKey?.[0] === 'completeLesson'`
  — persist ONLY paused completion mutations (an offline completion awaiting
  sync), nothing settled.
- `main.tsx`:
  - call `registerOfflineMutations(queryClient)` after the client is created.
  - add `dehydrateOptions: { shouldDehydrateQuery, shouldDehydrateMutation }`.
  - add `onSuccess={() => queryClient.resumePausedMutations()}` to
    `PersistQueryClientProvider` (fires after the cache is restored from disk →
    drains any completion queued before an app restart). `onlineManager` already
    resumes live on reconnect.

## Data flow

1. Offline, kid finishes a lesson → `complete.mutate({lessonId, levelId, score})`
   → `onMutate` optimistically marks it done → `onlineManager` is offline →
   TanStack PAUSES the mutation (not sent).
2. The paused mutation is persisted to localStorage (`shouldDehydrateMutation`).
3. Reconnect → `onlineManager` resumes the paused mutation → POST
   `/lessons/{id}/complete` → `already`/fresh result → default `onSuccess`
   invalidates progress/level/modules → authoritative state appears.
4. App restarted while offline → on next boot the persister restores the paused
   mutation, `resumePausedMutations()` runs (drains when online).

## Error handling / replay safety

- Idempotent server: replay returns `already_completed: true` → success →
  dequeued, no double XP.
- `retry` drops `ApiError`s (4xx/handled) from the queue; retries network up to 3×.
- `onError` rolls back the optimistic flags only on a definitive error.
- Persisting only *paused* completion mutations bounds storage and avoids
  persisting in-flight/settled state.

## Testing

- **Default mutation:** `onMutate` optimistically patches `['lesson', id]` +
  `['level-lessons', levelId]` and returns a rollback ctx; `onError` restores it;
  `onSuccess` invalidates the expected keys; `retry` returns false for an
  `ApiError` and true (< 3) for a generic/network error.
- **Offline → paused:** with `onlineManager` offline, mutating does not call the
  network fn (mutation is paused); going online resumes it (one POST).
- **Persistence:** `shouldDehydrateMutation` returns true for a paused
  `['completeLesson']` mutation, false for a settled one and for other keys.
- **Resume on restore:** the `PersistQueryClientProvider onSuccess` calls
  `queryClient.resumePausedMutations()`.
- **Idempotent replay:** an `already_completed: true` response is treated as
  success (no rollback, dequeued).
- **Regression:** `Lesson.tsx`'s interactive completion still navigates + toasts
  (its own onSuccess still fires); existing Lesson tests pass.

## Implementation phasing (single plan)

1. `offlineMutations.ts` — `registerOfflineMutations` (defaults: mutationFn,
   onMutate optimistic, onError rollback, onSuccess invalidate, retry) + tests.
2. `queryPersistence.ts` — `shouldDehydrateMutation` + test.
3. `main.tsx` — register defaults, add `shouldDehydrateMutation`, add
   `resumePausedMutations` on restore.
4. `Lesson.tsx` — switch to `mutationKey: ['completeLesson']` + object variables.
5. Verify (`npm run lint` = `eslint .`, tsc, vitest, build) → ship (CI → Vercel;
   `cap sync` — no native code, so no rebuild) → docs.

## Future (out of scope)

- Phase 3 — move the cache (incl. the paused-mutation outbox) to Capacitor
  Preferences / SQLite.
- Extend the outbox to other safe-to-replay writes if any emerge.
