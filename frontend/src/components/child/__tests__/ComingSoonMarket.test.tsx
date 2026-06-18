import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

const switchMock = vi.fn();
vi.mock('../../../hooks/useMarkets', () => ({
  useSwitchMarket: () => ({ mutate: switchMock, isPending: false }),
  useMarkets: () => ({ data: [
    { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: false },
    { code: 'US', name: 'United States', currency_code: 'USD', has_content: false, enrolled: true, is_selected: true },
  ] }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, string>) => (o ? `${k} ${JSON.stringify(o)}` : k) }) }));

import { ComingSoonMarket } from '../ComingSoonMarket';

describe('ComingSoonMarket', () => {
  it('switch-back CTA targets the content-ready (GB) market', () => {
    render(<ComingSoonMarket marketName="United States" />);
    fireEvent.click(screen.getByRole('button', { name: /switchBack/i }));
    expect(switchMock).toHaveBeenCalledWith('GB');
  });
  it('has no a11y violations', async () => {
    const { container } = render(<ComingSoonMarket marketName="United States" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
