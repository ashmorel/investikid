import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const switchMock = vi.fn().mockResolvedValue({ active_market_code: 'US' });
vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: false, is_selected: false },
  ] }),
  useSwitchMarket: () => ({ mutate: switchMock, isPending: false }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { Markets } from '../Markets';

function wrap() {
  return <QueryClientProvider client={new QueryClient()}><MemoryRouter><Markets /></MemoryRouter></QueryClientProvider>;
}

describe('Markets picker', () => {
  it('lists all markets; selected shows Learning, empty shows Coming soon, both tappable', () => {
    render(wrap());
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
    expect(screen.getByText('picker.learning')).toBeInTheDocument();      // GB selected
    expect(screen.getByText('picker.comingSoon')).toBeInTheDocument();    // US coming soon
  });
  it('tapping a market switches to it', () => {
    render(wrap());
    fireEvent.click(screen.getByText('United States'));
    expect(switchMock).toHaveBeenCalledWith('US', expect.objectContaining({ onSuccess: expect.any(Function) }));
  });
});
