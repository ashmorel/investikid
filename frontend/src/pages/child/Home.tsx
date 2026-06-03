import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type ModuleOut } from '@/api/content';
import { useRecommendations, type RecommendationCategoryItem } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { ReviewBanner } from '@/components/child/ReviewBanner';
import { QuestTile } from '@/components/child/ui/QuestTile';
import { Button } from '@/components/ui/button';
import HomeHero from '@/components/child/HomeHero';

type Category = 'continue_learning' | 'practise_again' | 'something_new';

const CATEGORY_META: Record<Category, { label: string; icon: string; color: string }> = {
  continue_learning: { label: 'Continue Learning', icon: '▶', color: 'text-green-400' },
  practise_again: { label: 'Practise Again', icon: '🔄', color: 'text-amber-400' },
  something_new: { label: 'Something New', icon: '✨', color: 'text-sky-400' },
};

type Quest = {
  key: string;
  module: ModuleOut;
  href: string;
  eyebrow: string;
  reason: string;
};

function toQuests(
  recommendations: Partial<Record<Category, RecommendationCategoryItem[]>> | undefined,
  modules: ModuleOut[],
): Quest[] {
  const byId = new Map(modules.map((module) => [module.id, module]));
  const seen = new Set<string>();
  const categories: Category[] = ['continue_learning', 'practise_again', 'something_new'];

  return categories.flatMap((category) =>
    (recommendations?.[category] ?? []).flatMap((item) => {
      const module = byId.get(item.module_id);
      if (!module || seen.has(module.id)) return [];
      seen.add(module.id);
      return [{
        key: `${category}-${module.id}`,
        module,
        href: item.lesson_id ? `/lessons/${item.module_id}/${item.lesson_id}` : `/lessons/${item.module_id}`,
        eyebrow: CATEGORY_META[category].label,
        reason: item.reason,
      }];
    }),
  );
}

export default function Home() {
  const { data: progress } = useProgress();
  const { data: recs, isLoading: recsLoading } = useRecommendations();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const modules = modulesQ.data ?? [];
  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;
  const xpInLevel = xp % 100;
  const xpForNext = 100;

  const quests = toQuests(recs ?? undefined, modules);
  const fallbackQuests: Quest[] = quests.length > 0
    ? quests
    : modules.slice(0, 4).map((module) => ({
        key: `module-${module.id}`,
        module,
        href: `/lessons/${module.id}`,
        eyebrow: 'New quest',
        reason: module.locked ? 'Unlock this quest as you keep learning.' : 'Start this quest when you are ready.',
      }));

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">Your learning home</h1>
      <section aria-label="Up next">
        <HomeHero />
      </section>

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

      <section className="mt-6" aria-label="Your quests">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-extrabold uppercase text-orange-600">Quest board</p>
            <h2 className="text-xl font-black leading-tight text-gray-950">Your quests</h2>
          </div>
          <Link to="/lessons" className="text-sm font-extrabold text-orange-600 hover:text-orange-700">
            See all
          </Link>
        </div>
        {recsLoading ? (
          <p className="rounded-3xl border border-white/80 bg-white p-4 text-sm font-semibold text-gray-500 shadow-sm">
            Loading recommendations...
          </p>
        ) : fallbackQuests.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {fallbackQuests.map((quest) => (
              <QuestTile
                key={quest.key}
                module={quest.module}
                href={quest.href}
                eyebrow={quest.eyebrow}
                reason={quest.reason}
              />
            ))}
          </div>
        ) : null}
      </section>

      <div className="mt-5">
        <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}
