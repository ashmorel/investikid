import { useQuery } from '@tanstack/react-query';
import { groupsApi, type GroupLeaderboard } from '@/api/groups';

export function useGroupLeaderboard() {
  return useQuery<GroupLeaderboard[] | null>({
    queryKey: ['group-leaderboard'],
    queryFn: () => groupsApi.myLeaderboards(),
    retry: false,
    staleTime: 60_000,
  });
}
