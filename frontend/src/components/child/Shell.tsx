import { useRef, useCallback, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useChildSession } from '@/hooks/useChildSession';
import { useChildAuthGuard } from '@/hooks/useChildAuthGuard';
import { VerifyEmailBanner } from '@/components/VerifyEmailBanner';
import { useSwipeNav } from '@/hooks/useSwipeNav';
import { usePullToRefresh } from '@/hooks/usePullToRefresh';
import { PullToRefreshIndicator } from '@/components/mobile/PullToRefreshIndicator';
import { TopNav } from './TopNav';
import { TierBadge } from './TierBadge';
import { BottomTabBar } from './BottomTabBar';
import { SkipLink } from '@/components/a11y/SkipLink';
import { RouteErrorBoundary } from '@/components/a11y/RouteErrorBoundary';
import { useRouteFocus } from '@/components/a11y/useRouteFocus';
import { useRecommendations } from '@/api/ai';
import { PennyFAB } from './PennyFAB';
import { CoachPanel } from './CoachPanel';
import { useStreakReminder } from '@/hooks/useStreakReminder';
import { useOfflineMarketSync } from '@/hooks/useOfflineMarketSync';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';

function CoachLauncher({ dueCount, isPremium }: { dueCount: number; isPremium: boolean }) {
  const [coachOpen, setCoachOpen] = useState(false);
  const { open: openPaywall } = usePremiumPaywall();
  const { t } = useTranslation('child');
  return (
    <>
      <PennyFAB
        dueCount={dueCount}
        locked={!isPremium}
        onOpen={() =>
          isPremium
            ? setCoachOpen(true)
            : openPaywall({ kind: 'coach', label: t('coach.title') })
        }
      />
      <CoachPanel open={coachOpen} onOpenChange={setCoachOpen} />
    </>
  );
}

export function Shell() {
  const session = useChildSession();
  useChildAuthGuard(session.error);
  const location = useLocation();
  useRouteFocus();
  const { t } = useTranslation('child');
  const { data: recsData } = useRecommendations();

  const mainRef = useRef<HTMLDivElement>(null);
  const swipeRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  useSwipeNav({ ref: swipeRef });

  const handleRefresh = useCallback(async () => {
    await queryClient.refetchQueries({ type: 'active' });
  }, [queryClient]);

  const { indicatorProps } = usePullToRefresh({ ref: mainRef, onRefresh: handleRefresh });

  useStreakReminder();
  useOfflineMarketSync();

  if (session.isLoading) {
    return (
      <div className="min-h-screen bg-surface">
        <header className="h-14 border-b border-brand-200" aria-busy="true" />
        <p className="mx-auto mt-6 max-w-2xl px-4 text-sm text-muted-foreground">{t('shell.loading')}</p>
      </div>
    );
  }

  if (!session.data) {
    return null;
  }

  return (
    <PremiumPaywallProvider>
      <div ref={swipeRef} className="min-h-screen bg-surface">
        <SkipLink />
        <TopNav username={session.data.username} />
        <div className="mx-auto flex max-w-5xl items-center px-4 pt-2">
          <TierBadge premium={session.data.is_premium} />
        </div>
        <VerifyEmailBanner profile={session.data} />
        <div ref={mainRef}>
          <PullToRefreshIndicator {...indicatorProps} />
          <main
            key={location.pathname}
            id="main"
            tabIndex={-1}
            className="pb-20 md:pb-0 outline-none animate-route-in"
            style={{ paddingLeft: 'var(--safe-left)', paddingRight: 'var(--safe-right)' }}
          >
            <RouteErrorBoundary>
              <Outlet />
            </RouteErrorBoundary>
          </main>
        </div>
        <BottomTabBar />
        {location.pathname !== '/coach' && (
          <CoachLauncher
            dueCount={recsData?.review_summary?.due_count ?? 0}
            isPremium={session.data.is_premium}
          />
        )}
      </div>
    </PremiumPaywallProvider>
  );
}
