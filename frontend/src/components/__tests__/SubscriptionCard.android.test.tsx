import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

vi.mock('@/lib/platform', () => ({
  isNativeApp: () => true,
  isAndroid: () => true,
}));

vi.mock('@/lib/playBilling', () => ({
  PlayBilling: {
    getProducts: vi.fn().mockResolvedValue({ products: [] }),
    purchase: vi
      .fn()
      .mockResolvedValue({ purchaseToken: 'TOK', productId: 'premium_monthly' }),
    restore: vi.fn().mockResolvedValue({ purchaseTokens: [] }),
  },
}));

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: vi.fn().mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    }),
    accountToken: vi
      .fn()
      .mockResolvedValue({ token: '11111111-1111-1111-1111-111111111111' }),
    googleVerify: vi.fn().mockResolvedValue({ status: 'ok' }),
    createCheckout: vi.fn(),
    createPortal: vi.fn(),
  },
}));

import { SubscriptionCard } from '../SubscriptionCard';
import { billingApi } from '@/api/billing';
import { PlayBilling } from '@/lib/playBilling';

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SubscriptionCard />
    </QueryClientProvider>,
  );
}

describe('SubscriptionCard (native Play Billing)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Subscribe and Restore buttons, and no Stripe checkout button', async () => {
    renderCard();
    expect(await screen.findByRole('button', { name: /subscribe/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /restore purchases/i })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /subscribe to premium/i }),
    ).not.toBeInTheDocument();
  });

  it('runs the Play Billing purchase + verify flow on Subscribe', async () => {
    renderCard();
    fireEvent.click(await screen.findByRole('button', { name: /^subscribe$/i }));

    await waitFor(() => expect(billingApi.accountToken).toHaveBeenCalled());
    await waitFor(() =>
      expect(PlayBilling.purchase).toHaveBeenCalledWith({
        productId: 'premium_monthly',
        obfuscatedAccountId: '11111111-1111-1111-1111-111111111111',
      }),
    );
    await waitFor(() =>
      expect(billingApi.googleVerify).toHaveBeenCalledWith({
        purchaseToken: 'TOK',
        productId: 'premium_monthly',
      }),
    );
  });

  it('has no accessibility violations', async () => {
    const { container } = renderCard();
    await screen.findByRole('button', { name: /subscribe/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
