import { describe, it, expect } from 'vitest';
import { groupByExchange } from './Market';

const quote = (exchange: string, ticker: string) =>
  ({ exchange, ticker, name: ticker, price: '1', currency: 'USD', change: 0, change_pct: 0 } as never);

describe('groupByExchange region prioritisation', () => {
  it('puts the region exchanges first, then the rest alphabetically', () => {
    const stocks = [quote('NASDAQ', 'AAPL'), quote('LSE', 'VOD'), quote('HKEX', '0700')];
    const order = groupByExchange(stocks, ['HKEX']).map(([ex]) => ex);
    expect(order[0]).toBe('HKEX');
    expect(order.slice(1)).toEqual(['LSE', 'NASDAQ']);
  });

  it('falls back to alphabetical when no priority given', () => {
    const stocks = [quote('NASDAQ', 'AAPL'), quote('LSE', 'VOD')];
    const order = groupByExchange(stocks, []).map(([ex]) => ex);
    expect(order).toEqual(['LSE', 'NASDAQ']);
  });
});
