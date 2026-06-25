import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useChildSession } from '@/hooks/useChildSession';
import { StatsHero } from '@/components/child/stats/StatsHero';
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

const ZONE = 'text-xs font-bold uppercase tracking-wider text-muted-foreground';
const CARD = 'rounded-2xl border border-brand-200 bg-card p-4 shadow-sm sm:p-5';
const CARD_TITLE = 'mb-3 text-sm font-bold text-ink';

export default function Stats() {
  const { t } = useTranslation('child');
  const progress = useProgress();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const challenges = useChallenges();
  const session = useChildSession();
  const groupBoards = useGroupLeaderboard();

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-4 sm:py-6">
      <h1 className="text-2xl font-extrabold text-ink">{t('stats.pageTitle')}</h1>

      {/* XP hero */}
      {progress.isLoading ? (
        <SectionSkeleton />
      ) : progress.data ? (
        <StatsHero
          xp={progress.data.xp}
          streakCount={progress.data.streak_count}
          lastActivityDate={progress.data.last_activity_date}
          badgeCount={earnedBadges.data?.length ?? 0}
          challengeCount={challenges.data?.length ?? 0}
        />
      ) : null}
      {!progress.isLoading && progress.data ? (
        <p className="-mt-3 text-xs text-muted-foreground">{t('stats.streakFreeze')}</p>
      ) : null}

      {/* Zone: Your progress (personal) */}
      <section className="space-y-3" aria-label={t('stats.zoneProgress')}>
        <h2 className={ZONE}>{t('stats.zoneProgress')}</h2>

        <MarketXpBreakdown />

        <div className={CARD}>
          <h3 className={CARD_TITLE}>{t('stats.badgesSection')}</h3>
          {allBadges.isLoading || earnedBadges.isLoading ? (
            <SectionSkeleton />
          ) : allBadges.data && earnedBadges.data ? (
            <BadgeGrid allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
          ) : null}
        </div>

        <div className={CARD}>
          <h3 className={CARD_TITLE}>{t('stats.challengesSection')}</h3>
          {challenges.isLoading ? (
            <SectionSkeleton />
          ) : challenges.data ? (
            <ChallengeList challenges={challenges.data} isPremium={session.data?.is_premium ?? false} />
          ) : null}
        </div>
      </section>

      {/* Zone: Community (social) */}
      <section className="space-y-3" aria-label={t('stats.zoneCommunity')}>
        <h2 className={ZONE}>{t('stats.zoneCommunity')}</h2>

        <div className={CARD}>
          <LeaderboardCard />
        </div>

        <div className={CARD}>
          <h3 className={CARD_TITLE}>{t('stats.groupsSection')}</h3>
          <div className="space-y-3">
            <GroupLeaderboard boards={groupBoards.data ?? []} />
            <GroupGoals />
          </div>
        </div>
      </section>
    </div>
  );
}
