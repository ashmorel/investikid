import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

import Simulator from '@/pages/child/Simulator';
import { TradeForm } from '@/components/child/simulator/TradeForm';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { MarketSearchBar } from '@/components/child/simulator/MarketSearchBar';
import { MarketNews } from '@/components/child/simulator/MarketNews';
import { StockNewsSection } from '@/components/child/simulator/StockNews';
import type { HoldingOut } from '@/api/simulator';

function wrap(ui: React.ReactNode, initial = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="*" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetchRoutes(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    const sorted = Object.entries(routeMap).sort((a, b) => b[0].length - a[0].length);
    for (const [path, body] of sorted) {
      if (url.startsWith(path)) return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
}

beforeEach(() => vi.restoreAllMocks());

const holdings: HoldingOut[] = [
  { ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' },
  { ticker: 'VOD', exchange: 'LSE', shares: '10', avg_buy_price: '13.00', current_price: '12.34', market_value: '123.40', unrealized_pl: '-6.60' },
];

describe('a11y: simulator surfaces', () => {
  it('Simulator page has no axe violations', async () => {
    mockFetchRoutes({
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings,
      },
      '/portfolio/trades': [],
    });
    const { container } = wrap(<Simulator />, '/simulator');
    await waitFor(() => expect(screen.getByText(/practice portfolio/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('TradeForm has no axe violations', async () => {
    const { container } = wrap(
      <TradeForm
        ticker="AAPL" exchange="NASDAQ" price="185.42" currency="USD"
        availableCash="10000.00" ownedShares="0"
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        isSubmitting={false} submitError={null}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('HoldingsTable has no axe violations', async () => {
    const { container } = wrap(<HoldingsTable holdings={holdings} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('HoldingsTable empty has no axe violations', async () => {
    const { container } = wrap(<HoldingsTable holdings={[]} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('MarketSearchBar has no axe violations', async () => {
    const { container } = wrap(<MarketSearchBar value="" onChange={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('MarketNews has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 'n1', title: 'Headline', url: 'https://example.com/n1', source: 'Reuters', published_at: '2026-05-01T00:00:00Z', summary: 'Body' },
        ]),
        { status: 200 },
      ) as never,
    );
    const { container } = wrap(<MarketNews />);
    await waitFor(() => expect(screen.queryByText(/Headline/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('StockNews has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 'n1', title: 'Apple headline', url: 'https://example.com/n1', source: 'Reuters', published_at: '2026-05-01T00:00:00Z', summary: 'Body' },
        ]),
        { status: 200 },
      ) as never,
    );
    const { container } = wrap(<StockNewsSection ticker="AAPL" exchange="NASDAQ" />);
    await waitFor(() => expect(screen.queryByText(/Apple headline/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
