import { useQuery } from '@tanstack/react-query';
import { authApi, type Me } from '@/api/auth';

export function useChildSession() {
  return useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    retry: false,
    staleTime: 5 * 60_000,
  });
}
