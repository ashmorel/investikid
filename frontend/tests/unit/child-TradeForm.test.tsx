import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TradeForm } from '@/components/child/simulator/TradeForm';

beforeEach(() => vi.restoreAllMocks());

const baseProps = {
  ticker: 'AAPL',
  exchange: 'NASDAQ',
  price: '185.42',
  currency: 'USD',
  availableCash: '10000.00',
  ownedShares: '0',
  onSubmit: vi.fn().mockResolvedValue(undefined),
  isSubmitting: false,
  submitError: null as string | null,
};

describe('TradeForm', () => {
  it('renders Buy/Sell toggle with Sell disabled when 0 shares owned', () => {
    render(<TradeForm {...baseProps} />);
    expect(screen.getByRole('radio', { name: /buy/i })).toBeInTheDocument();
    const sellBtn = screen.getByRole('radio', { name: /sell/i });
    expect(sellBtn).toBeDisabled();
  });

  it('enables Sell when user owns shares', () => {
    render(<TradeForm {...baseProps} ownedShares="5" />);
    expect(screen.getByRole('radio', { name: /sell/i })).not.toBeDisabled();
  });

  it('shows live cost preview as user types shares', async () => {
    render(<TradeForm {...baseProps} />);
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
    render(<TradeForm {...baseProps} />);
    const input = screen.getByLabelText(/number of shares/i);
    await userEvent.type(input, '2');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/Buy 2 shares of AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/Cash after trade/i)).toBeInTheDocument();
  });

  it('calls onSubmit with correct payload on Confirm', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<TradeForm {...baseProps} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '3');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onSubmit).toHaveBeenCalledWith({ ticker: 'AAPL', exchange: 'NASDAQ', type: 'buy', shares: 3 });
  });

  it('Go back button returns to step 1', async () => {
    render(<TradeForm {...baseProps} />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '1');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    await userEvent.click(screen.getByRole('button', { name: /go back/i }));
    expect(screen.getByRole('button', { name: /review trade/i })).toBeInTheDocument();
  });

  it('shows insufficient cash error for Buy exceeding available cash', async () => {
    render(<TradeForm {...baseProps} availableCash="100.00" />);
    await userEvent.type(screen.getByLabelText(/number of shares/i), '5');
    await userEvent.click(screen.getByRole('button', { name: /review trade/i }));
    expect(screen.getByText(/insufficient/i)).toBeInTheDocument();
  });

  it('shows Max button for Sell that fills shares owned', async () => {
    render(<TradeForm {...baseProps} ownedShares="10" />);
    await userEvent.click(screen.getByRole('radio', { name: /sell/i }));
    await userEvent.click(screen.getByRole('button', { name: /max/i }));
    expect(screen.getByLabelText(/number of shares/i)).toHaveValue(10);
  });

  it('displays submitError when present', () => {
    render(<TradeForm {...baseProps} submitError="Insufficient virtual cash" />);
    expect(screen.getByText(/insufficient virtual cash/i)).toBeInTheDocument();
  });
});
