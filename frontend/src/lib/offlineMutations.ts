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
