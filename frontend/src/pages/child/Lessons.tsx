import { useQueries, useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { ModuleCard } from '@/components/child/ModuleCard';
import { useToast } from '@/hooks/use-toast';

export default function Lessons() {
  const { toast } = useToast();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const modules = modulesQ.data ?? [];

  const lessonQueries = useQueries({
    queries: modules.filter((m) => !m.locked).map((m) => ({
      queryKey: ['module', m.id, 'lessons'],
      queryFn: () => contentApi.listLessons(m.id),
      retry: false,
      staleTime: 60_000,
    })),
  });

  const lessonsByModuleId = new Map<string, LessonSummary[]>();
  let qIdx = 0;
  for (const m of modules) {
    if (m.locked) {
      lessonsByModuleId.set(m.id, []);
    } else {
      const data = (lessonQueries[qIdx]?.data ?? []) as LessonSummary[];
      lessonsByModuleId.set(m.id, data);
      qIdx++;
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-semibold">Lessons</h1>
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
        {modules.map((m) => {
          const lessons = lessonsByModuleId.get(m.id) ?? [];
          const completedCount = lessons.filter((l) => l.completed).length;
          return (
            <ModuleCard
              key={m.id}
              module={m}
              completedCount={completedCount}
              totalCount={lessons.length}
              onLockedClick={() => {
                toast({ title: 'Premium required', description: 'This module is part of the premium tier.' });
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
