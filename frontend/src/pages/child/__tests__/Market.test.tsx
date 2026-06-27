import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { simulatorApi } from '@/api/simulator';
import { authApi } from '@/api/auth';
import Market from '../Market';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    searchMarket: vi.fn(),
    getSnapshot: vi.fn(() => Promise.resolve({ region: 'GB', featured: [], movers: {} })),
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

// The non-search child widgets only render when not searching; stub them out.
// MarketMovers records its region prop so we can assert wiring.
vi.mock('@/components/child/simulator/MarketMovers', () => ({
  MarketMovers: ({ region }: { region: string }) => <div data-testid="movers">movers:{region}</div>,
}));
vi.mock('@/components/child/simulator/MarketNews', () => ({ MarketNews: () => null }));
vi.mock('@/components/child/simulator/InvestingTips', () => ({ InvestingTips: () => null }));

const QUOTE = { ticker: 'NVDA', exchange: 'NASDAQ', name: 'NVIDIA Corp.', price: '525.40', currency: 'USD' };
const VOD_QUOTE = { ticker: 'VOD', exchange: 'LSE', name: 'Vodafone', price: '70.00', currency: 'GBP' };

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

  it('getSnapshot is called with the active region for featured stocks', async () => {
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({
      region: 'GB',
      featured: [VOD_QUOTE],
      movers: {},
    });
    vi.mocked(simulatorApi.searchMarket).mockResolvedValue([]);
    renderWithProviders('/simulator/market');
    expect(await screen.findByText('Vodafone')).toBeInTheDocument();
    expect(simulatorApi.getSnapshot).toHaveBeenCalledWith('GB');
  });

  it('shows a loading indicator (not "No stocks found") while a search is in flight', async () => {
    let resolveSearch: (v: typeof QUOTE[]) => void = () => {};
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'GB', featured: [], movers: {} });
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
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'GB', featured: [], movers: {} });
    vi.mocked(simulatorApi.searchMarket).mockImplementation(() => Promise.resolve([]));
    renderWithProviders('/simulator/market');
    await userEvent.type(await screen.findByRole('searchbox', { name: /search stocks/i }), 'ZZZZ');
    expect(await screen.findByText(/no stocks found/i, {}, { timeout: 2000 })).toBeInTheDocument();
  });

  it('defaults the region selector to the child content_region and wires movers', async () => {
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'GB', featured: [], movers: {} });
    vi.mocked(simulatorApi.searchMarket).mockImplementation(() => Promise.resolve([]));
    renderWithProviders('/simulator/market');
    expect(await screen.findByRole('radio', { name: /UK/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('movers')).toHaveTextContent('movers:GB');
    // the dead "Exchange" tooltip is gone
    expect(screen.queryByLabelText(/info about exchange/i)).toBeNull();
  });

  it('switching region updates the movers query', async () => {
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'GB', featured: [], movers: {} });
    vi.mocked(simulatorApi.searchMarket).mockImplementation(() => Promise.resolve([]));
    const user = userEvent.setup();
    renderWithProviders('/simulator/market');
    await user.click(await screen.findByRole('radio', { name: /US/i }));
    expect(screen.getByTestId('movers')).toHaveTextContent('movers:US');
  });

  it('defaults to US when the child is in an unsupported country (no content_region)', async () => {
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'US', featured: [], movers: {} });
    vi.mocked(simulatorApi.searchMarket).mockImplementation(() => Promise.resolve([]));
    vi.mocked(authApi.me).mockResolvedValueOnce({
      id: 1, role: 'child', country_code: 'FR', content_region: null,
    } as never);
    renderWithProviders('/simulator/market');
    expect(await screen.findByRole('radio', { name: /US/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('movers')).toHaveTextContent('movers:US');
  });

  it('has no axe violations in the loading state', async () => {
    vi.mocked(simulatorApi.getSnapshot).mockResolvedValue({ region: 'GB', featured: [], movers: {} });
    vi.mocked(simulatorApi.searchMarket).mockImplementation((q: string) =>
      q === '' ? Promise.resolve([]) : new Promise(() => {}));
    const { container } = renderWithProviders('/simulator/market');
    await userEvent.type(await screen.findByRole('searchbox', { name: /search stocks/i }), 'NVDA');
    await screen.findByText(/searching/i, {}, { timeout: 2000 });
    expect(await axe(container)).toHaveNoViolations();
  });
});
