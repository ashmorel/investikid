import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations } from '@/api/ai';
import { Button } from '@/components/ui/button';
import HomeHero from '@/components/child/HomeHero';
import { StatsCard } from '@/components/child/StatsCard';
import { QuickLinksRow } from '@/components/child/home/QuickLinksRow';
import { PremiumUpsellCard } from '@/components/child/PremiumUpsellCard';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { authApi, type Me } from '@/api/auth';
import { trackOncePerSession } from '@/lib/analytics';

export default function Home() {
  useEffect(() => trackOncePerSession('home_view'), []);
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const { data: portfolio } = usePortfolio();
  const { data: me } = useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    retry: false,
    staleTime: 60_000,
  });

  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;

  // Earned subset out of all badge definitions; hidden until both are loaded
  // and definitions exist.
  const badgesTotal = allBadges.data && allBadges.data.length > 0 ? allBadges.data.length : null;
  const badgesEarned = earnedBadges.data ? earnedBadges.data.length : null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">Your learning home</h1>
      <HomeHero />

      <div className="mt-4">
        <StatsCard
          xp={xp}
          level={level}
          streakCount={progress?.streak_count ?? 0}
          streakFreezes={progress?.streak_freezes ?? 0}
          lastActivityDate={progress?.last_activity_date ?? null}
          dailyGoalXp={progress?.daily_goal_xp ?? 30}
          xpToday={progress?.xp_today ?? 0}
        />
      </div>

      <div className="mt-4">
        <QuickLinksRow
          portfolioValue={portfolio?.total_value ?? null}
          currencyCode={portfolio?.currency_code ?? 'USD'}
          reviewDue={recs?.review_summary.due_count ?? 0}
          badgesEarned={badgesEarned}
          badgesTotal={badgesTotal}
        />
      </div>

      <div className="mt-4">
        <PremiumUpsellCard isPremium={me?.is_premium ?? false} />
      </div>

      <div className="mt-5">
        <Button asChild className="bg-brand-gradient hover:brightness-110 text-white font-bold rounded-xl">
          <Link to="/lessons">Browse all modules →</Link>
        </Button>
      </div>
    </div>
  );
}
