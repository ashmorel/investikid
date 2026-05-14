import { describe, it, expect, vi, beforeEach } from 'vitest';
import { simulatorApi } from '@/api/simulator';

beforeEach(() => vi.restoreAllMocks());

function mockFetch(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
}

describe('simulatorApi', () => {
  it('searchMarket calls GET /market/search?q=AAPL', async () => {
    const spy = mockFetch([{ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' }]);
    const result = await simulatorApi.searchMarket('AAPL');
    expect(spy).toHaveBeenCalledWith('/market/search?q=AAPL', expect.objectContaining({ method: 'GET' }));
    expect(result).toEqual([{ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' }]);
  });

  it('getQuote calls GET /market/quote/NASDAQ/AAPL', async () => {
    const spy = mockFetch({ ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' });
    await simulatorApi.getQuote('NASDAQ', 'AAPL');
    expect(spy).toHaveBeenCalledWith('/market/quote/NASDAQ/AAPL', expect.objectContaining({ method: 'GET' }));
  });

  it('getPortfolio calls GET /portfolio', async () => {
    const spy = mockFetch({ id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] });
    await simulatorApi.getPortfolio();
    expect(spy).toHaveBeenCalledWith('/portfolio', expect.objectContaining({ method: 'GET' }));
  });

  it('listTrades calls GET /portfolio/trades', async () => {
    const spy = mockFetch([]);
    await simulatorApi.listTrades();
    expect(spy).toHaveBeenCalledWith('/portfolio/trades', expect.objectContaining({ method: 'GET' }));
  });

  it('placeTrade calls POST /portfolio/trades with body', async () => {
    const spy = mockFetch({ id: 't1', ticker: 'AAPL', type: 'buy', shares: '2', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }, 201);
    await simulatorApi.placeTrade({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 2 });
    expect(spy).toHaveBeenCalledWith('/portfolio/trades', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 2 }),
    }));
  });
});
