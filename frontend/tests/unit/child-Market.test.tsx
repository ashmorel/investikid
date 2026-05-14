import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Market from '@/pages/child/Market';
import type { QuoteOut } from '@/api/simulator';

beforeEach(() => vi.restoreAllMocks());

const allQuotes: QuoteOut[] = [
  { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
  { ticker: 'MSFT', exchange: 'NASDAQ', name: 'Microsoft Corp.', price: '420.10', currency: 'USD' },
  { ticker: 'VOD', exchange: 'LSE', name: 'Vodafone Group', price: '12.34', currency: 'GBP' },
  { ticker: '0700', exchange: 'HKEX', name: 'Tencent Holdings', price: '350.00', currency: 'HKD' },
];

function renderPage() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(allQuotes), { status: 200 }),
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Market />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Market page', () => {
  it('renders all stocks grouped by exchange', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
      expect(screen.getByText('Tencent Holdings')).toBeInTheDocument();
    });
    expect(screen.getByText(/US Stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/UK Stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/Hong Kong Stocks/i)).toBeInTheDocument();
  });

  it('filters stocks client-side as user types', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'vod');
    expect(screen.queryByText('Apple Inc.')).not.toBeInTheDocument();
    expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
  });

  it('shows no-matches message when filter yields nothing', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'xyz');
    expect(screen.getByText(/no stocks match/i)).toBeInTheDocument();
  });

  it('each stock card links to stock detail page', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const aaplLink = screen.getByText('Apple Inc.').closest('a');
    expect(aaplLink).toHaveAttribute('href', '/simulator/stock/NASDAQ/AAPL');
  });

  it('includes EduTooltip for Exchange', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole('button', { name: /info about Exchange/i })).toBeInTheDocument());
  });
});
