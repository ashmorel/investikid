import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations } from '@/api/ai';
import HomeHero from '@/components/child/HomeHero';
import { MarketChip } from '@/components/child/MarketChip';
import { ComingSoonMarket } from '@/components/child/ComingSoonMarket';
import { useMarkets, useMarketProgress } from '@/hooks/useMarkets';
import { StatsCard } from '@/components/child/StatsCard';
import StreakReminderNudge from '@/components/child/StreakReminderNudge';
import { QuickLinksRow } from '@/components/child/home/QuickLinksRow';
import { ReviseCard } from '@/components/child/home/ReviseCard';
import { PremiumUpsellCard } from '@/components/child/PremiumUpsellCard';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { authApi, type Me } from '@/api/auth';
import { trackOncePerSession } from '@/lib/analytics';
import { EventStrip } from '@/components/child/home/EventStrip';
import ArcadeHomeCard from '@/components/child/home/ArcadeHomeCard';
import ArcadeDailyCard from '@/components/child/home/ArcadeDailyCard';
import FeaturedDropCard from '@/components/child/home/FeaturedDropCard';

export default function Home() {
  const { t } = useTranslation('home');
  const { t: tMarkets } = useTranslation('markets');
  const { open: openPaywall } = usePremiumPaywall();
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
  // A free user may only progress in their started market; the backend marks
  // every other market `locked`. When the active market is locked, surface a
  // Premium-unlock panel above the lesson content (the completion endpoint also
  // hard-gates with a 403). GB default users are never locked, so this is inert
  // for them.
  const marketLocked = activeMarket != null && activeMarket.locked;

  // Additive per-market indicator: the active market's XP, alongside (not
  // replacing) the global level/streak/coins shown in StatsCard.
  const activeMarketCode = activeMarket?.code ?? me?.active_market_code ?? 'GB';
  const activeMarketXp =
    marketProgress?.markets?.find((m) => m.market_code === activeMarketCode)?.xp ?? 0;

  // Earned subset out of all badge definitions; hidden until both are loaded
  // and definitions exist.
  const badgesTotal = allBadges.data && allBadges.data.length > 0 ? allBadges.data.length : null;
  const badgesEarned = earnedBadges.data ? earnedBadges.data.length : null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">{t('pageTitle')}</h1>
      <EventStrip />
      <div className="mb-2 flex items-center justify-end gap-2">
        <MarketChip
          activeCode={me?.active_market_code ?? 'GB'}
          xp={activeMarket != null ? activeMarketXp : null}
        />
      </div>
      {!marketComingSoon && <HomeHero />}

      <div className="mt-3">
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

      <StreakReminderNudge />

      {marketComingSoon ? (
        <div className="mt-4">
          <ComingSoonMarket marketName={activeMarket!.name} />
        </div>
      ) : (
        <>
          {marketLocked && (
            <div className="mt-4 rounded-2xl border border-brand-200 bg-brand-50 p-4">
              <h2 className="text-base font-extrabold text-brand-800">{tMarkets('unlock.title')}</h2>
              <p className="mt-1 text-sm text-brand-700">{tMarkets('unlock.body')}</p>
              <button
                type="button"
                onClick={() => openPaywall({ kind: 'home', label: activeMarket!.name })}
                className="mt-3 min-h-[44px] rounded-xl bg-brand-gradient px-4 py-2 text-sm font-bold text-white hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
              >
                {tMarkets('unlock.cta')}
              </button>
            </div>
          )}

          {/* Keep learning — the two learning actions, grouped */}
          <h2 className="mb-1 mt-5 text-xs font-bold uppercase tracking-wider text-gray-500">
            {t('zones.keepLearning')}
          </h2>
          <ReviseCard />
          <Link
            to="/lessons"
            className="mt-3 flex min-h-[44px] items-center gap-2 rounded-2xl border border-line bg-card p-4 text-base font-extrabold text-ink shadow-sm transition-colors hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            <span aria-hidden="true">📚</span>
            <span className="flex-1">{t('browseAll')}</span>
            <span aria-hidden="true" className="text-brand-400">→</span>
          </Link>

          {/* Play — the limited drop + the two games, grouped */}
          <h2 className="mb-1 mt-6 text-xs font-bold uppercase tracking-wider text-gray-500">
            {t('zones.play')}
          </h2>
          <FeaturedDropCard />
          <div className="mt-3 grid grid-cols-2 gap-3">
            <ArcadeDailyCard />
            <ArcadeHomeCard />
          </div>

          {/* Shortcuts */}
          <div className="mt-6">
            <QuickLinksRow
              portfolioValue={portfolio?.total_value ?? null}
              currencyCode={portfolio?.currency_code ?? 'USD'}
              reviewDue={recs?.review_summary.due_count ?? 0}
              badgesEarned={badgesEarned}
              badgesTotal={badgesTotal}
              coins={progress?.virtual_coins ?? 0}
            />
          </div>

          <div className="mt-5">
            <PremiumUpsellCard isPremium={me?.is_premium ?? false} />
          </div>
        </>
      )}
    </div>
  );
}
