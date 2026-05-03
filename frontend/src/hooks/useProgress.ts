import { useQuery } from '@tanstack/react-query';
import { contentApi, type Progress } from '@/api/content';

export function useProgress() {
  return useQuery<Progress | null>({
    queryKey: ['progress'],
    queryFn: () => contentApi.getProgress(),
    retry: false,
    staleTime: 60_000,
  });
}
