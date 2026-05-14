import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type BadgeDefinition } from '@/api/gamification';

export function useAllBadges() {
  return useQuery<BadgeDefinition[] | null>({
    queryKey: ['badges-all'],
    queryFn: () => gamificationApi.getAllBadges(),
    retry: false,
    staleTime: Infinity,
  });
}
