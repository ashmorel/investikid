// frontend/src/lib/__tests__/offlineMutations.test.ts
import { describe, it, expect, vi } from 'vitest';
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
    // ApiError(status, detail, code?, context?) — real constructor order
    expect(defs.retry(0, new ApiError(403, 'msg', 'premium_required'))).toBe(false);
  });
});
