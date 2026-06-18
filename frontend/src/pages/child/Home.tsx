import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations } from '@/api/ai';
import { Button } from '@/components/ui/button';
import HomeHero from '@/components/child/HomeHero';
import { MarketChip } from '@/components/child/MarketChip';
import { ComingSoonMarket } from '@/components/child/ComingSoonMarket';
import { useMarkets, useMarketProgress } from '@/hooks/useMarkets';
import { flagFor } from '@/lib/marketFlags';
import { StatsCard } from '@/components/child/StatsCard';
import { QuickLinksRow } from '@/components/child/home/QuickLinksRow';
import { ReviseCard } from '@/components/child/home/ReviseCard';
import { PremiumUpsellCard } from '@/components/child/PremiumUpsellCard';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { authApi, type Me } from '@/api/auth';
import { trackOncePerSession } from '@/lib/analytics';
import { EventStrip } from '@/components/child/home/EventStrip';

export default function Home() {
  const { t } = useTranslation('home');
  const { t: tMarkets } = useTranslation('markets');
  useEffect(() => trackOncePerSession('home_view'), []);
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const { data: portfolio } = usePortfolio();
  const { data: markets } = useMarkets();
  const { data: marketProgress } = useMarketProgress();
  const { data: me } = useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    retry: false,
    staleTime: 60_000,
  });

  const level = progress?.level ?? 1;
  const xp = progress?.xp ?? 0;

  // The active market: backend marks it with is_selected; fall back to the
  // user's active_market_code. When it has no content yet, swap the lesson /
  // module surfaces for a friendly coming-soon panel (GB default is unaffected).
  const activeMarket =
    markets?.find((m) => m.is_selected) ??
    markets?.find((m) => m.code === (me?.active_market_code ?? 'GB'));
  const marketComingSoon = activeMarket != null && !activeMarket.has_content;

  // Additive per-market indicator: the active market's XP, alongside (not
  // replacing) the global level/streak/coins shown in StatsCard.
  const activeMarketCode = activeMarket?.code ?? me?.active_market_code ?? 'GB';
  const activeMarketXp =
    marketProgress?.markets.find((m) => m.market_code === activeMarketCode)?.xp ?? 0;

  // Earned subset out of all badge definitions; hidden until both are loaded
  // and definitions exist.
  const badgesTotal = allBadges.data && allBadges.data.length > 0 ? allBadges.data.length : null;
  const badgesEarned = earnedBadges.data ? earnedBadges.data.length : null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">{t('pageTitle')}</h1>
      <EventStrip />
      <div className="mb-2 flex items-center justify-end gap-2">
        {activeMarket != null && (
          <span
            className="inline-flex items-center gap-1.5 rounded-xl border border-brand-100 bg-card px-3 py-2 text-sm font-semibold text-brand-700"
            aria-label={`${activeMarketXp} ${tMarkets('home.marketXp', { market: activeMarket.name })}`}
          >
            <span aria-hidden="true">{flagFor(activeMarketCode)}</span>
            <span className="font-bold">{activeMarketXp}</span>
            <span aria-hidden="true" className="text-brand-400">XP</span>
          </span>
        )}
        <MarketChip activeCode={me?.active_market_code ?? 'GB'} />
      </div>
      {!marketComingSoon && <HomeHero />}

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

      {marketComingSoon ? (
        <div className="mt-4">
          <ComingSoonMarket marketName={activeMarket!.name} />
        </div>
      ) : (
        <>
          <ReviseCard />

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
              <Link to="/lessons">{t('browseAll')}</Link>
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
