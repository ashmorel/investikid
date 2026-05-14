import { useQuery } from '@tanstack/react-query';
import { gamificationApi, type ChallengeOut } from '@/api/gamification';

export function useChallenges() {
  return useQuery<ChallengeOut[] | null>({
    queryKey: ['challenges'],
    queryFn: () => gamificationApi.getChallenges(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
