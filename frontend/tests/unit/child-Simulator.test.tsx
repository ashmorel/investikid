import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Simulator from '@/pages/child/Simulator';

beforeEach(() => vi.restoreAllMocks());

function mockFetchRoutes(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    // Sort by longest path first to avoid prefix-matching issues
    const sorted = Object.entries(routeMap).sort((a, b) => b[0].length - a[0].length);
    for (const [path, body] of sorted) {
      if (url.startsWith(path)) return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response('not mocked', { status: 500 });
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Simulator />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Simulator page', () => {
  it('renders practice portfolio hero', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/practice portfolio/i)).toBeInTheDocument();
    });
  });

  it('shows empty holdings state and Available Cash card', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Available Cash/i)).toBeInTheDocument();
      expect(screen.getByText(/No stocks yet!/i)).toBeInTheDocument();
    });
  });

  it('renders holdings when present', async () => {
    mockFetchRoutes({
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings: [{ ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' }],
      },
      '/portfolio/trades': [{ id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
  });

  it('switches between Holdings and Trade History tabs', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [{ id: 't1', ticker: 'AAPL', type: 'buy', shares: '5', price: '185.42', executed_at: '2026-05-05T00:00:00Z' }],
    });
    renderPage();
    await waitFor(() => expect(screen.getByRole('tab', { name: /holdings/i })).toBeInTheDocument());

    const historyTab = screen.getByRole('tab', { name: /trade history/i });
    await userEvent.click(historyTab);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('Buy')).toBeInTheDocument();
    });
  });

  it('renders Browse stocks link to /simulator/market', async () => {
    mockFetchRoutes({
      '/portfolio': { id: 'p1', virtual_cash: '10000.00', currency_code: 'USD', total_value: '10000.00', holdings: [] },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /browse stocks/i });
      expect(link).toHaveAttribute('href', '/simulator/market');
    });
  });
});

describe('Simulator long-term signal cards', () => {
  it('renders the diversification and growth projection cards', async () => {
    mockFetchRoutes({
      '/portfolio': {
        id: 'p1', virtual_cash: '9000.00', currency_code: 'USD', total_value: '9927.10',
        holdings: [{ ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' }],
      },
      '/portfolio/trades': [],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('All eggs in one basket')).toBeInTheDocument();
      expect(screen.getByText('An illustration of compounding — not a prediction or a promise.')).toBeInTheDocument();
    });
  });
});
