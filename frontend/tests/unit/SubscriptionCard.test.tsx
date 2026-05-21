import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubscriptionCard } from '@/components/SubscriptionCard';

// Mock the billing API
const mockGetStatus = vi.fn();
const mockCreateCheckout = vi.fn();
const mockCreatePortal = vi.fn();

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => mockGetStatus(),
    createCheckout: () => mockCreateCheckout(),
    createPortal: () => mockCreatePortal(),
  },
}));

function wrap() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={qc}>
      <SubscriptionCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SubscriptionCard', () => {
  it('shows Subscribe button when no subscription', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByRole('button', { name: /subscribe to premium/i })).toBeInTheDocument();
    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
  });

  it('shows trial status with days remaining', async () => {
    const futureDate = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'trialing',
      trial_ends_at: futureDate,
      current_period_end: futureDate,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/premium trial/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  it('shows active status with renewal date', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'active',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/premium — renews/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  it('shows cancellation date when cancel_at_period_end', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'active',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: true,
    });
    wrap();
    expect(await screen.findByText(/premium — cancels/i)).toBeInTheDocument();
  });

  it('shows payment issue for past_due', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: true,
      status: 'past_due',
      trial_ends_at: null,
      current_period_end: '2026-06-20T00:00:00Z',
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByText(/payment issue/i)).toBeInTheDocument();
  });

  it('shows Subscribe button when canceled', async () => {
    mockGetStatus.mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    });
    wrap();
    expect(await screen.findByRole('button', { name: /subscribe to premium/i })).toBeInTheDocument();
  });
});
