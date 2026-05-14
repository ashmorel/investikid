import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type PortfolioOut } from '@/api/simulator';

export function usePortfolio() {
  return useQuery<PortfolioOut | null>({
    queryKey: ['portfolio'],
    queryFn: () => simulatorApi.getPortfolio(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
