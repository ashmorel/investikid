import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type LeaderboardRow, type LeaderboardScope, type LeaderboardMetric } from '@/api/gamification';

export function useLeaderboard(scope: LeaderboardScope, metric: LeaderboardMetric) {
  return useQuery<LeaderboardRow[] | null>({
    queryKey: ['leaderboard', scope, metric],
    queryFn: () => gamificationApi.getLeaderboard(scope, metric),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
