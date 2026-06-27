import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { contentApi, type LessonSummary } from '@/api/content';
import { useOnline } from '@/hooks/useOnline';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '@/lib/offline/scope';
import { cacheFirst } from '@/lib/offline/useOfflineContent';
import { getLesson, upsertLesson } from '@/lib/offline/contentStore';

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
      const scope = scopeFromMe(queryClient.getQueryData<Me>(['me']));
      for (const lesson of lessons) {
        void queryClient.prefetchQuery({
          queryKey: ['lesson', lesson.id],
          queryFn: cacheFirst({
            scope,
            fetch: () => contentApi.getLesson(lesson.id),
            read: (s) => getLesson(s, lesson.id),
            write: (s, data) => data != null ? upsertLesson(s, data, null) : Promise.resolve(),
          }),
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
