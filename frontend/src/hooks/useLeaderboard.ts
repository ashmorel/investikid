import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type LeaderboardEntry } from '@/api/gamification';

export function useLeaderboard() {
  return useQuery<LeaderboardEntry[] | null>({
    queryKey: ['leaderboard'],
    queryFn: () => gamificationApi.getLeaderboard(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
