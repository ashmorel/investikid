import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { TradeForm } from '@/components/child/simulator/TradeForm';

beforeEach(() => vi.restoreAllMocks());

function mockTradeConfig(commissionPct: string | null) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.includes('/market/trade-config')) {
      if (commissionPct === null) return new Response('boom', { status: 500 });
      return new Response(JSON.stringify({ commission_pct: commissionPct }), { status: 200 });
    }
    return new Response('not mocked', { status: 500 });
  });
}

const baseProps = {
  ticker: 'AAPL',
  exchange: 'NASDAQ',
  price: '185.42',
  currency: 'USD',
  availableCash: '10000.00',
  ownedShares: '0',
  avgBuyPrice: null as string | null,
  onSubmit: vi.fn().mockResolvedValue(undefined),
  isSubmitting: false,
  submitError: null as string | null,
};

function renderForm(overrides: Partial<typeof baseProps> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TradeForm {...baseProps} {...overrides} />
    </QueryClientProvider>,
  );
}

describe('TradeForm', () => {
  it('renders Buy/Sell toggle with Sell disabled when 0 shares owned', () => {
    mockTradeConfig('1.0');
    renderForm();
    expect(screen.getByRole('radio', { name: /buy/i })).toBeInTheDocument();
    const sellBtn = screen.getByRole('radio', { name: /sell/i });
    expect(sellBtn).toBeDisabled();
  });

  it('enables Sell when user owns shares', () => {
    mockTradeConfig('1.0');
    renderForm({ ownedShares: '5' });
    expect(screen.getByRole('radio', { name: /sell/i })).not.toBeDisabled();
  });

  it('shows live cost preview as user types shares', async () => {
    mockTradeConfig('1.0');
    renderForm();
    const input = screen.getByLabelText(/number of shares/i);
    await userEvent.type(input, '5');
    expect(
      screen.getByText((_, el) =>
        el?.tagName === 'P' &&
        /5 shares × \$185\.42 USD = \$927\.10 USD/.test(el.textContent ?? '')
      )
    ).toBeInTheDocument();
  });

  it('advances to step 2 on Review click and shows confirmation', async () => {
    mockTradeConfig('1.0');
    renderForm();
    const input = screen.getByLabelText(/number of shares/i);
    await userEvent.type(input, '2');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/Buy 2 shares of AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/Cash after trade/i)).toBeInTheDocument();
  });

  it('calls onSubmit with correct payload on Confirm', async () => {
    mockTradeConfig('1.0');
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ onSubmit });
    await userEvent.type(screen.getByLabelText(/number of shares/i), '3');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onSubmit).toHaveBeenCalledWith({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 3 });
  });

  it('Go back button returns to step 1', async () => {
    mockTradeConfig('1.0');
    renderForm();
    await userEvent.type(screen.getByLabelText(/number of shares/i), '1');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /go back/i }));
    expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
  });

  it('shows insufficient cash error for Buy exceeding available cash', async () => {
    mockTradeConfig('1.0');
    renderForm({ availableCash: '100.00' });
    await userEvent.type(screen.getByLabelText(/number of shares/i), '5');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/insufficient/i)).toBeInTheDocument();
  });

  it('shows Max button for Sell that fills shares owned', async () => {
    mockTradeConfig('1.0');
    renderForm({ ownedShares: '10' });
    await userEvent.click(screen.getByRole('radio', { name: /sell/i }));
    await userEvent.click(screen.getByRole('button', { name: /max/i }));
    expect(screen.getByLabelText(/number of shares/i)).toHaveValue(10);
  });

  it('displays submitError when present', () => {
    mockTradeConfig('1.0');
    renderForm({ submitError: 'Insufficient virtual cash' });
    expect(screen.getByText(/insufficient virtual cash/i)).toBeInTheDocument();
  });
});

describe('TradeForm fee line', () => {
  it('shows fee and total for a buy', async () => {
    mockTradeConfig('1.0');
    renderForm();
    await userEvent.type(screen.getByLabelText(/number of shares/i), '5');
    // 5 × 185.42 = 927.10; fee 1% = 9.27; total = 936.37
    await waitFor(() => {
      expect(
        screen.getByText((_, el) =>
          el?.tagName === 'P' &&
          /Fee \(1%\): \$9\.27 USD · Total: \$936\.37 USD/.test(el.textContent ?? '')
        )
      ).toBeInTheDocument();
    });
  });

  it('shows fee and net proceeds for a sell', async () => {
    mockTradeConfig('1.0');
    renderForm({ ownedShares: '5' });
    await userEvent.click(screen.getByRole('radio', { name: /sell/i }));
    await userEvent.type(screen.getByLabelText(/number of shares/i), '2');
    // 2 × 185.42 = 370.84; fee 1% = 3.71; receive ≈ 367.13
    await waitFor(() => {
      expect(
        screen.getByText((_, el) =>
          el?.tagName === 'P' &&
          /Fee \(1%\): \$3\.71 USD · You'll receive ≈ \$367\.13 USD/.test(el.textContent ?? '')
        )
      ).toBeInTheDocument();
    });
  });

  it('omits the fee line when the config request fails (form still works)', async () => {
    mockTradeConfig(null);
    renderForm();
    await userEvent.type(screen.getByLabelText(/number of shares/i), '5');
    expect(screen.queryByText(/Fee \(/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/Buy 5 shares of AAPL/)).toBeInTheDocument();
  });
});

describe('TradeForm sell-at-loss reflection', () => {
  const lossProps = { ownedShares: '5', avgBuyPrice: '200.00' }; // price 185.42 < 200.00

  async function goToConfirm(shares = '2') {
    await userEvent.click(screen.getByRole('radio', { name: /sell/i }));
    await userEvent.type(screen.getByLabelText(/number of shares/i), shares);
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm sell of/i }));
  }

  it('shows the reflection step when selling below avg buy price', async () => {
    mockTradeConfig('1.0');
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ ...lossProps, onSubmit });
    await goToConfirm();
    expect(screen.getByText(/You'd be selling at a loss\. What's your reason\?/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not show the reflection step when selling at a gain', async () => {
    mockTradeConfig('1.0');
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ ownedShares: '5', avgBuyPrice: '100.00', onSubmit });
    await goToConfirm();
    expect(screen.queryByText(/selling at a loss/i)).not.toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledWith({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'sell', shares: 2 });
  });

  it.each([
    ["The company's story has changed", 'A real reason to rethink — stories matter more than prices.'],
    ['I need the cash for something else', 'Fair — needing money is a real reason.'],
    ['The price is falling and it scares me', "That's the one to watch: falling prices alone are often the worst reason to sell. Markets wobble; selling locks in the loss."],
  ])('shows the response for reason "%s"', async (reason, response) => {
    mockTradeConfig('1.0');
    renderForm(lossProps);
    await goToConfirm();
    await userEvent.click(screen.getByRole('radio', { name: reason }));
    expect(screen.getByText(response)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^confirm sell$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('confirm completes onSubmit with the original payload', async () => {
    mockTradeConfig('1.0');
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ ...lossProps, onSubmit });
    await goToConfirm('3');
    await userEvent.click(screen.getByRole('radio', { name: /I need the cash/i }));
    await userEvent.click(screen.getByRole('button', { name: /^confirm sell$/i }));
    expect(onSubmit).toHaveBeenCalledWith({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'sell', shares: 3 });
  });

  it('cancel returns to the form without submitting', async () => {
    mockTradeConfig('1.0');
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm({ ...lossProps, onSubmit });
    await goToConfirm();
    await userEvent.click(screen.getByRole('radio', { name: /scares me/i }));
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
  });

  it('reflection state has no axe violations', async () => {
    mockTradeConfig('1.0');
    const { container } = renderForm(lossProps);
    await goToConfirm();
    await userEvent.click(screen.getByRole('radio', { name: /scares me/i }));
    expect(await axe(container)).toHaveNoViolations();
  });
});
