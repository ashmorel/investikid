import { useQuery } from '@tanstack/react-query';
import { type ActiveMission, missionsApi } from '@/api/missions';

export function useActiveMissions() {
  return useQuery<ActiveMission[] | null>({
    queryKey: ['active-missions'],
    queryFn: () => missionsApi.getActive(),
    retry: false,
  });
}
