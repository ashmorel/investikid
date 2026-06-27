import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { marketApi, type MarketProgress, type MarketSummary } from '../api/market';
import type { Me } from '../api/auth';
import { scopeFromMe } from '../lib/offline/scope';
import { clearForChild } from '../lib/offline/contentStore';

// Switching the active market changes which content + progress the backend
// serves, so every market-scoped query must be re-fetched. These are the REAL
// query keys used across the child content/Revise surfaces (see src/pages/child
// and src/hooks). Keep this in sync if a content query key changes.
const CONTENT_KEYS: string[][] = [
  ['me'], ['markets'], ['me', 'markets'],
  ['modules'], ['module'], ['module-levels'], ['level-lessons'],
  ['recommendations'], ['next-lesson'], ['progress'],
  ['revise-modules'],
];

export function useMarkets() {
  return useQuery<MarketSummary[] | null>({ queryKey: ['markets'], queryFn: () => marketApi.list(), staleTime: 5 * 60_000 });
}

export function useMarketProgress() {
  return useQuery<MarketProgress | null>({ queryKey: ['me', 'markets'], queryFn: () => marketApi.progress(), staleTime: 60_000 });
}

export function useSwitchMarket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (market_code: string) => marketApi.switch(market_code),
    onSuccess: async () => {
      const prevScope = scopeFromMe(qc.getQueryData<Me>(['me']));
      if (prevScope) await clearForChild(prevScope); // no-op on web
      for (const key of CONTENT_KEYS) qc.invalidateQueries({ queryKey: key });
    },
  });
}
