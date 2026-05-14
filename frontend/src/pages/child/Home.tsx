import { Link } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { aiApi, type Recommendations } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { Button } from '@/components/ui/button';

type NextUp = {
  module: ModuleOut;
  lesson: LessonSummary;
  hasAnyCompletion: boolean;
  reason: string;
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

  const recsQ = useQuery<Recommendations | null>({
    queryKey: ['recommendations'],
    queryFn: () => aiApi.getRecommendations(),
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
    const nq = recsQ.data?.next_quest;
    if (!nq) return null;
    const module = accessibleModules.find((m) => m.id === nq.module_id);
    if (!module) return null;
    // Find the lesson in the lesson queries
    const modIdx = accessibleModules.indexOf(module);
    const lessons = (lessonQueries[modIdx]?.data ?? []) as LessonSummary[];
    const lesson = lessons.find((l) => l.id === nq.lesson_id);
    if (!lesson) return null;
    const hasAnyCompletion = lessonQueries.some((q) =>
      ((q.data ?? []) as LessonSummary[]).some((l) => l.completed)
    );
    return { module, lesson, hasAnyCompletion, reason: nq.reason };
  })();

  const allDone = recsQ.isSuccess && !recsQ.data?.next_quest
    && lessonQueries.length > 0
    && lessonQueries.every((q) => q.isSuccess);

  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;
  const xpInLevel = xp % 100;
  const xpForNext = 100;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-extrabold text-gray-900">
        Hey {me?.username ?? '…'}! 👋
      </h1>
      <p className="mt-1 text-sm text-gray-500">Ready to level up your money skills?</p>

      <div className="mt-4">
        <StatsBar
          xp={xp}
          level={level}
          streakCount={progress?.streak_count ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
        />
      </div>

      {/* XP Progress to next level */}
      <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Level {level}</span>
          <span>{xpInLevel} / {xpForNext} XP</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-amber-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500 transition-all"
            style={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
          />
        </div>
      </div>

      {/* Next Quest card */}
      <section className="mt-5 rounded-2xl border-2 border-amber-200 bg-white p-4">
        {nextUp ? (
          <QuestCard nextUp={nextUp} />
        ) : allDone ? (
          <p className="text-sm text-center">🎉 You've completed all available quests — more coming soon!</p>
        ) : (
          <p className="text-sm text-gray-500">Loading quests…</p>
        )}
      </section>

      <div className="mt-5">
        <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}

function QuestCard({ nextUp }: { nextUp: NonNullable<NextUp> }) {
  const { module, lesson, hasAnyCompletion, reason } = nextUp;
  const cta = hasAnyCompletion ? 'Resume' : 'Start';
  return (
    <>
      <p className="text-xs font-bold text-amber-700 mb-2">🎯 YOUR NEXT QUEST</p>
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 text-2xl">
          {module.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-gray-900 truncate">{lesson.title}</p>
          <p className="text-xs text-gray-500">{module.title} · {lesson.xp_reward} XP</p>
          <p className="text-xs text-amber-600 mt-0.5">{reason}</p>
        </div>
        <Link
          to={`/lessons/${module.id}/${lesson.id}`}
          className="shrink-0 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-2 text-sm font-bold text-white hover:from-amber-500 hover:to-orange-600 transition-colors"
        >
          {cta} →
        </Link>
      </div>
    </>
  );
}
