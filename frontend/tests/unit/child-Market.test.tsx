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

function makeFetchMock(filterFn?: (q: string) => QuoteOut[]) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.includes('/market/search')) {
      const qParam = new URL(url, 'http://localhost').searchParams.get('q') ?? '';
      const results = filterFn ? filterFn(qParam) : allQuotes;
      return new Response(JSON.stringify(results), { status: 200 });
    }
    // Other API calls (market movers, news, tips, etc.) return empty/null gracefully
    return new Response(JSON.stringify(null), { status: 200 });
  });
}

function renderPage(filterFn?: (q: string) => QuoteOut[]) {
  makeFetchMock(filterFn);
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
    renderPage((q) => q ? allQuotes.filter((s) => s.name.toLowerCase().includes(q.toLowerCase())) : allQuotes);
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'vod');
    await waitFor(() => {
      expect(screen.queryByText('Apple Inc.')).not.toBeInTheDocument();
      expect(screen.getByText('Vodafone Group')).toBeInTheDocument();
    });
  });

  it('shows no-matches message when filter yields nothing', async () => {
    renderPage((q) => q ? allQuotes.filter((s) => s.name.toLowerCase().includes(q.toLowerCase())) : allQuotes);
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'xyz');
    await waitFor(() => expect(screen.getByText(/no stocks found/i)).toBeInTheDocument());
  });

  it('each stock card links to stock detail page', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Apple Inc.')).toBeInTheDocument());
    const aaplLink = screen.getByText('Apple Inc.').closest('a');
    expect(aaplLink).toHaveAttribute('href', '/simulator/stock/NASDAQ/AAPL');
  });

  it('shows the region selector (replacing the old Exchange tooltip)', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole('radiogroup', { name: /market region/i })).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /info about Exchange/i })).not.toBeInTheDocument();
  });
});
