import { apiFetch } from './client';

export type MarketSummary = {
  code: string;
  name: string;
  currency_code: string;
  has_content: boolean;
  enrolled: boolean;
  is_selected: boolean;
};

export type MarketProgress = {
  markets: { market_code: string; xp: number }[];
  total_xp: number;
  level: number;
};

export const marketApi = {
  list: () => apiFetch<MarketSummary[]>('/markets'),
  progress: () => apiFetch<MarketProgress>('/me/markets'),
  switch: (market_code: string) =>
    apiFetch<{ active_market_code: string }>('/me/active-market', {
      method: 'POST',
      body: JSON.stringify({ market_code }),
    }),
};
