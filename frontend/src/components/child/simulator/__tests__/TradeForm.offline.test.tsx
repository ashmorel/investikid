import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOnline } from '@/hooks/useOnline';
import { TradeForm } from '../TradeForm';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn(() => true) }));

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getTradeConfig: vi.fn(() => Promise.resolve({ commission_pct: '0.5' })),
  },
}));

const mockUseOnline = vi.mocked(useOnline);

function renderForm() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TradeForm
        ticker="NVDA"
        exchange="NASDAQ"
        price="525.40"
        currency="USD"
        availableCash="10000.00"
        ownedShares="0"
        onSubmit={vi.fn()}
        isSubmitting={false}
        submitError={null}
      />
    </QueryClientProvider>,
  );
}

describe('TradeForm offline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOnline.mockReturnValue(true);
  });

  it('disables the submit button and shows the notice when offline', async () => {
    mockUseOnline.mockReturnValue(false);
    const { container } = renderForm();
    expect(screen.getByRole('button', { name: /review trade/i })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent(/you're offline/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('keeps the submit button enabled and hides the notice when online', () => {
    renderForm();
    expect(screen.getByRole('button', { name: /review trade/i })).toBeEnabled();
    expect(screen.queryByText(/you're offline/i)).not.toBeInTheDocument();
  });
});
