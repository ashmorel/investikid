import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary } from '@/api/content';
import { ApiError } from '@/api/client';
import { LessonRow } from '@/components/child/LessonRow';

export default function Level() {
  const { moduleId, levelId } = useParams<{ moduleId: string; levelId: string }>();

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['level-lessons', levelId],
    queryFn: () => contentApi.listLevelLessons(levelId!),
    enabled: !!levelId, retry: false, staleTime: 60_000,
  });

  if (lessonsQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">Loading…</div>;
  }

  if (lessonsQ.isError) {
    const err = lessonsQ.error;
    if (err instanceof ApiError && err.status === 403) {
      return (
        <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
          <p className="font-semibold text-gray-900">This level is premium.</p>
          <p className="mt-1 text-sm text-gray-500">Ask a grown-up to unlock premium content.</p>
          <Link to={`/lessons/${moduleId ?? ''}`} className="mt-3 inline-block text-sm text-amber-600 hover:underline">← Back to levels</Link>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <p>Level not found.</p>
        <Link to={`/lessons/${moduleId ?? ''}`} className="text-sm text-amber-600 hover:underline">← Back to levels</Link>
      </div>
    );
  }

  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const completed = lessons.filter((l) => l.completed).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <Link to={`/lessons/${moduleId ?? ''}`} className="text-sm text-amber-600 hover:underline">← Back to levels</Link>

      <p className="mt-3 text-sm text-gray-500">
        {completed} / {lessons.length} quests complete
      </p>

      <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white overflow-hidden">
        {lessons.map((lesson, i) => {
          const nextIndex = lessons.findIndex((l) => !l.completed);
          return (
            <LessonRow
              key={lesson.id}
              moduleId={moduleId!}
              levelId={levelId!}
              lesson={lesson}
              status={lesson.completed ? 'done' : i === nextIndex ? 'next' : 'later'}
            />
          );
        })}
      </div>
    </div>
  );
}
