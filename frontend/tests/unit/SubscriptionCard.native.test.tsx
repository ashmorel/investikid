import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubscriptionCard } from '@/components/SubscriptionCard';

const mockGetStatus = vi.fn();

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => mockGetStatus(),
    createCheckout: vi.fn(),
    createPortal: vi.fn(),
  },
}));

// Force native (Capacitor) platform — purchase UI must be suppressed.
// iOS branch (not Android), so isAndroid() is false here.
vi.mock('@/lib/platform', () => ({
  isNativeApp: () => true,
  isAndroid: () => false,
  getPlatform: () => 'ios',
}));

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SubscriptionCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SubscriptionCard on native (App Store compliance)', () => {
  it('renders nothing on free plan — no Subscribe CTA', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    });
    const { container } = wrap();
    // Give the query a tick to resolve.
    await waitFor(() => expect(mockGetStatus).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: /subscribe/i })).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it('shows status text but hides Manage Billing when subscribed', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'active',
      trial_ends_at: null,
      current_period_end: '2099-01-01T00:00:00Z',
      cancel_at_period_end: false,
    });
    wrap();
    await screen.findByText(/Premium/i);
    expect(screen.queryByRole('button', { name: /manage billing/i })).not.toBeInTheDocument();
  });
});
