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

  getMarketMovers: () =>
    apiFetch<Record<string, ExchangeMovers>>('/market/movers'),

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
};
