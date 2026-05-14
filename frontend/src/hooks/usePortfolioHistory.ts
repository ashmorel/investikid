import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type PortfolioSnapshot } from '@/api/simulator';

export function usePortfolioHistory() {
  return useQuery<PortfolioSnapshot[] | null>({
    queryKey: ['portfolio-history'],
    queryFn: () => simulatorApi.getPortfolioHistory(),
    retry: false,
    staleTime: 60_000,
  });
}
