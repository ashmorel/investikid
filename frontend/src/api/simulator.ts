import { apiFetch } from './client';

export type QuoteOut = {
  ticker: string;
  exchange: string;
  name: string;
  price: string;
  currency: string;
};

export type HoldingOut = {
  ticker: string;
  exchange: string;
  shares: string;
  avg_buy_price: string;
  current_price: string;
  market_value: string;
  unrealized_pl: string;
};

export type PortfolioOut = {
  id: string;
  virtual_cash: string;
  currency_code: string;
  total_value: string;
  holdings: HoldingOut[];
};

export type TradeType = 'buy' | 'sell';

export type TradeRequest = {
  ticker: string;
  exchange: string;
  type: TradeType;
  shares: number;
};

export type TradeOut = {
  id: string;
  ticker: string;
  type: TradeType;
  shares: string;
  price: string;
  executed_at: string;
};

export type PortfolioSnapshot = {
  date: string;
  value: number;
};

export type PricePoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export const simulatorApi = {
  searchMarket: (q: string, refresh = false) =>
    apiFetch<QuoteOut[]>(`/market/search?q=${encodeURIComponent(q)}${refresh ? '&refresh=true' : ''}`),

  getQuote: (exchange: string, ticker: string) =>
    apiFetch<QuoteOut>(`/market/quote/${exchange}/${ticker}`),

  getPortfolio: () => apiFetch<PortfolioOut>('/portfolio'),

  listTrades: () => apiFetch<TradeOut[]>('/portfolio/trades'),

  placeTrade: (req: TradeRequest) =>
    apiFetch<TradeOut>('/portfolio/trades', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getPortfolioHistory: () => apiFetch<PortfolioSnapshot[]>('/portfolio/history'),

  getStockHistory: (exchange: string, ticker: string, period = '1mo') =>
    apiFetch<PricePoint[]>(`/market/history/${exchange}/${ticker}?period=${period}`),
};
