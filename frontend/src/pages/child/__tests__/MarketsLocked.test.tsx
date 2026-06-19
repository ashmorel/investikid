import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true, locked: false },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: true, enrolled: false, is_selected: false, locked: true },
  ] }),
  useSwitchMarket: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { Markets } from '../Markets';

function wrap() {
  return <QueryClientProvider client={new QueryClient()}><MemoryRouter><Markets /></MemoryRouter></QueryClientProvider>;
}

describe('Markets picker — locked markets', () => {
  it('shows a Premium chip on a locked market and not on the unlocked/selected one', () => {
    render(wrap());

    // The locked US card carries the Premium chip.
    const usCard = screen.getByText('United States').closest('button')!;
    expect(within(usCard).getByText('picker.premium')).toBeInTheDocument();

    // The unlocked, selected GB card does not — it shows Learning instead.
    const gbCard = screen.getByText('United Kingdom').closest('button')!;
    expect(within(gbCard).queryByText('picker.premium')).toBeNull();
    expect(within(gbCard).getByText('picker.learning')).toBeInTheDocument();
  });
});
