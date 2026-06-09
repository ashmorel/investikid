import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketNews } from '../MarketNews';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getMarketNews: vi.fn(),
    getNewsSummary: vi.fn(() => Promise.resolve(null)),
  },
}));
import { simulatorApi } from '@/api/simulator';

const NEWS = [
  { title: 'Apple climbs on earnings', url: 'https://x.test/a', publisher: 'Wire', published: '', related_ticker: 'AAPL', summary: '', thumbnail: '' },
];

function renderNews() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MarketNews />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(simulatorApi.getMarketNews).mockResolvedValue(NEWS as never);
  vi.mocked(simulatorApi.getNewsSummary).mockResolvedValue(null as never);
});

describe('MarketNews', () => {
  it('is collapsed by default and reveals news when expanded', async () => {
    renderNews();
    const toggle = await screen.findByRole('button', { name: /news for your stocks/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/apple climbs on earnings/i)).toBeNull();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/apple climbs on earnings/i)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderNews();
    await screen.findByRole('button', { name: /news for your stocks/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
