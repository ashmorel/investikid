import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StockChart } from '../StockChart';
import { simulatorApi, type PricePoint } from '@/api/simulator';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getStockHistory: vi.fn(),
  },
}));

const mockGetHistory = vi.mocked(simulatorApi.getStockHistory);

function renderChart() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <StockChart exchange="NASDAQ" ticker="ARM" currency="USD" />
    </QueryClientProvider>,
  );
}

describe('StockChart null-close guard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing when a point has a null close', async () => {
    // A malformed payload (e.g. NASDAQ/ARM) with a null close used to throw
    // `Cannot read properties of null (reading 'toFixed')` and trip the error boundary.
    const points = [
      { date: '2024-01-01', open: 100, high: 101, low: 99, close: 100.5, volume: 1000 },
      { date: '2024-01-02', open: 101, high: 103, low: 100, close: 102.5, volume: 2000 },
      { date: '2024-01-03', open: 102, high: 104, low: 101, close: null, volume: 3000 },
    ] as unknown as PricePoint[];
    mockGetHistory.mockResolvedValue(points);

    renderChart();

    // The null-close row is filtered out, leaving two valid points -> chart renders.
    expect(await screen.findByText('Price History')).toBeInTheDocument();
    await waitFor(() => expect(mockGetHistory).toHaveBeenCalled());
  });

  it('degrades to the no-data state when every close is null', async () => {
    const points = [
      { date: '2024-01-01', open: 100, high: 101, low: 99, close: null, volume: 1000 },
      { date: '2024-01-02', open: 101, high: 103, low: 100, close: null, volume: 2000 },
    ] as unknown as PricePoint[];
    mockGetHistory.mockResolvedValue(points);

    renderChart();

    expect(await screen.findByText('Price History')).toBeInTheDocument();
    expect(
      await screen.findByText(/No price data available/i),
    ).toBeInTheDocument();
  });
});
