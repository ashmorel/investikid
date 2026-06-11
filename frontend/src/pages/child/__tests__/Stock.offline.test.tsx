import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOnline } from '@/hooks/useOnline';
import Stock from '../Stock';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn(() => true) }));
vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open: vi.fn() }) }));

const QUOTE = { ticker: 'NVDA', exchange: 'NASDAQ', name: 'NVIDIA Corp.', price: '525.40', currency: 'USD' };
const PORTFOLIO = { virtual_cash: '10000.00', holdings: [] };

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getQuote: vi.fn(() => Promise.resolve(QUOTE)),
    getPortfolio: vi.fn(() => Promise.resolve(PORTFOLIO)),
    placeTrade: vi.fn(),
    getTradeConfig: vi.fn(() => Promise.resolve({ commission_pct: '0.5' })),
  },
}));

// Stub the heavy child widgets; this test targets the offline notice only.
vi.mock('@/components/child/simulator/StockChart', () => ({ StockChart: () => null }));
vi.mock('@/components/child/simulator/ChartGuide', () => ({ ChartGuide: () => null }));
vi.mock('@/components/child/simulator/StockNews', () => ({ StockNewsSection: () => null }));
vi.mock('@/components/child/simulator/InvestmentTimeMachine', () => ({ InvestmentTimeMachine: () => null }));
vi.mock('@/components/child/simulator/InvestingTips', () => ({ InvestingTips: () => null }));
vi.mock('@/components/child/simulator/ChartCoachPanel', () => ({ ChartCoachPanel: () => null }));
vi.mock('@/components/child/simulator/TradeForm', () => ({ TradeForm: () => <div data-testid="trade-form" /> }));

const mockUseOnline = vi.mocked(useOnline);

function renderStock() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/simulator/stock/NASDAQ/NVDA']}>
        <Routes>
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Stock offline notice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOnline.mockReturnValue(true);
  });

  it('shows the offline notice above the stock view when offline', async () => {
    mockUseOnline.mockReturnValue(false);
    renderStock();
    expect(await screen.findByText(/NVIDIA Corp\./)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/you're offline/i);
  });

  it('does not show the offline notice when online', async () => {
    renderStock();
    expect(await screen.findByText(/NVIDIA Corp\./)).toBeInTheDocument();
    expect(screen.queryByText(/you're offline/i)).not.toBeInTheDocument();
  });
});
