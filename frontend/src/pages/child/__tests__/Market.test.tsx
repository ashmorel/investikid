import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { simulatorApi } from '@/api/simulator';
import Market from '../Market';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    searchMarket: vi.fn(),
    getMarketMovers: vi.fn(() => Promise.resolve([])),
    getMarketNews: vi.fn(() => Promise.resolve([])),
    getNewsSummary: vi.fn(() => Promise.resolve(null)),
    getInvestingTips: vi.fn(() => Promise.resolve([])),
    getStockHistory: vi.fn(() => Promise.resolve(null)),
  },
}));

vi.mock('@/api/auth', () => ({
  authApi: { me: vi.fn(() => Promise.resolve(null)) },
}));

// The non-search child widgets only render when not searching; stub them out.
vi.mock('@/components/child/simulator/MarketMovers', () => ({ MarketMovers: () => null }));
vi.mock('@/components/child/simulator/MarketNews', () => ({ MarketNews: () => null }));
vi.mock('@/components/child/simulator/InvestingTips', () => ({ InvestingTips: () => null }));

const QUOTE = { ticker: 'NVDA', exchange: 'NASDAQ', name: 'NVIDIA Corp.', price: '525.40', currency: 'USD' };

function renderWithProviders(route: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <Market />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Market search loading vs empty', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows a loading indicator (not "No stocks found") while a search is in flight', async () => {
    let resolveSearch: (v: typeof QUOTE[]) => void = () => {};
    vi.mocked(simulatorApi.searchMarket).mockImplementation((q: string) =>
      q === '' ? Promise.resolve([]) : new Promise<typeof QUOTE[]>((res) => { resolveSearch = res; }));
    renderWithProviders('/simulator/market');
    await userEvent.type(await screen.findByRole('searchbox', { name: /search stocks/i }), 'NVDA');
    expect(await screen.findByText(/searching/i, {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.queryByText(/no stocks found/i)).not.toBeInTheDocument();
    resolveSearch([QUOTE]);
    expect(await screen.findByText(/NVIDIA Corp\./)).toBeInTheDocument();
  });

  it('shows "No stocks found" only after a search settles empty', async () => {
    vi.mocked(simulatorApi.searchMarket).mockImplementation(() => Promise.resolve([]));
    renderWithProviders('/simulator/market');
    await userEvent.type(await screen.findByRole('searchbox', { name: /search stocks/i }), 'ZZZZ');
    expect(await screen.findByText(/no stocks found/i, {}, { timeout: 2000 })).toBeInTheDocument();
  });

  it('has no axe violations in the loading state', async () => {
    vi.mocked(simulatorApi.searchMarket).mockImplementation((q: string) =>
      q === '' ? Promise.resolve([]) : new Promise(() => {}));
    const { container } = renderWithProviders('/simulator/market');
    await userEvent.type(await screen.findByRole('searchbox', { name: /search stocks/i }), 'NVDA');
    await screen.findByText(/searching/i, {}, { timeout: 2000 });
    expect(await axe(container)).toHaveNoViolations();
  });
});
