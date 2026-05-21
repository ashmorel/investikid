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

function SectionSkeleton() {
  return <div className="h-32 animate-pulse rounded-lg bg-muted" />;
}

export default function Stats() {
  const progress = useProgress();
  const allBadges = useAllBadges();
  const earnedBadges = useBadges();
  const challenges = useChallenges();
  const leaderboard = useLeaderboard();
  const session = useChildSession();

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

      {/* Badges */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Badges</h2>
        {allBadges.isLoading || earnedBadges.isLoading ? (
          <SectionSkeleton />
        ) : allBadges.data && earnedBadges.data ? (
          <BadgeGrid allBadges={allBadges.data} earnedBadges={earnedBadges.data} />
        ) : null}
      </section>

      {/* Weekly Challenges */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Weekly Challenges</h2>
        {challenges.isLoading ? (
          <SectionSkeleton />
        ) : challenges.data ? (
          <ChallengeList challenges={challenges.data} />
        ) : null}
      </section>

      {/* Weekly Leaderboard */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Weekly Leaderboard</h2>
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
