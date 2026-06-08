import { useProgress } from '@/hooks/useProgress';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import { useChildSession } from '@/hooks/useChildSession';
import { XpSummary } from '@/components/child/stats/XpSummary';
import { BadgeGrid } from '@/components/child/stats/BadgeGrid';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import { LeaderboardTable } from '@/components/child/stats/LeaderboardTable';
import { useGroupLeaderboard } from '@/hooks/useGroupLeaderboard';
import { GroupLeaderboard } from '@/components/child/stats/GroupLeaderboard';

function SectionSkeleton() {
  return <div className="h-32 animate-pulse rounded-2xl bg-muted" />;
}

export default function Stats() {
  const progress = useProgress();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const challenges = useChallenges();
  const leaderboard = useLeaderboard();
  const session = useChildSession();
  const groupBoards = useGroupLeaderboard();

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-4 sm:space-y-8 sm:py-6">
      <h1 className="text-2xl font-bold">Your Stats</h1>

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
        <p className="text-xs text-muted-foreground">🛡️ A streak freeze saves your streak if you miss a day. Earn one every 7-day streak (up to 2).</p>
      ) : null}

      {/* Badges */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Badges</h2>
        {allBadges.isLoading || earnedBadges.isLoading ? (
          <SectionSkeleton />
        ) : allBadges.data && earnedBadges.data ? (
          <BadgeGrid allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
        ) : null}
      </section>

      {/* Weekly Challenges */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Weekly Challenges</h2>
        {challenges.isLoading ? (
          <SectionSkeleton />
        ) : challenges.data ? (
          <ChallengeList challenges={challenges.data} isPremium={session.data?.is_premium ?? false} />
        ) : null}
      </section>

      <section className="mt-5" aria-label="Your groups">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Your groups</h2>
        <GroupLeaderboard boards={groupBoards.data ?? []} />
      </section>

      {/* Weekly Leaderboard */}
      <section className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm sm:p-5">
        <h2 className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">Weekly Leaderboard</h2>
        {leaderboard.isLoading ? (
          <SectionSkeleton />
        ) : leaderboard.data ? (
          <LeaderboardTable
            entries={leaderboard.data}
            currentUsername={session.data?.username ?? ''}
          />
        ) : null}
      </section>
    </div>
  );
}
