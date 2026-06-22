import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketSwitcher } from '../MarketSwitcher';
import { marketApi, type MarketSummary } from '@/api/market';

vi.mock('@/api/market', async (orig) => {
  const actual = await orig<typeof import('@/api/market')>();
  return { ...actual, marketApi: { ...actual.marketApi, list: vi.fn(), switch: vi.fn() } };
});

const M = (over: Partial<MarketSummary>): MarketSummary => ({
  code: 'GB', name: 'United Kingdom', currency_code: 'GBP',
  has_content: true, enrolled: true, is_selected: false, locked: false, ...over,
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(marketApi.list).mockResolvedValue([
    M({ code: 'GB', name: 'United Kingdom', is_selected: true }),
    M({ code: 'US', name: 'United States' }),
    M({ code: 'HK', name: 'Hong Kong' }),
    M({ code: 'FR', name: 'France', has_content: false }), // no content → hidden
  ]);
  vi.mocked(marketApi.switch).mockResolvedValue({
    active_market_code: 'US',
    reward: { coins: 0, badge_name: null, badge_icon: null },
  });
});

describe('MarketSwitcher', () => {
  it('shows only markets with content, marking the active one', async () => {
    wrap(<MarketSwitcher />);
    const gb = await screen.findByRole('button', { name: /United Kingdom/ });
    expect(gb).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /United States/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hong Kong/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /France/ })).not.toBeInTheDocument();
  });

  it('switches the active market in place on click', async () => {
    wrap(<MarketSwitcher />);
    const us = await screen.findByRole('button', { name: /United States/ });
    await userEvent.click(us);
    await waitFor(() => expect(marketApi.switch).toHaveBeenCalledWith('US'));
  });

  it('does not switch the already-active market', async () => {
    wrap(<MarketSwitcher />);
    const gb = await screen.findByRole('button', { name: /United Kingdom/ });
    await userEvent.click(gb);
    expect(marketApi.switch).not.toHaveBeenCalled();
  });

  it('routes a locked market to onLockedClick instead of switching', async () => {
    vi.mocked(marketApi.list).mockResolvedValue([
      M({ code: 'GB', name: 'United Kingdom', is_selected: true }),
      M({ code: 'US', name: 'United States', locked: true }),
    ]);
    const onLockedClick = vi.fn();
    wrap(<MarketSwitcher onLockedClick={onLockedClick} />);
    const us = await screen.findByRole('button', { name: /United States/ });
    await userEvent.click(us);
    expect(onLockedClick).toHaveBeenCalledWith(expect.objectContaining({ code: 'US' }));
    expect(marketApi.switch).not.toHaveBeenCalled();
  });

  it('renders nothing when fewer than two markets have content', async () => {
    vi.mocked(marketApi.list).mockResolvedValue([
      M({ code: 'GB', name: 'United Kingdom', is_selected: true }),
      M({ code: 'US', name: 'United States', has_content: false }),
    ]);
    const { container } = wrap(<MarketSwitcher />);
    await waitFor(() => expect(marketApi.list).toHaveBeenCalled());
    expect(screen.queryByRole('group')).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<MarketSwitcher />);
    await screen.findByRole('button', { name: /United Kingdom/ });
    expect(await axe(container)).toHaveNoViolations();
  });
});
