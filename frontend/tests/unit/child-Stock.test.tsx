import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Stock from '@/pages/child/Stock';

beforeEach(() => vi.restoreAllMocks());

function mockFetchRoutes(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    // Sort by longest path first to avoid prefix-matching issues
    const sorted = Object.entries(routeMap).sort((a, b) => b[0].length - a[0].length);
    for (const [path, body] of sorted) {
      if (url.startsWith(path)) {
        const status = path === '/portfolio/trades' && init?.method === 'POST' ? 201 : 200;
        return new Response(JSON.stringify(body), { status });
      }
    }
    return new Response('not mocked', { status: 500 });
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/simulator/stock/NASDAQ/AAPL']}>
        <Routes>
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
          <Route path="/simulator" element={<div>portfolio page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Stock page', () => {
  it('renders stock header and trade form', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getAllByText(/\$185\.42 USD/).length).toBeGreaterThan(0);
      expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
    });
  });

  it('shows Back to market link', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /back to market/i })).toHaveAttribute('href', '/simulator/market');
    });
  });

  it('shows existing holding info from portfolio', async () => {
    mockFetchRoutes({
      '/market/quote/NASDAQ/AAPL': { ticker: 'AAPL', exchange: 'NASDAQ', name: 'Apple Inc.', price: '185.42', currency: 'USD' },
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings: [{ ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' }],
      },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/You own 5 shares/)).toBeInTheDocument();
    });
  });

  it('shows 404 state for unknown ticker', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.startsWith('/market/quote')) return new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 });
      if (url.startsWith('/portfolio')) return new Response(JSON.stringify({ id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] }), { status: 200 });
      return new Response('', { status: 500 });
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/stock not found/i)).toBeInTheDocument();
    });
  });
});
