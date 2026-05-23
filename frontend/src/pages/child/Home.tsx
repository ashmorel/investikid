import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type ModuleOut } from '@/api/content';
import { useRecommendations, type RecommendationCategoryItem } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { ReviewBanner } from '@/components/child/ReviewBanner';
import { RecommendationCard } from '@/components/child/RecommendationCard';
import { Button } from '@/components/ui/button';

type Category = 'continue_learning' | 'practise_again' | 'something_new';

const CATEGORY_META: Record<Category, { label: string; icon: string; color: string }> = {
  continue_learning: { label: 'Continue Learning', icon: '▶', color: 'text-green-400' },
  practise_again: { label: 'Practise Again', icon: '🔄', color: 'text-amber-400' },
  something_new: { label: 'Something New', icon: '✨', color: 'text-sky-400' },
};

function CategorySection({
  category,
  items,
  modules,
}: {
  category: Category;
  items: RecommendationCategoryItem[];
  modules: ModuleOut[];
}) {
  if (items.length === 0) return null;
  const meta = CATEGORY_META[category];

  return (
    <section className="mt-5" aria-label={meta.label}>
      <h2 className={`${meta.color} text-xs font-bold uppercase tracking-wider mb-2`}>
        {meta.icon} {meta.label}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const mod = modules.find((m) => m.id === item.module_id);
          return (
            <RecommendationCard
              key={item.module_id}
              item={item}
              category={category}
              moduleTitle={mod?.title ?? 'Module'}
              completedCount={0}
              totalCount={0}
            />
          );
        })}
      </div>
    </section>
  );
}

export default function Home() {
  const { data: me } = useChildSession();
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

  const hasAnything =
    (recs?.continue_learning?.length ?? 0) > 0 ||
    (recs?.practise_again?.length ?? 0) > 0 ||
    (recs?.something_new?.length ?? 0) > 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
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

      {/* Categorised recommendations */}
      {recsLoading ? (
        <p className="mt-5 text-sm text-gray-500">Loading recommendations…</p>
      ) : hasAnything ? (
        <>
          <CategorySection category="continue_learning" items={recs?.continue_learning ?? []} modules={modules} />
          <CategorySection category="practise_again" items={recs?.practise_again ?? []} modules={modules} />
          <CategorySection category="something_new" items={recs?.something_new ?? []} modules={modules} />
        </>
      ) : (
        <section className="mt-5 rounded-2xl border-2 border-amber-200 bg-white p-4">
          <p className="text-sm text-center text-gray-500">
            Complete a lesson to get personalised recommendations!
          </p>
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
