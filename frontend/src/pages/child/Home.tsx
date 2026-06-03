import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type ModuleOut } from '@/api/content';
import { useRecommendations } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { ReviewBanner } from '@/components/child/ReviewBanner';
import { Button } from '@/components/ui/button';
import HomeHero from '@/components/child/HomeHero';
import { ModuleTile } from '@/components/child/ui/ModuleTile';

const TOPIC_STYLE: Record<string, { accent: string; tint: string }> = {
  stocks: { accent: '#fbbf24', tint: '#fff4d6' },
  savings: { accent: '#38bdf8', tint: '#e0f2fe' },
  budgeting: { accent: '#34d399', tint: '#dcfce7' },
  risk: { accent: '#a78bfa', tint: '#ede9fe' },
  crypto: { accent: '#6366f1', tint: '#e6e9ff' },
  taxes: { accent: '#f43f72', tint: '#ffe4ec' },
  debt: { accent: '#14b8a6', tint: '#d7f5f1' },
  entrepreneurship: { accent: '#f97316', tint: '#ffedd5' },
  real_estate: { accent: '#eab308', tint: '#fef9c3' },
};
const styleFor = (t: string) => TOPIC_STYLE[t] ?? { accent: '#fbbf24', tint: '#fff4d6' };

export default function Home() {
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const modules = [...(modulesQ.data ?? [])].sort((a, b) => a.order_index - b.order_index);
  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;
  const xpInLevel = xp % 100;
  const xpForNext = 100;

  const recommendedModuleId =
    recs?.continue_learning?.[0]?.module_id ??
    recs?.something_new?.[0]?.module_id ??
    null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">Your learning home</h1>
      <HomeHero />

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
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
            initial={{ width: 0 }}
            animate={{ width: `${(xpInLevel / xpForNext) * 100}%` }}
            transition={{ duration: 0.8, delay: 0.2 }}
          />
        </div>
      </div>

      {/* Review nudge banner */}
      {recs && recs.review_summary.due_count > 0 && (
        <div className="mt-5">
          <ReviewBanner dueCount={recs.review_summary.due_count} />
        </div>
      )}

      {/* Your quests module grid */}
      {modules.length > 0 && (
        <section className="mt-5" aria-label="Your quests">
          <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Your quests</h2>
          <div className="grid grid-cols-2 gap-3">
            {modules.map((m) => {
              const { accent, tint } = styleFor(m.topic);
              return (
                <ModuleTile
                  key={m.id}
                  emoji={m.icon}
                  title={m.title}
                  subtitle={m.locked ? 'Locked' : 'Open'}
                  accent={accent}
                  tint={tint}
                  to={`/lessons/${m.id}`}
                  locked={m.locked}
                  recommended={m.id === recommendedModuleId}
                />
              );
            })}
          </div>
        </section>
      )}

      <div className="mt-5">
        <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}
