import { Link } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { StatsBar } from '@/components/child/StatsBar';
import { Button } from '@/components/ui/button';

type NextUp = {
  module: ModuleOut;
  lesson: LessonSummary;
  hasAnyCompletion: boolean;
} | null;

export default function Home() {
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const accessibleModules = (modulesQ.data ?? []).filter((m) => !m.locked);

  const lessonQueries = useQueries({
    queries: accessibleModules.map((m) => ({
      queryKey: ['module', m.id, 'lessons'],
      queryFn: () => contentApi.listLessons(m.id),
      retry: false,
      staleTime: 60_000,
    })),
  });

  const nextUp: NextUp = (() => {
    if (lessonQueries.some((q) => !q.isSuccess)) return null;
    let anyCompletion = false;
    for (let i = 0; i < accessibleModules.length; i++) {
      const lessons = (lessonQueries[i].data ?? []) as LessonSummary[];
      anyCompletion = anyCompletion || lessons.some((l) => l.completed);
      const next = lessons.find((l) => !l.completed);
      if (next) return { module: accessibleModules[i], lesson: next, hasAnyCompletion: anyCompletion };
    }
    return null;
  })();

  const allDone = lessonQueries.length > 0
    && lessonQueries.every((q) => q.isSuccess)
    && nextUp === null;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">
        Welcome back, {me?.username ?? '…'}
      </h1>

      <div className="mt-4">
        <StatsBar
          xp={progress?.xp ?? 0}
          level={progress?.level ?? 1}
          streakCount={progress?.streak_count ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
        />
      </div>

      <section className="mt-6 rounded-lg border bg-card p-4">
        {nextUp ? (
          <ContinueCard nextUp={nextUp} />
        ) : allDone ? (
          <p className="text-sm">🎉 You've completed all available modules — more coming soon.</p>
        ) : (
          <p className="text-sm text-muted-foreground">Loading lessons…</p>
        )}
      </section>

      <div className="mt-6">
        <Button asChild variant="outline">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}

function ContinueCard({ nextUp }: { nextUp: NonNullable<NextUp> }) {
  const { module, lesson, hasAnyCompletion } = nextUp;
  const cta = hasAnyCompletion ? 'Resume' : 'Start learning';
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm text-muted-foreground">{module.title}</p>
        <p className="font-medium">{lesson.title}</p>
        <p className="text-xs text-muted-foreground capitalize">
          {lesson.type} · {lesson.xp_reward} XP
        </p>
      </div>
      <Button asChild>
        <Link to={`/lessons/${module.id}/${lesson.id}`}>{cta} →</Link>
      </Button>
    </div>
  );
}
