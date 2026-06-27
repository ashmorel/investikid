# Offline Phase 2b (writes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a child complete a lesson offline — optimistically marked done, queued, and synced automatically on reconnect (surviving an app restart) — via TanStack Query's native paused/persisted mutations.

**Architecture:** Register a `['completeLesson']` mutation default (recoverable fn + optimistic `onMutate` + invalidating `onSuccess` + retry); `onlineManager` (Phase 1) pauses it offline and resumes on reconnect; persist only paused completion mutations and resume them on cache restore. The server endpoint is idempotent, so replay is safe.

**Tech Stack:** React 18, TanStack Query 5 (`setMutationDefaults`, paused mutations, persistence), TypeScript, vitest.

## Global Constraints

- Frontend-only; no new dependency; no backend change. No native code → no native rebuild.
- One source of truth for connectivity is `onlineManager` (Phase 1). Mutation key is exactly `['completeLesson']`. Variables are `CompleteLessonVars = { lessonId: string; levelId: string | null; score: number | null }`.
- The completion endpoint is idempotent (replay → `already_completed: true`, no double XP). `retry: (failureCount, error) => failureCount < 3 && !(error instanceof ApiError)` — retry network up to 3×, never retry an `ApiError` (drop 4xx from the queue).
- `onMutate` optimistically sets `completed: true` on `['lesson', lessonId]` (LessonOut) and the matching item in `['level-lessons', levelId]` (LessonSummary[]); both types have `completed: boolean`. `onError` rolls back from the returned context. `onSuccess` invalidates `['progress']`, `['modules']`, `['module-levels']`, `['level-lessons', levelId]`, `['lesson', lessonId]` — it lives on the DEFAULT so it fires on background resume.
- Persist ONLY paused `['completeLesson']` mutations (`shouldDehydrateMutation`); resume them via `queryClient.resumePausedMutations()` on `PersistQueryClientProvider` `onSuccess`.
- No `as any` in tests (use `as unknown as T` / proper types) — CI runs `npm run lint` (= `eslint .`) which errors on `@typescript-eslint/no-explicit-any`.
- Verify: `npx tsc --noEmit` + **`npm run lint`** (eslint . — 0 errors) + `npx vitest run <files>` + `npm run build`. Known `api-*`/MSW `child-*` failures are pre-existing local-env (prod-API-base `.env`); verify only target files, compare to clean HEAD if unsure.
- Commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- `frontend/src/lib/offlineMutations.ts` (create) — `registerOfflineMutations(queryClient)` + `CompleteLessonVars`.
- `frontend/src/lib/queryPersistence.ts` (modify) — `shouldDehydrateMutation`.
- `frontend/src/main.tsx` (modify) — register defaults, persist mutations, resume on restore.
- `frontend/src/pages/child/Lesson.tsx` (modify) — use the keyed default + object variables; drop now-default invalidations.
- Tests alongside.

---

## Task 1: Completion mutation default (offlineMutations.ts)

**Files:**
- Create: `frontend/src/lib/offlineMutations.ts`
- Test: `frontend/src/lib/__tests__/offlineMutations.test.ts` (create)

**Interfaces:**
- Consumes: `QueryClient` (`@tanstack/react-query`); `ApiError` (`@/api/client`); `contentApi`, `type LessonOut`, `type LessonSummary`, `type LessonCompletionResult` (`@/api/content`).
- Produces: `registerOfflineMutations(queryClient: QueryClient): void`; `type CompleteLessonVars = { lessonId: string; levelId: string | null; score: number | null }`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/__tests__/offlineMutations.test.ts
import { describe, it, expect } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import type { LessonSummary, LessonOut } from '@/api/content';
import { registerOfflineMutations, type CompleteLessonVars } from '../offlineMutations';

function setup() {
  const qc = new QueryClient();
  registerOfflineMutations(qc);
  // getMutationDefaults returns the registered options object
  const defs = qc.getMutationDefaults(['completeLesson']) as {
    onMutate: (v: CompleteLessonVars) => Promise<unknown>;
    onError: (e: unknown, v: CompleteLessonVars, ctx: unknown) => void;
    onSuccess: (d: unknown, v: CompleteLessonVars) => void;
    retry: (n: number, e: unknown) => boolean;
  };
  return { qc, defs };
}

const vars: CompleteLessonVars = { lessonId: 'L1', levelId: 'LV1', score: null };

describe('registerOfflineMutations', () => {
  it('onMutate optimistically marks the lesson + list item completed', async () => {
    const { qc, defs } = setup();
    qc.setQueryData(['lesson', 'L1'], { id: 'L1', completed: false } as unknown as LessonOut);
    qc.setQueryData(['level-lessons', 'LV1'], [{ id: 'L1', completed: false }] as unknown as LessonSummary[]);
    await defs.onMutate(vars);
    expect(qc.getQueryData<LessonOut>(['lesson', 'L1'])).toMatchObject({ completed: true });
    expect((qc.getQueryData(['level-lessons', 'LV1']) as LessonSummary[])[0].completed).toBe(true);
  });

  it('onError rolls back the optimistic update', async () => {
    const { qc, defs } = setup();
    qc.setQueryData(['level-lessons', 'LV1'], [{ id: 'L1', completed: false }] as unknown as LessonSummary[]);
    const ctx = await defs.onMutate(vars);
    defs.onError(new Error('boom'), vars, ctx);
    expect((qc.getQueryData(['level-lessons', 'LV1']) as LessonSummary[])[0].completed).toBe(false);
  });

  it('onSuccess invalidates progress + the level list', async () => {
    const { qc, defs } = setup();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    defs.onSuccess(null, vars);
    expect(spy).toHaveBeenCalledWith({ queryKey: ['progress'] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['level-lessons', 'LV1'] });
  });

  it('retry: network errors retry up to 3, ApiError never retries', () => {
    const { defs } = setup();
    expect(defs.retry(0, new Error('network'))).toBe(true);
    expect(defs.retry(3, new Error('network'))).toBe(false);
    expect(defs.retry(0, new ApiError('premium_required', 'msg', 403))).toBe(false);
  });
});
```
(Add `import { vi } from 'vitest';` at the top. NOTE: `new ApiError(...)` must match the real `ApiError` constructor in `src/api/client.ts` — read it and adjust the args; the only thing the test needs is a real `instanceof ApiError` instance.)

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run src/lib/__tests__/offlineMutations.test.ts`
Expected: FAIL (`../offlineMutations` not found).

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/offlineMutations.ts
import type { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { contentApi, type LessonOut, type LessonSummary } from '@/api/content';

export type CompleteLessonVars = { lessonId: string; levelId: string | null; score: number | null };

type RollbackCtx = { prevLesson?: LessonOut | null; prevList?: LessonSummary[] | null };

/**
 * Register a resumable, optimistic default for the lesson-completion mutation
 * (key ['completeLesson']). A keyed default (not an inline closure) lets a
 * persisted/paused completion resume after an app restart — TanStack recovers
 * the fn by key. onlineManager pauses it offline + resumes on reconnect; the
 * server endpoint is idempotent so replay is safe.
 */
export function registerOfflineMutations(queryClient: QueryClient): void {
  queryClient.setMutationDefaults(['completeLesson'], {
    mutationFn: ({ lessonId, score }: CompleteLessonVars) => contentApi.completeLesson(lessonId, score),

    onMutate: async ({ lessonId, levelId }: CompleteLessonVars): Promise<RollbackCtx> => {
      const prevLesson = queryClient.getQueryData<LessonOut | null>(['lesson', lessonId]);
      if (prevLesson) {
        queryClient.setQueryData(['lesson', lessonId], { ...prevLesson, completed: true });
      }
      let prevList: LessonSummary[] | null | undefined;
      if (levelId) {
        prevList = queryClient.getQueryData<LessonSummary[] | null>(['level-lessons', levelId]);
        if (prevList) {
          queryClient.setQueryData(
            ['level-lessons', levelId],
            prevList.map((l) => (l.id === lessonId ? { ...l, completed: true } : l)),
          );
        }
      }
      return { prevLesson, prevList };
    },

    onError: (_error: unknown, { lessonId, levelId }: CompleteLessonVars, context: RollbackCtx | undefined) => {
      if (context && 'prevLesson' in context && context.prevLesson !== undefined) {
        queryClient.setQueryData(['lesson', lessonId], context.prevLesson);
      }
      if (levelId && context && 'prevList' in context && context.prevList !== undefined) {
        queryClient.setQueryData(['level-lessons', levelId], context.prevList);
      }
    },

    onSuccess: (_data: unknown, { lessonId, levelId }: CompleteLessonVars) => {
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      queryClient.invalidateQueries({ queryKey: ['module-levels'] });
      if (levelId) queryClient.invalidateQueries({ queryKey: ['level-lessons', levelId] });
      queryClient.invalidateQueries({ queryKey: ['lesson', lessonId] });
    },

    retry: (failureCount: number, error: unknown) => failureCount < 3 && !(error instanceof ApiError),
  });
}
```

- [ ] **Step 4: Run tests** — `npx vitest run src/lib/__tests__/offlineMutations.test.ts` → PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd frontend && npm run lint
git add frontend/src/lib/offlineMutations.ts frontend/src/lib/__tests__/offlineMutations.test.ts
git commit -m "feat(offline): completeLesson mutation default (optimistic + resumable) (Goal4 P2b)"
```

---

## Task 2: Persist only paused completion mutations

**Files:**
- Modify: `frontend/src/lib/queryPersistence.ts`
- Test: `frontend/src/lib/__tests__/queryPersistence.test.ts` (extend)

**Interfaces:**
- Produces: `shouldDehydrateMutation(mutation: Mutation): boolean`.

- [ ] **Step 1: Write the failing test**

```ts
// add to frontend/src/lib/__tests__/queryPersistence.test.ts
import type { Mutation } from '@tanstack/react-query';
import { shouldDehydrateMutation } from '../queryPersistence';

function m(isPaused: boolean, key: unknown[]): Mutation {
  return { state: { isPaused }, options: { mutationKey: key } } as unknown as Mutation;
}

it('persists only paused completeLesson mutations', () => {
  expect(shouldDehydrateMutation(m(true, ['completeLesson']))).toBe(true);
  expect(shouldDehydrateMutation(m(false, ['completeLesson']))).toBe(false); // settled
  expect(shouldDehydrateMutation(m(true, ['someOther']))).toBe(false);       // other key
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run src/lib/__tests__/queryPersistence.test.ts`
Expected: FAIL (`shouldDehydrateMutation` not exported).

- [ ] **Step 3: Implement**

Add to `frontend/src/lib/queryPersistence.ts` (import `Mutation` alongside the existing `Query` type import):
```ts
import type { Mutation, Query } from '@tanstack/react-query';

// ... existing code ...

/** Persist only paused lesson-completion mutations — the offline outbox.
 * Settled mutations and other keys are not persisted. */
export function shouldDehydrateMutation(mutation: Mutation): boolean {
  return (
    mutation.state.isPaused === true &&
    Array.isArray(mutation.options.mutationKey) &&
    mutation.options.mutationKey[0] === 'completeLesson'
  );
}
```

- [ ] **Step 4: Run tests** — `npx vitest run src/lib/__tests__/queryPersistence.test.ts` → PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd frontend && npm run lint
git add frontend/src/lib/queryPersistence.ts frontend/src/lib/__tests__/queryPersistence.test.ts
git commit -m "feat(offline): persist only paused completeLesson mutations (Goal4 P2b)"
```

---

## Task 3: Wire main.tsx — register defaults, persist + resume mutations

**Files:**
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Consumes: `registerOfflineMutations` (Task 1), `shouldDehydrateMutation` (Task 2).

- [ ] **Step 1: Register the defaults + import**

Add imports near the other lib imports:
```ts
import { createAppPersister, PERSIST_MAX_AGE, shouldDehydrateMutation, shouldDehydrateQuery } from './lib/queryPersistence';
import { registerOfflineMutations } from './lib/offlineMutations';
```
After `const persister = createAppPersister();` and `void initConnectivity();`, add:
```ts
registerOfflineMutations(queryClient);
```

- [ ] **Step 2: Persist mutations + resume on restore**

Change the `PersistQueryClientProvider` block:
```tsx
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{
            persister,
            maxAge: PERSIST_MAX_AGE,
            dehydrateOptions: { shouldDehydrateQuery, shouldDehydrateMutation },
          }}
          onSuccess={() => { void queryClient.resumePausedMutations(); }}
        >
          {appTree}
        </PersistQueryClientProvider>
```

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm run build`
Expected: clean / 0 errors / built.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx
git commit -m "feat(offline): persist + resume paused completion mutations on restore (Goal4 P2b)"
```

---

## Task 4: Wire Lesson.tsx to the keyed default

**Files:**
- Modify: `frontend/src/pages/child/Lesson.tsx`

**Interfaces:**
- Consumes: the `['completeLesson']` default (Task 1) + `CompleteLessonVars`.

- [ ] **Step 1: Add the mutation key + keep an inline mutationFn (object form)**

Change the `complete` mutation: add `mutationKey: ['completeLesson']`, change the variables type to `CompleteLessonVars`, and change the inline `mutationFn` to destructure the object. **Keep the inline `mutationFn`** — the interactive path and the existing Lesson tests (which create their own QueryClient without the default registered) rely on it; the *default's* mutationFn is what handles a RESTORED/RESUMED paused mutation (no observer mounted), and the default also supplies optimistic `onMutate`, cache-invalidation `onSuccess`, and `retry` (these fire alongside the component callbacks in production). Keep the component's presentational onSuccess (reward/collectables toasts), onError (paywall), and onSettled. Remove the 3 cache invalidations from the component onSuccess (now handled by the default's onSuccess):
```tsx
  const complete = useMutation<LessonCompletionResult | null, Error, CompleteLessonVars>({
    mutationKey: ['completeLesson'],
    mutationFn: ({ lessonId: lid, score }) => contentApi.completeLesson(lid, score),
    onSuccess: (result) => {
      // The default's onSuccess already invalidates progress / module-levels /
      // level-lessons / lesson. Here: presentational rewards only.
      if (result && !result.already_completed) {
        const marketName = (markets ?? []).find((m) => m.is_selected)?.name ?? '';
        const msg = formatRewardToast(tMarkets, result.reward, marketName);
        if (msg) toast({ description: msg });
        if (result.granted_collectables && result.granted_collectables.length > 0) {
          qc.invalidateQueries({ queryKey: ['collectables'] });
          toast({
            title: t('lesson.collectableEarned.title'),
            description: t('lesson.collectableEarned.description', {
              names: result.granted_collectables.join(', '),
            }),
          });
        }
      }
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'premium_required') {
        const label = (err.context as { label?: string } | undefined)?.label ?? t('lesson.premiumContent');
        openPaywall({ kind: 'home', label });
        return;
      }
      toast({ title: t('lesson.saveError'), description: t('lesson.tryAgain') });
    },
    onSettled: () => {
      completionInFlight.current = false;
    },
  });
```
Add the import: `import { type CompleteLessonVars } from '@/lib/offlineMutations';`

- [ ] **Step 2: Update the mutate call site**

Find where `complete.mutate(...)` is called (it currently passes a `score`). Change it to pass the object:
```tsx
complete.mutate({ lessonId: lessonId!, levelId, score });
```
(`levelId` is already in scope in Lesson.tsx — it's used in the existing `invalidateQueries(['level-lessons', levelId])`. `score` is whatever was passed before.)

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/pages/child/__tests__/Lesson.test.tsx 2>/dev/null; npm run build`
Expected: tsc/lint clean, build ok. (If a `Lesson.test.tsx` exists and mocks the mutation, ensure it still passes — the interactive completion must still navigate/toast.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/child/Lesson.tsx
git commit -m "feat(offline): Lesson uses the ['completeLesson'] keyed default (Goal4 P2b)"
```

---

## Task 5: Verify + ship + docs

**Files:** modify `docs/MASTER-BACKLOG.md`.

- [ ] **Step 1: Full frontend verify**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/lib src/pages/child/__tests__/Lesson.test.tsx 2>/dev/null; npm run build`
Expected: tsc clean, `npm run lint` 0 errors, target tests PASS, build ok. Then run the FULL suite once and confirm the failing file set is exactly the known `api-*`/MSW `child-*` baseline (compare to clean HEAD if any new file appears).

- [ ] **Step 2: Push + watch CI**

```bash
git push
# poll: gh run view <id> -R ashmorel/investikid --json conclusion,jobs
```
Expected: all 6 jobs green.

- [ ] **Step 3: Manual Vercel prod + native sync**

```bash
cd frontend && vercel --prod --yes
vercel alias set <new-hash>-investikid.vercel.app app.investikid.ai
curl -s -o /dev/null -w "%{http_code}\n" https://app.investikid.ai   # expect 200
npx cap sync ios && npx cap sync android   # no native code, but keep web assets in sync
```

- [ ] **Step 4: Docs + commit**

Update `docs/MASTER-BACKLOG.md` Goal 4: mark Phase 2b done (lesson-completion sync outbox via TanStack paused/persisted mutations; optimistic + idempotent replay); note Phase 3 (SQLite) remains.
```bash
git add docs/MASTER-BACKLOG.md
git commit -m "docs: offline Phase 2b (writes) shipped"
git push
```

---

## Notes / decisions baked in

- TanStack's `onlineManager` (Phase 1) does the pausing/resuming; we only register the default, persist paused completions, and resume on restore.
- The default's `onSuccess` (not the component's) carries the cache invalidation so it fires on a background resume with no Lesson mounted. The component keeps presentational rewards.
- Idempotent server → replay returns `already_completed` (no double XP); `retry` drops `ApiError`s so a bad item never blocks the queue.
- Quizzes (LLM-generated) + trades (need live prices) stay online-only.
