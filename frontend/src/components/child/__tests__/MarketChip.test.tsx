import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('../../../hooks/useMarkets', () => ({
  useMarkets: () => ({ data: [{ code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true }] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { MarketChip } from '../MarketChip';

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

describe('MarketChip', () => {
  it('shows the active market name and links to the picker', () => {
    render(wrap(<MarketChip activeCode="GB" />));
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /change learning market|united kingdom/i })).toHaveAttribute('href', '/markets');
  });
  it('has no a11y violations', async () => {
    const { container } = render(wrap(<MarketChip activeCode="GB" />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
