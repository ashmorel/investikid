import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../../hooks/useMarkets', () => ({
  useMarketProgress: () => ({ data: { markets: [{ market_code: 'GB', xp: 110 }, { market_code: 'US', xp: 20 }], total_xp: 130, level: 2 } }),
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: true, is_selected: false },
  ] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

import { MarketXpBreakdown } from '../../../components/child/MarketXpBreakdown';

describe('MarketXpBreakdown', () => {
  it('lists per-market XP with market names', () => {
    render(<MarketXpBreakdown />);
    expect(screen.getByText('United Kingdom')).toBeInTheDocument();
    expect(screen.getByText('110')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });
});
