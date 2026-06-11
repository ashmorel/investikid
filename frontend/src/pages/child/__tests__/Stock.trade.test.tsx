import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Stock from '../Stock';
import { simulatorApi, type TradeRequest } from '@/api/simulator';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn(() => true) }));
vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open: vi.fn() }) }));
vi.mock('@/lib/sound', () => ({ playSound: vi.fn() }));
vi.mock('@/lib/haptics', () => ({ haptic: vi.fn() }));

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

// Stub the heavy child widgets; this test targets the trade success path only.
vi.mock('@/components/child/simulator/StockChart', () => ({ StockChart: () => null }));
vi.mock('@/components/child/simulator/ChartGuide', () => ({ ChartGuide: () => null }));
vi.mock('@/components/child/simulator/StockNews', () => ({ StockNewsSection: () => null }));
vi.mock('@/components/child/simulator/InvestmentTimeMachine', () => ({ InvestmentTimeMachine: () => null }));
vi.mock('@/components/child/simulator/InvestingTips', () => ({ InvestingTips: () => null }));
vi.mock('@/components/child/simulator/ChartCoachPanel', () => ({ ChartCoachPanel: () => null }));
vi.mock('@/components/child/simulator/TradeForm', () => ({
  TradeForm: ({ onSubmit }: { onSubmit: (req: TradeRequest) => Promise<void> }) => (
    <button onClick={() => void onSubmit({ ticker: 'NVDA', exchange: 'NASDAQ', type: 'buy', shares: 1 })}>
      Submit trade
    </button>
  ),
}));

const mockPlaceTrade = vi.mocked(simulatorApi.placeTrade);

function renderStock() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/simulator/stock/NASDAQ/NVDA']}>
        <Routes>
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
          <Route path="/simulator" element={<div>Portfolio page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Stock trade success juice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('successful trade fires the trade sound and medium haptic', async () => {
    const user = userEvent.setup();
    mockPlaceTrade.mockResolvedValue({
      rewards: { xp_awarded: 5, streak_extended: false, cash_granted: '0', missions_completed: [] },
    } as unknown as Awaited<ReturnType<typeof simulatorApi.placeTrade>>);
    renderStock();

    await user.click(await screen.findByRole('button', { name: /Submit trade/i }));

    await waitFor(() => expect(playSound).toHaveBeenCalledExactlyOnceWith('trade'));
    expect(haptic).toHaveBeenCalledWith('medium');
  });

  it('failed trade fires no sound or haptic', async () => {
    const user = userEvent.setup();
    mockPlaceTrade.mockRejectedValue(new Error('boom'));
    renderStock();

    await user.click(await screen.findByRole('button', { name: /Submit trade/i }));

    await waitFor(() => expect(mockPlaceTrade).toHaveBeenCalled());
    expect(playSound).not.toHaveBeenCalled();
    expect(haptic).not.toHaveBeenCalled();
  });
});
