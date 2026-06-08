import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary } from '@/api/content';
import { ApiError } from '@/api/client';
import { LessonRow } from '@/components/child/LessonRow';
import { BackButton } from '@/components/child/BackButton';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';

export default function Level() {
  const { moduleId, levelId } = useParams<{ moduleId: string; levelId: string }>();
  const { open: openPaywall } = usePremiumPaywall();

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['level-lessons', levelId],
    queryFn: () => contentApi.listLevelLessons(levelId!),
    enabled: !!levelId, retry: false, staleTime: 60_000,
  });

  const premiumErr = lessonsQ.isError && lessonsQ.error instanceof ApiError
    && lessonsQ.error.code === 'premium_required' ? lessonsQ.error : null;
  const premiumLabel = ((premiumErr?.context as { label?: string }) ?? {}).label ?? 'this level';
  useEffect(() => {
    if (premiumErr) {
      openPaywall({ kind: 'level', label: premiumLabel });
    }
  }, [premiumErr, premiumLabel, openPaywall]);

  if (lessonsQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">Loading…</div>;
  }

  if (lessonsQ.isError) {
    const err = lessonsQ.error;
    if (premiumErr || (err instanceof ApiError && err.status === 403)) {
      return (
        <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
          <BackButton to={`/lessons/${moduleId ?? ''}`} label="Levels" />
          <p className="mt-2 font-semibold text-gray-900">Premium</p>
          <button
            type="button"
            onClick={() => openPaywall({ kind: 'level', label: premiumLabel })}
            className="mt-2 rounded-full bg-brand-gradient px-5 py-2 text-sm font-bold text-white shadow"
          >
            See what's included
          </button>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to={`/lessons/${moduleId ?? ''}`} label="Levels" />
        <p className="mt-2">Level not found.</p>
      </div>
    );
  }

  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const completed = lessons.filter((l) => l.completed).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to={`/lessons/${moduleId ?? ''}`} label="Levels" />

      <div className="mt-3 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span>Level progress</span>
          <span>{completed} / {lessons.length} lessons</span>
        </div>
        <div
          className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
          role="progressbar"
          aria-valuenow={completed}
          aria-valuemin={0}
          aria-valuemax={lessons.length}
          aria-label="Level progress"
        >
          <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${lessons.length ? Math.round((completed / lessons.length) * 100) : 0}%` }} />
        </div>
      </div>

      <div className="mt-4 rounded-2xl border-2 border-brand-200 bg-white overflow-hidden">
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
