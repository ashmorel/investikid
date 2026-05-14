import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type TradeOut } from '@/api/simulator';

export function useTrades() {
  return useQuery<TradeOut[] | null>({
    queryKey: ['trades'],
    queryFn: () => simulatorApi.listTrades(),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
