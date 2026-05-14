import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type EarnedBadge } from '@/api/gamification';

export function useBadges() {
  return useQuery<EarnedBadge[] | null>({
    queryKey: ['badges-earned'],
    queryFn: () => gamificationApi.getEarnedBadges(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
