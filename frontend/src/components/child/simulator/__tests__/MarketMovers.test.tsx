import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketMovers } from '../MarketMovers';

vi.mock('@/api/simulator', () => ({
  simulatorApi: { getSnapshot: vi.fn(() => Promise.resolve({ region: 'GB', featured: [], movers: {} })) },
}));
import { simulatorApi } from '@/api/simulator';

function renderMovers(region: 'US' | 'GB' | 'HK') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MarketMovers region={region} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('MarketMovers', () => {
  it('fetches snapshot for the given region', async () => {
    renderMovers('GB');
    await screen.findByText(/market movers|loading market movers/i);
    expect(simulatorApi.getSnapshot).toHaveBeenCalledWith('GB');
  });
});
