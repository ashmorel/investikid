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
