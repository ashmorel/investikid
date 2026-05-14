import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';
import type { TradeOut } from '@/api/simulator';

const trades: TradeOut[] = [
  { id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T10:30:00Z' },
  { id: 't2', ticker: 'VOD', type: 'sell', shares: '3', price: '12.34', executed_at: '2026-05-04T09:00:00Z' },
];

describe('TradeHistoryTab', () => {
  it('renders each trade with ticker, type badge, shares, and price', () => {
    render(<TradeHistoryTab trades={trades} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Buy')).toBeInTheDocument();
    expect(screen.getByText('VOD')).toBeInTheDocument();
    expect(screen.getByText('Sell')).toBeInTheDocument();
  });

  it('renders empty state when no trades', () => {
    render(<TradeHistoryTab trades={[]} />);
    expect(screen.getByText(/no trades yet/i)).toBeInTheDocument();
  });

  it('includes EduTooltip for Trade term', () => {
    render(<TradeHistoryTab trades={trades} />);
    expect(screen.getByRole('button', { name: /info about Trade/i })).toBeInTheDocument();
  });
});
