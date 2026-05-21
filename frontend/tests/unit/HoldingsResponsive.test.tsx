import { screen } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { renderMobile, renderDesktop } from '../helpers/responsive';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';

const MOCK_HOLDINGS = [
  {
    ticker: 'AAPL',
    exchange: 'NASDAQ',
    shares: '5',
    avg_buy_price: '168.20',
    current_price: '210.50',
    market_value: '1052.50',
    unrealized_pl: '42.30',
  },
  {
    ticker: 'MSFT',
    exchange: 'NASDAQ',
    shares: '3',
    avg_buy_price: '425.10',
    current_price: '419.10',
    market_value: '1257.30',
    unrealized_pl: '-18.60',
  },
];

describe('HoldingsTable responsive', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders cards on mobile', () => {
    renderMobile(
      <MemoryRouter>
        <HoldingsTable holdings={MOCK_HOLDINGS} />
      </MemoryRouter>,
    );
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('renders table on desktop', () => {
    renderDesktop(
      <MemoryRouter>
        <HoldingsTable holdings={MOCK_HOLDINGS} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
  });
});
