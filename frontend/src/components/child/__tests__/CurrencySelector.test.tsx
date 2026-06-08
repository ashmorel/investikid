import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { simulatorApi } from '@/api/simulator';
import { CurrencySelector } from '../CurrencySelector';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    setCurrency: vi.fn(() =>
      Promise.resolve({ id: '1', virtual_cash: '787.40', currency_code: 'GBP' }),
    ),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('CurrencySelector', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lists current + major currencies deduped', () => {
    wrap(<CurrencySelector currentCurrency="USD" />);
    const select = screen.getByLabelText(/practice currency/i) as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['USD', 'GBP', 'HKD']); // USD deduped
  });

  it('keeps a non-major current currency in the list', () => {
    wrap(<CurrencySelector currentCurrency="EUR" />);
    const select = screen.getByLabelText(/practice currency/i) as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['EUR', 'USD', 'GBP', 'HKD']);
  });

  it('calls simulatorApi.setCurrency on change', async () => {
    wrap(<CurrencySelector currentCurrency="USD" />);
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: /practice currency/i }),
      'GBP',
    );
    await waitFor(() =>
      expect(vi.mocked(simulatorApi.setCurrency)).toHaveBeenCalledWith('GBP'),
    );
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<CurrencySelector currentCurrency="USD" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
