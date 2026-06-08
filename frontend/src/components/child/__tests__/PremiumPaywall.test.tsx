import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

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
import type { PaywallContext } from '@/hooks/usePremiumPaywall';

const context: PaywallContext = { kind: 'module', label: 'Saving Smarts' };

beforeEach(async () => {
  vi.clearAllMocks();
  PremiumPaywall = (await import('@/components/child/PremiumPaywall')).PremiumPaywall;
  premiumApi = (await import('@/api/premium')).premiumApi;
});

function renderPaywall() {
  return render(<PremiumPaywall context={context} onClose={() => {}} />);
}

describe('PremiumPaywall', () => {
  it('shows the sent confirmation when the request is delivered', async () => {
    vi.mocked(premiumApi.requestUnlock).mockResolvedValue({ status: 'sent' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    await waitFor(() => expect(screen.getByText(/let your grown-up know/i)).toBeInTheDocument());
  });

  it('shows a gentle declined state with no purchase button', async () => {
    vi.mocked(premiumApi.requestUnlock).mockResolvedValue({ status: 'declined' });
    renderPaywall();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));

    await waitFor(() => expect(screen.getByText(/sort it out later/i)).toBeInTheDocument());

    expect(screen.queryByRole('button', { name: /subscribe|buy|pay/i })).toBeNull();
  });
});
