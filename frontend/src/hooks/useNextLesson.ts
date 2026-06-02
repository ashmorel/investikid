import { useQuery } from '@tanstack/react-query';
import { contentApi, type ModuleOut, type LevelOut, type LessonSummary } from '@/api/content';
import { useRecommendations } from '@/api/ai';
import { pickTargetModule, pickTargetLevel, pickTargetLesson, type HeroMode } from '@/lib/homeHero';

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
  const { data: recs, isLoading: recsLoading } = useRecommendations();
  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'], queryFn: () => contentApi.listModules(), retry: false, staleTime: 60_000,
  });
  const modules = modulesQ.data ?? [];

  const target = pickTargetModule(recs, modules);
  const moduleId = target?.moduleId ?? null;
  const module = modules.find((m) => m.id === moduleId) ?? null;

  const levelsQ = useQuery<LevelOut[] | null>({
    queryKey: ['module-levels', moduleId], queryFn: () => contentApi.listLevels(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });
  const targetLevel = levelsQ.data ? pickTargetLevel(levelsQ.data) : null;

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['level-lessons', targetLevel?.id], queryFn: () => contentApi.listLevelLessons(targetLevel!.id),
    enabled: !!targetLevel, retry: false, staleTime: 60_000,
  });
  const targetLesson = lessonsQ.data ? pickTargetLesson(lessonsQ.data) : null;

  const isLoading = recsLoading || modulesQ.isLoading || modulesQ.data == null
    || (!!moduleId && levelsQ.isLoading)
    || (!!targetLevel && lessonsQ.isLoading);

  const caughtUp = !isLoading && (
    target === null
    || (!!levelsQ.data && targetLevel === null)
    || (!!lessonsQ.data && targetLesson === null)
  );

  if (caughtUp) {
    return { mode: 'caught_up', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: false };
  }

  if (!target || !targetLevel || !targetLesson || !module) {
    return { mode: target?.mode ?? 'start', moduleId, levelId: targetLevel?.id ?? null, lessonId: null, moduleTitle: module?.title ?? null, moduleIcon: module?.icon ?? null, lessonLabel: null, to: null, isLoading };
  }

  return {
    mode: target.mode,
    moduleId, levelId: targetLevel.id, lessonId: targetLesson.id,
    moduleTitle: module.title, moduleIcon: module.icon, lessonLabel: targetLesson.title,
    to: `/lessons/${moduleId}/${targetLevel.id}/${targetLesson.id}`,
    isLoading: false,
  };
}
