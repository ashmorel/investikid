import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { LessonRow } from '@/components/child/LessonRow';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
  });

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['module', moduleId, 'lessons'],
    queryFn: () => contentApi.listLessons(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  if (modulesQ.isLoading || lessonsQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">Loading…</div>;
  }

  if (modulesQ.isError || lessonsQ.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <p>Module not found or locked.</p>
        <Link to="/lessons" className="text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);
  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const completed = lessons.filter((l) => l.completed).length;

  return (
    <div className="mx-auto max-w-3xl">
      {/* Banner */}
      <div className="bg-gradient-to-br from-amber-100 to-amber-200 px-4 py-6 sm:px-6 sm:py-8 text-center">
        <span className="text-5xl">{module?.icon ?? '📚'}</span>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-900">{module?.title ?? 'Module'}</h1>
        <p className="mt-1 text-sm text-gray-600">
          {completed} / {lessons.length} quests complete
        </p>
      </div>

      {/* Quest list */}
      <div className="px-4 py-4 sm:px-6">
        <div className="rounded-2xl border-2 border-amber-200 bg-white overflow-hidden">
          {lessons.map((lesson, i) => {
            const nextIndex = lessons.findIndex((l) => !l.completed);
            return (
              <LessonRow
                key={lesson.id}
                moduleId={moduleId!}
                lesson={lesson}
                status={lesson.completed ? 'done' : i === nextIndex ? 'next' : 'later'}
              />
            );
          })}
        </div>
        <Link to="/lessons" className="mt-4 inline-block text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    </div>
  );
}
