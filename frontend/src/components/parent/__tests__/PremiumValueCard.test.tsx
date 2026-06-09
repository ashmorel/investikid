import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumValueCard } from '../PremiumValueCard';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';

const getStatus = vi.fn();
const parentRequests = vi.fn();

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => getStatus(),
  },
}));

vi.mock('@/api/premium', () => ({
  premiumApi: {
    parentRequests: () => parentRequests(),
  },
}));

const NOT_SUBSCRIBED = {
  has_subscription: false,
  status: null,
  trial_ends_at: null,
  current_period_end: null,
  cancel_at_period_end: false,
};

const SUBSCRIBED = {
  has_subscription: true,
  status: 'active',
  trial_ends_at: null,
  current_period_end: '2026-12-01T00:00:00Z',
  cancel_at_period_end: false,
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe('PremiumValueCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    parentRequests.mockResolvedValue([]);
  });

  it('shows the value block and a Subscribe CTA for a non-subscribed parent', async () => {
    getStatus.mockResolvedValue(NOT_SUBSCRIBED);
    render(wrap(<PremiumValueCard />));

    expect(await screen.findByText(/premium gives your child/i)).toBeInTheDocument();
    expect(screen.getByText(PREMIUM_BENEFITS[0])).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /subscribe/i })).toBeInTheDocument();
  });

  it('highlights a pending request with the child name', async () => {
    getStatus.mockResolvedValue(NOT_SUBSCRIBED);
    parentRequests.mockResolvedValue([
      {
        id: 'req-1',
        child_username: 'Yasmin',
        context_kind: 'coach',
        context_label: 'Coach Penny',
        created_at: '2026-06-07T10:00:00Z',
      },
    ]);
    render(wrap(<PremiumValueCard />));

    const highlight = await screen.findByText(/asked to unlock premium/i);
    expect(highlight).toHaveTextContent(/Yasmin/);
  });

  it('does not show the upsell for a subscribed parent', async () => {
    getStatus.mockResolvedValue(SUBSCRIBED);
    const { container } = render(wrap(<PremiumValueCard />));

    // wait for the query to resolve
    await Promise.resolve();
    expect(screen.queryByText(/premium gives your child/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /subscribe/i })).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it('has no accessibility violations (non-subscribed)', async () => {
    getStatus.mockResolvedValue(NOT_SUBSCRIBED);
    const { container } = render(wrap(<PremiumValueCard />));
    await screen.findByText(/premium gives your child/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('invokes onSubscribe when the CTA is clicked', async () => {
    getStatus.mockResolvedValue(NOT_SUBSCRIBED);
    const onSubscribe = vi.fn();
    const user = userEvent.setup();
    render(wrap(<PremiumValueCard onSubscribe={onSubscribe} />));
    await user.click(await screen.findByRole('button', { name: /subscribe/i }));
    expect(onSubscribe).toHaveBeenCalled();
  });
});
