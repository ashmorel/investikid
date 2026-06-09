import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ModuleCard } from '../ModuleCard';
import type { ModuleOut } from '@/api/content';

const base: ModuleOut = {
  id: 'm1', topic: 'savings', title: 'Saving', country_codes: ['US'],
  is_premium: false, order_index: 0, icon: '💰', locked: false,
};

function renderCard(module: ModuleOut, onLockedClick = () => {}) {
  return render(
    <MemoryRouter>
      <ModuleCard module={module} completedCount={0} totalCount={4} onLockedClick={onLockedClick} />
    </MemoryRouter>,
  );
}

describe('ModuleCard', () => {
  it('premium-locked module shows the PremiumBadge and a teaser', () => {
    renderCard({ ...base, is_premium: true, locked: true });
    expect(screen.getByText('Premium')).toBeInTheDocument();
    expect(screen.getByText(/unlock to continue/i)).toBeInTheDocument();
  });

  it('premium-locked module calls onLockedClick when tapped', () => {
    const onLockedClick = vi.fn();
    renderCard({ ...base, is_premium: true, locked: true }, onLockedClick);
    fireEvent.click(screen.getByRole('button'));
    expect(onLockedClick).toHaveBeenCalled();
  });

  it('free/unlocked module shows no PremiumBadge', () => {
    renderCard(base);
    expect(screen.queryByText('Premium')).not.toBeInTheDocument();
  });
});
