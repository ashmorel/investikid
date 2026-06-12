import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { PlansResponse } from '@/api/billing';
import { SubscriptionCard } from '../SubscriptionCard';

const plans: PlansResponse = {
  currency: 'GBP',
  plans: [
    { plan: 'annual', interval: 'year', display_price: '£29.99', savings_pct: 33, apple_product_id: 'premium_annual', google_product_id: 'premium_annual' },
    { plan: 'monthly', interval: 'month', display_price: '£3.99', savings_pct: null, apple_product_id: 'premium_monthly', google_product_id: 'premium_monthly' },
  ],
};

const createCheckout = vi.fn().mockResolvedValue({ url: 'https://checkout' });
vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => Promise.resolve({ has_subscription: false, status: null, trial_ends_at: null, current_period_end: null, cancel_at_period_end: false }),
    getPlans: () => Promise.resolve(plans),
    createCheckout: (plan: string) => createCheckout(plan),
    createPortal: vi.fn(),
    appleVerify: vi.fn(),
    appleAccountToken: vi.fn(),
    googleVerify: vi.fn(),
    accountToken: vi.fn(),
  },
}));
vi.mock('@/lib/platform', () => ({ isNativeApp: () => false, isAndroid: () => false }));

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SubscriptionCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => createCheckout.mockClear());

describe('SubscriptionCard plan picker (m5)', () => {
  it('renders both plans with regional prices, annual preselected with savings badge', async () => {
    renderCard();
    expect(await screen.findByRole('radiogroup', { name: /choose a plan/i })).toBeInTheDocument();
    expect(screen.getByText('£29.99')).toBeInTheDocument();
    expect(screen.getByText('£3.99')).toBeInTheDocument();
    expect(screen.getByText(/save 33%/i)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /annual/i })).toBeChecked();
    expect(
      screen.getByText((_, el) => el?.tagName === 'P' && /unlocks premium for all your children/i.test(el.textContent ?? '')),
    ).toBeInTheDocument();
  });

  it('checks out with the selected plan', async () => {
    renderCard();
    await screen.findByRole('radiogroup', { name: /choose a plan/i });
    fireEvent.click(screen.getByRole('button', { name: /subscribe to premium/i }));
    await waitFor(() => expect(createCheckout).toHaveBeenCalledWith('annual'));

    fireEvent.click(screen.getByRole('radio', { name: /monthly/i }));
    fireEvent.click(screen.getByRole('button', { name: /subscribe to premium/i }));
    await waitFor(() => expect(createCheckout).toHaveBeenCalledWith('monthly'));
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    await screen.findByRole('radiogroup', { name: /choose a plan/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
