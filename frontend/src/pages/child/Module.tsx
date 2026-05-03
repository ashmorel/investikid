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
    return <div className="mx-auto max-w-3xl p-6 text-sm text-muted-foreground">Loading…</div>;
  }

  if (modulesQ.isError || lessonsQ.isError) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p>Module not found or locked.</p>
        <Link to="/lessons" className="text-sm underline">← Back to lessons</Link>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);
  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const completed = lessons.filter((l) => l.completed).length;
  const nextIndex = lessons.findIndex((l) => !l.completed);

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">{module?.title ?? 'Module'}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {completed} / {lessons.length} lessons complete
      </p>
      <div className="mt-4 rounded-lg border bg-card">
        {lessons.map((lesson, i) => (
          <LessonRow
            key={lesson.id}
            moduleId={moduleId!}
            lesson={lesson}
            status={lesson.completed ? 'done' : i === nextIndex ? 'next' : 'later'}
          />
        ))}
      </div>
      <Link to="/lessons" className="mt-4 inline-block text-sm underline">← Back to lessons</Link>
    </div>
  );
}
