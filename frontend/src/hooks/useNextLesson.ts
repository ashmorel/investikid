import { useQuery } from '@tanstack/react-query';
import { contentApi } from '@/api/content';
import type { HeroMode } from '@/lib/homeHero';

export interface NextLesson {
  mode: HeroMode;
  moduleId: string | null;
  levelId: string | null;
  lessonId: string | null;
  moduleTitle: string | null;
  moduleIcon: string | null;
  lessonLabel: string | null;
  to: string | null;
  isLoading: boolean;
}

export function useNextLesson(): NextLesson {
  const { data, isLoading } = useQuery({
    queryKey: ['next-lesson'],
    queryFn: () => contentApi.nextLesson(),
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return { mode: 'start', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: true };
  }

  const next = data?.next ?? null;
  if (!next) {
    return { mode: 'caught_up', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: false };
  }

  return {
    mode: next.mode,
    moduleId: next.module_id,
    levelId: next.level_id,
    lessonId: next.lesson_id,
    moduleTitle: next.module_title,
    moduleIcon: next.module_icon,
    lessonLabel: next.lesson_title,
    to: `/lessons/${next.module_id}/${next.level_id}/${next.lesson_id}`,
    isLoading: false,
  };
}
