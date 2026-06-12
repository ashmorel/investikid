import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';

const open = vi.fn();
vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open }) }));
vi.mock('@/lib/premiumNudge', () => ({
  isNudgeDismissed: vi.fn(() => false),
  dismissNudge: vi.fn(),
}));
import { isNudgeDismissed, dismissNudge } from '@/lib/premiumNudge';
import { PremiumUpsellCard } from '../PremiumUpsellCard';

beforeEach(() => { vi.clearAllMocks(); vi.mocked(isNudgeDismissed).mockReturnValue(false); });

describe('PremiumUpsellCard', () => {
  it('hidden for premium users', () => {
    const { container } = render(<PremiumUpsellCard isPremium />);
    expect(container).toBeEmptyDOMElement();
  });
  it('hidden when dismissed', () => {
    vi.mocked(isNudgeDismissed).mockReturnValue(true);
    const { container } = render(<PremiumUpsellCard isPremium={false} />);
    expect(container).toBeEmptyDOMElement();
  });
  it('renders a single-line upsell with paywall CTA', () => {
    render(<PremiumUpsellCard isPremium={false} />);
    expect(screen.getByText(/unlock all levels & the ai coach/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ask my grown-up/i })).toBeInTheDocument();
  });
  it('shows for non-premium and asks via the paywall', async () => {
    render(<PremiumUpsellCard isPremium={false} />);
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    expect(open).toHaveBeenCalledWith({ kind: 'home', label: 'Premium' });
  });
  it('dismiss hides the card and persists', async () => {
    render(<PremiumUpsellCard isPremium={false} />);
    await userEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(dismissNudge).toHaveBeenCalledWith('home-upsell');
    expect(screen.queryByText(/unlock all levels/i)).toBeNull();
  });
  it('no axe violations', async () => {
    const { container } = render(<PremiumUpsellCard isPremium={false} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
