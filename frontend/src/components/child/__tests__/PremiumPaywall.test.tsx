import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const isNativeApp = vi.fn(() => false);
const isAndroid = vi.fn(() => false);
vi.mock('@/lib/platform', () => ({
  isNativeApp: () => isNativeApp(),
  isAndroid: () => isAndroid(),
}));

const runNativePurchase = vi.fn();
vi.mock('@/lib/nativePurchase', () => ({
  runNativePurchase: (...args: unknown[]) => runNativePurchase(...args),
}));

// Stub the gate to a deterministic "pass" button so we don't solve the maths.
vi.mock('@/components/child/ParentalGate', () => ({
  ParentalGate: ({ onPass, onCancel }: { onPass: () => void; onCancel: () => void }) => (
    <div>
      <button type="button" onClick={onPass}>pass-gate</button>
      <button type="button" onClick={onCancel}>cancel-gate</button>
    </div>
  ),
}));

vi.mock('@/api/billing', () => ({
  billingApi: {
    childPlans: vi.fn(),
    childAppleAccountToken: vi.fn(),
    childAppleVerify: vi.fn(),
    childGoogleAccountToken: vi.fn(),
    childGoogleVerify: vi.fn(),
  },
}));

vi.mock('@/api/premium', async () => {
  const actual = await vi.importActual('@/api/premium');
  return {
    ...actual,
    premiumApi: {
      ...((actual as { premiumApi?: object }).premiumApi ?? {}),
      requestUnlock: vi.fn(),
    },
  };
});

let PremiumPaywall: typeof import('@/components/child/PremiumPaywall').PremiumPaywall;
let premiumApi: typeof import('@/api/premium').premiumApi;
let billingApi: typeof import('@/api/billing').billingApi;
import type { PaywallContext } from '@/hooks/usePremiumPaywall';

const context: PaywallContext = { kind: 'module', label: 'Saving Smarts' };

const ONE_PLAN = {
  currency: 'GBP',
  plans: [{
    plan: 'annual' as const,
    interval: 'year' as const,
    display_price: '£39.99',
    savings_pct: null,
    apple_product_id: 'com.investikid.annual',
    google_product_id: 'annual_sub',
  }],
};

beforeEach(async () => {
  vi.clearAllMocks();
  isNativeApp.mockReturnValue(false);
  isAndroid.mockReturnValue(false);
  PremiumPaywall = (await import('@/components/child/PremiumPaywall')).PremiumPaywall;
  premiumApi = (await import('@/api/premium')).premiumApi;
  billingApi = (await import('@/api/billing')).billingApi;
});

function renderPaywall() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywall context={context} onClose={() => {}} />
    </QueryClientProvider>,
  );
}

describe('PremiumPaywall — web email path', () => {
  it('shows the sent confirmation when the request is delivered', async () => {
    vi.mocked(premiumApi.requestUnlock).mockResolvedValue({ status: 'sent' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    await waitFor(() => expect(screen.getByText(/let your grown-up know/i)).toBeInTheDocument());
    expect(runNativePurchase).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /pass-gate/i })).toBeNull();
  });

  it('shows a gentle declined state with no purchase button', async () => {
    vi.mocked(premiumApi.requestUnlock).mockResolvedValue({ status: 'declined' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    await waitFor(() => expect(screen.getByText(/sort it out later/i)).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /subscribe|buy|pay/i })).toBeNull();
  });
});

describe('PremiumPaywall — native purchase path', () => {
  beforeEach(() => {
    isNativeApp.mockReturnValue(true);
    vi.mocked(billingApi.childPlans).mockResolvedValue(ONE_PLAN);
    vi.mocked(billingApi.childAppleAccountToken).mockResolvedValue({ token: 'acct-tok' });
    vi.mocked(billingApi.childAppleVerify).mockResolvedValue({ status: 'active' });
  });

  it('shows the get-premium CTA, gates it, and unlocks on an active purchase', async () => {
    runNativePurchase.mockResolvedValue({ status: 'active' });
    renderPaywall();

    // Native CTA, not the email one.
    await userEvent.click(screen.getByRole('button', { name: /get premium/i }));
    // Gate appears before any purchase runs.
    expect(runNativePurchase).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: /pass-gate/i }));

    await waitFor(() => expect(runNativePurchase).toHaveBeenCalledTimes(1));
    expect(runNativePurchase).toHaveBeenCalledWith(
      expect.objectContaining({ platform: 'ios', productId: 'com.investikid.annual' }),
    );
    await waitFor(() => expect(screen.getByText(/premium unlocked/i)).toBeInTheDocument());
    expect(premiumApi.requestUnlock).not.toHaveBeenCalled();
  });

  it('shows the asked-grown-up message and no unlocked state on a pending purchase', async () => {
    runNativePurchase.mockResolvedValue({ status: 'pending' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /get premium/i }));
    await userEvent.click(screen.getByRole('button', { name: /pass-gate/i }));

    await waitFor(() => expect(screen.getByText(/asked your grown-up/i)).toBeInTheDocument());
    expect(screen.queryByText(/premium unlocked/i)).toBeNull();
  });

  it('shows an error and keeps the paywall usable when the purchase throws', async () => {
    runNativePurchase.mockRejectedValue(new Error('store unavailable'));
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /get premium/i }));
    await userEvent.click(screen.getByRole('button', { name: /pass-gate/i }));

    await waitFor(() => expect(screen.getByText(/something went wrong/i)).toBeInTheDocument());
    expect(screen.queryByText(/premium unlocked/i)).toBeNull();
    // Not stuck in a loading state: the get-premium CTA is usable again.
    expect(screen.getByRole('button', { name: /get premium/i })).toBeEnabled();
  });

  it('returns to the paywall on a cancelled purchase', async () => {
    runNativePurchase.mockResolvedValue({ status: 'cancelled' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /get premium/i }));
    await userEvent.click(screen.getByRole('button', { name: /pass-gate/i }));

    await waitFor(() => expect(runNativePurchase).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(/premium unlocked/i)).toBeNull();
    expect(screen.queryByText(/asked your grown-up/i)).toBeNull();
    // Back on the paywall: the get-premium CTA is visible again.
    expect(screen.getByRole('button', { name: /get premium/i })).toBeInTheDocument();
  });
});
