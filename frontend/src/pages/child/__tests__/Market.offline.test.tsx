import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOnline } from '@/hooks/useOnline';
import Market from '../Market';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn(() => true) }));

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    searchMarket: vi.fn(() => Promise.resolve([])),
    getMarketMovers: vi.fn(() => Promise.resolve([])),
    getMarketNews: vi.fn(() => Promise.resolve([])),
    getNewsSummary: vi.fn(() => Promise.resolve(null)),
    getInvestingTips: vi.fn(() => Promise.resolve([])),
    getStockHistory: vi.fn(() => Promise.resolve(null)),
  },
}));

vi.mock('@/api/auth', () => ({
  authApi: {
    me: vi.fn(() =>
      Promise.resolve({ id: 1, role: 'child', country_code: 'US', content_region: 'GB' }),
    ),
  },
}));

vi.mock('@/components/child/simulator/MarketMovers', () => ({ MarketMovers: () => null }));
vi.mock('@/components/child/simulator/MarketNews', () => ({ MarketNews: () => null }));
vi.mock('@/components/child/simulator/InvestingTips', () => ({ InvestingTips: () => null }));

const mockUseOnline = vi.mocked(useOnline);

function renderMarket() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/simulator/market']}>
        <Market />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Market offline notice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOnline.mockReturnValue(true);
  });

  it('shows the offline notice when offline', async () => {
    mockUseOnline.mockReturnValue(false);
    const { container } = renderMarket();
    const notice = await screen.findByRole('status');
    expect(notice).toHaveTextContent(/you're offline/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('does not show the offline notice when online', async () => {
    renderMarket();
    expect(await screen.findByRole('searchbox', { name: /search stocks/i })).toBeInTheDocument();
    expect(screen.queryByText(/you're offline/i)).not.toBeInTheDocument();
  });
});
