import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useChildSession } from '@/hooks/useChildSession';
import { XpSummary } from '@/components/child/stats/XpSummary';
import { BadgeGrid } from '@/components/child/stats/BadgeGrid';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import { LeaderboardCard } from '@/components/child/stats/LeaderboardCard';
import { useGroupLeaderboard } from '@/hooks/useGroupLeaderboard';
import { GroupLeaderboard } from '@/components/child/stats/GroupLeaderboard';
import { GroupGoals } from '@/components/child/stats/GroupGoals';
import { MarketXpBreakdown } from '@/components/child/MarketXpBreakdown';

function SectionSkeleton() {
  return <div className="h-32 animate-pulse rounded-2xl bg-muted" />;
}

export default function Stats() {
  const { t } = useTranslation('child');
  const progress = useProgress();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const challenges = useChallenges();
  const session = useChildSession();
  const groupBoards = useGroupLeaderboard();

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-4 sm:space-y-8 sm:py-6">
      <h1 className="text-2xl font-bold">{t('stats.pageTitle')}</h1>

      {/* XP Summary */}
      {progress.isLoading ? (
        <SectionSkeleton />
      ) : progress.data ? (
        <XpSummary
          xp={progress.data.xp}
          streakCount={progress.data.streak_count}
          lastActivityDate={progress.data.last_activity_date}
        />
      ) : null}

      {!progress.isLoading && progress.data ? (
        <p className="text-xs text-muted-foreground">{t('stats.streakFreeze')}</p>
      ) : null}

      {/* Per-market XP breakdown */}
      <MarketXpBreakdown />

      {/* Badges */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">{t('stats.badgesSection')}</h2>
        {allBadges.isLoading || earnedBadges.isLoading ? (
          <SectionSkeleton />
        ) : allBadges.data && earnedBadges.data ? (
          <BadgeGrid allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
        ) : null}
      </section>

      {/* Weekly Challenges */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">{t('stats.challengesSection')}</h2>
        {challenges.isLoading ? (
          <SectionSkeleton />
        ) : challenges.data ? (
          <ChallengeList challenges={challenges.data} isPremium={session.data?.is_premium ?? false} />
        ) : null}
      </section>

      <section className="mt-5" aria-label={t('stats.groupsSection')}>
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">{t('stats.groupsSection')}</h2>
        <GroupLeaderboard boards={groupBoards.data ?? []} />
      <GroupGoals />
      </section>

      {/* Leaderboard */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <LeaderboardCard />
      </section>
    </div>
  );
}
