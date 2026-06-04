import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CurrencySelector } from '../CurrencySelector';
import { authApi } from '@/api/auth';

vi.mock('@/api/auth', async (orig) => {
  const actual = await orig<typeof import('@/api/auth')>();
  return { ...actual, authApi: { ...actual.authApi, updatePreferences: vi.fn().mockResolvedValue({}) } };
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('CurrencySelector', () => {
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

  it('calls updatePreferences with currency_code on change', async () => {
    wrap(<CurrencySelector currentCurrency="USD" />);
    await userEvent.selectOptions(screen.getByLabelText(/practice currency/i), 'HKD');
    expect(authApi.updatePreferences).toHaveBeenCalledWith({ currency_code: 'HKD' });
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<CurrencySelector currentCurrency="USD" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
