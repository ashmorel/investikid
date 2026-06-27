import { apiFetch } from './client';
import { type RegionCode } from '@/lib/region';

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
  holdings_value: string;
  total_unrealized_pl: string;
  holdings: HoldingOut[];
};

export type PortfolioSummaryOut = {
  id: string;
  virtual_cash: string;
  currency_code: string;
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

export type TradeReward = {
  xp_awarded: number;
  streak_extended: boolean;
  cash_granted: string;
  missions_completed: { id: string; title: string }[];
  badges_unlocked: string[];
};

export type TradeResult = TradeOut & {
  fee: string;
  commission_pct: string;
  rewards: TradeReward;
};

export type TradeConfigOut = {
  commission_pct: string;
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

export type MarketMover = {
  ticker: string;
  exchange: string;
  name: string;
  price: string;
  currency: string;
  change_percent: number;
};

export type ExchangeMovers = {
  winners: MarketMover[];
  losers: MarketMover[];
};

export interface MarketSnapshot {
  region: RegionCode;
  featured: QuoteOut[];
  movers: Record<string, ExchangeMovers>;
}

export type StockNews = {
  title: string;
  summary: string;
  publisher: string;
  url: string;
  published: string;
  thumbnail: string;
  related_ticker: string;
  related_exchange: string;
};

export type NewsSummary = {
  summary: string;
  tickers_mentioned: string[];
};

export type TimeMachinePeriod = {
  years_ago: number;
  invested: string;
  current_value: string;
  return_pct: number;
  currency: string;
  usd_equivalent: string | null;
};

export type TimeMachineData = {
  ticker: string;
  periods: TimeMachinePeriod[];
  fun_fact: string;
};

export type InvestingTip = {
  id: string;
  title: string;
  description: string;
  example_ticker: string;
  example_exchange: string;
  personalised?: boolean;
};

export type ChartCoachRequest = {
  ticker: string;
  exchange: string;
  period: string;
  message: string;
  conversation_id?: string | null;
};

export type ChartCoachResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};

export const simulatorApi = {
  searchMarket: (q: string, refresh = false) =>
    apiFetch<QuoteOut[]>(`/market/search?q=${encodeURIComponent(q)}${refresh ? '&refresh=true' : ''}`),

  getTradeConfig: () => apiFetch<TradeConfigOut>('/market/trade-config'),

  getQuote: (exchange: string, ticker: string) =>
    apiFetch<QuoteOut>(`/market/quote/${exchange}/${ticker}`),

  getPortfolio: () => apiFetch<PortfolioOut>('/portfolio'),

  setCurrency: (currency_code: string) =>
    apiFetch<PortfolioSummaryOut>('/portfolio/currency', {
      method: 'POST',
      body: JSON.stringify({ currency_code }),
    }),

  resetPortfolio: () =>
    apiFetch<PortfolioSummaryOut>('/portfolio/reset', { method: 'POST' }),

  listTrades: () => apiFetch<TradeOut[]>('/portfolio/trades'),

  placeTrade: (req: TradeRequest) =>
    apiFetch<TradeResult>('/portfolio/trades', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getPortfolioHistory: () => apiFetch<PortfolioSnapshot[]>('/portfolio/history'),

  getStockHistory: (exchange: string, ticker: string, period = '1mo') =>
    apiFetch<PricePoint[]>(`/market/history/${exchange}/${ticker}?period=${period}`),

  getMarketMovers: (region: RegionCode) =>
    apiFetch<Record<string, ExchangeMovers>>(`/market/movers?region=${region}`),

  getSnapshot: (region: RegionCode) =>
    apiFetch<MarketSnapshot>(`/market/snapshot?region=${region}`),

  getMarketNews: () =>
    apiFetch<StockNews[]>('/market/news'),

  getNewsSummary: () =>
    apiFetch<NewsSummary>('/market/news-summary'),

  getStockNews: (exchange: string, ticker: string) =>
    apiFetch<StockNews[]>(`/market/news/${exchange}/${ticker}`),

  getStockNewsSummary: (exchange: string, ticker: string) =>
    apiFetch<NewsSummary>(`/market/news-summary/${exchange}/${ticker}`),

  getChartGuide: (exchange: string, ticker: string, period = '1mo') =>
    apiFetch<NewsSummary>(`/market/chart-guide/${exchange}/${ticker}?period=${period}`),

  getTimeMachine: (exchange: string, ticker: string) =>
    apiFetch<TimeMachineData>(`/market/time-machine/${exchange}/${ticker}`),

  getInvestingTips: (refresh = false) =>
    apiFetch<InvestingTip[]>(`/market/tips${refresh ? '?refresh=true' : ''}`),

  sendChartCoachMessage: (req: ChartCoachRequest) =>
    apiFetch<ChartCoachResponse>('/market/chart-coach', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
};
