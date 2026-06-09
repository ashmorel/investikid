import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useProgress } from '@/hooks/useProgress';
import { contentApi, type ModuleOut } from '@/api/content';
import { useRecommendations } from '@/api/ai';
import { StatsBar } from '@/components/child/StatsBar';
import { ReviewBanner } from '@/components/child/ReviewBanner';
import { Button } from '@/components/ui/button';
import HomeHero from '@/components/child/HomeHero';
import { ModuleTile } from '@/components/child/ui/ModuleTile';
import { LevelProgressCard } from '@/components/child/LevelProgressCard';
import { PremiumUpsellCard } from '@/components/child/PremiumUpsellCard';
import { PortfolioSnapshotCard } from '@/components/child/home/PortfolioSnapshotCard';
import { AchievementsStrip } from '@/components/child/AchievementsStrip';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useNextLesson } from '@/hooks/useNextLesson';
import { orderModulesForTier } from '@/lib/tierModuleOrder';
import { useAgeTier } from '@/lib/ageTier';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { authApi, type Me } from '@/api/auth';

const TOPIC_STYLE: Record<string, { accent: string; tint: string }> = {
  savings: { accent: '#0ea5e9', tint: '#e0f2fe' },
  budgeting: { accent: '#10b981', tint: '#d1fae5' },
  stocks: { accent: '#6366f1', tint: '#e0e7ff' },
  risk: { accent: '#8b5cf6', tint: '#ede9fe' },
  crypto: { accent: '#4f46e5', tint: '#e0e7ff' },
  taxes: { accent: '#f43f5e', tint: '#ffe4e6' },
  debt: { accent: '#14b8a6', tint: '#d7f5f1' },
  entrepreneurship: { accent: '#f59e0b', tint: '#fef3c7' },
  real_estate: { accent: '#eab308', tint: '#fef9c3' },
};
const styleFor = (t: string) => TOPIC_STYLE[t] ?? { accent: '#0ea5e9', tint: '#e0f2fe' };

export default function Home() {
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const next = useNextLesson();
  const { data: portfolio } = usePortfolio();
  const { open: openPaywall } = usePremiumPaywall();
  const { data: me } = useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    retry: false,
    staleTime: 60_000,
  });

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const tier = useAgeTier();
  const modules = orderModulesForTier(modulesQ.data ?? [], tier);
  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;

  const recommendedModuleId = next.moduleId;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">Your learning home</h1>
      <HomeHero />

      <div className="mt-4">
        <StatsBar
          xp={xp}
          level={level}
          streakCount={progress?.streak_count ?? 0}
          streakFreezes={progress?.streak_freezes ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
        />
      </div>

      <div className="mt-4">
        <LevelProgressCard level={level} xp={xp} />
      </div>

      <div className="mt-4">
        <PremiumUpsellCard isPremium={me?.is_premium ?? false} />
      </div>

      {portfolio?.total_value && (
        <div className="mt-4">
          <PortfolioSnapshotCard
            totalValue={portfolio.total_value}
            currencyCode={portfolio.currency_code}
            changePct={null}
          />
        </div>
      )}

      {/* Review nudge banner */}
      {recs && recs.review_summary.due_count > 0 && (
        <div className="mt-5">
          <ReviewBanner dueCount={recs.review_summary.due_count} />
        </div>
      )}

      {allBadges.data && earnedBadges.data && (
        <div className="mt-5">
          <AchievementsStrip allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
        </div>
      )}

      {/* Your modules grid */}
      {modules.length > 0 && (
        <section className="mt-5" aria-label="Your modules">
          <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Your modules</h2>
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
                  onLockedClick={() => openPaywall({ kind: 'module', label: m.title })}
                />
              );
            })}
          </div>
        </section>
      )}

      <div className="mt-5">
        <Button asChild className="bg-brand-gradient hover:brightness-110 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}
